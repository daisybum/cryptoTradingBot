#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
전략 로더 클래스

이 모듈은 트레이딩 전략을 동적으로 로드하는 기능을 제공합니다.
"""

import os
import sys
import importlib
import inspect
import logging
from typing import List, Dict, Any, Type, Optional
import glob

from src.utils.logging_config import setup_logging

# 로깅 설정
logger = logging.getLogger(__name__)
setup_logging()

class StrategyLoader:
    """
    트레이딩 전략 로더 클래스
    """
    
    def __init__(self, strategies_dir: Optional[str] = None):
        """
        StrategyLoader 초기화
        
        Args:
            strategies_dir (Optional[str]): 전략 파일이 위치한 디렉토리 경로
        """
        # 기본 전략 디렉토리 설정
        if strategies_dir is None:
            # 프로젝트 루트 디렉토리 기준 user_data/strategies 디렉토리
            self.strategies_dir = os.path.abspath(os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'user_data', 'strategies'
            ))
        else:
            self.strategies_dir = os.path.abspath(strategies_dir)
        
        # 전략 디렉토리가 존재하는지 확인
        if not os.path.exists(self.strategies_dir):
            logger.warning(f"Strategies directory not found: {self.strategies_dir}")
        
        # 전략 디렉토리를 Python 경로에 추가
        if self.strategies_dir not in sys.path:
            sys.path.insert(0, os.path.dirname(self.strategies_dir))
    
    def list_available_strategies(self) -> List[str]:
        """
        사용 가능한 전략 목록 조회
        
        Returns:
            List[str]: 사용 가능한 전략 이름 목록
        """
        strategies = []
        
        try:
            # 전략 디렉토리에서 Python 파일 찾기
            strategy_files = glob.glob(os.path.join(self.strategies_dir, "*.py"))
            
            for file_path in strategy_files:
                file_name = os.path.basename(file_path)
                
                # __init__.py 파일 제외
                if file_name == "__init__.py":
                    continue
                
                # 파일 이름에서 .py 확장자 제거
                module_name = file_name[:-3]
                
                try:
                    # 모듈 동적 로드
                    module = importlib.import_module(f"strategies.{module_name}")
                    
                    # 모듈에서 전략 클래스 찾기
                    for name, obj in inspect.getmembers(module):
                        # 클래스이고, 모듈에 정의된 클래스이며, 'Strategy'로 끝나는 이름인 경우
                        if (inspect.isclass(obj) and 
                            obj.__module__ == module.__name__ and 
                            (name.endswith('Strategy') or name.endswith('_strategy'))):
                            strategies.append(name)
                
                except (ImportError, AttributeError) as e:
                    logger.error(f"Failed to load strategy from {file_name}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error while listing available strategies: {str(e)}")
        
        return strategies
    
    def load_strategy(self, strategy_name: str) -> Type:
        """
        전략 클래스 로드
        
        Args:
            strategy_name (str): 로드할 전략 이름
        
        Returns:
            Type: 로드된 전략 클래스
        
        Raises:
            ImportError: 전략을 찾을 수 없는 경우
            AttributeError: 전략 클래스를 찾을 수 없는 경우
        """
        # 전략 디렉토리에서 Python 파일 찾기
        strategy_files = glob.glob(os.path.join(self.strategies_dir, "*.py"))
        
        for file_path in strategy_files:
            file_name = os.path.basename(file_path)
            
            # __init__.py 파일 제외
            if file_name == "__init__.py":
                continue
            
            # 파일 이름에서 .py 확장자 제거
            module_name = file_name[:-3]
            
            try:
                # 모듈 동적 로드
                module = importlib.import_module(f"strategies.{module_name}")
                
                # 모듈에서 전략 클래스 찾기
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        obj.__module__ == module.__name__ and 
                        name == strategy_name):
                        return obj
            
            except ImportError:
                continue
        
        # 전략을 찾지 못한 경우
        raise ImportError(f"Strategy '{strategy_name}' not found")
    
    def get_strategy_parameters(self, strategy_name: str) -> Dict[str, Any]:
        """
        전략 파라미터 조회
        
        Args:
            strategy_name (str): 전략 이름
        
        Returns:
            Dict[str, Any]: 전략 파라미터
        
        Raises:
            ImportError: 전략을 찾을 수 없는 경우
        """
        try:
            # 전략 클래스 로드
            strategy_class = self.load_strategy(strategy_name)
            
            # 전략 인스턴스 생성
            strategy_instance = strategy_class({})
            
            # 기본 파라미터 가져오기
            if hasattr(strategy_instance, 'default_params'):
                return strategy_instance.default_params
            else:
                # 기본 파라미터가 없는 경우, 클래스 속성 중 파라미터로 사용될 수 있는 것들 수집
                params = {}
                for attr_name in dir(strategy_instance):
                    if not attr_name.startswith('_') and not callable(getattr(strategy_instance, attr_name)):
                        attr_value = getattr(strategy_instance, attr_name)
                        if isinstance(attr_value, (int, float, str, bool)):
                            params[attr_name] = attr_value
                
                return params
        
        except Exception as e:
            logger.error(f"Failed to get strategy parameters: {str(e)}")
            return {}
