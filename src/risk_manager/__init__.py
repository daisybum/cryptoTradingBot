"""
위험 관리 모듈 - 글로벌 드로다운 보호, 거래별 손절, 포지션 크기 조정
"""

from src.risk_manager.risk_manager import RiskManager, init_risk_manager, get_risk_manager
from src.risk_manager.api import app as risk_api_app

__all__ = ['RiskManager', 'init_risk_manager', 'get_risk_manager', 'risk_api_app']
