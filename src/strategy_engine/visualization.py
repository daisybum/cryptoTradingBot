#!/usr/bin/env python3
"""
백테스트 결과 시각화 모듈

이 모듈은 백테스트 결과를 시각화하는 기능을 제공합니다.
다양한 차트와 그래프를 통해 전략 성능을 분석할 수 있습니다.
"""

import os
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
import seaborn as sns

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BacktestVisualizer:
    """백테스트 결과 시각화 클래스"""
    
    def __init__(self, results_dir: str):
        """
        백테스트 시각화 초기화
        
        Args:
            results_dir: 결과 저장 디렉토리
        """
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)
        
        # 시각화 스타일 설정
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_context("talk")
        
    def plot_equity_curve(self, backtest_results: Dict[str, Any], title: str = "Equity Curve", 
                         save_path: Optional[str] = None) -> None:
        """
        자본금 곡선 시각화
        
        Args:
            backtest_results: 백테스트 결과 딕셔너리
            title: 차트 제목
            save_path: 저장 경로 (None이면 저장하지 않음)
        """
        if 'trades' not in backtest_results or not backtest_results['trades']:
            logger.warning("거래 데이터가 없어 자본금 곡선을 그릴 수 없습니다.")
            return
        
        trades = backtest_results['trades']
        
        # 거래 데이터를 DataFrame으로 변환
        df = pd.DataFrame(trades)
        
        # 날짜 형식 변환
        if 'close_date' in df.columns:
            df['close_date'] = pd.to_datetime(df['close_date'])
            df = df.sort_values('close_date')
        
        # 누적 수익 계산
        if 'profit_percent' in df.columns:
            df['cumulative_profit'] = (1 + df['profit_percent'] / 100).cumprod() - 1
        elif 'profit_ratio' in df.columns:
            df['cumulative_profit'] = (1 + df['profit_ratio']).cumprod() - 1
        else:
            logger.warning("수익 데이터가 없어 자본금 곡선을 그릴 수 없습니다.")
            return
        
        # 그래프 그리기
        plt.figure(figsize=(12, 6))
        
        # 누적 수익 곡선
        plt.plot(df['close_date'], df['cumulative_profit'] * 100, 'b-', linewidth=2)
        
        # 수익/손실 거래 표시
        if 'profit_percent' in df.columns:
            profit_mask = df['profit_percent'] > 0
        else:
            profit_mask = df['profit_ratio'] > 0
            
        plt.scatter(df.loc[profit_mask, 'close_date'], 
                   df.loc[profit_mask, 'cumulative_profit'] * 100, 
                   color='green', alpha=0.6, label='Win')
        plt.scatter(df.loc[~profit_mask, 'close_date'], 
                   df.loc[~profit_mask, 'cumulative_profit'] * 100, 
                   color='red', alpha=0.6, label='Loss')
        
        # 그래프 스타일 설정
        plt.title(title, fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Cumulative Profit (%)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # x축 날짜 포맷 설정
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gcf().autofmt_xdate()
        
        # 최종 수익률 표시
        final_profit = df['cumulative_profit'].iloc[-1] * 100
        plt.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        plt.text(df['close_date'].iloc[-1], final_profit, 
                f' {final_profit:.2f}%', 
                verticalalignment='center')
        
        plt.tight_layout()
        
        # 저장 또는 표시
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"자본금 곡선이 저장되었습니다: {save_path}")
        else:
            plt.show()
            
        plt.close()
    
    def plot_monthly_returns(self, backtest_results: Dict[str, Any], title: str = "Monthly Returns", 
                           save_path: Optional[str] = None) -> None:
        """
        월별 수익률 시각화
        
        Args:
            backtest_results: 백테스트 결과 딕셔너리
            title: 차트 제목
            save_path: 저장 경로 (None이면 저장하지 않음)
        """
        if 'trades' not in backtest_results or not backtest_results['trades']:
            logger.warning("거래 데이터가 없어 월별 수익률을 그릴 수 없습니다.")
            return
        
        trades = backtest_results['trades']
        
        # 거래 데이터를 DataFrame으로 변환
        df = pd.DataFrame(trades)
        
        # 날짜 형식 변환
        if 'close_date' in df.columns:
            df['close_date'] = pd.to_datetime(df['close_date'])
            df['year_month'] = df['close_date'].dt.strftime('%Y-%m')
        else:
            logger.warning("날짜 데이터가 없어 월별 수익률을 그릴 수 없습니다.")
            return
        
        # 수익 데이터 확인
        if 'profit_percent' in df.columns:
            profit_col = 'profit_percent'
        elif 'profit_ratio' in df.columns:
            # profit_ratio를 퍼센트로 변환
            df['profit_percent'] = df['profit_ratio'] * 100
            profit_col = 'profit_percent'
        else:
            logger.warning("수익 데이터가 없어 월별 수익률을 그릴 수 없습니다.")
            return
        
        # 월별 수익 계산
        monthly_returns = df.groupby('year_month')[profit_col].sum().reset_index()
        monthly_returns = monthly_returns.sort_values('year_month')
        
        # 그래프 그리기
        plt.figure(figsize=(12, 6))
        
        # 막대 색상 설정 (양수: 녹색, 음수: 빨간색)
        colors = ['green' if x > 0 else 'red' for x in monthly_returns[profit_col]]
        
        # 월별 수익 막대 그래프
        plt.bar(monthly_returns['year_month'], monthly_returns[profit_col], color=colors, alpha=0.7)
        
        # 그래프 스타일 설정
        plt.title(title, fontsize=16)
        plt.xlabel('Month', fontsize=12)
        plt.ylabel('Monthly Return (%)', fontsize=12)
        plt.grid(True, alpha=0.3, axis='y')
        
        # x축 레이블 회전
        plt.xticks(rotation=45)
        
        # 0선 표시
        plt.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        
        plt.tight_layout()
        
        # 저장 또는 표시
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"월별 수익률 차트가 저장되었습니다: {save_path}")
        else:
            plt.show()
            
        plt.close()
    
    def plot_drawdown(self, backtest_results: Dict[str, Any], title: str = "Drawdown Analysis", 
                     save_path: Optional[str] = None) -> None:
        """
        드로다운 분석 시각화
        
        Args:
            backtest_results: 백테스트 결과 딕셔너리
            title: 차트 제목
            save_path: 저장 경로 (None이면 저장하지 않음)
        """
        if 'trades' not in backtest_results or not backtest_results['trades']:
            logger.warning("거래 데이터가 없어 드로다운을 그릴 수 없습니다.")
            return
        
        trades = backtest_results['trades']
        
        # 거래 데이터를 DataFrame으로 변환
        df = pd.DataFrame(trades)
        
        # 날짜 형식 변환
        if 'close_date' in df.columns:
            df['close_date'] = pd.to_datetime(df['close_date'])
            df = df.sort_values('close_date')
        else:
            logger.warning("날짜 데이터가 없어 드로다운을 그릴 수 없습니다.")
            return
        
        # 누적 수익 계산
        if 'profit_percent' in df.columns:
            df['cumulative_profit'] = (1 + df['profit_percent'] / 100).cumprod() - 1
        elif 'profit_ratio' in df.columns:
            df['cumulative_profit'] = (1 + df['profit_ratio']).cumprod() - 1
        else:
            logger.warning("수익 데이터가 없어 드로다운을 그릴 수 없습니다.")
            return
        
        # 드로다운 계산
        df['peak'] = df['cumulative_profit'].cummax()
        df['drawdown'] = (df['cumulative_profit'] - df['peak']) * 100  # 퍼센트로 변환
        
        # 그래프 그리기
        plt.figure(figsize=(12, 6))
        
        # 드로다운 곡선
        plt.fill_between(df['close_date'], df['drawdown'], 0, color='red', alpha=0.3)
        plt.plot(df['close_date'], df['drawdown'], 'r-', linewidth=1)
        
        # 그래프 스타일 설정
        plt.title(title, fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Drawdown (%)', fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # x축 날짜 포맷 설정
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gcf().autofmt_xdate()
        
        # 최대 드로다운 표시
        max_drawdown = df['drawdown'].min()
        max_dd_date = df.loc[df['drawdown'].idxmin(), 'close_date']
        plt.scatter(max_dd_date, max_drawdown, color='darkred', s=80, zorder=5)
        plt.text(max_dd_date, max_drawdown, f' Max DD: {max_drawdown:.2f}%', 
                verticalalignment='center')
        
        plt.tight_layout()
        
        # 저장 또는 표시
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"드로다운 차트가 저장되었습니다: {save_path}")
        else:
            plt.show()
            
        plt.close()
    
    def plot_pair_performance(self, backtest_results: Dict[str, Any], title: str = "Pair Performance", 
                             save_path: Optional[str] = None, top_n: int = 10) -> None:
        """
        거래쌍별 성능 시각화
        
        Args:
            backtest_results: 백테스트 결과 딕셔너리
            title: 차트 제목
            save_path: 저장 경로 (None이면 저장하지 않음)
            top_n: 표시할 상위 거래쌍 수
        """
        if 'pairs' not in backtest_results or not backtest_results['pairs']:
            logger.warning("거래쌍 데이터가 없어 거래쌍별 성능을 그릴 수 없습니다.")
            return
        
        pairs_data = backtest_results['pairs']
        
        # 딕셔너리를 DataFrame으로 변환
        pairs_df = pd.DataFrame.from_dict(pairs_data, orient='index')
        
        # 거래 횟수로 필터링 (최소 2회 이상)
        pairs_df = pairs_df[pairs_df['count'] >= 2]
        
        # 수익률로 정렬
        pairs_df = pairs_df.sort_values('profit', ascending=False)
        
        # 상위 N개 선택
        top_pairs = pairs_df.head(top_n)
        
        # 그래프 그리기
        plt.figure(figsize=(12, 8))
        
        # 막대 색상 설정 (양수: 녹색, 음수: 빨간색)
        colors = ['green' if x > 0 else 'red' for x in top_pairs['profit']]
        
        # 거래쌍별 수익 막대 그래프
        bars = plt.barh(top_pairs.index, top_pairs['profit'], color=colors, alpha=0.7)
        
        # 거래 횟수 표시
        for i, bar in enumerate(bars):
            plt.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, 
                    f"{top_pairs.iloc[i]['count']} trades", 
                    va='center')
        
        # 그래프 스타일 설정
        plt.title(title, fontsize=16)
        plt.xlabel('Profit (%)', fontsize=12)
        plt.ylabel('Trading Pair', fontsize=12)
        plt.grid(True, alpha=0.3, axis='x')
        
        # 0선 표시
        plt.axvline(x=0, color='k', linestyle='-', alpha=0.3)
        
        plt.tight_layout()
        
        # 저장 또는 표시
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"거래쌍별 성능 차트가 저장되었습니다: {save_path}")
        else:
            plt.show()
            
        plt.close()
    
    def plot_win_loss_distribution(self, backtest_results: Dict[str, Any], title: str = "Win/Loss Distribution", 
                                 save_path: Optional[str] = None) -> None:
        """
        승/패 분포 시각화
        
        Args:
            backtest_results: 백테스트 결과 딕셔너리
            title: 차트 제목
            save_path: 저장 경로 (None이면 저장하지 않음)
        """
        if 'trades' not in backtest_results or not backtest_results['trades']:
            logger.warning("거래 데이터가 없어 승/패 분포를 그릴 수 없습니다.")
            return
        
        trades = backtest_results['trades']
        
        # 거래 데이터를 DataFrame으로 변환
        df = pd.DataFrame(trades)
        
        # 수익 데이터 확인
        if 'profit_percent' in df.columns:
            profit_col = 'profit_percent'
        elif 'profit_ratio' in df.columns:
            # profit_ratio를 퍼센트로 변환
            df['profit_percent'] = df['profit_ratio'] * 100
            profit_col = 'profit_percent'
        else:
            logger.warning("수익 데이터가 없어 승/패 분포를 그릴 수 없습니다.")
            return
        
        # 그래프 그리기
        plt.figure(figsize=(12, 6))
        
        # 승/패 구분
        win_trades = df[df[profit_col] > 0][profit_col]
        loss_trades = df[df[profit_col] <= 0][profit_col]
        
        # 히스토그램 빈 설정
        bins = np.linspace(df[profit_col].min(), df[profit_col].max(), 30)
        
        # 승/패 히스토그램
        plt.hist(win_trades, bins=bins, alpha=0.7, color='green', label=f'Win ({len(win_trades)})')
        plt.hist(loss_trades, bins=bins, alpha=0.7, color='red', label=f'Loss ({len(loss_trades)})')
        
        # 그래프 스타일 설정
        plt.title(title, fontsize=16)
        plt.xlabel('Profit (%)', fontsize=12)
        plt.ylabel('Number of Trades', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # 0선 표시
        plt.axvline(x=0, color='k', linestyle='-', alpha=0.3)
        
        # 평균 수익/손실 표시
        avg_win = win_trades.mean() if len(win_trades) > 0 else 0
        avg_loss = loss_trades.mean() if len(loss_trades) > 0 else 0
        
        plt.axvline(x=avg_win, color='green', linestyle='--', alpha=0.7,
                   label=f'Avg Win: {avg_win:.2f}%')
        plt.axvline(x=avg_loss, color='red', linestyle='--', alpha=0.7,
                   label=f'Avg Loss: {avg_loss:.2f}%')
        
        plt.legend()
        plt.tight_layout()
        
        # 저장 또는 표시
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"승/패 분포 차트가 저장되었습니다: {save_path}")
        else:
            plt.show()
            
        plt.close()
    
    def create_performance_report(self, backtest_results: Dict[str, Any], strategy_name: str, 
                                output_dir: Optional[str] = None) -> str:
        """
        종합 성능 보고서 생성
        
        Args:
            backtest_results: 백테스트 결과 딕셔너리
            strategy_name: 전략 이름
            output_dir: 출력 디렉토리 (None이면 results_dir 사용)
            
        Returns:
            str: 보고서 저장 경로
        """
        if output_dir is None:
            output_dir = self.results_dir
            
        os.makedirs(output_dir, exist_ok=True)
        
        # 타임스탬프 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = os.path.join(output_dir, f"{strategy_name}_{timestamp}")
        os.makedirs(report_dir, exist_ok=True)
        
        # 각 차트 생성 및 저장
        self.plot_equity_curve(backtest_results, 
                             title=f"{strategy_name} - Equity Curve",
                             save_path=os.path.join(report_dir, "equity_curve.png"))
        
        self.plot_monthly_returns(backtest_results, 
                                title=f"{strategy_name} - Monthly Returns",
                                save_path=os.path.join(report_dir, "monthly_returns.png"))
        
        self.plot_drawdown(backtest_results, 
                         title=f"{strategy_name} - Drawdown Analysis",
                         save_path=os.path.join(report_dir, "drawdown.png"))
        
        self.plot_pair_performance(backtest_results, 
                                 title=f"{strategy_name} - Pair Performance",
                                 save_path=os.path.join(report_dir, "pair_performance.png"))
        
        self.plot_win_loss_distribution(backtest_results, 
                                      title=f"{strategy_name} - Win/Loss Distribution",
                                      save_path=os.path.join(report_dir, "win_loss_distribution.png"))
        
        # 결과 JSON 저장
        with open(os.path.join(report_dir, "backtest_results.json"), 'w') as f:
            json.dump(backtest_results, f, indent=4)
        
        # 요약 보고서 생성
        self._create_summary_report(backtest_results, strategy_name, report_dir)
        
        logger.info(f"성능 보고서가 생성되었습니다: {report_dir}")
        return report_dir
    
    def _create_summary_report(self, backtest_results: Dict[str, Any], strategy_name: str, report_dir: str) -> None:
        """
        요약 보고서 텍스트 파일 생성
        
        Args:
            backtest_results: 백테스트 결과 딕셔너리
            strategy_name: 전략 이름
            report_dir: 보고서 디렉토리
        """
        summary_path = os.path.join(report_dir, "summary.txt")
        
        with open(summary_path, 'w') as f:
            f.write(f"=== {strategy_name} 백테스트 요약 보고서 ===\n")
            f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 주요 지표 추출
            total_trades = backtest_results.get('total_trades', 0)
            win_trades = backtest_results.get('win_trades', 0)
            loss_trades = backtest_results.get('loss_trades', 0)
            win_pct = backtest_results.get('win_pct', 0)
            total_profit = backtest_results.get('total_profit', 0)
            profit_factor = backtest_results.get('profit_factor', 0)
            max_drawdown = backtest_results.get('max_drawdown', 0)
            
            # 요약 정보 작성
            f.write(f"총 거래 수: {total_trades}\n")
            f.write(f"승리 거래: {win_trades}\n")
            f.write(f"손실 거래: {loss_trades}\n")
            f.write(f"승률: {win_pct:.2f}%\n")
            f.write(f"총 수익: {total_profit:.2f}%\n")
            f.write(f"수익 요소: {profit_factor:.2f}\n")
            f.write(f"최대 드로다운: {max_drawdown:.2f}%\n\n")
            
            # 거래쌍별 성능
            if 'pairs' in backtest_results and backtest_results['pairs']:
                f.write("=== 거래쌍별 성능 ===\n")
                
                pairs_data = backtest_results['pairs']
                pairs_df = pd.DataFrame.from_dict(pairs_data, orient='index')
                pairs_df = pairs_df.sort_values('profit', ascending=False)
                
                for pair, row in pairs_df.iterrows():
                    f.write(f"{pair}: {row['count']}회 거래, 수익 {row['profit']:.2f}%, 승률 {row['winrate']:.2f}%\n")
                
                f.write("\n")
            
            # 거래 지속 시간별 분포
            if 'duration' in backtest_results and backtest_results['duration']:
                f.write("=== 거래 지속 시간별 분포 ===\n")
                
                duration_data = backtest_results['duration']
                for duration, data in duration_data.items():
                    f.write(f"{duration}: {data['count']}회 거래, 승리 {data['wins']}회, 패배 {data['losses']}회\n")
                
                f.write("\n")
            
            f.write("=== 보고서 파일 목록 ===\n")
            f.write("equity_curve.png - 자본금 곡선\n")
            f.write("monthly_returns.png - 월별 수익률\n")
            f.write("drawdown.png - 드로다운 분석\n")
            f.write("pair_performance.png - 거래쌍별 성능\n")
            f.write("win_loss_distribution.png - 승/패 분포\n")
            f.write("backtest_results.json - 백테스트 결과 JSON\n")
