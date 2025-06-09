"""
리스크 관리 시스템 - NASOSv5_mod3 전략과 통합
"""
import logging
import numpy as np
from typing import Dict, Any, Optional
import json

# Redis 의존성을 선택적으로 만듦
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

class RiskManager:
    """
    리스크 관리 클래스 - Kelly Criterion 기반 포지션 크기 조정 및 글로벌 드로다운 보호 기능 제공
    """
    def __init__(self, max_drawdown_allowed: float = 0.03, 
                 risk_free_rate: float = 0.01,
                 use_redis: bool = True,
                 redis_host: str = '127.0.0.1',
                 redis_port: int = 6379,
                 max_risk_per_trade: float = 0.005,
                 max_open_trades: int = 3):
        """
        리스크 관리자 초기화
        
        Args:
            max_drawdown_allowed: 허용 가능한 최대 드로다운 (기본값: 8%)
            risk_free_rate: 무위험 수익률 (기본값: 1%)
            use_redis: Redis 사용 여부
            redis_host: Redis 호스트
            redis_port: Redis 포트
        """
        self.max_drawdown_allowed = max_drawdown_allowed
        self.risk_free_rate = risk_free_rate
        self.use_redis = use_redis and REDIS_AVAILABLE  # Redis 모듈이 없으면 사용 불가
        
        # Redis 연결 설정
        if self.use_redis and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)
                self.redis_client.ping()
                logger.info("Redis 서버에 성공적으로 연결되었습니다.")
            except Exception as e:
                logger.warning(f"Redis 서버에 연결할 수 없습니다: {e}. 로컬 모드로 전환합니다.")
                self.use_redis = False
        
        # 거래 통계 초기화
        self.trade_stats = {
            'win_rate': 0.5,  # 기본 승률 50%
            'avg_win': 0.03,  # 기본 평균 수익 3%
            'avg_loss': 0.05,  # 기본 평균 손실 5%
            'total_trades': 0,
            'wins': 0,
            'losses': 0
        }
        
        # 계좌 정보 초기화
        self.account_info = {
            'balance': 1000.0,
            'peak_balance': 1000.0,
            'current_drawdown': 0.0,
            'max_drawdown': 0.0,
            'circuit_breaker_active': False
        }
        
        # Redis에서 상태 복원
        if self.use_redis:
            self._restore_state_from_redis()
    
    def _restore_state_from_redis(self):
        """Redis에서 상태 정보 복원"""
        if not self.use_redis or not REDIS_AVAILABLE:
            logger.info("Redis를 사용하지 않아 상태 복원을 건너뜁니다.")
            return
            
        try:
            trade_stats = self.redis_client.get('risk_manager:trade_stats')
            if trade_stats:
                self.trade_stats = json.loads(trade_stats)
            
            account_info = self.redis_client.get('risk_manager:account_info')
            if account_info:
                self.account_info = json.loads(account_info)
                
            logger.info("Redis에서 리스크 관리자 상태를 복원했습니다.")
        except Exception as e:
            logger.error(f"Redis에서 상태 복원 중 오류 발생: {e}")
    
    def _save_state_to_redis(self):
        """Redis에 상태 정보 저장"""
        if not self.use_redis or not REDIS_AVAILABLE:
            return
            
        try:
            self.redis_client.set('risk_manager:trade_stats', json.dumps(self.trade_stats))
            self.redis_client.set('risk_manager:account_info', json.dumps(self.account_info))
            self.redis_client.publish('risk_events', json.dumps({
                'event': 'state_updated',
                'trade_stats': self.trade_stats,
                'account_info': self.account_info
            }))
        except Exception as e:
            logger.error(f"Redis에 상태 저장 중 오류 발생: {e}")
            # Redis 연결 오류 발생 시 사용 중지
            self.use_redis = False
    
    def update_trade_stats(self, is_win: bool, profit_pct: float):
        """
        거래 결과로 통계 업데이트
        
        Args:
            is_win: 승리 여부
            profit_pct: 수익률 (%)
        """
        self.trade_stats['total_trades'] += 1
        
        if is_win:
            self.trade_stats['wins'] += 1
            # 수익 거래의 평균 수익률 업데이트 (지수 이동 평균)
            self.trade_stats['avg_win'] = (self.trade_stats['avg_win'] * 0.9) + (profit_pct * 0.1)
        else:
            self.trade_stats['losses'] += 1
            # 손실 거래의 평균 손실률 업데이트 (지수 이동 평균)
            self.trade_stats['avg_loss'] = (self.trade_stats['avg_loss'] * 0.9) + (abs(profit_pct) * 0.1)
        
        # 승률 업데이트
        if self.trade_stats['total_trades'] > 0:
            self.trade_stats['win_rate'] = self.trade_stats['wins'] / self.trade_stats['total_trades']
        
        # Redis에 상태 저장
        self._save_state_to_redis()
    
    def update_account_balance(self, new_balance: float):
        """
        계좌 잔액 업데이트 및 드로다운 계산
        
        Args:
            new_balance: 새로운 계좌 잔액
        """
        self.account_info['balance'] = new_balance
        
        # 최고 잔액 업데이트
        if new_balance > self.account_info['peak_balance']:
            self.account_info['peak_balance'] = new_balance
            self.account_info['current_drawdown'] = 0.0
        else:
            # 현재 드로다운 계산
            self.account_info['current_drawdown'] = 1.0 - (new_balance / self.account_info['peak_balance'])
            
            # 최대 드로다운 업데이트
            if self.account_info['current_drawdown'] > self.account_info['max_drawdown']:
                self.account_info['max_drawdown'] = self.account_info['current_drawdown']
        
        # 서킷 브레이커 확인
        if self.account_info['current_drawdown'] > self.max_drawdown_allowed:
            self.account_info['circuit_breaker_active'] = True
            if self.use_redis:
                self.redis_client.publish('risk_events', json.dumps({
                    'event': 'circuit_breaker_triggered',
                    'drawdown': self.account_info['current_drawdown'],
                    'threshold': self.max_drawdown_allowed
                }))
            logger.warning(f"서킷 브레이커 작동! 현재 드로다운: {self.account_info['current_drawdown']:.2%}")
        
        # Redis에 상태 저장
        self._save_state_to_redis()
        
        return self.account_info['circuit_breaker_active']
    
    def reset_circuit_breaker(self):
        """서킷 브레이커 재설정"""
        self.account_info['circuit_breaker_active'] = False
        if self.use_redis:
            self.redis_client.publish('risk_events', json.dumps({
                'event': 'circuit_breaker_reset'
            }))
        logger.info("서킷 브레이커가 재설정되었습니다.")
        
        # Redis에 상태 저장
        self._save_state_to_redis()
    
    def calculate_kelly_position_size(self, stake_amount: float, win_rate: Optional[float] = None, 
                                     avg_win: Optional[float] = None, avg_loss: Optional[float] = None) -> float:
        """
        Kelly Criterion 기반 최적 포지션 크기 계산
        
        Args:
            stake_amount: 기본 스테이크 금액
            win_rate: 승률 (None인 경우 저장된 통계 사용)
            avg_win: 평균 수익률 (None인 경우 저장된 통계 사용)
            avg_loss: 평균 손실률 (None인 경우 저장된 통계 사용)
            
        Returns:
            조정된 스테이크 금액
        """
        # 기본값이 제공되지 않은 경우 저장된 통계 사용
        win_rate = win_rate if win_rate is not None else self.trade_stats['win_rate']
        avg_win = avg_win if avg_win is not None else self.trade_stats['avg_win']
        avg_loss = avg_loss if avg_loss is not None else self.trade_stats['avg_loss']
        
        # Kelly 공식: f* = (p * b - q) / b
        # p: 승률, q: 패률 (1-p), b: 수익/손실 비율
        
        # 거래 데이터가 충분하지 않은 경우 기본 스테이크 금액 반환
        if self.trade_stats['total_trades'] < 10:
            return stake_amount
        
        # 손실이 0인 경우 (불가능한 상황) 기본 스테이크 금액 반환
        if avg_loss == 0:
            return stake_amount
            
        # 수익/손실 비율
        b = avg_win / avg_loss
        
        # 패률
        q = 1 - win_rate
        
        # Kelly 비율 계산
        kelly_ratio = (win_rate * b - q) / b
        
        # Kelly 비율이 음수인 경우 (기대 수익이 음수) 최소 스테이크 금액 반환
        if kelly_ratio <= 0:
            return stake_amount * 0.25  # 기본 스테이크의 25%
        
        # Kelly 비율에 안전 계수 적용 (Half Kelly)
        safe_kelly = kelly_ratio * 0.5
        
        # 최대 75%로 제한
        safe_kelly = min(safe_kelly, 0.75)
        
        # 드로다운에 따른 추가 조정
        drawdown_factor = 1.0 - (self.account_info['current_drawdown'] / self.max_drawdown_allowed)
        drawdown_factor = max(0.25, min(1.0, drawdown_factor))
        
        # 최종 조정된 스테이크 금액
        adjusted_stake = stake_amount * safe_kelly * drawdown_factor
        
        # 최소 스테이크 금액 보장
        adjusted_stake = max(stake_amount * 0.25, adjusted_stake)
        
        # 매우 작은 포지션 크기 거래 방지 (원래 금액의 20% 미만 시 거래 취소 플래그 설정)
        self.too_small_position = adjusted_stake < (stake_amount * 0.2)
        if self.too_small_position:
            logger.warning(f"포지션 크기가 너무 작습니다 (원래 금액의 {adjusted_stake/stake_amount:.1%}). 거래가 취소될 수 있습니다.")
            if self.use_redis:
                self.redis_client.publish('risk_events', json.dumps({
                    'event': 'position_too_small',
                    'ratio': adjusted_stake/stake_amount
                }))
        
        return adjusted_stake
    
    def get_market_condition(self, pair: str) -> str:
        """
        현재 시장 상황을 분석하여 반환합니다.
        
        Args:
            pair: 거래 쌍
            
        Returns:
            시장 상황 ('bullish', 'bearish', 'neutral', 'volatile')
        """
        # Redis에서 시장 상태 정보 가져오기
        if self.use_redis and REDIS_AVAILABLE:
            try:
                market_data = self.redis_client.get(f'market_condition:{pair}')
                if market_data:
                    return json.loads(market_data)['condition']
                    
                # 전체 시장 상태 확인
                market_data = self.redis_client.get('market_condition:global')
                if market_data:
                    return json.loads(market_data)['condition']
            except Exception as e:
                logger.warning(f"Redis에서 시장 상태 정보를 가져오는 중 오류 발생: {e}")
        
        # 기본값은 중립(neutral)으로 설정
        return 'neutral'
    
    def check_trade_allowed(self, pair: str) -> bool:
        """
        거래 허용 여부 확인
        
        Args:
            pair: 거래 쌍
            
        Returns:
            거래 허용 여부 (True/False)
        """
        # 서킷 브레이커가 활성화된 경우 거래 금지
        if self.account_info.get('circuit_breaker_active', False):
            logger.warning(f"서킷 브레이커가 활성화되어 {pair} 거래가 거부되었습니다.")
            return False
            
        # 현재 드로다운이 최대 허용 드로다운의 90%를 초과하면 거래 금지
        current_drawdown = self.account_info.get('current_drawdown', 0)
        if current_drawdown > self.max_drawdown_allowed * 0.9:
            logger.warning(f"현재 드로다운({current_drawdown:.2%})이 최대 허용치의 90%를 초과하여 {pair} 거래가 거부되었습니다.")
            return False
        
        # 매우 작은 포지션 크기 거래 방지 (원래 금액의 20% 미만 시 거래 취소)
        if hasattr(self, 'too_small_position') and self.too_small_position:
            logger.warning(f"포지션 크기가 너무 작아 {pair} 거래가 거부되었습니다.")
            return False
        
        # 시장 상황에 따른 추가 검사
        market_condition = self.get_market_condition(pair)
        if market_condition == 'bearish' and current_drawdown > self.max_drawdown_allowed * 0.7:
            logger.warning(f"약세장에서 드로다운({current_drawdown:.2%})이 높아 {pair} 거래가 거부되었습니다.")
            return False
        elif market_condition == 'volatile' and current_drawdown > self.max_drawdown_allowed * 0.6:
            logger.warning(f"변동성이 큰 시장에서 드로다운({current_drawdown:.2%})이 높아 {pair} 거래가 거부되었습니다.")
            return False
            
        return True
    
    def adjust_trade_parameters(self, default_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        현재 리스크 상황에 따라 거래 파라미터 조정
        
        Args:
            default_params: 기본 거래 파라미터
            
        Returns:
            조정된 거래 파라미터
        """
        adjusted_params = default_params.copy()
        
        # 드로다운에 따른 스탑로스 조정
        if 'stoploss' in adjusted_params:
            # 드로다운이 높을수록 더 타이트한 스탑로스 사용
            drawdown_ratio = self.account_info['current_drawdown'] / self.max_drawdown_allowed
            if drawdown_ratio > 0.5:
                # 기본 스탑로스의 50-90% 수준으로 조정 (드로다운에 비례)
                tightening_factor = 0.5 + (drawdown_ratio * 0.4)
                adjusted_params['stoploss'] = default_params['stoploss'] * tightening_factor
        
        # 승률이 낮을 때 ROI 조정
        if 'minimal_roi' in adjusted_params and self.trade_stats['win_rate'] < 0.4:
            # 더 빠른 이익 실현
            for key in adjusted_params['minimal_roi']:
                adjusted_params['minimal_roi'][key] = adjusted_params['minimal_roi'][key] * 0.8
        
        return adjusted_params
