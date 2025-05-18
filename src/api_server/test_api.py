#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
역사적 데이터 REST API 테스트 스크립트

이 스크립트는 역사적 데이터 API 서버의 기능을 테스트합니다.
"""

import os
import sys
import json
import asyncio
import logging
import argparse
import dotenv
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp
from aiohttp import ClientSession

from src.utils.logging_config import setup_logging

# 로깅 설정
logger = logging.getLogger(__name__)
setup_logging()

class APITester:
    """
    API 테스트 클래스
    """
    def __init__(self, base_url: str):
        """
        초기화
        
        Args:
            base_url: API 서버 기본 URL
        """
        self.base_url = base_url
        self.session = None
    
    async def setup(self):
        """
        세션 설정
        """
        self.session = ClientSession()
    
    async def close(self):
        """
        세션 종료
        """
        if self.session:
            await self.session.close()
    
    async def test_root_endpoint(self):
        """
        루트 엔드포인트 테스트
        """
        url = f"{self.base_url}/"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"루트 엔드포인트 응답: {data}")
                    return True
                else:
                    logger.error(f"루트 엔드포인트 오류: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"루트 엔드포인트 요청 중 오류 발생: {e}")
            return False
    
    async def test_symbols_endpoint(self):
        """
        심볼 목록 엔드포인트 테스트
        """
        url = f"{self.base_url}/symbols"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"심볼 목록 응답: {data[:5]}... (총 {len(data)}개)")
                    return True
                else:
                    logger.error(f"심볼 목록 엔드포인트 오류: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"심볼 목록 엔드포인트 요청 중 오류 발생: {e}")
            return False
    
    async def test_timeframes_endpoint(self):
        """
        타임프레임 목록 엔드포인트 테스트
        """
        url = f"{self.base_url}/timeframes"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"타임프레임 목록 응답: {data}")
                    return True
                else:
                    logger.error(f"타임프레임 목록 엔드포인트 오류: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"타임프레임 목록 엔드포인트 요청 중 오류 발생: {e}")
            return False
    
    async def test_historical_endpoint(self, symbol: str, timeframe: str):
        """
        역사적 데이터 엔드포인트 테스트
        
        Args:
            symbol: 심볼 (예: BTC/USDT)
            timeframe: 타임프레임 (예: 5m)
        """
        # 심볼 형식 변환 (BTC/USDT -> BTC_USDT)
        formatted_symbol = symbol.replace('/', '_')
        
        # 30일 전 시간 계산
        start_time = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
        end_time = int(datetime.now().timestamp() * 1000)
        
        url = f"{self.base_url}/historical/{formatted_symbol}/{timeframe}?start={start_time}&end={end_time}&limit=100"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"역사적 데이터 응답: {symbol} {timeframe} (총 {len(data['data'])}개 캔들)")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"역사적 데이터 엔드포인트 오류: {response.status} - {error_text}")
                    return False
        except Exception as e:
            logger.error(f"역사적 데이터 엔드포인트 요청 중 오류 발생: {e}")
            return False
    
    async def test_recent_endpoint(self, symbol: str, timeframe: str):
        """
        최근 데이터 엔드포인트 테스트
        
        Args:
            symbol: 심볼 (예: BTC/USDT)
            timeframe: 타임프레임 (예: 5m)
        """
        # 심볼 형식 변환 (BTC/USDT -> BTC_USDT)
        formatted_symbol = symbol.replace('/', '_')
        
        url = f"{self.base_url}/recent/{formatted_symbol}/{timeframe}?limit=50"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"최근 데이터 응답: {symbol} {timeframe} (총 {len(data['data'])}개 캔들)")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"최근 데이터 엔드포인트 오류: {response.status} - {error_text}")
                    return False
        except Exception as e:
            logger.error(f"최근 데이터 엔드포인트 요청 중 오류 발생: {e}")
            return False
    
    async def run_all_tests(self, symbol: str = "BTC/USDT", timeframe: str = "5m"):
        """
        모든 테스트 실행
        
        Args:
            symbol: 테스트할 심볼
            timeframe: 테스트할 타임프레임
        """
        await self.setup()
        
        try:
            logger.info("API 테스트 시작...")
            
            # 루트 엔드포인트 테스트
            root_result = await self.test_root_endpoint()
            
            # 심볼 목록 엔드포인트 테스트
            symbols_result = await self.test_symbols_endpoint()
            
            # 타임프레임 목록 엔드포인트 테스트
            timeframes_result = await self.test_timeframes_endpoint()
            
            # 역사적 데이터 엔드포인트 테스트
            historical_result = await self.test_historical_endpoint(symbol, timeframe)
            
            # 최근 데이터 엔드포인트 테스트
            recent_result = await self.test_recent_endpoint(symbol, timeframe)
            
            # 결과 출력
            logger.info("API 테스트 결과:")
            logger.info(f"  루트 엔드포인트: {'성공' if root_result else '실패'}")
            logger.info(f"  심볼 목록 엔드포인트: {'성공' if symbols_result else '실패'}")
            logger.info(f"  타임프레임 목록 엔드포인트: {'성공' if timeframes_result else '실패'}")
            logger.info(f"  역사적 데이터 엔드포인트: {'성공' if historical_result else '실패'}")
            logger.info(f"  최근 데이터 엔드포인트: {'성공' if recent_result else '실패'}")
            
            all_passed = all([root_result, symbols_result, timeframes_result, historical_result, recent_result])
            logger.info(f"전체 테스트 결과: {'모두 성공' if all_passed else '일부 실패'}")
            
            return all_passed
        finally:
            await self.close()

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
    project_root = Path(__file__).parents[2]  # /home/shpark/workspace/altTradingBot
    env_file = project_root / "config" / "env" / "project.env"
    
    if env_file.exists():
        logger.info(f"project.env 파일에서 환경 변수를 로드합니다: {env_file}")
        dotenv.load_dotenv(env_file)
    else:
        logger.warning(f"project.env 파일을 찾을 수 없습니다: {env_file}")
    
    args = parse_arguments()
    
    # API 테스터 생성
    tester = APITester(args.url)
    
    # 테스트 실행
    success = await tester.run_all_tests(args.symbol, args.timeframe)
    
    # 종료 코드 설정
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
