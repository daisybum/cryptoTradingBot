"""
시각화 모듈

이 모듈은 트레이딩 봇의 성능 데이터를 시각화하는 기능을 제공합니다.
Matplotlib, Plotly 등을 사용하여 다양한 차트와 그래프를 생성합니다.
"""
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import io
import base64
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PerformanceVisualizer:
    """성능 시각화 클래스"""
    
    def __init__(self, db_manager=None, output_dir=None):
        """
        성능 시각화 클래스 초기화
        
        Args:
            db_manager: 데이터베이스 관리자 인스턴스
            output_dir: 출력 디렉토리 경로
        """
        self.db_manager = db_manager
        self.output_dir = output_dir or Path("./reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 시각화 스타일 설정
        plt.style.use('seaborn-v0_8-darkgrid')
    
    def plot_equity_curve(self, trades_df: pd.DataFrame, save_path: Optional[str] = None) -> Optional[str]:
        """
        자산 곡선 플롯 생성
        
        Args:
            trades_df: 거래 데이터 DataFrame
            save_path: 저장 경로
            
        Returns:
            Optional[str]: 이미지 경로 또는 Base64 인코딩된 이미지
        """
        if trades_df.empty:
            logger.warning("자산 곡선을 플롯할 거래 데이터가 없습니다.")
            return None
        
        try:
            # 누적 수익 계산
            trades_df = trades_df.sort_values('close_time')
            trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
            trades_df['equity'] = 10000 + trades_df['cumulative_pnl']  # 초기 자본 10,000 USDT 가정
            
            # 드로다운 계산
            trades_df['max_equity'] = trades_df['equity'].cummax()
            trades_df['drawdown'] = trades_df['max_equity'] - trades_df['equity']
            trades_df['drawdown_pct'] = trades_df['drawdown'] / trades_df['max_equity'] * 100
            
            # 플롯 생성
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
            
            # 자산 곡선 플롯
            ax1.plot(trades_df['close_time'], trades_df['equity'], label='Equity')
            ax1.set_title('Equity Curve')
            ax1.set_ylabel('Equity (USDT)')
            ax1.legend()
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            
            # 드로다운 플롯
            ax2.fill_between(trades_df['close_time'], 0, trades_df['drawdown_pct'], color='red', alpha=0.3)
            ax2.set_title('Drawdown')
            ax2.set_ylabel('Drawdown (%)')
            ax2.set_ylim(bottom=0, top=max(trades_df['drawdown_pct']) * 1.1)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path)
                plt.close()
                return save_path
            else:
                # Base64 인코딩된 이미지 반환
                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                plt.close()
                buf.seek(0)
                img_str = base64.b64encode(buf.read()).decode('utf-8')
                return img_str
                
        except Exception as e:
            logger.error(f"자산 곡선 플롯 생성 실패: {e}")
            return None
    
    def plot_monthly_returns(self, trades_df: pd.DataFrame, save_path: Optional[str] = None) -> Optional[str]:
        """
        월별 수익 플롯 생성
        
        Args:
            trades_df: 거래 데이터 DataFrame
            save_path: 저장 경로
            
        Returns:
            Optional[str]: 이미지 경로 또는 Base64 인코딩된 이미지
        """
        if trades_df.empty:
            logger.warning("월별 수익을 플롯할 거래 데이터가 없습니다.")
            return None
        
        try:
            # 월별 수익 계산
            trades_df['year_month'] = trades_df['close_time'].dt.strftime('%Y-%m')
            monthly_returns = trades_df.groupby('year_month')['pnl'].sum().reset_index()
            
            # 플롯 생성
            plt.figure(figsize=(12, 6))
            
            # 양수 및 음수 수익 구분
            positive_returns = monthly_returns[monthly_returns['pnl'] >= 0]
            negative_returns = monthly_returns[monthly_returns['pnl'] < 0]
            
            plt.bar(positive_returns['year_month'], positive_returns['pnl'], color='green', alpha=0.7)
            plt.bar(negative_returns['year_month'], negative_returns['pnl'], color='red', alpha=0.7)
            
            plt.title('Monthly Returns')
            plt.xlabel('Month')
            plt.ylabel('Profit/Loss (USDT)')
            plt.xticks(rotation=45)
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path)
                plt.close()
                return save_path
            else:
                # Base64 인코딩된 이미지 반환
                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                plt.close()
                buf.seek(0)
                img_str = base64.b64encode(buf.read()).decode('utf-8')
                return img_str
                
        except Exception as e:
            logger.error(f"월별 수익 플롯 생성 실패: {e}")
            return None
    
    def plot_win_loss_distribution(self, trades_df: pd.DataFrame, save_path: Optional[str] = None) -> Optional[str]:
        """
        승리/손실 분포 플롯 생성
        
        Args:
            trades_df: 거래 데이터 DataFrame
            save_path: 저장 경로
            
        Returns:
            Optional[str]: 이미지 경로 또는 Base64 인코딩된 이미지
        """
        if trades_df.empty:
            logger.warning("승리/손실 분포를 플롯할 거래 데이터가 없습니다.")
            return None
        
        try:
            # 승리/손실 거래 구분
            winning_trades = trades_df[trades_df['pnl'] > 0]['pnl']
            losing_trades = trades_df[trades_df['pnl'] <= 0]['pnl']
            
            # 플롯 생성
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
            
            # 승리 거래 히스토그램
            if not winning_trades.empty:
                ax1.hist(winning_trades, bins=20, color='green', alpha=0.7)
                ax1.set_title('Winning Trades Distribution')
                ax1.set_xlabel('Profit (USDT)')
                ax1.set_ylabel('Frequency')
                ax1.grid(linestyle='--', alpha=0.7)
            else:
                ax1.text(0.5, 0.5, 'No winning trades', horizontalalignment='center', verticalalignment='center', transform=ax1.transAxes)
            
            # 손실 거래 히스토그램
            if not losing_trades.empty:
                ax2.hist(losing_trades, bins=20, color='red', alpha=0.7)
                ax2.set_title('Losing Trades Distribution')
                ax2.set_xlabel('Loss (USDT)')
                ax2.set_ylabel('Frequency')
                ax2.grid(linestyle='--', alpha=0.7)
            else:
                ax2.text(0.5, 0.5, 'No losing trades', horizontalalignment='center', verticalalignment='center', transform=ax2.transAxes)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path)
                plt.close()
                return save_path
            else:
                # Base64 인코딩된 이미지 반환
                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                plt.close()
                buf.seek(0)
                img_str = base64.b64encode(buf.read()).decode('utf-8')
                return img_str
                
        except Exception as e:
            logger.error(f"승리/손실 분포 플롯 생성 실패: {e}")
            return None
    
    def plot_trade_duration(self, trades_df: pd.DataFrame, save_path: Optional[str] = None) -> Optional[str]:
        """
        거래 기간 분포 플롯 생성
        
        Args:
            trades_df: 거래 데이터 DataFrame
            save_path: 저장 경로
            
        Returns:
            Optional[str]: 이미지 경로 또는 Base64 인코딩된 이미지
        """
        if trades_df.empty:
            logger.warning("거래 기간 분포를 플롯할 거래 데이터가 없습니다.")
            return None
        
        try:
            # 거래 기간 계산 (시간 단위)
            trades_df['duration'] = (trades_df['close_time'] - trades_df['open_time']).dt.total_seconds() / 3600
            
            # 플롯 생성
            plt.figure(figsize=(10, 6))
            
            plt.hist(trades_df['duration'], bins=20, color='blue', alpha=0.7)
            plt.title('Trade Duration Distribution')
            plt.xlabel('Duration (hours)')
            plt.ylabel('Frequency')
            plt.grid(linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path)
                plt.close()
                return save_path
            else:
                # Base64 인코딩된 이미지 반환
                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                plt.close()
                buf.seek(0)
                img_str = base64.b64encode(buf.read()).decode('utf-8')
                return img_str
                
        except Exception as e:
            logger.error(f"거래 기간 분포 플롯 생성 실패: {e}")
            return None
    
    def generate_performance_report(self, trades_df: pd.DataFrame, metrics: Dict[str, Any], 
                                   output_file: Optional[str] = None) -> Optional[str]:
        """
        성능 보고서 생성
        
        Args:
            trades_df: 거래 데이터 DataFrame
            metrics: 성능 지표 딕셔너리
            output_file: 출력 파일 경로
            
        Returns:
            Optional[str]: 보고서 파일 경로
        """
        if trades_df.empty:
            logger.warning("성능 보고서를 생성할 거래 데이터가 없습니다.")
            return None
        
        try:
            # 출력 파일 경로 설정
            if not output_file:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = self.output_dir / f"performance_report_{timestamp}.html"
            
            # 보고서 HTML 생성
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Trading Performance Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1, h2 {{ color: #333; }}
                    .container {{ max-width: 1200px; margin: 0 auto; }}
                    .metrics {{ display: flex; flex-wrap: wrap; }}
                    .metric-card {{ background-color: #f5f5f5; border-radius: 5px; padding: 15px; margin: 10px; flex: 1; min-width: 200px; }}
                    .metric-value {{ font-size: 24px; font-weight: bold; margin: 10px 0; }}
                    .metric-name {{ font-size: 14px; color: #666; }}
                    .chart {{ margin: 20px 0; background-color: #fff; border-radius: 5px; padding: 15px; }}
                    .positive {{ color: green; }}
                    .negative {{ color: red; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Trading Performance Report</h1>
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    
                    <h2>Performance Metrics</h2>
                    <div class="metrics">
                        <div class="metric-card">
                            <div class="metric-name">Total Trades</div>
                            <div class="metric-value">{metrics.get('total_trades', 0)}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-name">Win Rate</div>
                            <div class="metric-value">{metrics.get('win_rate', 0) * 100:.2f}%</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-name">Profit Factor</div>
                            <div class="metric-value">{metrics.get('profit_factor', 0):.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-name">Average Profit</div>
                            <div class="metric-value {('positive' if metrics.get('average_profit', 0) > 0 else 'negative')}">
                                {metrics.get('average_profit', 0):.2f} USDT
                            </div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-name">Max Drawdown</div>
                            <div class="metric-value negative">{metrics.get('max_drawdown', 0) * 100:.2f}%</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-name">Sharpe Ratio</div>
                            <div class="metric-value">{metrics.get('sharpe_ratio', 0):.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-name">Sortino Ratio</div>
                            <div class="metric-value">{metrics.get('sortino_ratio', 0):.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-name">Calmar Ratio</div>
                            <div class="metric-value">{metrics.get('calmar_ratio', 0):.2f}</div>
                        </div>
                    </div>
                    
                    <h2>Equity Curve</h2>
                    <div class="chart">
                        <img src="data:image/png;base64,{self.plot_equity_curve(trades_df)}" width="100%">
                    </div>
                    
                    <h2>Monthly Returns</h2>
                    <div class="chart">
                        <img src="data:image/png;base64,{self.plot_monthly_returns(trades_df)}" width="100%">
                    </div>
                    
                    <h2>Win/Loss Distribution</h2>
                    <div class="chart">
                        <img src="data:image/png;base64,{self.plot_win_loss_distribution(trades_df)}" width="100%">
                    </div>
                    
                    <h2>Trade Duration Distribution</h2>
                    <div class="chart">
                        <img src="data:image/png;base64,{self.plot_trade_duration(trades_df)}" width="100%">
                    </div>
                </div>
            </body>
            </html>
            """
            
            # HTML 파일 저장
            with open(output_file, 'w') as f:
                f.write(html_content)
            
            logger.info(f"성능 보고서가 생성되었습니다: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"성능 보고서 생성 실패: {e}")
            return None
    
    def get_trades_from_db(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, 
                          strategy: Optional[str] = None, pair: Optional[str] = None) -> pd.DataFrame:
        """
        데이터베이스에서 거래 데이터 가져오기
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            strategy: 전략 이름
            pair: 거래 페어
            
        Returns:
            pd.DataFrame: 거래 데이터 DataFrame
        """
        if not self.db_manager:
            logger.error("데이터베이스 관리자가 초기화되지 않았습니다.")
            return pd.DataFrame()
        
        try:
            with self.db_manager.get_pg_session() as session:
                query = """
                SELECT 
                    trade_id, pair, strategy, open_time, close_time, 
                    entry_price, exit_price, quantity, side, status, 
                    pnl, pnl_pct, fee
                FROM trades
                WHERE status = 'closed'
                """
                
                params = {}
                
                if start_date:
                    query += " AND open_time >= :start_date"
                    params['start_date'] = start_date
                
                if end_date:
                    query += " AND close_time <= :end_date"
                    params['end_date'] = end_date
                
                if strategy:
                    query += " AND strategy = :strategy"
                    params['strategy'] = strategy
                
                if pair:
                    query += " AND pair = :pair"
                    params['pair'] = pair
                
                query += " ORDER BY open_time ASC"
                
                result = session.execute(query, params)
                trades = result.fetchall()
                
                if not trades:
                    logger.warning("조건에 맞는 거래 데이터가 없습니다.")
                    return pd.DataFrame()
                
                # DataFrame 생성
                columns = [
                    'trade_id', 'pair', 'strategy', 'open_time', 'close_time',
                    'entry_price', 'exit_price', 'quantity', 'side', 'status',
                    'pnl', 'pnl_pct', 'fee'
                ]
                
                trades_df = pd.DataFrame(trades, columns=columns)
                
                return trades_df
                
        except Exception as e:
            logger.error(f"거래 데이터 가져오기 실패: {e}")
            return pd.DataFrame()
