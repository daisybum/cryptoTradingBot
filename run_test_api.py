#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
역사적 데이터 REST API 테스트 스크립트

이 스크립트는 역사적 데이터 API 서버의 기능을 테스트합니다.
"""

import os
import sys
import asyncio
import logging
import argparse
import dotenv
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.utils.logging_config import setup_logging
from src.api_server.test_api import APITester

# 로깅 설정
logger = logging.getLogger(__name__)
setup_logging()

def parse_arguments():
    """
    명령행 인수 파싱
    """
    parser = argparse.ArgumentParser(description='역사적 데이터 API 테스트')
    parser.add_argument('--url', type=str, default='http://localhost:8000', help='API 서버 URL (기본값: http://localhost:8000)')
    parser.add_argument('--symbol', type=str, default='BTC/USDT', help='테스트할 심볼 (기본값: BTC/USDT)')
    parser.add_argument('--timeframe', type=str, default='5m', help='테스트할 타임프레임 (기본값: 5m)')
    
    return parser.parse_args()

async def main():
    """
    메인 함수
    """
    # project.env 파일에서 환경 변수 로드
    env_file = os.path.join(project_root, "config", "env", "project.env")
    
    if os.path.exists(env_file):
        logger.info(f"project.env 파일에서 환경 변수를 로드합니다: {env_file}")
        dotenv.load_dotenv(env_file)
    else:
        logger.warning(f"project.env 파일을 찾을 수 없습니다: {env_file}")
    
    # 명령행 인수 파싱
    args = parse_arguments()
    
    # API 테스터 생성
    tester = APITester(args.url)
    
    # 테스트 실행
    success = await tester.run_all_tests(args.symbol, args.timeframe)
    
    # 종료 코드 설정
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
