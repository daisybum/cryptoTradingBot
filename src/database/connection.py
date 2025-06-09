"""
데이터베이스 연결 모듈

이 모듈은 PostgreSQL 및 InfluxDB 데이터베이스 연결을 관리합니다.
"""

import logging
import os
from typing import Dict, Any, Optional
from urllib.parse import quote_plus

# DEAD CODE: from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger(__name__)

# SQLAlchemy Base 클래스 정의
Base = declarative_base()

class DatabaseManager:
    """데이터베이스 연결 관리자 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        데이터베이스 관리자 초기화
        
        Args:
            config: 데이터베이스 설정
        """
        self.config = config
        self.pg_engine = None
        self.pg_session_factory = None
        self.influx_client = None
        self.influx_write_api = None
        self.influx_query_api = None
        
        # PostgreSQL 연결 설정
        self._setup_postgresql()
        
        # InfluxDB 연결 설정
        self._setup_influxdb()
        
        logger.info("데이터베이스 관리자 초기화됨")
    
    def _setup_postgresql(self):
        """PostgreSQL 연결 설정"""
        try:
            # 연결 정보 가져오기
            pg_config = self.config.get('postgresql', {})
            host = pg_config.get('host', 'localhost')
            port = pg_config.get('port', 5432)
            database = pg_config.get('database', 'trading')
            user = pg_config.get('user', 'postgres')
            password = pg_config.get('password', '')
            
            # 연결 문자열 생성
            connection_string = f"postgresql://{user}:{quote_plus(password)}@{host}:{port}/{database}"
            
            # 엔진 생성
            self.pg_engine = create_engine(
                connection_string,
                echo=pg_config.get('echo', False),
                pool_size=pg_config.get('pool_size', 5),
                max_overflow=pg_config.get('max_overflow', 10),
                pool_timeout=pg_config.get('pool_timeout', 30),
                pool_recycle=pg_config.get('pool_recycle', 1800)
            )
            
            # 세션 팩토리 생성
            self.pg_session_factory = sessionmaker(bind=self.pg_engine)
            
            logger.info(f"PostgreSQL 연결 설정됨: {host}:{port}/{database}")
            
        except Exception as e:
            logger.error(f"PostgreSQL 연결 설정 실패: {e}")
            raise
    
    def _setup_influxdb(self):
        """InfluxDB 연결 설정"""
        try:
            # 연결 정보 가져오기
            influx_config = self.config.get('influxdb', {})
            url = influx_config.get('url', 'http://localhost:8086')
            token = influx_config.get('token', '')
            org = influx_config.get('org', 'trading')
            bucket = influx_config.get('bucket', 'trading')
            
            # 클라이언트 생성
            self.influx_client = InfluxDBClient(url=url, token=token, org=org)
            self.influx_write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            self.influx_query_api = self.influx_client.query_api()
            
            # 기본 버킷 설정
# DEAD CODE:             self.default_bucket = bucket
            
            logger.info(f"InfluxDB 연결 설정됨: {url}, 조직: {org}, 버킷: {bucket}")
            
        except Exception as e:
            logger.error(f"InfluxDB 연결 설정 실패: {e}")
            # InfluxDB 연결 실패는 치명적이지 않을 수 있으므로 예외를 다시 발생시키지 않음
            self.influx_client = None
    
    def get_pg_session(self) -> Session:
        """
        PostgreSQL 세션 가져오기
        
        Returns:
            Session: SQLAlchemy 세션
        """
        if not self.pg_session_factory:
            raise RuntimeError("PostgreSQL 연결이 설정되지 않았습니다")
        
        return self.pg_session_factory()
    
# DEAD CODE:     def get_influx_write_api(self):
        """
        InfluxDB 쓰기 API 가져오기
        
        Returns:
            WriteApi: InfluxDB 쓰기 API
        """
        if not self.influx_write_api:
            raise RuntimeError("InfluxDB 연결이 설정되지 않았습니다")
        
        return self.influx_write_api
    
# DEAD CODE:     def get_influx_query_api(self):
        """
        InfluxDB 쿼리 API 가져오기
        
        Returns:
            QueryApi: InfluxDB 쿼리 API
        """
        if not self.influx_query_api:
            raise RuntimeError("InfluxDB 연결이 설정되지 않았습니다")
        
        return self.influx_query_api
    
    def close(self):
        """데이터베이스 연결 종료"""
        if self.influx_client:
            self.influx_client.close()
        
        if self.pg_engine:
            self.pg_engine.dispose()
        
        logger.info("데이터베이스 연결 종료됨")


# 싱글톤 인스턴스
_db_manager = None

def init_db(config: Dict[str, Any]) -> DatabaseManager:
    """
    데이터베이스 초기화
    
    Args:
        config: 데이터베이스 설정
        
    Returns:
        DatabaseManager: 데이터베이스 관리자 인스턴스
    """
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager(config)
    
    return _db_manager

def get_db_manager() -> Optional[DatabaseManager]:
    """
    데이터베이스 관리자 가져오기
    
    Returns:
        Optional[DatabaseManager]: 데이터베이스 관리자 인스턴스
    """
    global _db_manager
    
    if _db_manager is None:
        logger.warning("데이터베이스가 초기화되지 않았습니다. init_db()를 먼저 호출하세요.")
    
    return _db_manager

def create_tables():
    """데이터베이스 테이블 생성"""
    db_manager = get_db_manager()
    
    if db_manager and db_manager.pg_engine:
        Base.metadata.create_all(db_manager.pg_engine)
        logger.info("데이터베이스 테이블 생성됨")
    else:
        logger.error("데이터베이스 테이블 생성 실패: 데이터베이스 연결이 설정되지 않았습니다")
