"""
알림 시스템 API 모듈

이 모듈은 성능 분석 엔진과 알림 시스템을 통합하는 API 엔드포인트를 제공합니다.
FastAPI를 사용하여 알림 시스템을 관리하고 성능 보고서를 전송할 수 있습니다.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path
from pydantic import BaseModel, Field

from src.notifications.manager import NotificationManager
from src.notifications.handlers import EventType
from src.analytics.performance import PerformanceAnalyzer
from src.analytics.reporting import ReportGenerator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API 라우터 생성
router = APIRouter(
    prefix="/api/v1/notifications",
    tags=["notifications"],
    responses={404: {"description": "Not found"}},
)

# 모델 정의
class NotificationBase(BaseModel):
    """알림 기본 모델"""
    message: str = Field(..., description="알림 메시지")
    level: str = Field("info", description="알림 레벨 (info, warning, error)")
    immediate: bool = Field(False, description="즉시 전송 여부")

class TradeNotification(BaseModel):
    """거래 알림 모델"""
    trade_id: str = Field(..., description="거래 ID")
    pair: str = Field(..., description="거래 페어")
    side: str = Field(..., description="거래 방향 (buy, sell)")
    entry_price: float = Field(..., description="진입 가격")
    quantity: float = Field(..., description="거래 수량")
    stop_loss: Optional[float] = Field(None, description="손절가")
    take_profit: Optional[float] = Field(None, description="이익실현가")
    strategy: Optional[str] = Field(None, description="전략 이름")
    status: str = Field(..., description="거래 상태 (open, closed)")
    exit_price: Optional[float] = Field(None, description="청산 가격")
    pnl: Optional[float] = Field(None, description="손익")
    pnl_pct: Optional[float] = Field(None, description="손익률 (%)")
    duration: Optional[str] = Field(None, description="거래 기간")
    immediate: bool = Field(False, description="즉시 전송 여부")

class OrderNotification(BaseModel):
    """주문 알림 모델"""
    order_id: str = Field(..., description="주문 ID")
    symbol: str = Field(..., description="심볼")
    side: str = Field(..., description="주문 방향 (buy, sell)")
    order_type: str = Field(..., description="주문 유형 (limit, market)")
    quantity: float = Field(..., description="주문 수량")
    price: Optional[float] = Field(None, description="주문 가격")
    status: str = Field(..., description="주문 상태 (new, filled, canceled)")
    reason: Optional[str] = Field(None, description="취소 이유")
    immediate: bool = Field(False, description="즉시 전송 여부")

class RiskNotification(BaseModel):
    """리스크 알림 모델"""
    alert_type: str = Field(..., description="알림 유형 (drawdown, kill_switch, circuit_breaker)")
    value: float = Field(..., description="현재 값")
    threshold: float = Field(..., description="임계값")
    description: Optional[str] = Field(None, description="설명")
    immediate: bool = Field(True, description="즉시 전송 여부")

class SystemNotification(BaseModel):
    """시스템 알림 모델"""
    component: str = Field(..., description="컴포넌트 이름")
    status: str = Field(..., description="상태 (ok, error, warning, info)")
    description: Optional[str] = Field(None, description="설명")
    immediate: bool = Field(False, description="즉시 전송 여부")

class PerformanceNotification(BaseModel):
    """성능 알림 모델"""
    period: str = Field(..., description="기간 (daily, weekly, monthly)")
    total_trades: int = Field(..., description="총 거래 수")
    win_rate: float = Field(..., description="승률 (%)")
    profit_factor: float = Field(..., description="수익 요소")
    total_profit: float = Field(..., description="총 수익 (USDT)")
    max_drawdown: float = Field(..., description="최대 드로다운 (%)")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe 비율")
    calmar_ratio: Optional[float] = Field(None, description="Calmar 비율")
    immediate: bool = Field(False, description="즉시 전송 여부")

class NotificationStatus(BaseModel):
    """알림 상태 모델"""
    is_running: bool = Field(..., description="실행 상태")
    telegram_active: bool = Field(..., description="텔레그램 활성화 상태")
    redis_publisher_connected: bool = Field(..., description="Redis 발행자 연결 상태")
    redis_subscriber_connected: bool = Field(..., description="Redis 구독자 연결 상태")
    notification_count: int = Field(..., description="알림 수")
    start_time: str = Field(..., description="시작 시간")
    uptime_seconds: float = Field(..., description="가동 시간 (초)")
    queue_size: int = Field(..., description="큐 크기")

# 알림 관리자 의존성
def get_notification_manager():
    """알림 관리자 가져오기"""
    return NotificationManager()

# 성능 분석기 의존성
def get_performance_analyzer():
    """성능 분석기 가져오기"""
    return PerformanceAnalyzer()

# 보고서 생성기 의존성
def get_report_generator():
    """보고서 생성기 가져오기"""
    return ReportGenerator()

# API 엔드포인트
@router.post("/general", response_model=dict)
async def send_general_notification(
    notification: NotificationBase,
    background_tasks: BackgroundTasks,
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """일반 알림 전송"""
    try:
        if notification.level.lower() == "error":
            success = notification_manager.send_error(notification.message, notification.immediate)
        elif notification.level.lower() == "warning":
            success = notification_manager.send_warning(notification.message, notification.immediate)
        else:
            success = notification_manager.send_info(notification.message, notification.immediate)
        
        return {"success": success, "message": "알림이 전송되었습니다."}
    except Exception as e:
        logger.error(f"알림 전송 실패: {e}")
        raise HTTPException(status_code=500, detail=f"알림 전송 실패: {str(e)}")

@router.post("/trade", response_model=dict)
async def send_trade_notification(
    notification: TradeNotification,
    background_tasks: BackgroundTasks,
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """거래 알림 전송"""
    try:
        data = notification.dict()
        
        if notification.status.lower() == "open":
            success = notification_manager.send_trade_open_notification(data, notification.immediate)
        else:
            success = notification_manager.send_trade_close_notification(data, notification.immediate)
        
        return {"success": success, "message": "거래 알림이 전송되었습니다."}
    except Exception as e:
        logger.error(f"거래 알림 전송 실패: {e}")
        raise HTTPException(status_code=500, detail=f"거래 알림 전송 실패: {str(e)}")

@router.post("/order", response_model=dict)
async def send_order_notification(
    notification: OrderNotification,
    background_tasks: BackgroundTasks,
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """주문 알림 전송"""
    try:
        data = notification.dict()
        success = notification_manager.send_order_notification(data, notification.immediate)
        
        return {"success": success, "message": "주문 알림이 전송되었습니다."}
    except Exception as e:
        logger.error(f"주문 알림 전송 실패: {e}")
        raise HTTPException(status_code=500, detail=f"주문 알림 전송 실패: {str(e)}")

@router.post("/risk", response_model=dict)
async def send_risk_notification(
    notification: RiskNotification,
    background_tasks: BackgroundTasks,
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """리스크 알림 전송"""
    try:
        data = notification.dict()
        success = notification_manager.send_risk_alert(data, notification.immediate)
        
        return {"success": success, "message": "리스크 알림이 전송되었습니다."}
    except Exception as e:
        logger.error(f"리스크 알림 전송 실패: {e}")
        raise HTTPException(status_code=500, detail=f"리스크 알림 전송 실패: {str(e)}")

@router.post("/system", response_model=dict)
async def send_system_notification(
    notification: SystemNotification,
    background_tasks: BackgroundTasks,
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """시스템 알림 전송"""
    try:
        data = notification.dict()
        success = notification_manager.send_system_status(data, notification.immediate)
        
        return {"success": success, "message": "시스템 알림이 전송되었습니다."}
    except Exception as e:
        logger.error(f"시스템 알림 전송 실패: {e}")
        raise HTTPException(status_code=500, detail=f"시스템 알림 전송 실패: {str(e)}")

@router.post("/performance", response_model=dict)
async def send_performance_notification(
    notification: PerformanceNotification,
    background_tasks: BackgroundTasks,
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """성능 알림 전송"""
    try:
        data = notification.dict()
        success = notification_manager.send_performance_update(data, notification.immediate)
        
        return {"success": success, "message": "성능 알림이 전송되었습니다."}
    except Exception as e:
        logger.error(f"성능 알림 전송 실패: {e}")
        raise HTTPException(status_code=500, detail=f"성능 알림 전송 실패: {str(e)}")

@router.post("/report/{report_type}", response_model=dict)
async def generate_and_send_report(
    report_type: str = Path(..., description="보고서 유형 (daily, weekly, monthly)"),
    strategy: Optional[str] = Query(None, description="전략 이름"),
    report_date: Optional[str] = Query(None, description="보고서 날짜 (YYYY-MM-DD)"),
    background_tasks: BackgroundTasks = None,
    report_generator: ReportGenerator = Depends(get_report_generator),
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """보고서 생성 및 전송"""
    try:
        # 날짜 파싱
        if report_date:
            try:
                parsed_date = datetime.strptime(report_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="날짜 형식이 잘못되었습니다. YYYY-MM-DD 형식을 사용하세요.")
        else:
            parsed_date = date.today()
        
        # 보고서 유형에 따라 생성
        report_path = None
        if report_type.lower() == "daily":
            report_path = report_generator.generate_daily_report(parsed_date, strategy)
        elif report_type.lower() == "weekly":
            report_path = report_generator.generate_weekly_report(parsed_date, strategy)
        elif report_type.lower() == "monthly":
            report_path = report_generator.generate_monthly_report(parsed_date.year, parsed_date.month, strategy)
        else:
            raise HTTPException(status_code=400, detail="지원되지 않는 보고서 유형입니다. daily, weekly, monthly 중 하나를 사용하세요.")
        
        if not report_path:
            raise HTTPException(status_code=404, detail="보고서 생성에 실패했습니다.")
        
        # 성능 지표 계산
        performance_analyzer = get_performance_analyzer()
        metrics = performance_analyzer.get_metrics_for_period(report_type.lower(), parsed_date, strategy)
        
        if metrics:
            # 알림 데이터 구성
            notification_data = {
                "period": f"{report_type} ({parsed_date})",
                "total_trades": metrics.get("total_trades", 0),
                "win_rate": metrics.get("win_rate", 0.0),
                "profit_factor": metrics.get("profit_factor", 0.0),
                "total_profit": metrics.get("total_profit", 0.0),
                "max_drawdown": metrics.get("max_drawdown", 0.0),
                "sharpe_ratio": metrics.get("sharpe_ratio"),
                "calmar_ratio": metrics.get("calmar_ratio"),
                "report_path": report_path
            }
            
            # 알림 전송
            success = notification_manager.send_performance_update(notification_data, True)
            
            return {
                "success": success,
                "message": f"{report_type.capitalize()} 보고서가 생성되고 알림이 전송되었습니다.",
                "report_path": report_path,
                "metrics": metrics
            }
        else:
            raise HTTPException(status_code=404, detail="해당 기간에 대한 성능 지표를 찾을 수 없습니다.")
    except Exception as e:
        logger.error(f"보고서 생성 및 전송 실패: {e}")
        raise HTTPException(status_code=500, detail=f"보고서 생성 및 전송 실패: {str(e)}")

@router.get("/status", response_model=NotificationStatus)
async def get_notification_status(
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """알림 시스템 상태 가져오기"""
    try:
        status = notification_manager.get_status()
        return status
    except Exception as e:
        logger.error(f"알림 상태 가져오기 실패: {e}")
        raise HTTPException(status_code=500, detail=f"알림 상태 가져오기 실패: {str(e)}")

@router.post("/start", response_model=dict)
async def start_notification_system(
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """알림 시스템 시작"""
    try:
        success = notification_manager.start()
        return {"success": success, "message": "알림 시스템이 시작되었습니다." if success else "알림 시스템 시작에 실패했습니다."}
    except Exception as e:
        logger.error(f"알림 시스템 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=f"알림 시스템 시작 실패: {str(e)}")

@router.post("/stop", response_model=dict)
async def stop_notification_system(
    notification_manager: NotificationManager = Depends(get_notification_manager)
):
    """알림 시스템 중지"""
    try:
        success = notification_manager.stop()
        return {"success": success, "message": "알림 시스템이 중지되었습니다." if success else "알림 시스템 중지에 실패했습니다."}
    except Exception as e:
        logger.error(f"알림 시스템 중지 실패: {e}")
        raise HTTPException(status_code=500, detail=f"알림 시스템 중지 실패: {str(e)}")
