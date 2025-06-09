"""
환경 변수 로더 모듈

이 모듈은 환경 변수를 로드하고 애플리케이션 구성에 사용할 수 있도록 처리합니다.
Vault에서 비밀을 로드하는 기능도 포함되어 있습니다.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from src.utils.security import SecretsManager

# 로깅 설정
logger = logging.getLogger(__name__)

class EnvLoader:
    """환경 변수 로더 클래스"""
    
    def __init__(self, env_file: str = None, use_vault: bool = True):
        """
        환경 변수 로더 초기화
        
        Args:
            env_file: 환경 변수 파일 경로 (기본값: 프로젝트 루트의 .env)
            use_vault: Vault 사용 여부
        """
        # 프로젝트 루트 경로
        self.project_root = Path(__file__).parent.parent.parent.absolute()
        
        # 환경 변수 파일 경로
        self.env_file = env_file or os.path.join(self.project_root, 'config/env/project.env')
        
        # 환경 변수 로드
        self._load_env_file()
        
        # Vault 사용 여부
        self.use_vault = use_vault
        
        # Vault 클라이언트
        self.secrets_manager = None
        
        if self.use_vault:
            self._init_vault()
        
        logger.debug(f"환경 변수 로더 초기화 완료: {self.env_file}")
    
    def _load_env_file(self) -> None:
        """환경 변수 파일 로드"""
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file)
            logger.debug(f"환경 변수 파일 로드됨: {self.env_file}")
        else:
            logger.warning(f"환경 변수 파일을 찾을 수 없습니다: {self.env_file}")
    
    def _init_vault(self) -> None:
        """Vault 초기화"""
        try:
            self.secrets_manager = SecretsManager()
            logger.debug("Vault 클라이언트 초기화 완료")
        except Exception as e:
            logger.error(f"Vault 클라이언트 초기화 실패: {e}")
            self.use_vault = False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        환경 변수 가져오기
        
        Args:
            key: 환경 변수 키
            default: 기본값
        
        Returns:
            Any: 환경 변수 값 또는 기본값
        """
        # 환경 변수에서 검색
        value = os.environ.get(key)
        
        # 환경 변수에 없고 Vault를 사용하는 경우 Vault에서 검색
        if value is None and self.use_vault and self.secrets_manager:
            try:
                value = self.secrets_manager.vault.get_secret(key)
                if value:
                    logger.debug(f"Vault에서 값을 가져옴: {key}")
            except Exception as e:
                logger.error(f"Vault에서 값을 가져오는 중 오류 발생: {key} - {e}")
        
        # 값이 없는 경우 기본값 반환
        if value is None:
            return default
        
        return value
    
    def get_int(self, key: str, default: int = 0) -> int:
        """
        정수 환경 변수 가져오기
        
        Args:
            key: 환경 변수 키
            default: 기본값
        
        Returns:
            int: 정수 환경 변수 값 또는 기본값
        """
        value = self.get(key)
        
        if value is None:
            return default
        
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"환경 변수를 정수로 변환할 수 없습니다: {key}={value}")
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        실수 환경 변수 가져오기
        
        Args:
            key: 환경 변수 키
            default: 기본값
        
        Returns:
            float: 실수 환경 변수 값 또는 기본값
        """
        value = self.get(key)
        
        if value is None:
            return default
        
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"환경 변수를 실수로 변환할 수 없습니다: {key}={value}")
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        불리언 환경 변수 가져오기
        
        Args:
            key: 환경 변수 키
            default: 기본값
        
        Returns:
            bool: 불리언 환경 변수 값 또는 기본값
        """
        value = self.get(key)
        
        if value is None:
            return default
        
        if isinstance(value, bool):
            return value
        
        return value.lower() in ('true', 'yes', '1', 'y', 't')
    
    def get_list(self, key: str, default: list = None, separator: str = ',') -> list:
        """
        리스트 환경 변수 가져오기
        
        Args:
            key: 환경 변수 키
            default: 기본값
            separator: 구분자
        
        Returns:
            list: 리스트 환경 변수 값 또는 기본값
        """
        if default is None:
            default = []
        
        value = self.get(key)
        
        if value is None:
            return default
        
        return [item.strip() for item in value.split(separator) if item.strip()]
    
    def get_dict(self, prefix: str, default: dict = None) -> dict:
        """
        접두사로 시작하는 환경 변수를 딕셔너리로 가져오기
        
        Args:
            prefix: 환경 변수 접두사
            default: 기본값
        
        Returns:
            dict: 딕셔너리 환경 변수 값 또는 기본값
        """
        if default is None:
            default = {}
        
        result = {}
        
        # 환경 변수에서 검색
        for key, value in os.environ.items():
            if key.startswith(prefix):
                result[key[len(prefix):].lower()] = value
        
        # Vault에서 검색
        if self.use_vault and self.secrets_manager:
            try:
                secrets = self.secrets_manager.vault.list_secrets()
                
                for key in secrets:
                    if key.startswith(prefix):
                        value = self.secrets_manager.vault.get_secret(key)
                        if value:
                            result[key[len(prefix):].lower()] = value
            except Exception as e:
                logger.error(f"Vault에서 값을 가져오는 중 오류 발생: {prefix} - {e}")
        
        if not result:
            return default
        
        return result
    
    def get_api_credentials(self, exchange: str = 'binance') -> tuple:
        """
        API 자격 증명 가져오기
        
        Args:
            exchange: 거래소 이름
        
        Returns:
            tuple: API 키와 시크릿
        """
        if self.use_vault and self.secrets_manager:
            try:
                return self.secrets_manager.get_api_credentials(exchange)
            except Exception as e:
                logger.error(f"Vault에서 API 자격 증명을 가져오는 중 오류 발생: {exchange} - {e}")
        
        # 환경 변수에서 검색
        key_name = f"{exchange.upper()}_API_KEY"
        secret_name = f"{exchange.upper()}_API_SECRET"
        
        api_key = self.get(key_name)
        api_secret = self.get(secret_name)
        
        return api_key, api_secret
    
    def get_database_credentials(self, db_type: str = 'postgresql') -> dict:
        """
        데이터베이스 자격 증명 가져오기
        
        Args:
            db_type: 데이터베이스 유형
        
        Returns:
            dict: 데이터베이스 자격 증명
        """
        if self.use_vault and self.secrets_manager:
            try:
                return self.secrets_manager.get_database_credentials(db_type)
            except Exception as e:
                logger.error(f"Vault에서 데이터베이스 자격 증명을 가져오는 중 오류 발생: {db_type} - {e}")
        
        # 환경 변수에서 검색
        prefix = f"{db_type.upper()}_"
        
        return self.get_dict(prefix, {})
    
    def get_telegram_credentials(self) -> tuple:
        """
        텔레그램 자격 증명 가져오기
        
        Returns:
            tuple: 텔레그램 토큰과 채팅 ID
        """
        if self.use_vault and self.secrets_manager:
            try:
                return self.secrets_manager.get_telegram_credentials()
            except Exception as e:
                logger.error(f"Vault에서 텔레그램 자격 증명을 가져오는 중 오류 발생: {e}")
        
        # 환경 변수에서 검색
        token = self.get('TELEGRAM_TOKEN')
        chat_id = self.get('TELEGRAM_CHAT_ID')
        
        return token, chat_id


# 싱글톤 인스턴스
_env_loader = None

def get_env_loader(env_file: str = None, use_vault: bool = True) -> EnvLoader:
    """
    환경 변수 로더 인스턴스 가져오기
    
    Args:
        env_file: 환경 변수 파일 경로
        use_vault: Vault 사용 여부
    
    Returns:
        EnvLoader: 환경 변수 로더 인스턴스
    """
    global _env_loader
    
    if _env_loader is None:
        _env_loader = EnvLoader(env_file, use_vault)
    
    return _env_loader
