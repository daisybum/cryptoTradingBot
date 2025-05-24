#!/usr/bin/env python3
"""
워크포워드 분석 스크립트

이 스크립트는 워크포워드 테스팅을 통해 전략의 견고성을 검증합니다.
과적합을 방지하고 실제 트레이딩 환경에서의 성능을 예측하는 데 도움이 됩니다.
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta

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

class WalkForwardAnalyzer:
    """워크포워드 분석 클래스"""
    
    def __init__(self, config_path: str, data_dir: str, results_dir: str):
        """
        워크포워드 분석 초기화
        
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
    
    def run_walk_forward_analysis(self, strategy: str, start_date: str, end_date: str,
                                in_sample_days: int = 90, out_sample_days: int = 30,
                                step_days: int = 30, optimize_epochs: int = 50,
                                optimize_spaces: Optional[List[str]] = None,
                                max_open_trades: int = 5) -> Dict[str, Any]:
        """
        워크포워드 분석 실행
        
        Args:
            strategy: 전략 이름
            start_date: 시작 날짜 (YYYYMMDD 형식)
            end_date: 종료 날짜 (YYYYMMDD 형식)
            in_sample_days: 최적화(학습) 기간 (일)
            out_sample_days: 테스트 기간 (일)
            step_days: 창 이동 간격 (일)
            optimize_epochs: 최적화 반복 횟수
            optimize_spaces: 최적화할 공간 (예: ['buy', 'sell'])
            max_open_trades: 최대 동시 거래 수
            
        Returns:
            Dict[str, Any]: 워크포워드 분석 결과
        """
        logger.info(f"워크포워드 분석 시작: {strategy}")
        
        # 날짜 변환
        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')
        
        # 결과 저장 디렉토리
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wf_dir = os.path.join(self.results_dir, f"{strategy}_walkforward_{timestamp}")
        os.makedirs(wf_dir, exist_ok=True)
        
        # 창 생성
        windows = []
        current_start = start
        
        while current_start + timedelta(days=in_sample_days + out_sample_days) <= end:
            # 최적화 기간 계산
            optimize_end = current_start + timedelta(days=in_sample_days)
            optimize_timerange = f"{current_start.strftime('%Y%m%d')}-{optimize_end.strftime('%Y%m%d')}"
            
            # 테스트 기간 계산
            test_start = optimize_end
            test_end = min(test_start + timedelta(days=out_sample_days), end)
            test_timerange = f"{test_start.strftime('%Y%m%d')}-{test_end.strftime('%Y%m%d')}"
            
            window = {
                'window_id': len(windows) + 1,
                'optimize_period': optimize_timerange,
                'test_period': test_timerange,
                'optimize_start': current_start.strftime('%Y%m%d'),
                'optimize_end': optimize_end.strftime('%Y%m%d'),
                'test_start': test_start.strftime('%Y%m%d'),
                'test_end': test_end.strftime('%Y%m%d')
            }
            
            windows.append(window)
            
            # 다음 창으로 이동
            current_start += timedelta(days=step_days)
        
        logger.info(f"총 {len(windows)}개의 워크포워드 창 생성됨")
        
        # 각 창에 대해 최적화 및 테스트 실행
        for i, window in enumerate(windows):
            logger.info(f"창 {window['window_id']} 처리 중 ({i+1}/{len(windows)})")
            
            # 1. 최적화 실행
            logger.info(f"최적화 기간: {window['optimize_period']}")
            hyperopt_results = self.backtesting.run_hyperopt(
                strategy=strategy,
                epochs=optimize_epochs,
                spaces=optimize_spaces,
                timerange=window['optimize_period'],
                max_open_trades=max_open_trades
            )
            
            if not hyperopt_results:
                logger.warning(f"창 {window['window_id']} 최적화 실패")
                continue
            
            # 최적 매개변수 추출
            best_params = hyperopt_results.get('best_params', {})
            
            # 매개변수 저장
            params_file = os.path.join(wf_dir, f"window_{window['window_id']}_params.json")
            with open(params_file, 'w') as f:
                json.dump(best_params, f, indent=4)
            
            window['best_params'] = best_params
            window['optimize_results'] = hyperopt_results
            
            # 2. 테스트 실행
            logger.info(f"테스트 기간: {window['test_period']}")
            backtest_results = self.backtesting.run_backtest(
                strategy=strategy,
                timerange=window['test_period'],
                parameter_file=params_file,
                max_open_trades=max_open_trades
            )
            
            if not backtest_results:
                logger.warning(f"창 {window['window_id']} 테스트 실패")
                continue
            
            window['test_results'] = backtest_results
            
            # 결과 시각화
            self.visualizer.create_performance_report(
                backtest_results,
                f"{strategy}_Window{window['window_id']}",
                os.path.join(wf_dir, f"window_{window['window_id']}")
            )
        
        # 종합 결과 계산
        valid_windows = [w for w in windows if 'test_results' in w]
        
        if not valid_windows:
            logger.error("유효한 워크포워드 결과가 없습니다")
            return {'error': '유효한 워크포워드 결과가 없습니다', 'windows': windows}
        
        # 종합 지표 계산
        total_trades = sum(w['test_results'].get('total_trades', 0) for w in valid_windows)
        total_win_trades = sum(w['test_results'].get('win_trades', 0) for w in valid_windows)
        total_profit = sum(w['test_results'].get('total_profit', 0) for w in valid_windows) / len(valid_windows)
        max_drawdown = max(abs(w['test_results'].get('max_drawdown', 0)) for w in valid_windows)
        
        win_rate = (total_win_trades / total_trades * 100) if total_trades > 0 else 0
        
        # 종합 결과
        overall_results = {
            'windows': windows,
            'valid_windows': len(valid_windows),
            'total_windows': len(windows),
            'total_trades': total_trades,
            'win_trades': total_win_trades,
            'win_rate': win_rate,
            'overall_profit': total_profit,
            'max_drawdown': max_drawdown,
            'in_sample_days': in_sample_days,
            'out_sample_days': out_sample_days,
            'step_days': step_days
        }
        
        # 결과 저장
        results_file = os.path.join(wf_dir, "walkforward_results.json")
        with open(results_file, 'w') as f:
            # windows에서 큰 데이터 제거 (JSON 직렬화 가능하도록)
            save_windows = []
            for window in windows:
                save_window = {k: v for k, v in window.items() 
                             if k not in ['optimize_results', 'test_results']}
                
                # 테스트 결과 요약 추가
                if 'test_results' in window:
                    save_window['test_summary'] = {
                        'total_trades': window['test_results'].get('total_trades', 0),
                        'win_pct': window['test_results'].get('win_pct', 0),
                        'total_profit': window['test_results'].get('total_profit', 0),
                        'max_drawdown': window['test_results'].get('max_drawdown', 0)
                    }
                
                save_windows.append(save_window)
            
            save_results = {**overall_results, 'windows': save_windows}
            json.dump(save_results, f, indent=4)
        
        # 결과 시각화
        self._create_walkforward_charts(valid_windows, strategy, wf_dir)
        
        logger.info(f"워크포워드 분석 완료: {wf_dir}")
        logger.info(f"총 거래 수: {total_trades}")
        logger.info(f"승률: {win_rate:.2f}%")
        logger.info(f"평균 수익: {total_profit:.2f}%")
        logger.info(f"최대 드로다운: {max_drawdown:.2f}%")
        
        return overall_results
    
    def _create_walkforward_charts(self, windows: List[Dict[str, Any]], 
                                 strategy: str, output_dir: str) -> None:
        """
        워크포워드 분석 차트 생성
        
        Args:
            windows: 워크포워드 창 목록
            strategy: 전략 이름
            output_dir: 출력 디렉토리
        """
        if not windows:
            return
        
        # 1. 창별 수익률 차트
        plt.figure(figsize=(12, 6))
        
        window_ids = [w['window_id'] for w in windows]
        profits = [w['test_results'].get('total_profit', 0) for w in windows]
        
        bars = plt.bar(window_ids, profits, alpha=0.7)
        
        # 막대 색상 설정 (양수: 녹색, 음수: 빨간색)
        for i, profit in enumerate(profits):
            bars[i].set_color('green' if profit > 0 else 'red')
        
        plt.title(f'{strategy} - 워크포워드 창별 수익률', fontsize=16)
        plt.xlabel('창 ID', fontsize=12)
        plt.ylabel('수익률 (%)', fontsize=12)
        plt.grid(True, alpha=0.3, axis='y')
        
        # 수익률 값 표시
        for i, v in enumerate(profits):
            plt.text(i + 1, v + (1 if v >= 0 else -1), f"{v:.2f}%", 
                    ha='center', va='center' if v >= 0 else 'top', 
                    fontweight='bold')
        
        # 평균 수익률 선 추가
        avg_profit = sum(profits) / len(profits)
        plt.axhline(y=avg_profit, color='blue', linestyle='--', 
                   label=f'평균 수익률: {avg_profit:.2f}%')
        
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "window_profits.png"), dpi=300)
        plt.close()
        
        # 2. 누적 수익률 곡선
        plt.figure(figsize=(12, 6))
        
        # 각 창의 테스트 기간에 대한 거래 데이터 수집
        all_trades = []
        
        for window in windows:
            if 'test_results' not in window or 'trades' not in window['test_results']:
                continue
            
            trades = window['test_results']['trades']
            
            # 거래 데이터를 DataFrame으로 변환
            df = pd.DataFrame(trades)
            
            if df.empty:
                continue
            
            # 창 ID 추가
            df['window_id'] = window['window_id']
            
            # 거래 추가
            all_trades.append(df)
        
        if not all_trades:
            logger.warning("누적 수익률 곡선을 그릴 거래 데이터가 없습니다")
            return
        
        # 모든 거래 데이터 결합
        trades_df = pd.concat(all_trades)
        
        # 날짜 형식 변환
        if 'close_date' in trades_df.columns:
            trades_df['close_date'] = pd.to_datetime(trades_df['close_date'])
            trades_df = trades_df.sort_values('close_date')
        
        # 누적 수익 계산
        if 'profit_percent' in trades_df.columns:
            trades_df['profit'] = trades_df['profit_percent'] / 100
        elif 'profit_ratio' in trades_df.columns:
            trades_df['profit'] = trades_df['profit_ratio']
        else:
            logger.warning("누적 수익률을 계산할 수 없습니다")
            return
        
        trades_df['cumulative_profit'] = (1 + trades_df['profit']).cumprod() - 1
        
        # 누적 수익률 곡선 그리기
        plt.plot(trades_df['close_date'], trades_df['cumulative_profit'] * 100, 'b-', linewidth=2)
        
        # 창 경계 표시
        for window in windows:
            if 'test_start' in window and 'test_end' in window:
                test_start = datetime.strptime(window['test_start'], '%Y%m%d')
                plt.axvline(x=test_start, color='r', linestyle='--', alpha=0.5)
                
                # 창 ID 표시
                y_pos = max(0, min(trades_df['cumulative_profit']) * 100)
                plt.text(test_start, y_pos, f" W{window['window_id']}", 
                        rotation=90, verticalalignment='bottom')
        
        plt.title(f'{strategy} - 워크포워드 누적 수익률', fontsize=16)
        plt.xlabel('날짜', fontsize=12)
        plt.ylabel('누적 수익률 (%)', fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # x축 날짜 포맷 설정
        plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))
        plt.gcf().autofmt_xdate()
        
        # 0선 표시
        plt.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "cumulative_profit.png"), dpi=300)
        plt.close()
        
        # 3. 매개변수 안정성 분석
        common_params = set()
        
        # 모든 창에 공통적으로 있는 매개변수 찾기
        for window in windows:
            if 'best_params' not in window:
                continue
                
            if not common_params:
                common_params = set(window['best_params'].keys())
            else:
                common_params &= set(window['best_params'].keys())
        
        if not common_params:
            logger.warning("매개변수 안정성을 분석할 공통 매개변수가 없습니다")
            return
        
        # 각 매개변수에 대한 변화 추적
        for param in common_params:
            # 숫자형 매개변수만 분석
            param_values = [window['best_params'][param] for window in windows if 'best_params' in window]
            
            if not all(isinstance(v, (int, float)) for v in param_values):
                continue
            
            plt.figure(figsize=(12, 6))
            
            # 매개변수 값 변화 그래프
            plt.plot(window_ids, param_values, 'o-', linewidth=2)
            
            plt.title(f'{strategy} - {param} 매개변수 변화', fontsize=16)
            plt.xlabel('창 ID', fontsize=12)
            plt.ylabel(param, fontsize=12)
            plt.grid(True, alpha=0.3)
            
            # 평균값 선 추가
            avg_value = sum(param_values) / len(param_values)
            plt.axhline(y=avg_value, color='r', linestyle='--', 
                       label=f'평균: {avg_value:.4f}')
            
            # 표준편차 범위 추가
            std_value = np.std(param_values)
            plt.axhline(y=avg_value + std_value, color='g', linestyle=':', 
                       label=f'표준편차: {std_value:.4f}')
            plt.axhline(y=avg_value - std_value, color='g', linestyle=':')
            
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"param_{param}.png"), dpi=300)
            plt.close()
        
        # 4. 요약 보고서 생성
        self._create_summary_report(windows, strategy, output_dir)
    
    def _create_summary_report(self, windows: List[Dict[str, Any]], 
                             strategy: str, output_dir: str) -> None:
        """
        워크포워드 분석 요약 보고서 생성
        
        Args:
            windows: 워크포워드 창 목록
            strategy: 전략 이름
            output_dir: 출력 디렉토리
        """
        summary_path = os.path.join(output_dir, "summary.txt")
        
        with open(summary_path, 'w') as f:
            f.write(f"=== {strategy} 워크포워드 분석 요약 보고서 ===\n")
            f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 전체 성능 요약
            total_trades = sum(w['test_results'].get('total_trades', 0) for w in windows)
            total_win_trades = sum(w['test_results'].get('win_trades', 0) for w in windows)
            avg_profit = sum(w['test_results'].get('total_profit', 0) for w in windows) / len(windows)
            max_drawdown = max(abs(w['test_results'].get('max_drawdown', 0)) for w in windows)
            
            win_rate = (total_win_trades / total_trades * 100) if total_trades > 0 else 0
            
            f.write("=== 전체 성능 요약 ===\n")
            f.write(f"총 창 수: {len(windows)}\n")
            f.write(f"총 거래 수: {total_trades}\n")
            f.write(f"승리 거래: {total_win_trades}\n")
            f.write(f"승률: {win_rate:.2f}%\n")
            f.write(f"평균 수익: {avg_profit:.2f}%\n")
            f.write(f"최대 드로다운: {max_drawdown:.2f}%\n\n")
            
            # 각 창별 성능
            f.write("=== 창별 성능 ===\n")
            
            for window in windows:
                window_id = window['window_id']
                test_period = window['test_period']
                total_trades = window['test_results'].get('total_trades', 0)
                win_pct = window['test_results'].get('win_pct', 0)
                total_profit = window['test_results'].get('total_profit', 0)
                max_drawdown = window['test_results'].get('max_drawdown', 0)
                
                f.write(f"창 {window_id} ({test_period}):\n")
                f.write(f"  거래 수: {total_trades}\n")
                f.write(f"  승률: {win_pct:.2f}%\n")
                f.write(f"  수익: {total_profit:.2f}%\n")
                f.write(f"  최대 드로다운: {max_drawdown:.2f}%\n\n")
            
            # 매개변수 안정성 분석
            common_params = set()
            
            # 모든 창에 공통적으로 있는 매개변수 찾기
            for window in windows:
                if 'best_params' not in window:
                    continue
                    
                if not common_params:
                    common_params = set(window['best_params'].keys())
                else:
                    common_params &= set(window['best_params'].keys())
            
            if common_params:
                f.write("=== 매개변수 안정성 분석 ===\n")
                
                for param in common_params:
                    param_values = [window['best_params'][param] for window in windows if 'best_params' in window]
                    
                    if all(isinstance(v, (int, float)) for v in param_values):
                        avg_value = sum(param_values) / len(param_values)
                        std_value = np.std(param_values)
                        cv = (std_value / avg_value) * 100 if avg_value != 0 else float('inf')
                        
                        f.write(f"{param}:\n")
                        f.write(f"  평균: {avg_value:.4f}\n")
                        f.write(f"  표준편차: {std_value:.4f}\n")
                        f.write(f"  변동계수: {cv:.2f}%\n")
                        f.write(f"  범위: {min(param_values)} - {max(param_values)}\n\n")
            
            f.write("=== 보고서 파일 목록 ===\n")
            f.write("window_profits.png - 창별 수익률 차트\n")
            f.write("cumulative_profit.png - 누적 수익률 곡선\n")
            f.write("param_*.png - 매개변수 안정성 차트\n")
            f.write("walkforward_results.json - 워크포워드 결과 JSON\n")

def main():
    """워크포워드 분석 예제 실행"""
    # 설정 경로
    config_path = os.path.join(project_root, 'config', 'freqtrade.json')
    data_dir = os.path.join(project_root, 'data')
    results_dir = os.path.join(project_root, 'results', 'walkforward')
    
    # 디렉토리 생성
    os.makedirs(results_dir, exist_ok=True)
    
    # 워크포워드 분석 초기화
    analyzer = WalkForwardAnalyzer(
        config_path=config_path,
        data_dir=data_dir,
        results_dir=results_dir
    )
    
    # 워크포워드 분석 실행
    analyzer.run_walk_forward_analysis(
        strategy='NASOSv5_mod3',
        start_date='20220101',
        end_date='20221231',
        in_sample_days=60,  # 60일 최적화 기간
        out_sample_days=30,  # 30일 테스트 기간
        step_days=30,        # 30일마다 창 이동
        optimize_epochs=30,  # 최적화 반복 횟수
        optimize_spaces=['buy', 'sell'],  # 최적화 공간
        max_open_trades=5
    )
    
    logger.info("워크포워드 분석 예제 실행 완료")

if __name__ == "__main__":
    main()
