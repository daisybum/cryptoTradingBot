"""
보안 유틸리티 모듈

이 모듈은 API 키 및 비밀번호와 같은 민감한 정보를 안전하게 관리하기 위한 유틸리티를 제공합니다.
Hashicorp Vault를 사용하여 비밀을 저장하고 검색합니다.
"""

import os
import json
import logging
import hvac
from typing import Dict, Any, Optional, List, Tuple
from dotenv import load_dotenv

# 로깅 설정
logger = logging.getLogger(__name__)

class VaultClient:
    """Hashicorp Vault 클라이언트 클래스"""
    
    def __init__(self, url: str = None, token: str = None, role_id: str = None, secret_id: str = None):
        """
        Vault 클라이언트 초기화
        
        Args:
            url: Vault 서버 URL (기본값: 환경 변수 VAULT_ADDR)
            token: Vault 토큰 (기본값: 환경 변수 VAULT_TOKEN)
            role_id: AppRole 인증을 위한 Role ID (기본값: 환경 변수 VAULT_ROLE_ID)
            secret_id: AppRole 인증을 위한 Secret ID (기본값: 환경 변수 VAULT_SECRET_ID)
        """
        # 환경 변수 로드
        load_dotenv()
        
        # Vault 서버 URL
        self.url = url or os.environ.get('VAULT_ADDR', 'http://127.0.0.1:8200')
        
        # 클라이언트 초기화
        self.client = hvac.Client(url=self.url)
        
        # 인증
        self._authenticate(token, role_id, secret_id)
        
        # 마운트 포인트 및 경로
        self.mount_point = 'kv'
        self.base_path = 'nasos'
        
        logger.debug(f"Vault 클라이언트 초기화 완료: {self.url}")
    
    def _authenticate(self, token: str = None, role_id: str = None, secret_id: str = None) -> None:
        """
        Vault 인증 수행
        
        Args:
            token: Vault 토큰
            role_id: AppRole 인증을 위한 Role ID
            secret_id: AppRole 인증을 위한 Secret ID
        """
        # 토큰 인증
        if token or os.environ.get('VAULT_TOKEN'):
            self.client.token = token or os.environ.get('VAULT_TOKEN')
            logger.debug("Vault 토큰 인증 완료")
            
            # 인증 테스트
            try:
                if self.client.is_authenticated():
                    logger.debug("Vault 인증 확인 성공")
                    return
                else:
                    logger.warning("Vault 토큰이 유효하지 않습니다. 기본 개발 토큰을 사용합니다.")
                    # 기본 개발 토큰 사용 (Docker 환경에서 사용)
                    self.client.token = "root"
                    return
            except Exception as e:
                logger.error(f"Vault 인증 확인 오류: {e}")
                # 기본 개발 토큰 사용 (Docker 환경에서 사용)
                self.client.token = "root"
                return
        
        # AppRole 인증
        if (role_id or os.environ.get('VAULT_ROLE_ID')) and (secret_id or os.environ.get('VAULT_SECRET_ID')):
            role_id = role_id or os.environ.get('VAULT_ROLE_ID')
            secret_id = secret_id or os.environ.get('VAULT_SECRET_ID')
            
            try:
                self.client.auth.approle.login(
                    role_id=role_id,
                    secret_id=secret_id
                )
                logger.debug("Vault AppRole 인증 완료")
                return
            except Exception as e:
                logger.error(f"Vault AppRole 인증 실패: {e}")
        
        # 로그인 실패 시 기본 개발 토큰 사용 (Docker 환경에서 사용)
        logger.warning("Vault 인증 정보가 없습니다. 기본 개발 토큰을 사용합니다.")
        self.client.token = "root"
        
        # 개발 모드 (루트 토큰)
        if os.environ.get('VAULT_DEV_ROOT_TOKEN_ID'):
            self.client.token = os.environ.get('VAULT_DEV_ROOT_TOKEN_ID')
            logger.debug("개발 모드 루트 토큰 사용")
            return
        
        # 토큰 파일에서 로드
        token_file = os.path.join(os.path.expanduser('~'), '.vault-token')
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                self.client.token = f.read().strip()
            logger.debug("토큰 파일에서 로드")
            return
        
        logger.warning("Vault 인증 실패: 유효한 인증 방법이 없습니다.")
    
    def is_authenticated(self) -> bool:
        """
        Vault 인증 상태 확인
        
        Returns:
            bool: 인증 상태
        """
        try:
            return self.client.is_authenticated()
        except Exception as e:
            logger.error(f"인증 상태 확인 실패: {e}")
            return False
    
    def store_secret(self, key: str, value: str, description: str = None) -> bool:
        """
        비밀 저장
        
        Args:
            key: 비밀 키
            value: 비밀 값
            description: 비밀 설명
        
        Returns:
            bool: 성공 여부
        """
        try:
            # 데이터 준비
            data = {'value': value}
            if description:
                data['description'] = description
            
            # 비밀 저장
            self.client.secrets.kv.v2.create_or_update_secret(
                path=f"{self.base_path}/{key}",
                secret=data,
                mount_point=self.mount_point
            )
            
            logger.info(f"비밀 저장 성공: {key}")
            return True
        except Exception as e:
            logger.error(f"비밀 저장 실패: {key} - {e}")
            return False
    
    def get_secret(self, key: str) -> Optional[str]:
        """
        비밀 검색
        
        Args:
            key: 비밀 키
        
        Returns:
            Optional[str]: 비밀 값 또는 None
        """
        try:
            # 비밀 검색
            response = self.client.secrets.kv.v2.read_secret_version(
                path=f"{self.base_path}/{key}",
                mount_point=self.mount_point
            )
            
            # 값 반환
            if response and 'data' in response and 'data' in response['data']:
                return response['data']['data'].get('value')
            
            return None
        except Exception as e:
            logger.error(f"비밀 검색 실패: {key} - {e}")
            return None
    
    def list_secrets(self) -> List[str]:
        """
        비밀 목록 조회
        
        Returns:
            List[str]: 비밀 키 목록
        """
        try:
            # 비밀 목록 조회
            response = self.client.secrets.kv.v2.list_secrets(
                path=self.base_path,
                mount_point=self.mount_point
            )
            
            # 키 목록 반환
            if response and 'data' in response and 'keys' in response['data']:
                return response['data']['keys']
            
            return []
        except Exception as e:
            logger.error(f"비밀 목록 조회 실패: {e}")
            return []
    
# DEAD CODE:     def delete_secret(self, key: str) -> bool:
        """
        비밀 삭제
        
        Args:
            key: 비밀 키
        
        Returns:
            bool: 성공 여부
        """
        try:
            # 비밀 삭제
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=f"{self.base_path}/{key}",
                mount_point=self.mount_point
            )
            
            logger.info(f"비밀 삭제 성공: {key}")
            return True
        except Exception as e:
            logger.error(f"비밀 삭제 실패: {key} - {e}")
            return False


class SecretsManager:
    """비밀 관리 클래스"""
    
    def __init__(self, vault_url: str = None, vault_token: str = None):
        """
        비밀 관리자 초기화
        
        Args:
            vault_url: Vault 서버 URL
            vault_token: Vault 토큰
        """
        # Vault 클라이언트 초기화
        self.vault = VaultClient(url=vault_url, token=vault_token)
        
        # 환경 변수 로드
        load_dotenv()
        
        logger.debug("비밀 관리자 초기화 완료")
    
    def get_api_credentials(self, exchange: str = 'binance') -> Tuple[Optional[str], Optional[str]]:
        """
        API 자격 증명 가져오기
        
        Args:
            exchange: 거래소 이름 (기본값: binance)
        
        Returns:
            Tuple[Optional[str], Optional[str]]: API 키와 시크릿
        """
        # 키 이름 설정
        key_name = f"{exchange.upper()}_API_KEY"
        secret_name = f"{exchange.upper()}_API_SECRET"
        
        # Vault에서 검색
        api_key = self.vault.get_secret(key_name)
        api_secret = self.vault.get_secret(secret_name)
        
        # Vault에 없는 경우 환경 변수에서 검색
        if not api_key:
            api_key = os.environ.get(key_name)
        
        if not api_secret:
            api_secret = os.environ.get(secret_name)
        
        return api_key, api_secret
    
# DEAD CODE:     def store_api_credentials(self, api_key: str, api_secret: str, exchange: str = 'binance') -> bool:
        """
        API 자격 증명 저장
        
        Args:
            api_key: API 키
            api_secret: API 시크릿
            exchange: 거래소 이름 (기본값: binance)
        
        Returns:
            bool: 성공 여부
        """
        # 키 이름 설정
        key_name = f"{exchange.upper()}_API_KEY"
        secret_name = f"{exchange.upper()}_API_SECRET"
        
        # Vault에 저장
        key_success = self.vault.store_secret(key_name, api_key, f"{exchange} API Key")
        secret_success = self.vault.store_secret(secret_name, api_secret, f"{exchange} API Secret")
        
        return key_success and secret_success
    
    def get_database_credentials(self, db_type: str = 'postgresql') -> Dict[str, str]:
        """
        데이터베이스 자격 증명 가져오기
        
        Args:
            db_type: 데이터베이스 유형 (기본값: postgresql)
        
        Returns:
            Dict[str, str]: 데이터베이스 자격 증명
        """
        # 키 이름 설정
        prefix = f"{db_type.upper()}"
        
        # 필요한 자격 증명 키
        cred_keys = ['USER', 'PASSWORD', 'HOST', 'PORT', 'DATABASE']
        
        # 자격 증명 가져오기
        credentials = {}
        
        for key in cred_keys:
            full_key = f"{prefix}_{key}"
            
            # Vault에서 검색
            value = self.vault.get_secret(full_key)
            
            # Vault에 없는 경우 환경 변수에서 검색
            if not value:
                value = os.environ.get(full_key)
            
            if value:
                credentials[key.lower()] = value
        
        return credentials
    
# DEAD CODE:     def store_database_credentials(self, credentials: Dict[str, str], db_type: str = 'postgresql') -> bool:
        """
        데이터베이스 자격 증명 저장
        
        Args:
            credentials: 데이터베이스 자격 증명
            db_type: 데이터베이스 유형 (기본값: postgresql)
        
        Returns:
            bool: 성공 여부
        """
        # 키 이름 설정
        prefix = f"{db_type.upper()}"
        
        # 자격 증명 저장
        success = True
        
        for key, value in credentials.items():
            full_key = f"{prefix}_{key.upper()}"
            
            # Vault에 저장
            if not self.vault.store_secret(full_key, value, f"{db_type} {key}"):
                success = False
        
        return success
    
    def get_telegram_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """
        텔레그램 자격 증명 가져오기
        
        Returns:
            Tuple[Optional[str], Optional[str]]: 텔레그램 토큰과 채팅 ID
        """
        # 키 이름 설정
        token_key = "TELEGRAM_TOKEN"
        chat_id_key = "TELEGRAM_CHAT_ID"
        
        # Vault에서 검색
        token = self.vault.get_secret(token_key)
        chat_id = self.vault.get_secret(chat_id_key)
        
        # Vault에 없는 경우 환경 변수에서 검색
        if not token:
            token = os.environ.get(token_key)
        
        if not chat_id:
            chat_id = os.environ.get(chat_id_key)
        
        return token, chat_id
    
# DEAD CODE:     def store_telegram_credentials(self, token: str, chat_id: str) -> bool:
        """
        텔레그램 자격 증명 저장
        
        Args:
            token: 텔레그램 봇 토큰
            chat_id: 텔레그램 채팅 ID
        
        Returns:
            bool: 성공 여부
        """
        # 키 이름 설정
        token_key = "TELEGRAM_TOKEN"
        chat_id_key = "TELEGRAM_CHAT_ID"
        
        # Vault에 저장
        token_success = self.vault.store_secret(token_key, token, "Telegram Bot Token")
        chat_id_success = self.vault.store_secret(chat_id_key, chat_id, "Telegram Chat ID")
        
        return token_success and chat_id_success
    
# DEAD CODE:     def export_to_env_file(self, filepath: str = '.env') -> bool:
        """
        비밀을 환경 변수 파일로 내보내기
        
        Args:
            filepath: 환경 변수 파일 경로
        
        Returns:
            bool: 성공 여부
        """
        try:
            # 비밀 목록 가져오기
            secrets = self.vault.list_secrets()
            
            if not secrets:
                logger.warning("내보낼 비밀이 없습니다.")
                return False
            
            # 파일 생성
            with open(filepath, 'w') as f:
                f.write("# NASOSv5_mod3 Bot 환경 변수\n")
                f.write(f"# 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("# 주의: 이 파일에는 민감한 정보가 포함되어 있습니다. 안전하게 보관하세요.\n\n")
                
                # 각 비밀 추가
                for key in secrets:
                    value = self.vault.get_secret(key)
                    if value:
                        f.write(f"{key}={value}\n")
            
            # 파일 권한 설정
            os.chmod(filepath, 0o600)
            
            logger.info(f"비밀이 성공적으로 내보내졌습니다: {filepath}")
            return True
        except Exception as e:
            logger.error(f"비밀 내보내기 실패: {e}")
            return False
    
# DEAD CODE:     def import_from_env_file(self, filepath: str = '.env') -> bool:
        """
        환경 변수 파일에서 비밀 가져오기
        
        Args:
            filepath: 환경 변수 파일 경로
        
        Returns:
            bool: 성공 여부
        """
        try:
            # 파일 확인
            if not os.path.exists(filepath):
                logger.error(f"파일을 찾을 수 없습니다: {filepath}")
                return False
            
            # 파일 로드
            load_dotenv(filepath)
            
            # 환경 변수에서 비밀 가져오기
            success = True
            
            for key, value in os.environ.items():
                # 시스템 환경 변수 건너뛰기
                if key.startswith('VAULT_') or key.startswith('PATH') or key.startswith('HOME'):
                    continue
                
                # 비밀 저장
                if not self.vault.store_secret(key, value, f"Imported from {filepath}"):
                    success = False
            
            logger.info(f"비밀이 성공적으로 가져와졌습니다: {filepath}")
            return success
        except Exception as e:
            logger.error(f"비밀 가져오기 실패: {e}")
            return False


# 유틸리티 함수
# DEAD CODE: def validate_api_key(api_key: str) -> bool:
    """
    API 키 유효성 검사
    
    Args:
        api_key: API 키
    
    Returns:
        bool: 유효 여부
    """
    # 기본 검증
    if not api_key:
        return False
    
    # 길이 검증
    if len(api_key) < 10:
        return False
    
    # 형식 검증 (바이낸스 API 키는 일반적으로 영숫자)
    if not api_key.isalnum():
        return False
    
    return True

# DEAD CODE: def validate_api_secret(api_secret: str) -> bool:
    """
    API 시크릿 유효성 검사
    
    Args:
        api_secret: API 시크릿
    
    Returns:
        bool: 유효 여부
    """
    # 기본 검증
    if not api_secret:
        return False
    
    # 길이 검증
    if len(api_secret) < 10:
        return False
    
    # 형식 검증 (바이낸스 API 시크릿은 일반적으로 영숫자)
    if not api_secret.isalnum():
        return False
    
    return True

# DEAD CODE: def generate_secure_password(length: int = 16) -> str:
    """
    안전한 비밀번호 생성
    
    Args:
        length: 비밀번호 길이
    
    Returns:
        str: 생성된 비밀번호
    """
    import secrets
    import string
    
    # 문자 집합
    alphabet = string.ascii_letters + string.digits + string.punctuation
    
    # 비밀번호 생성
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    return password
