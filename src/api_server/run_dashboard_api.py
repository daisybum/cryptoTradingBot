#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
웹 대시보드 API 서버 실행 스크립트
"""

import os
import sys
import argparse
import uvicorn
import logging
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def parse_args():
    """
    명령행 인수 파싱
    """
    parser = argparse.ArgumentParser(description="Run the dashboard API server")
    parser.add_argument(
        "--host", 
        type=str, 
        default=os.getenv("API_HOST", "0.0.0.0"),
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=int(os.getenv("API_PORT", "8000")),
        help="Port to bind the server to (default: 8000)"
    )
    parser.add_argument(
        "--reload", 
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=int(os.getenv("API_WORKERS", "1")),
        help="Number of worker processes (default: 1)"
    )
    
    return parser.parse_args()

def main():
    """
    메인 함수
    """
    args = parse_args()
    
    logger.info(f"Starting dashboard API server on {args.host}:{args.port}")
    
    uvicorn.run(
        "src.api_server.dashboard_api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers
    )

if __name__ == "__main__":
    main()
