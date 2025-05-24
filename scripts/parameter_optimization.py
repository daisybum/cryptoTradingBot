#!/usr/bin/env python3
"""
전략 매개변수 최적화 스크립트

이 스크립트는 그리드 서치를 통해 전략 매개변수를 최적화하고 결과를 분석합니다.
"""

import os
import sys
import json
import logging
import itertools
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

# 프로젝트 루트 경로 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.strategy_engine.backtesting import BacktestingFramework
from src.strategy_engine.visualization import BacktestVisualizer

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ParameterOptimizer:
    """전략 매개변수 최적화 클래스"""
    
    def __init__(self, config_path: str, data_dir: str, results_dir: str):
        """
        매개변수 최적화 초기화
        
        Args:
            config_path: Freqtrade 설정 파일 경로
            data_dir: 데이터 디렉토리
            results_dir: 결과 저장 디렉토리
        """
        self.config_path = config_path
        self.data_dir = data_dir
        self.results_dir = results_dir
        
        # 디렉토리 생성
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(results_dir, exist_ok=True)
        
        # 백테스팅 프레임워크 초기화
        self.backtesting = BacktestingFramework(
            config_path=config_path,
            data_dir=data_dir
        )
        
        # 시각화 도구 초기화
        self.visualizer = BacktestVisualizer(results_dir)
    
    def grid_search(self, strategy: str, param_grid: Dict[str, List[Any]], 
                  timerange: str, stake_amount: float = 100, max_open_trades: int = 5) -> pd.DataFrame:
        """
        그리드 서치를 통한 매개변수 최적화
        
        Args:
            strategy: 전략 이름
            param_grid: 매개변수 그리드 (딕셔너리 형태의 매개변수 이름과 값 목록)
            timerange: 백테스트 시간 범위 (YYYYMMDD-YYYYMMDD 형식)
            stake_amount: 거래당 주문 금액
            max_open_trades: 최대 동시 거래 수
            
        Returns:
            pd.DataFrame: 최적화 결과 데이터프레임
        """
        # 매개변수 조합 생성
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(itertools.product(*param_values))
        
        logger.info(f"총 {len(param_combinations)}개의 매개변수 조합으로 그리드 서치 시작")
        
        # 결과 저장 리스트
        results = []
        
        # 각 매개변수 조합에 대해 백테스트 실행
        for i, combination in enumerate(param_combinations):
            # 매개변수 딕셔너리 생성
            params = {name: value for name, value in zip(param_names, combination)}
            
            # 진행 상황 로깅
            logger.info(f"조합 {i+1}/{len(param_combinations)} 테스트 중: {params}")
            
            # 매개변수 파일 생성
            param_file = os.path.join(self.results_dir, "temp_params.json")
            with open(param_file, 'w') as f:
                json.dump(params, f, indent=4)
            
            # 백테스트 실행
            backtest_results = self.backtesting.run_backtest(
                strategy=strategy,
                timerange=timerange,
                parameter_file=param_file,
                stake_amount=stake_amount,
                max_open_trades=max_open_trades
            )
            
            if not backtest_results:
                logger.warning(f"매개변수 조합 {params}에 대한 백테스트 실패")
                continue
            
            # 주요 지표 추출
            total_trades = backtest_results.get('total_trades', 0)
            win_pct = backtest_results.get('win_pct', 0)
            total_profit = backtest_results.get('total_profit', 0)
            max_drawdown = backtest_results.get('max_drawdown', 0)
            profit_factor = backtest_results.get('profit_factor', 0)
            
            # 결과 저장
            result = {
                'params': params,
                'total_trades': total_trades,
                'win_pct': win_pct,
                'total_profit': total_profit,
                'max_drawdown': max_drawdown,
                'profit_factor': profit_factor
            }
            
            results.append(result)
            
            # 임시 매개변수 파일 삭제
            if os.path.exists(param_file):
                os.remove(param_file)
        
        # 결과를 데이터프레임으로 변환
        if not results:
            logger.error("그리드 서치 결과가 없습니다")
            return pd.DataFrame()
        
        # 결과 데이터프레임 생성
        df_results = pd.DataFrame(results)
        
        # 매개변수 열 추가
        for param_name in param_names:
            df_results[param_name] = df_results['params'].apply(lambda x: x.get(param_name))
        
        # params 열 제거
        df_results = df_results.drop('params', axis=1)
        
        # 수익률로 정렬
        df_results = df_results.sort_values('total_profit', ascending=False)
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(self.results_dir, f"{strategy}_grid_search_{timestamp}.csv")
        df_results.to_csv(results_file, index=False)
        
        logger.info(f"그리드 서치 결과 저장됨: {results_file}")
        
        return df_results
    
    def analyze_parameter_impact(self, grid_results: pd.DataFrame, 
                               param_names: List[str], metric: str = 'total_profit') -> None:
        """
        매개변수가 성능에 미치는 영향 분석
        
        Args:
            grid_results: 그리드 서치 결과 데이터프레임
            param_names: 분석할 매개변수 이름 목록
            metric: 분석할 성능 지표 (total_profit, win_pct, max_drawdown 등)
        """
        if grid_results.empty:
            logger.error("분석할 그리드 서치 결과가 없습니다")
            return
        
        # 결과 디렉토리 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_dir = os.path.join(self.results_dir, f"param_analysis_{timestamp}")
        os.makedirs(analysis_dir, exist_ok=True)
        
        # 각 매개변수에 대한 영향 분석
        for param_name in param_names:
            if param_name not in grid_results.columns:
                logger.warning(f"매개변수 {param_name}이 결과에 없습니다")
                continue
            
            # 매개변수 값이 숫자인지 확인
            if pd.api.types.is_numeric_dtype(grid_results[param_name]):
                # 산점도 그래프 생성
                plt.figure(figsize=(10, 6))
                plt.scatter(grid_results[param_name], grid_results[metric], alpha=0.7)
                plt.title(f"{param_name}이 {metric}에 미치는 영향")
                plt.xlabel(param_name)
                plt.ylabel(metric)
                plt.grid(True, alpha=0.3)
                
                # 추세선 추가
                try:
                    z = np.polyfit(grid_results[param_name], grid_results[metric], 1)
                    p = np.poly1d(z)
                    plt.plot(grid_results[param_name], p(grid_results[param_name]), "r--", alpha=0.7)
                except:
                    logger.warning(f"{param_name}에 대한 추세선 생성 실패")
                
                # 저장
                plt.tight_layout()
                plt.savefig(os.path.join(analysis_dir, f"{param_name}_{metric}_scatter.png"), dpi=300)
                plt.close()
            
            # 박스플롯 생성 (범주형 또는 숫자형 모두 가능)
            plt.figure(figsize=(12, 6))
            grid_results.boxplot(column=metric, by=param_name, grid=False)
            plt.title(f"{param_name}에 따른 {metric} 분포")
            plt.suptitle("")  # 기본 제목 제거
            plt.xlabel(param_name)
            plt.ylabel(metric)
            plt.grid(True, alpha=0.3, axis='y')
            
            # x축 레이블 회전 (값이 많은 경우)
            if len(grid_results[param_name].unique()) > 5:
                plt.xticks(rotation=45)
            
            # 저장
            plt.tight_layout()
            plt.savefig(os.path.join(analysis_dir, f"{param_name}_{metric}_box.png"), dpi=300)
            plt.close()
        
        # 매개변수 쌍 간의 상호작용 분석 (최대 3쌍까지)
        if len(param_names) >= 2:
            param_pairs = list(itertools.combinations(param_names, 2))[:3]
            
            for param1, param2 in param_pairs:
                if param1 not in grid_results.columns or param2 not in grid_results.columns:
                    continue
                
                # 두 매개변수가 모두 숫자인 경우에만 히트맵 생성
                if (pd.api.types.is_numeric_dtype(grid_results[param1]) and 
                    pd.api.types.is_numeric_dtype(grid_results[param2])):
                    
                    # 피벗 테이블 생성
                    try:
                        pivot = grid_results.pivot_table(
                            values=metric,
                            index=param1,
                            columns=param2,
                            aggfunc='mean'
                        )
                        
                        # 히트맵 생성
                        plt.figure(figsize=(10, 8))
                        heatmap = plt.pcolor(pivot, cmap='viridis')
                        plt.colorbar(heatmap, label=metric)
                        
                        # 축 레이블 설정
                        plt.title(f"{param1}와 {param2}의 상호작용이 {metric}에 미치는 영향")
                        plt.xlabel(param2)
                        plt.ylabel(param1)
                        
                        # x축과 y축 값 설정
                        plt.xticks(np.arange(0.5, len(pivot.columns)), pivot.columns)
                        plt.yticks(np.arange(0.5, len(pivot.index)), pivot.index)
                        
                        # 저장
                        plt.tight_layout()
                        plt.savefig(os.path.join(analysis_dir, f"{param1}_{param2}_{metric}_heatmap.png"), dpi=300)
                        plt.close()
                    except:
                        logger.warning(f"{param1}와 {param2}에 대한 히트맵 생성 실패")
        
        logger.info(f"매개변수 영향 분석 완료: {analysis_dir}")
    
    def get_best_parameters(self, grid_results: pd.DataFrame, 
                          metric: str = 'total_profit', min_trades: int = 10) -> Dict[str, Any]:
        """
        최적 매개변수 추출
        
        Args:
            grid_results: 그리드 서치 결과 데이터프레임
            metric: 최적화 기준 지표 (total_profit, win_pct, max_drawdown 등)
            min_trades: 최소 거래 수
            
        Returns:
            Dict[str, Any]: 최적 매개변수 딕셔너리
        """
        if grid_results.empty:
            logger.error("최적 매개변수를 추출할 그리드 서치 결과가 없습니다")
            return {}
        
        # 최소 거래 수 필터링
        filtered_results = grid_results[grid_results['total_trades'] >= min_trades]
        
        if filtered_results.empty:
            logger.warning(f"최소 거래 수 {min_trades}를 만족하는 결과가 없습니다. 전체 결과에서 선택합니다.")
            filtered_results = grid_results
        
        # 지표에 따라 정렬
        if metric == 'max_drawdown':
            # 드로다운은 작을수록 좋음
            sorted_results = filtered_results.sort_values(metric, ascending=True)
        else:
            # 다른 지표는 클수록 좋음
            sorted_results = filtered_results.sort_values(metric, ascending=False)
        
        if sorted_results.empty:
            logger.error("정렬된 결과가 없습니다")
            return {}
        
        # 최적 결과 선택
        best_result = sorted_results.iloc[0]
        
        # 매개변수 추출
        param_columns = [col for col in sorted_results.columns 
                        if col not in ['total_trades', 'win_pct', 'total_profit', 
                                      'max_drawdown', 'profit_factor']]
        
        best_params = {param: best_result[param] for param in param_columns}
        
        # 결과 로깅
        logger.info(f"최적 매개변수 ({metric} 기준):")
        for param, value in best_params.items():
            logger.info(f"  {param}: {value}")
        
        logger.info(f"성능 지표:")
        logger.info(f"  총 거래 수: {best_result['total_trades']}")
        logger.info(f"  승률: {best_result['win_pct']:.2f}%")
        logger.info(f"  총 수익: {best_result['total_profit']:.2f}%")
        logger.info(f"  최대 드로다운: {best_result['max_drawdown']:.2f}%")
        logger.info(f"  수익 요소: {best_result['profit_factor']:.2f}")
        
        return best_params
    
    def save_best_parameters(self, best_params: Dict[str, Any], strategy: str) -> str:
        """
        최적 매개변수 저장
        
        Args:
            best_params: 최적 매개변수 딕셔너리
            strategy: 전략 이름
            
        Returns:
            str: 저장된 파일 경로
        """
        if not best_params:
            logger.error("저장할 최적 매개변수가 없습니다")
            return ""
        
        # 타임스탬프 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 파일 경로 생성
        params_dir = os.path.join(self.results_dir, "best_params")
        os.makedirs(params_dir, exist_ok=True)
        
        params_file = os.path.join(params_dir, f"{strategy}_best_params_{timestamp}.json")
        
        # 파일 저장
        with open(params_file, 'w') as f:
            json.dump(best_params, f, indent=4)
        
        logger.info(f"최적 매개변수 저장됨: {params_file}")
        
        return params_file
    
    def verify_best_parameters(self, strategy: str, best_params: Dict[str, Any], 
                             timerange: str, stake_amount: float = 100, 
                             max_open_trades: int = 5) -> Dict[str, Any]:
        """
        최적 매개변수 검증
        
        Args:
            strategy: 전략 이름
            best_params: 최적 매개변수 딕셔너리
            timerange: 백테스트 시간 범위 (YYYYMMDD-YYYYMMDD 형식)
            stake_amount: 거래당 주문 금액
            max_open_trades: 최대 동시 거래 수
            
        Returns:
            Dict[str, Any]: 백테스트 결과
        """
        if not best_params:
            logger.error("검증할 최적 매개변수가 없습니다")
            return {}
        
        logger.info(f"최적 매개변수 검증 시작: {strategy}")
        
        # 매개변수 파일 생성
        param_file = os.path.join(self.results_dir, "verify_params.json")
        with open(param_file, 'w') as f:
            json.dump(best_params, f, indent=4)
        
        # 백테스트 실행
        backtest_results = self.backtesting.run_backtest(
            strategy=strategy,
            timerange=timerange,
            parameter_file=param_file,
            stake_amount=stake_amount,
            max_open_trades=max_open_trades
        )
        
        # 임시 매개변수 파일 삭제
        if os.path.exists(param_file):
            os.remove(param_file)
        
        if not backtest_results:
            logger.error("최적 매개변수 검증 실패")
            return {}
        
        # 결과 요약 출력
        logger.info("최적 매개변수 검증 결과:")
        logger.info(f"총 거래 수: {backtest_results.get('total_trades', 0)}")
        logger.info(f"승률: {backtest_results.get('win_pct', 0):.2f}%")
        logger.info(f"총 수익: {backtest_results.get('total_profit', 0):.2f}%")
        logger.info(f"최대 드로다운: {backtest_results.get('max_drawdown', 0):.2f}%")
        
        # 결과 시각화
        self.visualizer.create_performance_report(
            backtest_results,
            f"{strategy}_Verified"
        )
        
        return backtest_results

def main():
    """매개변수 최적화 예제 실행"""
    # 설정 경로
    config_path = os.path.join(project_root, 'config', 'freqtrade.json')
    data_dir = os.path.join(project_root, 'data')
    results_dir = os.path.join(project_root, 'results', 'optimization')
    
    # 디렉토리 생성
    os.makedirs(results_dir, exist_ok=True)
    
    # 매개변수 최적화 초기화
    optimizer = ParameterOptimizer(
        config_path=config_path,
        data_dir=data_dir,
        results_dir=results_dir
    )
    
    # 전략 및 시간 범위 설정
    strategy = 'NASOSv5_mod3'
    timerange = '20220101-20220630'  # 최적화 기간
    verify_timerange = '20220701-20221231'  # 검증 기간
    
    # 매개변수 그리드 정의
    param_grid = {
        'buy_rsi': [25, 30, 35],
        'sell_rsi': [70, 75, 80],
        'buy_ema_length': [20, 50, 100],
        'sell_ema_length': [20, 50, 100],
        'stoploss': [-0.05, -0.1, -0.15]
    }
    
    # 그리드 서치 실행
    grid_results = optimizer.grid_search(
        strategy=strategy,
        param_grid=param_grid,
        timerange=timerange,
        stake_amount=100,
        max_open_trades=5
    )
    
    if grid_results.empty:
        logger.error("그리드 서치 실패")
        return
    
    # 매개변수 영향 분석
    optimizer.analyze_parameter_impact(
        grid_results=grid_results,
        param_names=list(param_grid.keys()),
        metric='total_profit'
    )
    
    # 최적 매개변수 추출
    best_params = optimizer.get_best_parameters(
        grid_results=grid_results,
        metric='total_profit',
        min_trades=10
    )
    
    if not best_params:
        logger.error("최적 매개변수 추출 실패")
        return
    
    # 최적 매개변수 저장
    params_file = optimizer.save_best_parameters(
        best_params=best_params,
        strategy=strategy
    )
    
    # 최적 매개변수 검증 (다른 기간에서)
    optimizer.verify_best_parameters(
        strategy=strategy,
        best_params=best_params,
        timerange=verify_timerange,
        stake_amount=100,
        max_open_trades=5
    )
    
    logger.info("매개변수 최적화 예제 실행 완료")

if __name__ == "__main__":
    main()
