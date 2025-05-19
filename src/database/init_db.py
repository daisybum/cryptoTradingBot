"""
데이터베이스 초기화 스크립트

이 스크립트는 거래 데이터베이스 스키마를 초기화합니다.
"""

import os
import sys
import logging
import argparse
from typing import Dict, Any
import yaml
from dotenv import load_dotenv

# 프로젝트 루트 경로를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.database.connection import init_db, create_tables, Base
from src.database.models import Order, Fill, OrderError, IndicatorSnapshot, TradeSession

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    설정 파일 로드
    
    Args:
        config_path: 설정 파일 경로 (선택 사항)
        
    Returns:
        Dict[str, Any]: 설정 데이터
    """
    # 기본 설정 파일 경로
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), '../../config/config.yaml')
    
    # 설정 파일 로드
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"설정 파일 로드됨: {config_path}")
        return config
    except Exception as e:
        logger.error(f"설정 파일 로드 실패: {e}")
        
        # 기본 설정 반환
        return {
            'postgresql': {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'trading'),
                'user': os.getenv('POSTGRES_USER', 'postgres'),
                'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
                'echo': False,
                'pool_size': 5,
                'max_overflow': 10
            },
            'influxdb': {
                'url': os.getenv('INFLUXDB_URL', 'http://localhost:8086'),
                'token': os.getenv('INFLUXDB_TOKEN', ''),
                'org': os.getenv('INFLUXDB_ORG', 'trading'),
                'bucket': os.getenv('INFLUXDB_BUCKET', 'trading')
            }
        }

def init_database(config: Dict[str, Any], drop_all: bool = False):
    """
    데이터베이스 초기화
    
    Args:
        config: 데이터베이스 설정
        drop_all: 모든 테이블 삭제 후 재생성 여부
    """
    try:
        # 데이터베이스 관리자 초기화
        db_manager = init_db(config)
        
        if drop_all:
            # 모든 테이블 삭제
            logger.warning("모든 테이블을 삭제합니다...")
            Base.metadata.drop_all(db_manager.pg_engine)
            logger.info("모든 테이블이 삭제되었습니다.")
        
        # 테이블 생성
        create_tables()
        logger.info("데이터베이스 테이블이 생성되었습니다.")
        
        return True
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        return False

def main():
    """메인 함수"""
    # 환경 변수 로드
    load_dotenv()
    
    # 명령행 인자 파싱
    parser = argparse.ArgumentParser(description='데이터베이스 초기화 스크립트')
    parser.add_argument('--config', type=str, help='설정 파일 경로')
    parser.add_argument('--drop-all', action='store_true', help='모든 테이블 삭제 후 재생성')
    args = parser.parse_args()
    
    # 설정 로드
    config = load_config(args.config)
    
    # 데이터베이스 초기화
    success = init_database(config, args.drop_all)
    
    if success:
        logger.info("데이터베이스 초기화가 완료되었습니다.")
    else:
        logger.error("데이터베이스 초기화에 실패했습니다.")
        sys.exit(1)

if __name__ == '__main__':
    main()
