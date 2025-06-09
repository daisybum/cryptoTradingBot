"""
SSL/TLS 인증서 관리 모듈

이 모듈은 Cloudflare와 통합하여 SSL/TLS 인증서를 관리하고 보안 통신을 설정합니다.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List, Tuple
from dotenv import load_dotenv

# 로깅 설정
logger = logging.getLogger(__name__)

class CloudflareManager:
    """Cloudflare API 관리 클래스"""
    
    def __init__(self, api_token: str = None, zone_id: str = None):
        """
        Cloudflare 관리자 초기화
        
        Args:
            api_token: Cloudflare API 토큰 (기본값: 환경 변수 CLOUDFLARE_API_TOKEN)
            zone_id: Cloudflare 영역 ID (기본값: 환경 변수 CLOUDFLARE_ZONE)
        """
        # 환경 변수 로드
        load_dotenv()
        
        # API 토큰 및 영역 ID 설정
        self.api_token = api_token or os.environ.get('CLOUDFLARE_API_TOKEN')
        self.zone_id = zone_id or os.environ.get('CLOUDFLARE_ZONE')
        
        # API 기본 URL
        self.base_url = "https://api.cloudflare.com/client/v4"
        
        # API 요청 헤더
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        logger.debug("Cloudflare 관리자 초기화 완료")
    
    def is_configured(self) -> bool:
        """
        Cloudflare 설정이 완료되었는지 확인
        
        Returns:
            bool: 설정 완료 여부
        """
        return bool(self.api_token and self.zone_id)
    
    def get_zone_details(self) -> Optional[Dict[str, Any]]:
        """
        영역 세부 정보 조회
        
        Returns:
            Optional[Dict[str, Any]]: 영역 세부 정보 또는 None
        """
        if not self.is_configured():
            logger.error("Cloudflare가 구성되지 않았습니다.")
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/zones/{self.zone_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('result')
            
            logger.error(f"영역 세부 정보 조회 실패: {response.text}")
            return None
        except Exception as e:
            logger.error(f"영역 세부 정보 조회 중 오류 발생: {e}")
            return None
    
    def list_dns_records(self, type: str = None, name: str = None) -> List[Dict[str, Any]]:
        """
        DNS 레코드 목록 조회
        
        Args:
            type: DNS 레코드 유형 (예: A, CNAME)
            name: DNS 레코드 이름
        
        Returns:
            List[Dict[str, Any]]: DNS 레코드 목록
        """
        if not self.is_configured():
            logger.error("Cloudflare가 구성되지 않았습니다.")
            return []
        
        try:
            params = {}
            if type:
                params['type'] = type
            if name:
                params['name'] = name
            
            response = requests.get(
                f"{self.base_url}/zones/{self.zone_id}/dns_records",
                headers=self.headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('result', [])
            
            logger.error(f"DNS 레코드 목록 조회 실패: {response.text}")
            return []
        except Exception as e:
            logger.error(f"DNS 레코드 목록 조회 중 오류 발생: {e}")
            return []
    
    def create_dns_record(self, type: str, name: str, content: str, ttl: int = 1, proxied: bool = True) -> Optional[Dict[str, Any]]:
        """
        DNS 레코드 생성
        
        Args:
            type: DNS 레코드 유형 (예: A, CNAME)
            name: DNS 레코드 이름
            content: DNS 레코드 내용
            ttl: TTL (Time To Live)
            proxied: Cloudflare 프록시 사용 여부
        
        Returns:
            Optional[Dict[str, Any]]: 생성된 DNS 레코드 또는 None
        """
        if not self.is_configured():
            logger.error("Cloudflare가 구성되지 않았습니다.")
            return None
        
        try:
            data = {
                "type": type,
                "name": name,
                "content": content,
                "ttl": ttl,
                "proxied": proxied
            }
            
            response = requests.post(
                f"{self.base_url}/zones/{self.zone_id}/dns_records",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info(f"DNS 레코드 생성 성공: {name}")
                    return data.get('result')
            
            logger.error(f"DNS 레코드 생성 실패: {response.text}")
            return None
        except Exception as e:
            logger.error(f"DNS 레코드 생성 중 오류 발생: {e}")
            return None
    
    def update_dns_record(self, record_id: str, type: str, name: str, content: str, ttl: int = 1, proxied: bool = True) -> Optional[Dict[str, Any]]:
        """
        DNS 레코드 업데이트
        
        Args:
            record_id: DNS 레코드 ID
            type: DNS 레코드 유형 (예: A, CNAME)
            name: DNS 레코드 이름
            content: DNS 레코드 내용
            ttl: TTL (Time To Live)
            proxied: Cloudflare 프록시 사용 여부
        
        Returns:
            Optional[Dict[str, Any]]: 업데이트된 DNS 레코드 또는 None
        """
        if not self.is_configured():
            logger.error("Cloudflare가 구성되지 않았습니다.")
            return None
        
        try:
            data = {
                "type": type,
                "name": name,
                "content": content,
                "ttl": ttl,
                "proxied": proxied
            }
            
            response = requests.put(
                f"{self.base_url}/zones/{self.zone_id}/dns_records/{record_id}",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info(f"DNS 레코드 업데이트 성공: {name}")
                    return data.get('result')
            
            logger.error(f"DNS 레코드 업데이트 실패: {response.text}")
            return None
        except Exception as e:
            logger.error(f"DNS 레코드 업데이트 중 오류 발생: {e}")
            return None
    
    def delete_dns_record(self, record_id: str) -> bool:
        """
        DNS 레코드 삭제
        
        Args:
            record_id: DNS 레코드 ID
        
        Returns:
            bool: 성공 여부
        """
        if not self.is_configured():
            logger.error("Cloudflare가 구성되지 않았습니다.")
            return False
        
        try:
            response = requests.delete(
                f"{self.base_url}/zones/{self.zone_id}/dns_records/{record_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info(f"DNS 레코드 삭제 성공: {record_id}")
                    return True
            
            logger.error(f"DNS 레코드 삭제 실패: {response.text}")
            return False
        except Exception as e:
            logger.error(f"DNS 레코드 삭제 중 오류 발생: {e}")
            return False
    
    def get_ssl_verification_status(self) -> Optional[Dict[str, Any]]:
        """
        SSL 인증서 검증 상태 조회
        
        Returns:
            Optional[Dict[str, Any]]: SSL 인증서 검증 상태 또는 None
        """
        if not self.is_configured():
            logger.error("Cloudflare가 구성되지 않았습니다.")
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/zones/{self.zone_id}/ssl/verification",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('result')
            
            logger.error(f"SSL 인증서 검증 상태 조회 실패: {response.text}")
            return None
        except Exception as e:
            logger.error(f"SSL 인증서 검증 상태 조회 중 오류 발생: {e}")
            return None
    
    def get_ssl_settings(self) -> Optional[Dict[str, Any]]:
        """
        SSL 설정 조회
        
        Returns:
            Optional[Dict[str, Any]]: SSL 설정 또는 None
        """
        if not self.is_configured():
            logger.error("Cloudflare가 구성되지 않았습니다.")
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/zones/{self.zone_id}/settings/ssl",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('result')
            
            logger.error(f"SSL 설정 조회 실패: {response.text}")
            return None
        except Exception as e:
            logger.error(f"SSL 설정 조회 중 오류 발생: {e}")
            return None
    
    def update_ssl_settings(self, value: str) -> Optional[Dict[str, Any]]:
        """
        SSL 설정 업데이트
        
        Args:
            value: SSL 설정 값 (off, flexible, full, strict)
        
        Returns:
            Optional[Dict[str, Any]]: 업데이트된 SSL 설정 또는 None
        """
        if not self.is_configured():
            logger.error("Cloudflare가 구성되지 않았습니다.")
            return None
        
        try:
            data = {
                "value": value
            }
            
            response = requests.patch(
                f"{self.base_url}/zones/{self.zone_id}/settings/ssl",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info(f"SSL 설정 업데이트 성공: {value}")
                    return data.get('result')
            
            logger.error(f"SSL 설정 업데이트 실패: {response.text}")
            return None
        except Exception as e:
            logger.error(f"SSL 설정 업데이트 중 오류 발생: {e}")
            return None

class SSLManager:
    """SSL/TLS 인증서 관리 클래스"""
    
    def __init__(self, cloudflare_api_token: str = None, cloudflare_zone_id: str = None):
        """
        SSL 관리자 초기화
        
        Args:
            cloudflare_api_token: Cloudflare API 토큰
            cloudflare_zone_id: Cloudflare 영역 ID
        """
        # Cloudflare 관리자 초기화
        self.cloudflare = CloudflareManager(
            api_token=cloudflare_api_token,
            zone_id=cloudflare_zone_id
        )
        
        # 환경 변수 로드
        load_dotenv()
        
        # SSL 인증서 디렉토리
        self.cert_dir = os.environ.get('SSL_CERT_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config/ssl/certs'))
        self.key_dir = os.environ.get('SSL_KEY_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config/ssl/private'))
        
        # 디렉토리 생성
        os.makedirs(self.cert_dir, exist_ok=True)
        os.makedirs(self.key_dir, exist_ok=True)
        
        logger.debug("SSL 관리자 초기화 완료")
    
    def setup_cloudflare_ssl(self, mode: str = 'strict') -> bool:
        """
        Cloudflare SSL 설정
        
        Args:
            mode: SSL 모드 (off, flexible, full, strict)
        
        Returns:
            bool: 성공 여부
        """
        if not self.cloudflare.is_configured():
            logger.error("Cloudflare가 구성되지 않았습니다.")
            return False
        
        try:
            # SSL 설정 업데이트
            result = self.cloudflare.update_ssl_settings(mode)
            
            if result:
                logger.info(f"Cloudflare SSL 설정 완료: {mode}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Cloudflare SSL 설정 중 오류 발생: {e}")
            return False
    
    def verify_ssl_configuration(self) -> Dict[str, Any]:
        """
        SSL 구성 확인
        
        Returns:
            Dict[str, Any]: SSL 구성 상태
        """
        result = {
            "cloudflare_configured": self.cloudflare.is_configured(),
            "ssl_settings": None,
            "verification_status": None
        }
        
        if result["cloudflare_configured"]:
            result["ssl_settings"] = self.cloudflare.get_ssl_settings()
            result["verification_status"] = self.cloudflare.get_ssl_verification_status()
        
        return result
    
    def create_subdomain(self, subdomain: str, target_ip: str, proxied: bool = True) -> bool:
        """
        서브도메인 생성
        
        Args:
            subdomain: 서브도메인 이름
            target_ip: 대상 IP 주소
            proxied: Cloudflare 프록시 사용 여부
        
        Returns:
            bool: 성공 여부
        """
        if not self.cloudflare.is_configured():
            logger.error("Cloudflare가 구성되지 않았습니다.")
            return False
        
        try:
            # 영역 정보 조회
            zone_info = self.cloudflare.get_zone_details()
            if not zone_info:
                logger.error("영역 정보를 조회할 수 없습니다.")
                return False
            
            zone_name = zone_info.get('name')
            if not zone_name:
                logger.error("영역 이름을 조회할 수 없습니다.")
                return False
            
            # 전체 도메인 이름 생성
            full_domain = f"{subdomain}.{zone_name}"
            
            # 기존 레코드 확인
            existing_records = self.cloudflare.list_dns_records(type="A", name=full_domain)
            
            if existing_records:
                # 기존 레코드 업데이트
                record = existing_records[0]
                result = self.cloudflare.update_dns_record(
                    record_id=record['id'],
                    type="A",
                    name=full_domain,
                    content=target_ip,
                    proxied=proxied
                )
                
                if result:
                    logger.info(f"서브도메인 업데이트 성공: {full_domain} -> {target_ip}")
                    return True
            else:
                # 새 레코드 생성
                result = self.cloudflare.create_dns_record(
                    type="A",
                    name=full_domain,
                    content=target_ip,
                    proxied=proxied
                )
                
                if result:
                    logger.info(f"서브도메인 생성 성공: {full_domain} -> {target_ip}")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"서브도메인 생성 중 오류 발생: {e}")
            return False
    
    def get_public_ip(self) -> Optional[str]:
        """
        공용 IP 주소 조회
        
        Returns:
            Optional[str]: 공용 IP 주소 또는 None
        """
        try:
            response = requests.get("https://api.ipify.org")
            if response.status_code == 200:
                return response.text.strip()
            
            logger.error(f"공용 IP 주소 조회 실패: {response.text}")
            return None
        except Exception as e:
            logger.error(f"공용 IP 주소 조회 중 오류 발생: {e}")
            return None
    
    def setup_api_subdomain(self, proxied: bool = True) -> bool:
        """
        API 서브도메인 설정
        
        Args:
            proxied: Cloudflare 프록시 사용 여부
        
        Returns:
            bool: 성공 여부
        """
        # 공용 IP 주소 조회
        public_ip = self.get_public_ip()
        if not public_ip:
            logger.error("공용 IP 주소를 조회할 수 없습니다.")
            return False
        
        # API 서브도메인 생성
        return self.create_subdomain("api", public_ip, proxied)
    
    def setup_dashboard_subdomain(self, proxied: bool = True) -> bool:
        """
        대시보드 서브도메인 설정
        
        Args:
            proxied: Cloudflare 프록시 사용 여부
        
        Returns:
            bool: 성공 여부
        """
        # 공용 IP 주소 조회
        public_ip = self.get_public_ip()
        if not public_ip:
            logger.error("공용 IP 주소를 조회할 수 없습니다.")
            return False
        
        # 대시보드 서브도메인 생성
        return self.create_subdomain("dashboard", public_ip, proxied)
    
    def list_subdomains(self) -> List[Dict[str, Any]]:
        """
        서브도메인 목록 조회
        
        Returns:
            List[Dict[str, Any]]: 서브도메인 목록
        """
        if not self.cloudflare.is_configured():
            logger.error("Cloudflare가 구성되지 않았습니다.")
            return []
        
        try:
            # 영역 정보 조회
            zone_info = self.cloudflare.get_zone_details()
            if not zone_info:
                logger.error("영역 정보를 조회할 수 없습니다.")
                return []
            
            zone_name = zone_info.get('name')
            if not zone_name:
                logger.error("영역 이름을 조회할 수 없습니다.")
                return []
            
            # DNS 레코드 조회
            records = self.cloudflare.list_dns_records()
            
            # 서브도메인 필터링
            subdomains = []
            for record in records:
                if record['type'] in ['A', 'CNAME'] and record['name'] != zone_name:
                    subdomains.append({
                        'id': record['id'],
                        'name': record['name'],
                        'type': record['type'],
                        'content': record['content'],
                        'proxied': record.get('proxied', False)
                    })
            
            return subdomains
        except Exception as e:
            logger.error(f"서브도메인 목록 조회 중 오류 발생: {e}")
            return []
