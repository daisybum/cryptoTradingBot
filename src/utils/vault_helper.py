"""
Vault 통합 유틸리티

이 모듈은 Hashicorp Vault와의 통합을 위한 유틸리티 함수를 제공합니다.
오류 처리 및 복원력 있는 시크릿 관리를 지원합니다.
"""

import os
import json
import time
import logging
import functools
from typing import Any, Dict, List, Optional, TypeVar, cast, Union, Callable
import hvac
from datetime import datetime, timedelta

from src.utils.error_handler import with_retry, with_circuit_breaker, with_fallback

# 타입 변수
T = TypeVar('T')

# 로깅 설정
logger = logging.getLogger(__name__)

# 환경 변수 - 로컬 및 Docker 환경에 따라 다른 기본값 사용
def get_default_vault_url():
    # 환경 변수에서 직접 URL을 가져오거나 자동 감지
    vault_addr = os.environ.get('VAULT_ADDR')
    if vault_addr:
        logger.debug(f"VAULT_ADDR 환경 변수 값 사용: {vault_addr}")
        return vault_addr
    
    # 환경 감지
    is_local_test = os.environ.get('LOCAL_TEST', 'false').lower() == 'true'
    is_docker = os.environ.get('DOCKER_ENV', 'false').lower() == 'true'
    
    if is_docker:
        logger.debug("Docker 환경 감지: http://vault:8200 사용")
        return 'http://vault:8200'
    elif is_local_test:
        logger.debug("로컬 테스트 환경 감지: http://localhost:8202 사용")
        return 'http://localhost:8202'  # 로컬에서는 8202 포트 사용
    else:
        logger.debug("기본 환경: http://localhost:8200 사용")
        return 'http://localhost:8200'

# 환경 변수에서 값 가져오기
VAULT_URL = get_default_vault_url()
VAULT_TOKEN = os.environ.get('VAULT_TOKEN', 'root')  # 개발 환경용 토큰
VAULT_MOUNT_POINT = os.environ.get('VAULT_MOUNT_POINT', 'kv')
VAULT_PATH_PREFIX = os.environ.get('VAULT_PATH_PREFIX', 'nasos')

logger.info(f"Vault 설정: URL={VAULT_URL}, 토큰={VAULT_TOKEN[:3]}*** (masked)")

# 캐시 설정
SECRET_CACHE = {}
# DEAD CODE: SECRET_CACHE_TTL = int(os.environ.get('SECRET_CACHE_TTL', '3600'))  # 초 단위


class VaultClient:
    """
    Vault 클라이언트 클래스
    
    이 클래스는 Vault 서버와의 통신을 관리하고 시크릿을 검색합니다.
    """
    
    def __init__(self, url: str = VAULT_URL, token: str = VAULT_TOKEN,
                 mount_point: str = VAULT_MOUNT_POINT, path_prefix: str = VAULT_PATH_PREFIX):
        """
        Vault 클라이언트 초기화
        
        Args:
            url: Vault 서버 URL
            token: Vault 인증 토큰
            mount_point: Vault 마운트 포인트
            path_prefix: Vault 경로 접두사
        """
        self.url = url
        self.token = token
        self.mount_point = mount_point
        self.path_prefix = path_prefix
        self.client = None
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)  # 기본 5분 캐시
        self.cache_timestamps = {}
        self.connection_error = None  # 연결 오류 상태 저장
        
        # 클라이언트 초기화
        try:
            logger.info(f"Vault 클라이언트 초기화 시도: {url}")
            self.client = hvac.Client(url=url, token=token)
            if self.client.is_authenticated():
                logger.info("Vault 클라이언트 초기화 성공")
                self.connection_error = None
            else:
                logger.warning("Vault 인증 실패")
                self.connection_error = "인증 실패: 토큰이 유효하지 않습니다."
        except Exception as e:
            logger.error(f"Vault 연결 오류: {e}")
            self.connection_error = str(e)
            
            # 로컬 폴백 시도
            if 'vault' in self.url and 'localhost' not in self.url:
                fallback_url = self.url.replace('vault', 'localhost')
                try:
                    logger.info(f"Vault 폴백 연결 시도: {fallback_url}")
                    self.client = hvac.Client(url=fallback_url, token=self.token)
                    if self.client.is_authenticated():
                        logger.info(f"Vault 폴백 연결 성공: {fallback_url}")
                        self.connection_error = None
                    else:
                        logger.warning(f"Vault 폴백 인증 실패: {fallback_url}")
                except Exception as fallback_e:
                    logger.error(f"Vault 폴백 연결 오류: {fallback_e}")
    
    @with_circuit_breaker
    @with_retry
    def _get_client(self) -> hvac.Client:
        """
        인증된 Vault 클라이언트를 반환합니다.
        
        Returns:
            hvac.Client: Vault 클라이언트
            
        Raises:
            RuntimeError: 클라이언트가 초기화되지 않았거나 인증되지 않은 경우
        """
        if self.client is None:
            logger.error("비밀 검색 실패: Vault 클라이언트가 초기화되지 않았습니다.")
            raise RuntimeError("Vault 클라이언트가 초기화되지 않았습니다.")
        
        if not self.client.is_authenticated():
            raise RuntimeError("Vault 클라이언트가 인증되지 않았습니다.")
        
        return self.client
    
    @with_circuit_breaker
    @with_retry
    @with_fallback(None)
    def get_secret(self, key: str) -> Any:
        """
        Vault에서 시크릿 값을 가져옵니다.
        
        Args:
            key: 시크릿 키
            
        Returns:
            Any: 시크릿 값
        """
        # 연결 오류 확인
        if self.connection_error is not None:
            logger.error(f"비밀 검색 실패: {key} - {self.connection_error}")
            return None
            
        # 캐시 확인
        cache_key = f"{self.path_prefix}/{key}"
        if cache_key in self.cache:
            cached_value, expiry = self.cache[cache_key]
            if expiry > time.time():
                return cached_value
            
        try:
            # Vault에서 데이터 가져오기
            secret_path = f"{self.path_prefix}/{key}"
            response = self._get_client().secrets.kv.v2.read_secret_version(
                path=secret_path,
                mount_point=self.mount_point
            )
            
            # 값 추출
            if response and 'data' in response and 'data' in response['data']:
                value = response['data']['data'].get('value')
                
                # 캐시 저장
                self.cache[cache_key] = (value, time.time() + self.cache_ttl.total_seconds())
                
                return value
            
            return None
        except Exception as e:
            logger.error(f"시크릿 읽기 실패: {key} - {e}")
            return None
            
    @with_circuit_breaker
    @with_retry
    @with_fallback(None)
    def read_secret(self, key: str) -> Any:
        """
        Vault에서 시크릿 값을 읽습니다. get_secret 메서드와 동일한 기능을 제공합니다.
        
        Args:
            key: 시크릿 키
            
        Returns:
            Any: 시크릿 값
        """
        return self.get_secret(key)
    
    def get_secret_with_fallback(self, key: str, default_value: Any = None) -> Any:
        """
        Vault에서 시크릿을 읽고 실패 시 기본값을 반환합니다.
        
        Args:
            key: 시크릿 키
            default_value: 기본값
            
        Returns:
            Any: 시크릿 값 또는 기본값
        """
        try:
            return self.read_secret(key)
        except Exception as e:
            logger.warning(f"시크릿 읽기 실패, 기본값 사용: {key} - {e}")
            return default_value
    
    def get_list_secret(self, key: str, default_value: List[Any] = None) -> List[Any]:
        """
        리스트 형식의 시크릿을 읽습니다.
        
        Args:
            key: 시크릿 키
            default_value: 기본값
            
        Returns:
            List[Any]: 시크릿 값 또는 기본값
        """
        if default_value is None:
            default_value = []
            
        value = self.get_secret_with_fallback(key, default_value)
        
        if not isinstance(value, list):
            logger.warning(f"시크릿이 리스트 형식이 아닙니다: {key}")
            return default_value
            
        return value
    
    def get_dict_secret(self, key: str, default_value: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        딕셔너리 형식의 시크릿을 읽습니다.
        
        Args:
            key: 시크릿 키
            default_value: 기본값
            
        Returns:
            Dict[str, Any]: 시크릿 값 또는 기본값
        """
        if default_value is None:
            default_value = {}
            
        value = self.get_secret_with_fallback(key, default_value)
        
        if not isinstance(value, dict):
            logger.warning(f"시크릿이 딕셔너리 형식이 아닙니다: {key}")
            return default_value
            
        return value
    
    def get_string_secret(self, key: str, default_value: str = "") -> str:
        """
        문자열 형식의 시크릿을 읽습니다.
        
        Args:
            key: 시크릿 키
            default_value: 기본값
            
        Returns:
            str: 시크릿 값 또는 기본값
        """
        value = self.get_secret_with_fallback(key, default_value)
        
        if not isinstance(value, str):
            logger.warning(f"시크릿이 문자열 형식이 아닙니다: {key}")
            return str(value)
            
        return value
    
    def clear_cache(self) -> None:
        """캐시를 비웁니다."""
        SECRET_CACHE.clear()
        logger.debug("시크릿 캐시 비움")


# 싱글톤 인스턴스
_vault_client = None


def get_vault_client() -> VaultClient:
    """
    Vault 클라이언트 싱글톤 인스턴스를 반환합니다.
    
    Returns:
        VaultClient: Vault 클라이언트
    """
    global _vault_client
    
    try:
        if _vault_client is None:
            logger.info(f"Vault 클라이언트 초기화 시도: {VAULT_URL}")
            _vault_client = VaultClient()
            
            # 인증 테스트
            if _vault_client.client and _vault_client.client.is_authenticated():
                logger.info("Vault 클라이언트 초기화 성공")
            else:
                logger.warning("Vault 클라이언트 인증 실패")
    except Exception as e:
        logger.error(f"Vault 클라이언트 초기화 오류: {e}")
        # 오류가 발생해도 None을 반환하지 않고 빈 클라이언트 생성
        if _vault_client is None:
            _vault_client = VaultClient()
        
    return _vault_client


def get_secret(key: str, default_value: Any = None) -> Any:
    """
    Vault에서 시크릿을 읽는 편의 함수
    
    Args:
        key: 시크릿 키
        default_value: 기본값
        
    Returns:
        Any: 시크릿 값 또는 기본값
    """
    client = get_vault_client()
    return client.get_secret_with_fallback(key, default_value)


def get_list_secret(key: str, default_value: List[Any] = None) -> List[Any]:
    """
    리스트 형식의 시크릿을 읽는 편의 함수
    
    Args:
        key: 시크릿 키
        default_value: 기본값
        
    Returns:
        List[Any]: 시크릿 값 또는 기본값
    """
    client = get_vault_client()
    return client.get_list_secret(key, default_value)


def get_dict_secret(key: str, default_value: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    딕셔너리 형식의 시크릿을 읽는 편의 함수
    
    Args:
        key: 시크릿 키
        default_value: 기본값
        
    Returns:
        Dict[str, Any]: 시크릿 값 또는 기본값
    """
    client = get_vault_client()
    return client.get_dict_secret(key, default_value)


def get_string_secret(key: str, default_value: str = "") -> str:
    """
    문자열 형식의 시크릿을 읽는 편의 함수
    
    Args:
        key: 시크릿 키
        default_value: 기본값
        
    Returns:
        str: 시크릿 값 또는 기본값
    """
    client = get_vault_client()
    return client.get_string_secret(key, default_value)


def clear_cache():
    """ 시크릿 캐시를 비우는 편의 함수 """
    global SECRET_CACHE, _vault_client
    SECRET_CACHE = {}
    
    # Vault 클라이언트 재초기화
    _vault_client = None
    logger.info("Vault 캐시 및 클라이언트 초기화 완료")
    client = get_vault_client()
    client.clear_cache()
