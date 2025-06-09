"""
알림 템플릿 모듈

이 모듈은 텔레그램 알림을 위한 템플릿을 제공합니다.
다양한 이벤트 유형에 대한 일관된 메시지 형식을 정의합니다.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from jinja2 import Template

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NotificationTemplates:
    """알림 템플릿 클래스"""
    
    # 거래 시작 템플릿
    TRADE_OPEN_TEMPLATE = """
🟢 <b>새로운 거래 시작</b>
ID: <code>{{ trade_id }}</code>
페어: <code>{{ pair }}</code>
방향: <code>{{ side }}</code>
진입가: <code>{{ entry_price }}</code>
수량: <code>{{ quantity }}</code>
{% if stop_loss %}손절가: <code>{{ stop_loss }}</code>{% endif %}
{% if take_profit %}이익실현가: <code>{{ take_profit }}</code>{% endif %}
{% if strategy %}전략: <code>{{ strategy }}</code>{% endif %}
시간: <code>{{ timestamp }}</code>
    """
    
    # 거래 종료 템플릿
    TRADE_CLOSE_TEMPLATE = """
{% if pnl > 0 %}✅{% else %}❌{% endif %} <b>거래 종료</b>
ID: <code>{{ trade_id }}</code>
페어: <code>{{ pair }}</code>
방향: <code>{{ side }}</code>
진입가: <code>{{ entry_price }}</code>
청산가: <code>{{ exit_price }}</code>
수량: <code>{{ quantity }}</code>
손익: <code>{{ pnl }} USDT ({{ pnl_pct }}%)</code>
{% if strategy %}전략: <code>{{ strategy }}</code>{% endif %}
거래 기간: <code>{{ duration }}</code>
시간: <code>{{ timestamp }}</code>
    """
    
    # 주문 생성 템플릿
    ORDER_PLACED_TEMPLATE = """
{% if side == 'BUY' %}🟢{% else %}🔴{% endif %} <b>주문 생성</b>
ID: <code>{{ order_id }}</code>
심볼: <code>{{ symbol }}</code>
방향: <code>{{ side }}</code>
유형: <code>{{ order_type }}</code>
수량: <code>{{ quantity }}</code>
{% if price %}가격: <code>{{ price }}</code>{% endif %}
시간: <code>{{ timestamp }}</code>
    """
    
    # 주문 체결 템플릿
    ORDER_FILLED_TEMPLATE = """
{% if side == 'BUY' %}✅{% else %}💰{% endif %} <b>주문 체결</b>
ID: <code>{{ order_id }}</code>
심볼: <code>{{ symbol }}</code>
방향: <code>{{ side }}</code>
수량: <code>{{ quantity }}</code>
가격: <code>{{ price }}</code>
시간: <code>{{ timestamp }}</code>
    """
    
    # 주문 취소 템플릿
    ORDER_CANCELED_TEMPLATE = """
❌ <b>주문 취소</b>
ID: <code>{{ order_id }}</code>
심볼: <code>{{ symbol }}</code>
이유: <code>{{ reason }}</code>
시간: <code>{{ timestamp }}</code>
    """
    
    # 리스크 알림 템플릿
    RISK_ALERT_TEMPLATE = """
{% if alert_type == 'kill_switch' %}🔴{% elif alert_type == 'circuit_breaker' %}🟠{% else %}⚠️{% endif %} <b>리스크 알림</b>
유형: <code>{{ alert_type }}</code>
값: <code>{{ value }}</code>
임계값: <code>{{ threshold }}</code>
{% if description %}설명: {{ description }}{% endif %}
시간: <code>{{ timestamp }}</code>
    """
    
    # 시스템 상태 템플릿
    SYSTEM_STATUS_TEMPLATE = """
{% if status == 'error' %}🔴{% elif status == 'warning' %}🟠{% elif status == 'info' %}🔵{% else %}🟢{% endif %} <b>시스템 상태</b>
컴포넌트: <code>{{ component }}</code>
상태: <code>{{ status }}</code>
{% if description %}설명: {{ description }}{% endif %}
시간: <code>{{ timestamp }}</code>
    """
    
    # 성능 보고서 템플릿
    PERFORMANCE_REPORT_TEMPLATE = """
📊 <b>성능 보고서</b>
기간: <code>{{ period }}</code>
총 거래 수: <code>{{ total_trades }}</code>
승률: <code>{{ win_rate }}%</code>
수익 요소: <code>{{ profit_factor }}</code>
총 수익: <code>{{ total_profit }} USDT</code>
최대 드로다운: <code>{{ max_drawdown }}%</code>
{% if sharpe_ratio %}Sharpe 비율: <code>{{ sharpe_ratio }}</code>{% endif %}
{% if calmar_ratio %}Calmar 비율: <code>{{ calmar_ratio }}</code>{% endif %}
시간: <code>{{ timestamp }}</code>
    """
    
    # 오류 템플릿
    ERROR_TEMPLATE = """
🔴 <b>오류 발생</b>
{{ message }}
시간: <code>{{ timestamp }}</code>
    """
    
    # 경고 템플릿
    WARNING_TEMPLATE = """
⚠️ <b>경고</b>
{{ message }}
시간: <code>{{ timestamp }}</code>
    """
    
    # 정보 템플릿
    INFO_TEMPLATE = """
ℹ️ <b>정보</b>
{{ message }}
시간: <code>{{ timestamp }}</code>
    """
    
    @staticmethod
    def render_template(template_string: str, data: Dict[str, Any]) -> str:
        """
        템플릿 렌더링
        
        Args:
            template_string: 템플릿 문자열
            data: 템플릿 데이터
            
        Returns:
            str: 렌더링된 메시지
        """
        try:
            # 타임스탬프 추가
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
            template = Template(template_string)
            rendered = template.render(**data)
            
            # 빈 줄 제거 및 공백 정리
            lines = [line.strip() for line in rendered.split('\n') if line.strip()]
            return '\n'.join(lines)
            
        except Exception as e:
            logger.error(f"템플릿 렌더링 실패: {e}")
            return f"템플릿 렌더링 오류: {str(e)}"
    
    @classmethod
    def trade_open(cls, data: Dict[str, Any]) -> str:
        """
        거래 시작 메시지 생성
        
        Args:
            data: 거래 데이터
            
        Returns:
            str: 렌더링된 메시지
        """
        return cls.render_template(cls.TRADE_OPEN_TEMPLATE, data)
    
    @classmethod
    def trade_close(cls, data: Dict[str, Any]) -> str:
        """
        거래 종료 메시지 생성
        
        Args:
            data: 거래 데이터
            
        Returns:
            str: 렌더링된 메시지
        """
        return cls.render_template(cls.TRADE_CLOSE_TEMPLATE, data)
    
    @classmethod
    def order_placed(cls, data: Dict[str, Any]) -> str:
        """
        주문 생성 메시지 생성
        
        Args:
            data: 주문 데이터
            
        Returns:
            str: 렌더링된 메시지
        """
        return cls.render_template(cls.ORDER_PLACED_TEMPLATE, data)
    
    @classmethod
    def order_filled(cls, data: Dict[str, Any]) -> str:
        """
        주문 체결 메시지 생성
        
        Args:
            data: 주문 데이터
            
        Returns:
            str: 렌더링된 메시지
        """
        return cls.render_template(cls.ORDER_FILLED_TEMPLATE, data)
    
    @classmethod
    def order_canceled(cls, data: Dict[str, Any]) -> str:
        """
        주문 취소 메시지 생성
        
        Args:
            data: 주문 데이터
            
        Returns:
            str: 렌더링된 메시지
        """
        return cls.render_template(cls.ORDER_CANCELED_TEMPLATE, data)
    
    @classmethod
    def risk_alert(cls, data: Dict[str, Any]) -> str:
        """
        리스크 알림 메시지 생성
        
        Args:
            data: 리스크 데이터
            
        Returns:
            str: 렌더링된 메시지
        """
        return cls.render_template(cls.RISK_ALERT_TEMPLATE, data)
    
    @classmethod
    def system_status(cls, data: Dict[str, Any]) -> str:
        """
        시스템 상태 메시지 생성
        
        Args:
            data: 시스템 상태 데이터
            
        Returns:
            str: 렌더링된 메시지
        """
        return cls.render_template(cls.SYSTEM_STATUS_TEMPLATE, data)
    
    @classmethod
    def performance_report(cls, data: Dict[str, Any]) -> str:
        """
        성능 보고서 메시지 생성
        
        Args:
            data: 성능 데이터
            
        Returns:
            str: 렌더링된 메시지
        """
        return cls.render_template(cls.PERFORMANCE_REPORT_TEMPLATE, data)
    
    @classmethod
    def error(cls, message: str) -> str:
        """
        오류 메시지 생성
        
        Args:
            message: 오류 메시지
            
        Returns:
            str: 렌더링된 메시지
        """
        return cls.render_template(cls.ERROR_TEMPLATE, {'message': message})
    
    @classmethod
    def warning(cls, message: str) -> str:
        """
        경고 메시지 생성
        
        Args:
            message: 경고 메시지
            
        Returns:
            str: 렌더링된 메시지
        """
        return cls.render_template(cls.WARNING_TEMPLATE, {'message': message})
    
    @classmethod
    def info(cls, message: str) -> str:
        """
        정보 메시지 생성
        
        Args:
            message: 정보 메시지
            
        Returns:
            str: 렌더링된 메시지
        """
        return cls.render_template(cls.INFO_TEMPLATE, {'message': message})
