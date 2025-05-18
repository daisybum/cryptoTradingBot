#!/usr/bin/env python3
"""
Vault 초기화 스크립트

이 스크립트는 Vault를 초기화하고 필요한 시크릿을 설정합니다.
데이터 수집기에 필요한 API 키 및 구성 설정을 저장합니다.
"""

import os
import sys
import json
import logging
import argparse
import hvac
from hvac.exceptions import VaultError
import time
import random

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 환경 변수
VAULT_URL = os.environ.get('VAULT_ADDR', 'http://localhost:8202')
VAULT_TOKEN = os.environ.get('VAULT_TOKEN', 'root')  # 개발 환경용 토큰
VAULT_MOUNT_POINT = os.environ.get('VAULT_MOUNT_POINT', 'kv')
VAULT_PATH_PREFIX = os.environ.get('VAULT_PATH_PREFIX', 'nasos')

# 재시도 설정
MAX_RETRIES = 5
BASE_DELAY = 1.0  # 초 단위

def retry_with_backoff(func):
    """
    지수 백오프를 사용한 재시도 데코레이터
    
    Args:
        func: 재시도할 함수
        
    Returns:
        함수의 결과
    """
    def wrapper(*args, **kwargs):
        retries = 0
        while retries < MAX_RETRIES:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                retries += 1
                if retries >= MAX_RETRIES:
                    logger.error(f"최대 재시도 횟수 초과: {e}")
                    raise
                
                # 지수 백오프 계산 (무작위성 추가)
                delay = min(BASE_DELAY * (2 ** retries), 30)  # 최대 30초
                jitter = random.uniform(0, 0.1 * delay)  # 10% 지터
                sleep_time = delay + jitter
                
                logger.warning(f"오류 발생, {sleep_time:.2f}초 후 재시도 ({retries}/{MAX_RETRIES}): {e}")
                time.sleep(sleep_time)
    return wrapper


# 기본 시크릿 정의
DEFAULT_SECRETS = {
    'TRADING_SYMBOLS': ['BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'SOL/USDT'],
    'TIMEFRAMES': ['1m', '5m', '15m', '1h', '4h', '1d'],
    'BINANCE_API_KEY': '',
    'BINANCE_API_SECRET': '',
    'ERROR_HANDLING': {
        'circuit_breaker': {
            'failure_threshold': 5,
            'recovery_timeout': 60,
            'half_open_timeout': 30
        },
        'retry': {
            'max_retries': 3,
            'base_delay': 2.0,
            'max_delay': 30.0
        },
        'fallback': {
            'use_cache': True,
            'cache_ttl': 3600
        }
    },
    'HEALTH_CHECK': {
        'interval': 60,
        'timeout': 5,
        'max_failures': 3
    }
}


@retry_with_backoff
def connect_to_vault():
    """
    Vault에 연결하고 인증된 클라이언트를 반환합니다.
    
    Returns:
        hvac.Client: 인증된 Vault 클라이언트
        
    Raises:
        RuntimeError: 인증 실패 시
    """
    client = hvac.Client(url=VAULT_URL, token=VAULT_TOKEN)
    
    if not client.is_authenticated():
        raise RuntimeError(f"Vault 인증 실패: {VAULT_URL}")
    
    logger.info(f"Vault 연결 성공: {VAULT_URL}")
    return client


@retry_with_backoff
def ensure_kv_engine(client):
    """
    KV 시크릿 엔진이 존재하는지 확인하고, 없으면 생성합니다.
    
    Args:
        client: Vault 클라이언트
    """
    try:
        mounted_engines = client.sys.list_mounted_secrets_engines()['data']
        if f"{VAULT_MOUNT_POINT}/" not in mounted_engines:
            client.sys.enable_secrets_engine(
                backend_type='kv',
                path=VAULT_MOUNT_POINT,
                options={'version': '2'}
            )
            logger.info(f"KV 시크릿 엔진 생성됨: {VAULT_MOUNT_POINT}")
        else:
            logger.info(f"KV 시크릿 엔진 이미 존재함: {VAULT_MOUNT_POINT}")
    except Exception as e:
        logger.warning(f"KV 시크릿 엔진 확인 중 오류: {e}")
        raise


@retry_with_backoff
def write_secret(client, key, value):
    """
    Vault에 시크릿을 쓰기
    
    Args:
        client: Vault 클라이언트
        key: 시크릿 키
        value: 시크릿 값
        
    Returns:
        bool: 성공 여부
    """
    secret_path = f"{VAULT_PATH_PREFIX}/{key}"
    
    # 값을 적절한 형식으로 변환
    if isinstance(value, (dict, list)):
        formatted_value = json.dumps(value)
    else:
        formatted_value = value
    
    # 시크릿 생성 또는 업데이트
    client.secrets.kv.v2.create_or_update_secret(
        path=secret_path,
        mount_point=VAULT_MOUNT_POINT,
        secret=dict(value=formatted_value)
    )
    
    logger.info(f"시크릿 저장됨: {secret_path}")
    return True


@retry_with_backoff
def read_secret(client, key, default_value=None):
    """
    Vault에서 시크릿 읽기
    
    Args:
        client: Vault 클라이언트
        key: 시크릿 키
        default_value: 기본값
        
    Returns:
        Any: 시크릿 값 또는 기본값
    """
    secret_path = f"{VAULT_PATH_PREFIX}/{key}"
    
    try:
        response = client.secrets.kv.v2.read_secret_version(
            path=secret_path,
            mount_point=VAULT_MOUNT_POINT
        )
        
        value = response['data']['data']['value']
        
        # JSON 문자열인 경우 파싱
        if isinstance(value, str) and (value.startswith('[') or value.startswith('{')):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
                
        return value
    except Exception as e:
        logger.warning(f"시크릿 읽기 실패, 기본값 사용: {key} - {e}")
        return default_value


def setup_vault_policies(client: hvac.Client) -> bool:
    """
    Vault 정책을 설정합니다.
    
    Args:
        client: Vault 클라이언트
        
    Returns:
        bool: 성공 여부
    """
    try:
        # 데이터 수집기 정책
        data_collector_policy = """
        # 데이터 수집기 정책
        path "kv/data/nasos/*" {
            capabilities = ["read"]
        }
        """
        
        # 관리자 정책
        admin_policy = """
        # 관리자 정책
        path "kv/*" {
            capabilities = ["create", "read", "update", "delete", "list"]
        }
        """
        
        # 정책 생성
        client.sys.create_or_update_policy(
            name='data-collector',
            policy=data_collector_policy
        )
        
        client.sys.create_or_update_policy(
            name='admin',
            policy=admin_policy
        )
        
        logger.info("Vault 정책 설정 완료")
        return True
    except Exception as e:
        logger.error(f"Vault 정책 설정 실패: {e}")
        return False


def initialize_vault():
    """
    Vault를 초기화하고 기본 시크릿을 설정합니다.
    
    Returns:
        bool: 초기화 성공 여부
    """
    try:
        # Vault 연결
        client = connect_to_vault()
        
        # KV 시크릿 엔진 확인
        ensure_kv_engine(client)
        
        # 정책 설정 (선택사항)
        if setup_vault_policies(client):
            logger.info("Vault 정책 설정 완료")
        else:
            logger.warning("Vault 정책 설정 실패, 계속 진행합니다.")
        
        # 기본 시크릿 설정
        success_count = 0
        for key, value in DEFAULT_SECRETS.items():
            # 시크릿이 존재하는지 확인
            existing_value = read_secret(client, key)
            
            if existing_value is not None:
                logger.info(f"시크릿 이미 존재함: {VAULT_PATH_PREFIX}/{key}")
                success_count += 1
                continue
            
            # 시크릿 생성
            if write_secret(client, key, value):
                success_count += 1
        
        # 성공 여부 확인
        if success_count == len(DEFAULT_SECRETS):
            logger.info(f"모든 시크릿({success_count}/{len(DEFAULT_SECRETS)}) 성공적으로 설정됨")
        else:
            logger.warning(f"일부 시크릿만 설정됨: {success_count}/{len(DEFAULT_SECRETS)}")
        
        # 저장된 시크릿 확인
        logger.info("저장된 시크릿 확인:")
        for key in DEFAULT_SECRETS.keys():
            value = read_secret(client, key)
            if value is not None:
                if isinstance(value, (list, dict)):
                    # 리스트나 디셔너리는 JSON으로 표시
                    logger.info(f"  {key}: {json.dumps(value)}")
                else:
                    # API 키와 시크릿은 일부만 표시
                    if any(sensitive in key.upper() for sensitive in ['API_KEY', 'SECRET', 'TOKEN', 'PASSWORD']):
                        if isinstance(value, str) and len(value) > 8:
                            masked_value = value[:4] + '*' * (len(value) - 8) + value[-4:]
                        else:
                            masked_value = '****'
                        logger.info(f"  {key}: {masked_value}")
                    else:
                        logger.info(f"  {key}: {value}")
            else:
                logger.warning(f"  {key}: 설정되지 않음")
        
        logger.info("Vault 초기화 완료")
        return True
        
    except Exception as e:
        logger.error(f"Vault 초기화 실패: {e}")
        return False


def main():
    """
    메인 함수
    """
    logger.info("Vault 초기화 시작")
    
    # Vault 초기화
    if initialize_vault():
        logger.info("Vault 초기화 성공")
    else:
        logger.error("Vault 초기화 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
