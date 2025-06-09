"""
Freqtrade Binance Connector 모듈

이 모듈은 Freqtrade의 Binance 커넥터를 설정하고 검증하는 기능을 제공합니다.
API 키 관리, 환경 변수 사용, 교환소 특정 설정을 처리합니다.
"""

import logging
import os
import re
import json
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Freqtrade 환경 변수 접두사
FREQTRADE_ENV_PREFIX = "FREQTRADE__"

# Binance API 관련 설정 키
# DEAD CODE: BINANCE_CONFIG_KEYS = {
    "exchange_name": "name",
    "api_key": "key",
    "api_secret": "secret",
    "api_key_type": "key_type",  # 'api' 또는 'rsa'
}

# 최소 주문 크기 (USDT)
MIN_ORDER_SIZE = 10.0

class BinanceConnector:
    """Freqtrade Binance 커넥터 클래스"""
    
    def __init__(self, config_path: str = None, validate: bool = True):
        """
        Binance 커넥터 초기화
        
        Args:
            config_path: Freqtrade 설정 파일 경로 (기본값: config/freqtrade.json)
            validate: 초기화 시 설정 검증 여부
        """
        self.config_path = config_path or str(Path.cwd() / "config" / "freqtrade.json")
        self.config = self._load_config()
        self.exchange_config = self.config.get("exchange", {})
        
        # 환경 변수에서 민감한 정보 로드
        self._load_from_env()
        
        if validate:
            self.validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Freqtrade 설정 파일 로드"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            return {}
    
    def _load_from_env(self) -> None:
        """환경 변수에서 민감한 정보 로드"""
        # 환경 변수 로깅 (민감한 정보 마스킹)
        env_vars = {k: v for k, v in os.environ.items() if k.startswith(FREQTRADE_ENV_PREFIX)}
        masked_vars = {k: "***" if "KEY" in k or "SECRET" in k else v for k, v in env_vars.items()}
        logger.info(f"Freqtrade 환경 변수 감지됨: {masked_vars}")
        
        # API 키와 시크릿 로드
        if "FREQTRADE__EXCHANGE__KEY" in os.environ:
            self.exchange_config["key"] = os.environ["FREQTRADE__EXCHANGE__KEY"]
        
        if "FREQTRADE__EXCHANGE__SECRET" in os.environ:
            # 여러 줄 시크릿 처리 (RSA 키의 경우)
            secret = os.environ["FREQTRADE__EXCHANGE__SECRET"]
            if "\\n" in secret:
                secret = secret.replace("\\n", "\n")
            self.exchange_config["secret"] = secret
        
        # 교환소 이름 (binance/binanceus) 로드
        if "FREQTRADE__EXCHANGE__NAME" in os.environ:
            self.exchange_config["name"] = os.environ["FREQTRADE__EXCHANGE__NAME"]
    
    def validate_config(self) -> bool:
        """
        Binance 설정 유효성 검사
        
        Returns:
            bool: 설정이 유효하면 True, 그렇지 않으면 False
        
        Raises:
            ValueError: 필수 설정이 누락되었거나 유효하지 않은 경우
        """
        # 교환소 ID 검증
        exchange_id = self.exchange_config.get("name", "").lower()
        if not exchange_id:
            raise ValueError("교환소 ID가 설정되지 않았습니다. 'exchange.name'을 설정하세요.")
        
        if exchange_id not in ["binance", "binanceus"]:
            raise ValueError(f"지원되지 않는 교환소 ID: {exchange_id}. 'binance' 또는 'binanceus'를 사용하세요.")
        
        # API 키 및 시크릿 검증
        api_key = self.exchange_config.get("key", "")
        api_secret = self.exchange_config.get("secret", "")
        
        if not api_key:
            logger.warning("API 키가 설정되지 않았습니다. 실제 거래는 불가능합니다.")
        elif len(api_key) < 10:
            raise ValueError("API 키가 너무 짧습니다. 유효한 Binance API 키를 제공하세요.")
        
        if not api_secret:
            logger.warning("API 시크릿이 설정되지 않았습니다. 실제 거래는 불가능합니다.")
        elif len(api_secret) < 10:
            raise ValueError("API 시크릿이 너무 짧습니다. 유효한 Binance API 시크릿을 제공하세요.")
        
        # 최소 주문 크기 검증
        stake_amount = self.config.get("stake_amount", 0)
        if stake_amount != "unlimited":
            try:
                if float(stake_amount) < MIN_ORDER_SIZE:
                    logger.warning(f"stake_amount가 최소 주문 크기({MIN_ORDER_SIZE} USDT)보다 작습니다.")
            except (ValueError, TypeError):
                logger.warning(f"stake_amount 값({stake_amount})이 유효한 숫자가 아닙니다.")
        
        # 페어 화이트리스트 검증
        if not self.exchange_config.get("pair_whitelist"):
            logger.warning("페어 화이트리스트가 비어 있습니다. 거래할 페어를 지정하세요.")
        
        # 출금 권한 검사 (API 키에 출금 권한이 없어야 함)
        # 실제 구현에서는 Binance API를 호출하여 키 권한을 확인해야 함
        logger.info("API 키 권한 검증: 출금 권한이 비활성화되어 있는지 확인하세요.")
        
        # 설정이 유효함을 로그에 기록
        logger.info(f"Binance 커넥터 설정 검증 완료: {exchange_id}")
        return True
    
# DEAD CODE:     def get_exchange_config(self) -> Dict[str, Any]:
        """현재 교환소 설정 반환"""
        return self.exchange_config
    
    def get_dry_run_wallet(self) -> float:
        """드라이런 지갑 잔액 반환"""
        return float(self.config.get("dry_run_wallet", 0))
    
    def is_dry_run(self) -> bool:
        """드라이런 모드 여부 반환"""
        return bool(self.config.get("dry_run", True))
    
    def check_safety(self) -> Tuple[bool, str]:
        """
        안전 검사 수행
        
        Returns:
            Tuple[bool, str]: (안전 여부, 메시지)
        """
        is_safe = True
        message = "안전 검사 통과"
        
        # 드라이런 모드가 아니고 지갑 잔액이 최소 요구사항보다 작은 경우
        if not self.is_dry_run() and self.get_dry_run_wallet() < 0.0001:
            is_safe = False
            message = "실제 거래를 위한 지갑 잔액이 너무 적습니다 (최소 0.0001 BTC 필요)"
        
        # API 키 또는 시크릿이 설정되지 않은 경우
        if not self.exchange_config.get("key") or not self.exchange_config.get("secret"):
            is_safe = False
            message = "API 키 또는 시크릿이 설정되지 않았습니다"
        
        return is_safe, message


def validate_freqtrade_config(config_path: str = None) -> Dict[str, Any]:
    """
    Freqtrade 설정 파일 검증
    
    Args:
        config_path: 설정 파일 경로
    
    Returns:
        Dict[str, Any]: 검증된 설정
    """
    connector = BinanceConnector(config_path=config_path, validate=True)
    return connector.config


def check_api_key_validity() -> bool:
    """
    API 키 유효성 검사 (실제 구현에서는 Binance API 호출 필요)
    
    Returns:
        bool: API 키가 유효하면 True
    """
    # TODO: Binance API를 호출하여 키 유효성 검사
    # 현재는 단순히 키가 존재하는지만 확인
    connector = BinanceConnector(validate=False)
    return bool(connector.exchange_config.get("key")) and bool(connector.exchange_config.get("secret"))


def setup_binance_connector(config_path: str = None) -> BinanceConnector:
    """
    Binance 커넥터 설정 및 반환
    
    Args:
        config_path: 설정 파일 경로
    
    Returns:
        BinanceConnector: 설정된 Binance 커넥터 인스턴스
    """
    try:
        connector = BinanceConnector(config_path=config_path)
        is_safe, message = connector.check_safety()
        
        if not is_safe:
            logger.warning(f"안전 검사 실패: {message}")
        else:
            logger.info("Binance 커넥터 설정 완료")
        
        return connector
    except Exception as e:
        logger.exception(f"Binance 커넥터 설정 실패: {e}")
        raise
