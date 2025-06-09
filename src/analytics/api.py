"""
성능 분석 API 모듈

이 모듈은 성능 분석 엔진의 API 인터페이스를 제공합니다.
FastAPI 엔드포인트를 통해 성능 지표 및 보고서에 접근할 수 있습니다.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.analytics.performance import PerformanceAnalyzer
from src.analytics.visualization import PerformanceVisualizer
from src.analytics.reporting import ReportGenerator
from src.database.connection import get_db_manager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API 라우터 생성
router = APIRouter(prefix="/analytics", tags=["analytics"])

# 모델 정의
class PerformanceMetricsResponse(BaseModel):
    """성능 지표 응답 모델"""
    period: str
    total_trades: int
    win_rate: float
    profit_factor: float
    average_profit: float
    average_profit_percent: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    volatility: float
    expectancy: float
    recovery_factor: float
    profit_to_drawdown: float

class ReportGenerationRequest(BaseModel):
    """보고서 생성 요청 모델"""
    report_type: str  # daily, weekly, monthly, custom
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    strategy: Optional[str] = None
    title: Optional[str] = None

class ReportGenerationResponse(BaseModel):
    """보고서 생성 응답 모델"""
    success: bool
    report_path: Optional[str] = None
    message: Optional[str] = None

# 글로벌 인스턴스
db_manager = get_db_manager()
performance_analyzer = PerformanceAnalyzer(db_manager)
visualizer = PerformanceVisualizer(db_manager)
report_generator = ReportGenerator(db_manager)

# DEAD CODE: @router.get("/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    days: int = Query(30, description="분석할 일수"),
    strategy: Optional[str] = Query(None, description="전략 이름"),
    pair: Optional[str] = Query(None, description="거래 페어")
):
    """
    성능 지표 가져오기
    
    Args:
        days: 분석할 일수
        strategy: 전략 이름
        pair: 거래 페어
        
    Returns:
        PerformanceMetricsResponse: 성능 지표 응답
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        metrics = performance_analyzer.analyze_performance(start_date, end_date, strategy, pair)
        
        if not metrics:
            raise HTTPException(status_code=404, detail="성능 지표를 찾을 수 없습니다.")
        
        response = PerformanceMetricsResponse(
            period=f"최근 {days}일",
            total_trades=metrics.get('total_trades', 0),
            win_rate=metrics.get('win_rate', 0),
            profit_factor=metrics.get('profit_factor', 0),
            average_profit=metrics.get('average_profit', 0),
            average_profit_percent=metrics.get('average_profit_percent', 0),
            sharpe_ratio=metrics.get('sharpe_ratio', 0),
            sortino_ratio=metrics.get('sortino_ratio', 0),
            calmar_ratio=metrics.get('calmar_ratio', 0),
            max_drawdown=metrics.get('max_drawdown', 0),
            max_drawdown_duration=metrics.get('max_drawdown_duration', 0),
            volatility=metrics.get('volatility', 0),
            expectancy=metrics.get('expectancy', 0),
            recovery_factor=metrics.get('recovery_factor', 0),
            profit_to_drawdown=metrics.get('profit_to_drawdown', 0)
        )
        
        return response
        
    except Exception as e:
        logger.error(f"성능 지표 가져오기 실패: {e}")
        raise HTTPException(status_code=500, detail=f"성능 지표 가져오기 실패: {str(e)}")

# DEAD CODE: @router.post("/reports", response_model=ReportGenerationResponse)
async def generate_report(
    request: ReportGenerationRequest,
# DEAD CODE:     background_tasks: BackgroundTasks
):
    """
    보고서 생성
    
    Args:
        request: 보고서 생성 요청
        background_tasks: 백그라운드 작업
        
    Returns:
        ReportGenerationResponse: 보고서 생성 응답
    """
    try:
        report_path = None
        
        if request.report_type == "daily":
            # 일일 보고서
            date = request.start_date or (datetime.now() - timedelta(days=1))
            report_path = report_generator.generate_daily_report(date, request.strategy)
            
        elif request.report_type == "weekly":
            # 주간 보고서
            week_end_date = request.end_date or (datetime.now() - timedelta(days=datetime.now().weekday() + 1))
            report_path = report_generator.generate_weekly_report(week_end_date, request.strategy)
            
        elif request.report_type == "monthly":
            # 월간 보고서
            if request.start_date:
                month = request.start_date.month
                year = request.start_date.year
            else:
                today = datetime.now()
                month = today.month - 1
                if month == 0:
                    month = 12
                    year = today.year - 1
                else:
                    year = today.year
                    
            report_path = report_generator.generate_monthly_report(month, year, request.strategy)
            
        elif request.report_type == "custom":
            # 커스텀 보고서
            if not request.start_date or not request.end_date:
                raise HTTPException(status_code=400, detail="커스텀 보고서에는 시작 날짜와 종료 날짜가 필요합니다.")
                
            title = request.title or f"커스텀 보고서: {request.start_date.strftime('%Y-%m-%d')} ~ {request.end_date.strftime('%Y-%m-%d')}"
            
            # 출력 파일 경로 생성
            filename = f"custom_report_{request.start_date.strftime('%Y%m%d')}_{request.end_date.strftime('%Y%m%d')}"
            if request.strategy:
                filename += f"_{request.strategy}"
            filename += ".html"
            
            output_file = str(report_generator.output_dir / filename)
            
            report_path = report_generator.generate_custom_report(
                request.start_date, request.end_date, title, output_file, request.strategy
            )
            
        else:
            raise HTTPException(status_code=400, detail=f"알 수 없는 보고서 유형: {request.report_type}")
        
        if report_path:
            return ReportGenerationResponse(
                success=True,
                report_path=report_path,
                message="보고서가 성공적으로 생성되었습니다."
            )
        else:
            return ReportGenerationResponse(
                success=False,
                message="보고서 생성에 실패했습니다. 로그를 확인하세요."
            )
            
    except Exception as e:
        logger.error(f"보고서 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"보고서 생성 실패: {str(e)}")

@router.get("/reports/schedule")
async def schedule_reports():
    """
    보고서 생성 스케줄링
    
    Returns:
        Dict[str, Any]: 스케줄링 결과
    """
    try:
        scheduler = report_generator.schedule_reports()
        
        if scheduler:
            return {
                "success": True,
                "message": "보고서 생성 스케줄러가 시작되었습니다.",
                "jobs": [job.id for job in scheduler.get_jobs()]
            }
        else:
            return {
                "success": False,
                "message": "보고서 생성 스케줄러 시작에 실패했습니다."
            }
            
    except Exception as e:
        logger.error(f"보고서 스케줄링 실패: {e}")
        raise HTTPException(status_code=500, detail=f"보고서 스케줄링 실패: {str(e)}")

@router.get("/summary")
async def get_performance_summary(
    days: int = Query(30, description="분석할 일수"),
    strategy: Optional[str] = Query(None, description="전략 이름")
):
    """
    성능 요약 정보 가져오기
    
    Args:
        days: 분석할 일수
        strategy: 전략 이름
        
    Returns:
        Dict[str, Any]: 성능 요약 정보
    """
    try:
        summary = performance_analyzer.get_performance_summary(days, strategy)
        
        if not summary:
            raise HTTPException(status_code=404, detail="성능 요약 정보를 찾을 수 없습니다.")
        
        return summary
        
    except Exception as e:
        logger.error(f"성능 요약 정보 가져오기 실패: {e}")
        raise HTTPException(status_code=500, detail=f"성능 요약 정보 가져오기 실패: {str(e)}")
