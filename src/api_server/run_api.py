#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
역사적 데이터 REST API 서버 실행 스크립트

이 스크립트는 FastAPI 기반의 역사적 데이터 API 서버를 실행합니다.
"""

import os
import sys
import logging
import argparse
import uvicorn
import dotenv
from pathlib import Path

from src.utils.logging_config import setup_logging

# 로깅 설정
logger = logging.getLogger(__name__)
setup_logging()

def parse_arguments():
    """
    명령행 인수 파싱
    """
    parser = argparse.ArgumentParser(description='역사적 데이터 API 서버 실행')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='서버 호스트 (기본값: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000, help='서버 포트 (기본값: 8000)')
    parser.add_argument('--reload', action='store_true', help='코드 변경 시 자동 재시작')
    parser.add_argument('--debug', action='store_true', help='디버그 모드 활성화')
    
    return parser.parse_args()

def main():
    """
    메인 함수
    """
    args = parse_arguments()
    
    # project.env 파일에서 환경 변수 로드
    project_root = Path(__file__).parents[2]  # /home/shpark/workspace/altTradingBot
    env_file = project_root / "config" / "env" / "project.env"
    
    if env_file.exists():
        logger.info(f"project.env 파일에서 환경 변수를 로드합니다: {env_file}")
        dotenv.load_dotenv(env_file)
    else:
        logger.warning(f"project.env 파일을 찾을 수 없습니다: {env_file}")
    
    # 환경 변수 확인
    required_env_vars = [
        'BINANCE_API_KEY',
        'BINANCE_API_SECRET',
        'INFLUXDB_URL',
        'INFLUXDB_TOKEN',
        'INFLUXDB_ORG',
        'INFLUXDB_BUCKET'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    if missing_vars:
        logger.error(f"필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # 로그 레벨 설정
    log_level = "debug" if args.debug else "info"
    
    # FastAPI 앱 실행
    logger.info(f"역사적 데이터 API 서버 시작 중... (호스트: {args.host}, 포트: {args.port})")
    uvicorn.run(
        "src.api_server.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=log_level
    )

if __name__ == "__main__":
    main()
