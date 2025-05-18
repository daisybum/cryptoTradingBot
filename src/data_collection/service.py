"""
Binance 데이터 수집 서비스 실행 모듈

이 모듈은 Binance 데이터 수집기를 독립적인 서비스로 실행합니다.
Docker 컨테이너에서 실행되거나 독립 프로세스로 실행될 수 있습니다.
"""

import os
import sys
import asyncio
import signal
import logging
from datetime import datetime

from src.utils.logger import setup_logging
from src.utils.env_loader import get_env_loader
from src.data_collection.data_collector import DataCollector

# 환경 변수 로더
env = get_env_loader()

# 로깅 설정
log_level = env.get('LOG_LEVEL', 'INFO')
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
log_file = os.path.join(log_dir, f'data_collector_{datetime.now().strftime("%Y%m%d")}.log')

# 로거 설정
logger = setup_logging(log_level, log_file)

# 데이터 수집기 인스턴스
collector = None

async def main():
    """
    데이터 수집 서비스 메인 함수
    """
    global collector
    
    try:
        logger.info("Binance 데이터 수집 서비스 시작 중...")
        
        # 데이터 수집기 초기화
        collector = DataCollector()
        
        # 데이터 수집 시작
        await collector.start()
    except KeyboardInterrupt:
        logger.info("키보드 인터럽트로 서비스 종료")
    except Exception as e:
        logger.error(f"서비스 실행 중 오류 발생: {e}")
    finally:
        # 데이터 수집기 종료
        if collector:
            await collector.stop()
        
        logger.info("Binance 데이터 수집 서비스 종료됨")

def signal_handler():
    """
    시그널 핸들러
    """
    logger.info("종료 시그널 수신됨")
    
    # 이벤트 루프 가져오기
    loop = asyncio.get_event_loop()
    
    # 데이터 수집기 종료
    if collector:
        loop.create_task(collector.stop())
    
    # 이벤트 루프 종료
    loop.stop()

if __name__ == "__main__":
    # 시그널 핸들러 등록
    loop = asyncio.get_event_loop()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        # 메인 함수 실행
        loop.run_until_complete(main())
    finally:
        # 이벤트 루프 종료
        loop.close()
        
        logger.info("프로그램 종료")
