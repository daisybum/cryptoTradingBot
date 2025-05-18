#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
역사적 데이터 수집 스크립트

이 스크립트는 Binance API를 사용하여 역사적 OHLCV 데이터를 수집하고 InfluxDB에 저장합니다.
"""

import os
import sys
import asyncio
import logging
import argparse
import dotenv
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.utils.logging_config import setup_logging
from src.data_collection.data_collector import DataCollector

# 로깅 설정
logger = logging.getLogger(__name__)
setup_logging()

def parse_arguments():
    """
    명령행 인수 파싱
    """
    parser = argparse.ArgumentParser(description='역사적 데이터 수집')
    parser.add_argument('--symbol', type=str, default='BTC/USDT', help='수집할 심볼 (기본값: BTC/USDT)')
    parser.add_argument('--timeframe', type=str, default='1h', help='수집할 타임프레임 (기본값: 1h)')
    parser.add_argument('--days', type=int, default=30, help='수집할 일수 (기본값: 30)')
    
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
    
    # 필수 환경 변수 확인
    required_env_vars = [
        'BINANCE_API_KEY', 'BINANCE_API_SECRET',
        'INFLUXDB_URL', 'INFLUXDB_TOKEN', 'INFLUXDB_ORG', 'INFLUXDB_BUCKET'
    ]
    
    for var in required_env_vars:
        if not os.environ.get(var):
            logger.error(f"환경 변수가 설정되지 않았습니다: {var}")
            return
    
    logger.info(f"데이터 수집 시작: {args.symbol} {args.timeframe} (기간: {args.days}일)")
    
    try:
        # 데이터 수집기 초기화
        collector = DataCollector()
        
        # 역사적 데이터 수집 및 저장
        logger.info(f"역사적 데이터 수집 중: {args.symbol} {args.timeframe} (기간: {args.days}일)")
        
        # 데이터 수집기 시작
        await collector.start()
        
        # 역사적 데이터 수집
        data = await collector.fetch_complete_history(
            symbol=args.symbol,
            timeframe=args.timeframe,
            days=args.days
        )
        
        logger.info(f"수집된 데이터: {args.symbol} {args.timeframe} (총 {len(data) if data else 0}개 캔들)")
        
        logger.info(f"데이터 수집 완료: {args.symbol} {args.timeframe}")
    
    except Exception as e:
        logger.error(f"데이터 수집 중 오류 발생: {e}")
    
    finally:
        # 리소스 정리
        if 'collector' in locals():
            await collector.stop()

if __name__ == "__main__":
    asyncio.run(main())
