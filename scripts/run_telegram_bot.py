#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
텔레그램 봇 실행 스크립트

이 스크립트는 텔레그램 봇을 초기화하고 실행합니다.
"""

import os
import sys
import logging
import argparse
import asyncio
import signal
import dotenv
from pathlib import Path

from src.notifications.telegram_bot import init_telegram_bot, get_telegram_bot
from src.risk_manager.risk_manager import init_risk_manager, get_risk_manager
from src.execution_engine.trading import start_trading
from src.utils.logging_config import setup_logging

# 로깅 설정
logger = logging.getLogger(__name__)
setup_logging()

def parse_arguments():
    """
    명령행 인수 파싱
    """
    parser = argparse.ArgumentParser(description='텔레그램 봇 실행')
    parser.add_argument('--token', type=str, help='텔레그램 봇 토큰 (기본값: 환경 변수에서 가져옴)')
    parser.add_argument('--chat-id', type=str, help='텔레그램 채팅 ID (기본값: 환경 변수에서 가져옴)')
    parser.add_argument('--auth-users', type=str, help='인증된 사용자 ID 목록 (쉼표로 구분)')
    parser.add_argument('--debug', action='store_true', help='디버그 모드 활성화')
    
    return parser.parse_args()

def signal_handler(sig, frame):
    """
    시그널 핸들러 (Ctrl+C 등)
    """
    logger.info("종료 신호를 받았습니다. 텔레그램 봇을 종료합니다...")
    
    # 텔레그램 봇 종료
    telegram_bot = get_telegram_bot()
    if telegram_bot:
        telegram_bot.stop()
    
    sys.exit(0)

async def main():
    """
    메인 함수
    """
    args = parse_arguments()
    
    # project.env 파일에서 환경 변수 로드
    project_root = Path(__file__).parents[1]  # /home/shpark/workspace/altTradingBot
    env_file = project_root / "config" / "env" / "project.env"
    
    if env_file.exists():
        logger.info(f"project.env 파일에서 환경 변수를 로드합니다: {env_file}")
        dotenv.load_dotenv(env_file)
    else:
        logger.warning(f"project.env 파일을 찾을 수 없습니다: {env_file}")
    
    # 환경 변수 확인
    required_env_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    if missing_vars:
        logger.error(f"필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # 로그 레벨 설정
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.getLogger().setLevel(log_level)
    
    # 명령행 인수 또는 환경 변수에서 설정 가져오기
    token = args.token or os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = args.chat_id or os.environ.get('TELEGRAM_CHAT_ID')
    
    # 인증된 사용자 목록 설정
    authorized_users = None
    if args.auth_users:
        try:
            authorized_users = [int(user_id.strip()) for user_id in args.auth_users.split(',')]
        except ValueError:
            logger.error("인증된 사용자 ID 목록 파싱 오류")
            sys.exit(1)
    
    # 설정 파일 로드 (실제 구현에서는 설정 파일 경로를 적절히 조정해야 함)
    config_path = project_root / "config" / "config.json"
    config = {}  # 실제로는 설정 파일에서 로드해야 함
    
    # 리스크 관리자 초기화
    risk_manager = init_risk_manager(config)
    if not risk_manager:
        logger.error("리스크 관리자 초기화 실패")
        sys.exit(1)
    
    # Redis 연결 설정
    await risk_manager.connect_redis()
    
    # 실행 엔진 초기화 및 시작
    execution_engine = None
    try:
        execution_engine = start_trading(config)
    except Exception as e:
        logger.error(f"실행 엔진 초기화 실패: {e}")
    
    # 텔레그램 봇 초기화
    telegram_bot = init_telegram_bot(
        token=token,
        chat_id=chat_id,
        risk_manager=risk_manager,
        execution_engine=execution_engine,
        authorized_users=authorized_users
    )
    
    if not telegram_bot:
        logger.error("텔레그램 봇 초기화 실패")
        sys.exit(1)
    
    # 텔레그램 봇 시작
    telegram_bot.start()
    
    # 시작 메시지 로깅
    logger.info(f"텔레그램 봇이 시작되었습니다. 채팅 ID: {chat_id}")
    
    # 무한 루프로 봇 실행 유지
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("텔레그램 봇을 종료합니다...")
        telegram_bot.stop()

if __name__ == "__main__":
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 비동기 메인 함수 실행
    asyncio.run(main())
