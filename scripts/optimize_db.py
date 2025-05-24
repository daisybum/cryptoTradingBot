#!/usr/bin/env python3
"""
데이터베이스 최적화 스크립트

이 스크립트는 PostgreSQL 인덱스를 최적화하고 InfluxDB 버킷을 설정합니다.
Docker 환경에서 실행됩니다.
"""

import os
import sys
import logging
from pathlib import Path

# 프로젝트 루트 경로를 Python 경로에 추가
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from src.database.connection import init_db, get_db_manager
from src.database.init_db import setup_postgresql_indexes, setup_influxdb, setup_data_retention_policy, load_config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """메인 함수"""
    try:
        # 환경 변수 로드
        logger.info("환경 변수 로드 중...")
        
        # 설정 로드
        config = load_config()
        
        # 데이터베이스 관리자 초기화
        logger.info("데이터베이스 관리자 초기화 중...")
        db_manager = init_db(config)
        
        if not db_manager:
            logger.error("데이터베이스 관리자 초기화 실패")
            sys.exit(1)
        
        # PostgreSQL 인덱스 최적화
        logger.info("PostgreSQL 인덱스 최적화 중...")
        if setup_postgresql_indexes(config):
            logger.info("PostgreSQL 인덱스 최적화 완료")
        else:
            logger.error("PostgreSQL 인덱스 최적화 실패")
        
        # InfluxDB 설정
        logger.info("InfluxDB 설정 중...")
        if setup_influxdb(config):
            logger.info("InfluxDB 설정 완료")
        else:
            logger.error("InfluxDB 설정 실패")
        
        # 데이터 보존 정책 설정
        logger.info("데이터 보존 정책 설정 중...")
        if setup_data_retention_policy(config):
            logger.info("데이터 보존 정책 설정 완료")
        else:
            logger.error("데이터 보존 정책 설정 실패")
        
        logger.info("데이터베이스 최적화가 완료되었습니다.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"데이터베이스 최적화 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
