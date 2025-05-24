"""
보고서 생성 모듈

이 모듈은 트레이딩 봇의 성능 데이터를 기반으로 보고서를 생성하는 기능을 제공합니다.
일일, 주간, 월간 보고서 및 커스텀 보고서를 생성할 수 있습니다.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import os
from pathlib import Path
import json
from jinja2 import Template

from src.analytics.performance import PerformanceAnalyzer
from src.analytics.visualization import PerformanceVisualizer

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReportGenerator:
    """보고서 생성 클래스"""
    
    def __init__(self, db_manager=None, output_dir=None):
        """
        보고서 생성 클래스 초기화
        
        Args:
            db_manager: 데이터베이스 관리자 인스턴스
            output_dir: 출력 디렉토리 경로
        """
        self.db_manager = db_manager
        self.output_dir = output_dir or Path("./reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.performance_analyzer = PerformanceAnalyzer(db_manager)
        self.visualizer = PerformanceVisualizer(db_manager, output_dir)
    
    def generate_daily_report(self, date: Optional[datetime] = None, strategy: Optional[str] = None) -> Optional[str]:
        """
        일일 보고서 생성
        
        Args:
            date: 보고서 날짜 (기본값: 어제)
            strategy: 전략 이름
            
        Returns:
            Optional[str]: 보고서 파일 경로
        """
        # 날짜 설정
        if date is None:
            date = datetime.now() - timedelta(days=1)
        
        start_date = datetime(date.year, date.month, date.day, 0, 0, 0)
        end_date = datetime(date.year, date.month, date.day, 23, 59, 59)
        
        # 보고서 제목
        title = f"일일 성능 보고서: {date.strftime('%Y-%m-%d')}"
        if strategy:
            title += f" - {strategy}"
        
        # 보고서 파일 경로
        filename = f"daily_report_{date.strftime('%Y%m%d')}"
        if strategy:
            filename += f"_{strategy}"
        filename += ".html"
        
        output_file = self.output_dir / filename
        
        return self._generate_report(start_date, end_date, title, str(output_file), strategy)
    
    def generate_weekly_report(self, week_end_date: Optional[datetime] = None, strategy: Optional[str] = None) -> Optional[str]:
        """
        주간 보고서 생성
        
        Args:
            week_end_date: 주의 마지막 날짜 (기본값: 지난 일요일)
            strategy: 전략 이름
            
        Returns:
            Optional[str]: 보고서 파일 경로
        """
        # 날짜 설정
        if week_end_date is None:
            today = datetime.now()
            week_end_date = today - timedelta(days=today.weekday() + 1)  # 지난 일요일
        
        start_date = week_end_date - timedelta(days=6)  # 월요일
        start_date = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0)
        end_date = datetime(week_end_date.year, week_end_date.month, week_end_date.day, 23, 59, 59)
        
        # 보고서 제목
        title = f"주간 성능 보고서: {start_date.strftime('%Y-%m-%d')} ~ {week_end_date.strftime('%Y-%m-%d')}"
        if strategy:
            title += f" - {strategy}"
        
        # 보고서 파일 경로
        filename = f"weekly_report_{start_date.strftime('%Y%m%d')}_{week_end_date.strftime('%Y%m%d')}"
        if strategy:
            filename += f"_{strategy}"
        filename += ".html"
        
        output_file = self.output_dir / filename
        
        return self._generate_report(start_date, end_date, title, str(output_file), strategy)
    
    def generate_monthly_report(self, month: Optional[int] = None, year: Optional[int] = None, 
                              strategy: Optional[str] = None) -> Optional[str]:
        """
        월간 보고서 생성
        
        Args:
            month: 월 (기본값: 지난 달)
            year: 년도 (기본값: 현재 년도)
            strategy: 전략 이름
            
        Returns:
            Optional[str]: 보고서 파일 경로
        """
        # 날짜 설정
        today = datetime.now()
        if month is None:
            month = today.month - 1
            if month == 0:
                month = 12
                year = today.year - 1
        
        if year is None:
            year = today.year
        
        # 월의 첫 날과 마지막 날 계산
        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year
        
        start_date = datetime(year, month, 1, 0, 0, 0)
        end_date = datetime(next_year, next_month, 1, 0, 0, 0) - timedelta(seconds=1)
        
        # 보고서 제목
        title = f"월간 성능 보고서: {year}년 {month}월"
        if strategy:
            title += f" - {strategy}"
        
        # 보고서 파일 경로
        filename = f"monthly_report_{year}{month:02d}"
        if strategy:
            filename += f"_{strategy}"
        filename += ".html"
        
        output_file = self.output_dir / filename
        
        return self._generate_report(start_date, end_date, title, str(output_file), strategy)
    
    def generate_custom_report(self, start_date: datetime, end_date: datetime, title: str, 
                             output_file: str, strategy: Optional[str] = None) -> Optional[str]:
        """
        커스텀 보고서 생성
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            title: 보고서 제목
            output_file: 출력 파일 경로
            strategy: 전략 이름
            
        Returns:
            Optional[str]: 보고서 파일 경로
        """
        return self._generate_report(start_date, end_date, title, output_file, strategy)
    
    def _generate_report(self, start_date: datetime, end_date: datetime, title: str, 
                        output_file: str, strategy: Optional[str] = None) -> Optional[str]:
        """
        보고서 생성 내부 메서드
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            title: 보고서 제목
            output_file: 출력 파일 경로
            strategy: 전략 이름
            
        Returns:
            Optional[str]: 보고서 파일 경로
        """
        try:
            # 거래 데이터 가져오기
            trades_df = self.visualizer.get_trades_from_db(start_date, end_date, strategy)
            
            if trades_df.empty:
                logger.warning(f"보고서 기간 ({start_date} ~ {end_date})에 거래 데이터가 없습니다.")
                return None
            
            # 성능 지표 계산
            metrics = self.performance_analyzer.calculate_metrics(trades_df)
            
            # 보고서 생성
            report_path = self.visualizer.generate_performance_report(trades_df, metrics, output_file)
            
            if report_path:
                logger.info(f"보고서가 생성되었습니다: {report_path}")
                
                # 텔레그램 알림 전송 (텔레그램 모듈이 있는 경우)
                try:
                    from src.notifications.telegram import TelegramNotifier
                    
                    telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                    telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
                    
                    if telegram_token and telegram_chat_id:
                        telegram = TelegramNotifier(telegram_token, telegram_chat_id)
                        
                        # 요약 정보 생성
                        summary = {
                            'title': title,
                            'period': f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}",
                            'total_trades': metrics['total_trades'],
                            'win_rate': f"{metrics['win_rate'] * 100:.2f}%",
                            'profit_factor': f"{metrics['profit_factor']:.2f}",
                            'total_profit': f"{trades_df['pnl'].sum():.2f} USDT",
                            'max_drawdown': f"{metrics['max_drawdown'] * 100:.2f}%"
                        }
                        
                        # 메시지 구성
                        message = f"📊 *{summary['title']}*\n\n"
                        message += f"기간: {summary['period']}\n"
                        message += f"총 거래 수: {summary['total_trades']}\n"
                        message += f"승률: {summary['win_rate']}\n"
                        message += f"수익 요소: {summary['profit_factor']}\n"
                        message += f"총 수익: {summary['total_profit']}\n"
                        message += f"최대 드로다운: {summary['max_drawdown']}\n\n"
                        message += f"자세한 내용은 보고서를 참조하세요."
                        
                        telegram.send_message(message)
                        logger.info("보고서 요약이 텔레그램으로 전송되었습니다.")
                except Exception as e:
                    logger.warning(f"텔레그램 알림 전송 실패: {e}")
                
                return report_path
            else:
                logger.error("보고서 생성에 실패했습니다.")
                return None
                
        except Exception as e:
            logger.error(f"보고서 생성 중 오류 발생: {e}")
            return None
    
    def schedule_reports(self):
        """
        보고서 생성 스케줄링
        
        일일, 주간, 월간 보고서를 자동으로 생성하도록 스케줄링합니다.
        """
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
            
            scheduler = BackgroundScheduler()
            
            # 일일 보고서 (매일 오전 1시)
            scheduler.add_job(
                self.generate_daily_report,
                CronTrigger(hour=1, minute=0),
                args=[datetime.now() - timedelta(days=1)],
                id='daily_report',
                replace_existing=True
            )
            
            # 주간 보고서 (매주 월요일 오전 2시)
            scheduler.add_job(
                self.generate_weekly_report,
                CronTrigger(day_of_week='mon', hour=2, minute=0),
                id='weekly_report',
                replace_existing=True
            )
            
            # 월간 보고서 (매월 1일 오전 3시)
            scheduler.add_job(
                self.generate_monthly_report,
                CronTrigger(day=1, hour=3, minute=0),
                id='monthly_report',
                replace_existing=True
            )
            
            scheduler.start()
            logger.info("보고서 생성 스케줄러가 시작되었습니다.")
            
            return scheduler
            
        except Exception as e:
            logger.error(f"보고서 스케줄링 실패: {e}")
            return None
