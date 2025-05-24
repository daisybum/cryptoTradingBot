#!/usr/bin/env python3
"""
전략 비교 스크립트

이 스크립트는 여러 트레이딩 전략을 백테스트하고 성능을 비교합니다.
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
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

class StrategyComparator:
    """전략 비교 클래스"""
    
    def __init__(self, config_path: str, data_dir: str, results_dir: str):
        """
        전략 비교 초기화
        
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
    
    def compare_strategies(self, strategies: List[Dict[str, Any]], timerange: str, 
                         stake_amount: float = 100, max_open_trades: int = 5) -> pd.DataFrame:
        """
        여러 전략 비교
        
        Args:
            strategies: 전략 목록 (각 전략은 'name'과 'params_file' 키를 포함하는 딕셔너리)
            timerange: 백테스트 시간 범위 (YYYYMMDD-YYYYMMDD 형식)
            stake_amount: 거래당 주문 금액
            max_open_trades: 최대 동시 거래 수
            
        Returns:
            pd.DataFrame: 비교 결과 데이터프레임
        """
        # 결과 저장 리스트
        results = []
        
        # 각 전략에 대해 백테스트 실행
        for strategy_info in strategies:
            strategy_name = strategy_info['name']
            params_file = strategy_info.get('params_file')
            
            logger.info(f"전략 '{strategy_name}' 백테스트 시작")
            
            # 백테스트 실행
            backtest_results = self.backtesting.run_backtest(
                strategy=strategy_name,
                timerange=timerange,
                parameter_file=params_file,
                stake_amount=stake_amount,
                max_open_trades=max_open_trades
            )
            
            if not backtest_results:
                logger.warning(f"전략 '{strategy_name}' 백테스트 실패")
                continue
            
            # 주요 지표 추출
            total_trades = backtest_results.get('total_trades', 0)
            win_pct = backtest_results.get('win_pct', 0)
            total_profit = backtest_results.get('total_profit', 0)
            max_drawdown = backtest_results.get('max_drawdown', 0)
            profit_factor = backtest_results.get('profit_factor', 0)
            
            # 결과 저장
            result = {
                'strategy': strategy_name,
                'params_file': params_file,
                'total_trades': total_trades,
                'win_pct': win_pct,
                'total_profit': total_profit,
                'max_drawdown': max_drawdown,
                'profit_factor': profit_factor,
                'results': backtest_results
            }
            
            results.append(result)
            
            # 결과 시각화
            self.visualizer.create_performance_report(
                backtest_results,
                strategy_name
            )
        
        # 결과를 데이터프레임으로 변환
        if not results:
            logger.error("비교 결과가 없습니다")
            return pd.DataFrame()
        
        # 결과 데이터프레임 생성 (results 열 제외)
        df_results = pd.DataFrame([{k: v for k, v in r.items() if k != 'results'} for r in results])
        
        # 수익률로 정렬
        df_results = df_results.sort_values('total_profit', ascending=False)
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(self.results_dir, f"strategy_comparison_{timestamp}.csv")
        df_results.to_csv(results_file, index=False)
        
        logger.info(f"전략 비교 결과 저장됨: {results_file}")
        
        # 비교 차트 생성
        self._create_comparison_charts(results, timestamp)
        
        return df_results
    
    def _create_comparison_charts(self, results: List[Dict[str, Any]], timestamp: str) -> None:
        """
        전략 비교 차트 생성
        
        Args:
            results: 전략 백테스트 결과 목록
            timestamp: 타임스탬프 문자열
        """
        if not results:
            return
        
        # 차트 저장 디렉토리
        charts_dir = os.path.join(self.results_dir, f"comparison_{timestamp}")
        os.makedirs(charts_dir, exist_ok=True)
        
        # 전략 이름 목록
        strategy_names = [r['strategy'] for r in results]
        
        # 1. 수익률 비교 차트
        plt.figure(figsize=(12, 6))
        profits = [r['total_profit'] for r in results]
        bars = plt.bar(strategy_names, profits, alpha=0.7)
        
        # 막대 색상 설정 (양수: 녹색, 음수: 빨간색)
        for i, profit in enumerate(profits):
            bars[i].set_color('green' if profit > 0 else 'red')
        
        plt.title('전략별 총 수익률 비교', fontsize=16)
        plt.xlabel('전략', fontsize=12)
        plt.ylabel('총 수익률 (%)', fontsize=12)
        plt.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45)
        
        # 수익률 값 표시
        for i, v in enumerate(profits):
            plt.text(i, v + (5 if v >= 0 else -5), f"{v:.2f}%", 
                    ha='center', va='center' if v >= 0 else 'top', 
                    fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(charts_dir, "profit_comparison.png"), dpi=300)
        plt.close()
        
        # 2. 승률 비교 차트
        plt.figure(figsize=(12, 6))
        win_rates = [r['win_pct'] for r in results]
        plt.bar(strategy_names, win_rates, color='blue', alpha=0.7)
        
        plt.title('전략별 승률 비교', fontsize=16)
        plt.xlabel('전략', fontsize=12)
        plt.ylabel('승률 (%)', fontsize=12)
        plt.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45)
        
        # 승률 값 표시
        for i, v in enumerate(win_rates):
            plt.text(i, v + 2, f"{v:.2f}%", ha='center', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(charts_dir, "winrate_comparison.png"), dpi=300)
        plt.close()
        
        # 3. 드로다운 비교 차트
        plt.figure(figsize=(12, 6))
        drawdowns = [r['max_drawdown'] for r in results]
        plt.bar(strategy_names, drawdowns, color='red', alpha=0.7)
        
        plt.title('전략별 최대 드로다운 비교', fontsize=16)
        plt.xlabel('전략', fontsize=12)
        plt.ylabel('최대 드로다운 (%)', fontsize=12)
        plt.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45)
        
        # 드로다운 값 표시
        for i, v in enumerate(drawdowns):
            plt.text(i, v - 2, f"{v:.2f}%", ha='center', va='top', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(charts_dir, "drawdown_comparison.png"), dpi=300)
        plt.close()
        
        # 4. 거래 횟수 비교 차트
        plt.figure(figsize=(12, 6))
        trade_counts = [r['total_trades'] for r in results]
        plt.bar(strategy_names, trade_counts, color='purple', alpha=0.7)
        
        plt.title('전략별 거래 횟수 비교', fontsize=16)
        plt.xlabel('전략', fontsize=12)
        plt.ylabel('거래 횟수', fontsize=12)
        plt.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45)
        
        # 거래 횟수 값 표시
        for i, v in enumerate(trade_counts):
            plt.text(i, v + 2, str(v), ha='center', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(charts_dir, "trades_comparison.png"), dpi=300)
        plt.close()
        
        # 5. 종합 성능 레이더 차트
        if len(results) <= 5:  # 레이더 차트는 너무 많은 전략이 있으면 복잡해짐
            plt.figure(figsize=(10, 10))
            
            # 지표 정규화
            metrics = ['total_profit', 'win_pct', 'profit_factor']
            metric_names = ['총 수익률', '승률', '수익 요소']
            
            # 드로다운은 역으로 정규화 (낮을수록 좋음)
            metrics.append('max_drawdown_inv')
            metric_names.append('드로다운 저항성')
            
            # 데이터 준비
            normalized_data = []
            
            for metric in metrics:
                if metric == 'max_drawdown_inv':
                    # 드로다운 역수 계산 (낮을수록 좋음 -> 높을수록 좋음)
                    values = [1 / (abs(r['max_drawdown']) + 0.01) for r in results]  # 0으로 나누기 방지
                else:
                    values = [r[metric] for r in results]
                
                # 정규화 (0-1 범위)
                min_val = min(values)
                max_val = max(values)
                
                if max_val > min_val:
                    normalized = [(v - min_val) / (max_val - min_val) for v in values]
                else:
                    normalized = [0.5 for _ in values]
                
                normalized_data.append(normalized)
            
            # 각도 계산
            angles = np.linspace(0, 2*np.pi, len(metrics), endpoint=False).tolist()
            angles += angles[:1]  # 닫힌 다각형을 위해 첫 각도 추가
            
            # 레이더 차트 그리기
            ax = plt.subplot(111, polar=True)
            
            for i, strategy_name in enumerate(strategy_names):
                values = [normalized_data[j][i] for j in range(len(metrics))]
                values += values[:1]  # 닫힌 다각형을 위해 첫 값 추가
                
                ax.plot(angles, values, linewidth=2, label=strategy_name)
                ax.fill(angles, values, alpha=0.1)
            
            # 차트 스타일 설정
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(metric_names)
            ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
            ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'])
            ax.set_rlabel_position(0)
            
            plt.title('전략별 종합 성능 비교', fontsize=16, y=1.1)
            plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
            
            plt.tight_layout()
            plt.savefig(os.path.join(charts_dir, "radar_comparison.png"), dpi=300)
            plt.close()
        
        # 6. 자본금 곡선 비교
        plt.figure(figsize=(12, 6))
        
        for result in results:
            backtest_results = result['results']
            strategy_name = result['strategy']
            
            if 'trades' not in backtest_results or not backtest_results['trades']:
                continue
            
            trades = backtest_results['trades']
            
            # 거래 데이터를 DataFrame으로 변환
            df = pd.DataFrame(trades)
            
            # 날짜 형식 변환
            if 'close_date' in df.columns:
                df['close_date'] = pd.to_datetime(df['close_date'])
                df = df.sort_values('close_date')
            else:
                continue
            
            # 누적 수익 계산
            if 'profit_percent' in df.columns:
                df['cumulative_profit'] = (1 + df['profit_percent'] / 100).cumprod() - 1
            elif 'profit_ratio' in df.columns:
                df['cumulative_profit'] = (1 + df['profit_ratio']).cumprod() - 1
            else:
                continue
            
            # 자본금 곡선 그리기
            plt.plot(df['close_date'], df['cumulative_profit'] * 100, 
                    linewidth=2, label=strategy_name)
        
        plt.title('전략별 자본금 곡선 비교', fontsize=16)
        plt.xlabel('날짜', fontsize=12)
        plt.ylabel('누적 수익률 (%)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # x축 날짜 포맷 설정
        plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))
        plt.gcf().autofmt_xdate()
        
        # 0선 표시
        plt.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(charts_dir, "equity_comparison.png"), dpi=300)
        plt.close()
        
        logger.info(f"전략 비교 차트 생성 완료: {charts_dir}")
    
    def compare_market_conditions(self, strategy: str, parameter_file: Optional[str] = None,
                                timeranges: List[Dict[str, str]], stake_amount: float = 100,
                                max_open_trades: int = 5) -> pd.DataFrame:
        """
        다양한 시장 조건에서 전략 성능 비교
        
        Args:
            strategy: 전략 이름
            parameter_file: 전략 매개변수 파일 (선택 사항)
            timeranges: 시간 범위 목록 (각 범위는 'name'과 'range' 키를 포함하는 딕셔너리)
            stake_amount: 거래당 주문 금액
            max_open_trades: 최대 동시 거래 수
            
        Returns:
            pd.DataFrame: 비교 결과 데이터프레임
        """
        # 결과 저장 리스트
        results = []
        
        # 각 시간 범위에 대해 백테스트 실행
        for timerange_info in timeranges:
            period_name = timerange_info['name']
            timerange = timerange_info['range']
            
            logger.info(f"시장 조건 '{period_name}' 백테스트 시작")
            
            # 백테스트 실행
            backtest_results = self.backtesting.run_backtest(
                strategy=strategy,
                timerange=timerange,
                parameter_file=parameter_file,
                stake_amount=stake_amount,
                max_open_trades=max_open_trades
            )
            
            if not backtest_results:
                logger.warning(f"시장 조건 '{period_name}' 백테스트 실패")
                continue
            
            # 주요 지표 추출
            total_trades = backtest_results.get('total_trades', 0)
            win_pct = backtest_results.get('win_pct', 0)
            total_profit = backtest_results.get('total_profit', 0)
            max_drawdown = backtest_results.get('max_drawdown', 0)
            profit_factor = backtest_results.get('profit_factor', 0)
            
            # 결과 저장
            result = {
                'period': period_name,
                'timerange': timerange,
                'total_trades': total_trades,
                'win_pct': win_pct,
                'total_profit': total_profit,
                'max_drawdown': max_drawdown,
                'profit_factor': profit_factor,
                'results': backtest_results
            }
            
            results.append(result)
            
            # 결과 시각화
            self.visualizer.create_performance_report(
                backtest_results,
                f"{strategy}_{period_name}"
            )
        
        # 결과를 데이터프레임으로 변환
        if not results:
            logger.error("비교 결과가 없습니다")
            return pd.DataFrame()
        
        # 결과 데이터프레임 생성 (results 열 제외)
        df_results = pd.DataFrame([{k: v for k, v in r.items() if k != 'results'} for r in results])
        
        # 수익률로 정렬
        df_results = df_results.sort_values('total_profit', ascending=False)
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(self.results_dir, f"{strategy}_market_conditions_{timestamp}.csv")
        df_results.to_csv(results_file, index=False)
        
        logger.info(f"시장 조건 비교 결과 저장됨: {results_file}")
        
        # 비교 차트 생성
        self._create_market_condition_charts(results, strategy, timestamp)
        
        return df_results
    
    def _create_market_condition_charts(self, results: List[Dict[str, Any]], 
                                      strategy: str, timestamp: str) -> None:
        """
        시장 조건 비교 차트 생성
        
        Args:
            results: 시장 조건 백테스트 결과 목록
            strategy: 전략 이름
            timestamp: 타임스탬프 문자열
        """
        if not results:
            return
        
        # 차트 저장 디렉토리
        charts_dir = os.path.join(self.results_dir, f"{strategy}_conditions_{timestamp}")
        os.makedirs(charts_dir, exist_ok=True)
        
        # 기간 이름 목록
        period_names = [r['period'] for r in results]
        
        # 1. 수익률 비교 차트
        plt.figure(figsize=(12, 6))
        profits = [r['total_profit'] for r in results]
        bars = plt.bar(period_names, profits, alpha=0.7)
        
        # 막대 색상 설정 (양수: 녹색, 음수: 빨간색)
        for i, profit in enumerate(profits):
            bars[i].set_color('green' if profit > 0 else 'red')
        
        plt.title(f'{strategy} - 시장 조건별 수익률 비교', fontsize=16)
        plt.xlabel('시장 조건', fontsize=12)
        plt.ylabel('총 수익률 (%)', fontsize=12)
        plt.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45)
        
        # 수익률 값 표시
        for i, v in enumerate(profits):
            plt.text(i, v + (5 if v >= 0 else -5), f"{v:.2f}%", 
                    ha='center', va='center' if v >= 0 else 'top', 
                    fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(charts_dir, "profit_by_condition.png"), dpi=300)
        plt.close()
        
        # 2. 승률 비교 차트
        plt.figure(figsize=(12, 6))
        win_rates = [r['win_pct'] for r in results]
        plt.bar(period_names, win_rates, color='blue', alpha=0.7)
        
        plt.title(f'{strategy} - 시장 조건별 승률 비교', fontsize=16)
        plt.xlabel('시장 조건', fontsize=12)
        plt.ylabel('승률 (%)', fontsize=12)
        plt.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45)
        
        # 승률 값 표시
        for i, v in enumerate(win_rates):
            plt.text(i, v + 2, f"{v:.2f}%", ha='center', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(charts_dir, "winrate_by_condition.png"), dpi=300)
        plt.close()
        
        # 3. 거래 횟수 비교 차트
        plt.figure(figsize=(12, 6))
        trade_counts = [r['total_trades'] for r in results]
        plt.bar(period_names, trade_counts, color='purple', alpha=0.7)
        
        plt.title(f'{strategy} - 시장 조건별 거래 횟수 비교', fontsize=16)
        plt.xlabel('시장 조건', fontsize=12)
        plt.ylabel('거래 횟수', fontsize=12)
        plt.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45)
        
        # 거래 횟수 값 표시
        for i, v in enumerate(trade_counts):
            plt.text(i, v + 2, str(v), ha='center', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(charts_dir, "trades_by_condition.png"), dpi=300)
        plt.close()
        
        # 4. 종합 성능 비교 표 생성
        summary_data = {
            '시장 조건': period_names,
            '총 수익률 (%)': [r['total_profit'] for r in results],
            '승률 (%)': [r['win_pct'] for r in results],
            '최대 드로다운 (%)': [r['max_drawdown'] for r in results],
            '거래 횟수': [r['total_trades'] for r in results],
            '수익 요소': [r['profit_factor'] for r in results]
        }
        
        summary_df = pd.DataFrame(summary_data)
        
        # HTML 표 생성
        html_table = summary_df.to_html(index=False)
        
        # HTML 파일 생성
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{strategy} - 시장 조건별 성능 요약</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                tr:hover {{ background-color: #f5f5f5; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>{strategy} - 시장 조건별 성능 요약</h1>
            {html_table}
        </body>
        </html>
        """
        
        with open(os.path.join(charts_dir, "summary.html"), 'w') as f:
            f.write(html_content)
        
        logger.info(f"시장 조건 비교 차트 생성 완료: {charts_dir}")

def main():
    """전략 비교 예제 실행"""
    # 설정 경로
    config_path = os.path.join(project_root, 'config', 'freqtrade.json')
    data_dir = os.path.join(project_root, 'data')
    results_dir = os.path.join(project_root, 'results', 'comparison')
    
    # 디렉토리 생성
    os.makedirs(results_dir, exist_ok=True)
    
    # 전략 비교 초기화
    comparator = StrategyComparator(
        config_path=config_path,
        data_dir=data_dir,
        results_dir=results_dir
    )
    
    # 1. 여러 전략 비교 예제
    strategies = [
        {
            'name': 'NASOSv5_mod3',
            'params_file': None  # 기본 매개변수 사용
        },
        {
            'name': 'NASOSv5_mod3',
            'params_file': os.path.join(project_root, 'results', 'best_params', 'NASOSv5_mod3_best_params.json')
        },
        {
            'name': 'SampleStrategy',
            'params_file': None
        }
    ]
    
    # 전략 비교 실행
    strategy_results = comparator.compare_strategies(
        strategies=strategies,
        timerange='20220101-20221231',
        stake_amount=100,
        max_open_trades=5
    )
    
    # 2. 다양한 시장 조건에서 전략 성능 비교 예제
    timeranges = [
        {
            'name': '상승장',
            'range': '20210101-20210630'  # 2021년 상반기 (상승장 예시)
        },
        {
            'name': '하락장',
            'range': '20220501-20221031'  # 2022년 5-10월 (하락장 예시)
        },
        {
            'name': '횡보장',
            'range': '20220101-20220430'  # 2022년 1-4월 (횡보장 예시)
        },
        {
            'name': '변동성 높음',
            'range': '20200301-20200831'  # 2020년 3-8월 (코로나 변동성 예시)
        }
    ]
    
    # 시장 조건 비교 실행
    market_results = comparator.compare_market_conditions(
        strategy='NASOSv5_mod3',
        parameter_file=os.path.join(project_root, 'results', 'best_params', 'NASOSv5_mod3_best_params.json'),
        timeranges=timeranges,
        stake_amount=100,
        max_open_trades=5
    )
    
    logger.info("전략 비교 예제 실행 완료")

if __name__ == "__main__":
    main()
