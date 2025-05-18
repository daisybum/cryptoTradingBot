#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
로깅 설정 모듈

이 모듈은 애플리케이션 전체에서 사용할 로깅 설정을 제공합니다.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(log_level=logging.INFO, log_file=None):
    """
    로깅 설정
    
    Args:
        log_level: 로그 레벨 (기본값: logging.INFO)
        log_file: 로그 파일 경로 (기본값: None)
    """
    # 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러 설정 (지정된 경우)
    if log_file:
        try:
            # 로그 디렉토리 생성
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 파일 핸들러 추가
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            logging.error(f"로그 파일 설정 중 오류 발생: {e}")
    
    return root_logger
