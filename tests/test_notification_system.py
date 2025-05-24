"""
알림 시스템 테스트 스크립트

이 스크립트는 알림 시스템의 기능을 테스트합니다.
텔레그램 알림, Redis 통합, 성능 보고서 생성 및 전송 기능을 검증합니다.
"""
import os
import sys
import logging
import time
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import random
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

# 프로젝트 루트 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 모듈 임포트
from src.notifications.manager import NotificationManager
from src.notifications.handlers import EventType
from src.analytics.performance import PerformanceAnalyzer
from src.analytics.visualization import PerformanceVisualizer
from src.analytics.reporting import ReportGenerator

def generate_sample_trades(num_trades=50):
    """
    샘플 거래 데이터 생성
    
    Args:
        num_trades: 생성할 거래 수
        
    Returns:
        pd.DataFrame: 거래 데이터프레임
    """
    logger.info(f"{num_trades}개의 샘플 거래 데이터를 생성합니다.")
    
    # 현재 시간
    now = datetime.now()
    
    # 거래 데이터 초기화
    trades = []
    
    # 샘플 페어 목록
    pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT']
    
    # 누적 손익
    cumulative_profit = 0
    
    for i in range(num_trades):
        # 거래 시작 시간 (최근 30일 내)
        start_time = now - timedelta(days=random.uniform(0, 30))
        
        # 거래 지속 시간 (10분~24시간)
        duration_hours = random.uniform(0.17, 24)
        end_time = start_time + timedelta(hours=duration_hours)
        
        # 거래 페어
        pair = random.choice(pairs)
        
        # 거래 방향
        side = random.choice(['buy', 'sell'])
        
        # 진입 가격 (페어에 따라 다름)
        if 'BTC' in pair:
            entry_price = random.uniform(25000, 35000)
        elif 'ETH' in pair:
            entry_price = random.uniform(1500, 2500)
        elif 'SOL' in pair:
            entry_price = random.uniform(50, 150)
        elif 'BNB' in pair:
            entry_price = random.uniform(200, 400)
        else:  # XRP
            entry_price = random.uniform(0.4, 0.8)
        
        # 수량
        quantity = random.uniform(0.1, 2.0)
        if 'BTC' in pair:
            quantity = random.uniform(0.01, 0.2)
        
        # 승패 결정 (60% 확률로 승리)
        is_win = random.random() < 0.6
        
        # 청산 가격
        if is_win:
            # 승리: 1-5% 이익
            pnl_pct = random.uniform(1.0, 5.0)
            if side == 'buy':
                exit_price = entry_price * (1 + pnl_pct / 100)
            else:
                exit_price = entry_price * (1 - pnl_pct / 100)
        else:
            # 패배: 1-3% 손실
            pnl_pct = random.uniform(1.0, 3.0)
            if side == 'buy':
                exit_price = entry_price * (1 - pnl_pct / 100)
            else:
                exit_price = entry_price * (1 + pnl_pct / 100)
            pnl_pct = -pnl_pct
        
        # 손익 계산
        if side == 'buy':
            pnl = (exit_price - entry_price) * quantity
        else:
            pnl = (entry_price - exit_price) * quantity
        
        # 누적 손익 업데이트
        cumulative_profit += pnl
        
        # 거래 데이터 추가
        trade = {
            'trade_id': f"T{i+1:04d}",
            'pair': pair,
            'side': side,
            'entry_time': start_time,
            'exit_time': end_time,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'quantity': quantity,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'cumulative_profit': cumulative_profit,
            'strategy': 'NASOSv5_mod3'
        }
        
        trades.append(trade)
    
    # 데이터프레임 생성
    df = pd.DataFrame(trades)
    
    logger.info(f"샘플 거래 데이터 생성 완료: {len(df)}개")
    return df

def test_notification_manager():
    """알림 관리자 테스트"""
    logger.info("알림 관리자 테스트를 시작합니다.")
    
    # 알림 관리자 초기화
    notification_manager = NotificationManager()
    
    # 알림 시스템 시작
    notification_manager.start()
    
    # 상태 확인
    status = notification_manager.get_status()
    logger.info(f"알림 시스템 상태: {json.dumps(status, indent=2)}")
    
    # 정보 알림 전송
    notification_manager.send_info("알림 시스템 테스트가 시작되었습니다.")
    
    # 거래 시작 알림
    trade_open_data = {
        "trade_id": "T0001",
        "pair": "BTC/USDT",
        "side": "buy",
        "entry_price": 30000.0,
        "quantity": 0.1,
        "stop_loss": 29000.0,
        "take_profit": 32000.0,
        "strategy": "NASOSv5_mod3",
        "status": "open"
    }
    notification_manager.send_trade_open_notification(trade_open_data, True)
    
    # 잠시 대기
    time.sleep(2)
    
    # 주문 생성 알림
    order_placed_data = {
        "order_id": "O0001",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "order_type": "limit",
        "quantity": 0.1,
        "price": 30000.0,
        "status": "new"
    }
    notification_manager.send_order_notification(order_placed_data, True)
    
    # 잠시 대기
    time.sleep(2)
    
    # 주문 체결 알림
    order_filled_data = {
        "order_id": "O0001",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "quantity": 0.1,
        "price": 30000.0,
        "status": "filled"
    }
    notification_manager.send_order_notification(order_filled_data, True)
    
    # 잠시 대기
    time.sleep(2)
    
    # 거래 종료 알림
    trade_close_data = {
        "trade_id": "T0001",
        "pair": "BTC/USDT",
        "side": "buy",
        "entry_price": 30000.0,
        "exit_price": 31500.0,
        "quantity": 0.1,
        "pnl": 150.0,
        "pnl_pct": 5.0,
        "strategy": "NASOSv5_mod3",
        "duration": "2h 15m",
        "status": "closed"
    }
    notification_manager.send_trade_close_notification(trade_close_data, True)
    
    # 잠시 대기
    time.sleep(2)
    
    # 리스크 알림
    risk_alert_data = {
        "alert_type": "drawdown",
        "value": 5.2,
        "threshold": 10.0,
        "description": "일일 드로다운이 5.2%에 도달했습니다."
    }
    notification_manager.send_risk_alert(risk_alert_data, True)
    
    # 잠시 대기
    time.sleep(2)
    
    # 시스템 상태 알림
    system_status_data = {
        "component": "trading_engine",
        "status": "ok",
        "description": "거래 엔진이 정상적으로 작동 중입니다."
    }
    notification_manager.send_system_status(system_status_data, True)
    
    # 잠시 대기
    time.sleep(2)
    
    # 알림 시스템 중지
    notification_manager.stop()
    
    logger.info("알림 관리자 테스트가 완료되었습니다.")

def test_performance_analytics_with_notifications():
    """성능 분석 및 알림 통합 테스트"""
    logger.info("성능 분석 및 알림 통합 테스트를 시작합니다.")
    
    # 샘플 거래 데이터 생성
    trades_df = generate_sample_trades(50)
    
    # 성능 분석기 초기화
    performance_analyzer = PerformanceAnalyzer()
    
    # 성능 지표 계산
    metrics = performance_analyzer.calculate_metrics(trades_df)
    logger.info(f"성능 지표: {json.dumps(metrics, indent=2)}")
    
    # 시각화 도구 초기화
    visualizer = PerformanceVisualizer()
    
    # 임시 디렉토리 생성
    os.makedirs("temp", exist_ok=True)
    
    # 에쿼티 커브 생성
    equity_curve_path = visualizer.plot_equity_curve(trades_df, save_path="temp/equity_curve.png")
    logger.info(f"에쿼티 커브 저장 경로: {equity_curve_path}")
    
    # 월간 수익률 생성
    monthly_returns_path = visualizer.plot_monthly_returns(trades_df, save_path="temp/monthly_returns.png")
    logger.info(f"월간 수익률 저장 경로: {monthly_returns_path}")
    
    # 거래 분포 생성
    trade_distribution_path = visualizer.plot_trade_distribution(trades_df, save_path="temp/trade_distribution.png")
    logger.info(f"거래 분포 저장 경로: {trade_distribution_path}")
    
    # 보고서 생성기 초기화
    report_generator = ReportGenerator(performance_analyzer, visualizer)
    
    # 일일 보고서 생성
    daily_report_path = report_generator.generate_daily_report()
    logger.info(f"일일 보고서 저장 경로: {daily_report_path}")
    
    # 알림 관리자 초기화
    notification_manager = NotificationManager()
    
    # 알림 시스템 시작
    notification_manager.start()
    
    # 성능 보고서 알림 전송
    performance_data = {
        "period": f"일일 ({datetime.now().strftime('%Y-%m-%d')})",
        "total_trades": metrics["total_trades"],
        "win_rate": metrics["win_rate"],
        "profit_factor": metrics["profit_factor"],
        "total_profit": metrics["total_profit"],
        "max_drawdown": metrics["max_drawdown"],
        "sharpe_ratio": metrics.get("sharpe_ratio", 0),
        "calmar_ratio": metrics.get("calmar_ratio", 0),
        "report_path": daily_report_path
    }
    notification_manager.send_performance_update(performance_data, True)
    
    # 잠시 대기
    time.sleep(5)
    
    # 알림 시스템 중지
    notification_manager.stop()
    
    logger.info("성능 분석 및 알림 통합 테스트가 완료되었습니다.")

def main():
    """메인 함수"""
    logger.info("알림 시스템 테스트를 시작합니다.")
    
    # 알림 관리자 테스트
    test_notification_manager()
    
    # 잠시 대기
    time.sleep(5)
    
    # 성능 분석 및 알림 통합 테스트
    test_performance_analytics_with_notifications()
    
    logger.info("모든 테스트가 완료되었습니다.")

if __name__ == "__main__":
    main()
