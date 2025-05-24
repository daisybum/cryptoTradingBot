#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
텔레그램 봇 테스트 스크립트

이 스크립트는 텔레그램 봇 기능을 테스트합니다.
"""

import os
import sys
import logging
import asyncio
import json
import argparse
import dotenv
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 디렉토리 설정
project_root = Path(__file__).parents[1]
sys.path.append(str(project_root))

from src.notifications.telegram_bot import init_telegram_bot, get_telegram_bot
from src.risk_manager.risk_manager import init_risk_manager, get_risk_manager
from src.utils.logging_config import setup_logging

# 로깅 설정
logger = logging.getLogger(__name__)
setup_logging()

def parse_arguments():
    """
    명령행 인수 파싱
    """
    parser = argparse.ArgumentParser(description='텔레그램 봇 테스트')
    parser.add_argument('--token', type=str, help='텔레그램 봇 토큰 (기본값: 환경 변수에서 가져옴)')
    parser.add_argument('--chat-id', type=str, help='텔레그램 채팅 ID (기본값: 환경 변수에서 가져옴)')
    parser.add_argument('--test', choices=['all', 'messages', 'commands', 'events'], 
                        default='all', help='테스트 유형 (기본값: all)')
    parser.add_argument('--debug', action='store_true', help='디버그 모드 활성화')
    
    return parser.parse_args()

async def test_messages(telegram_bot):
    """
    메시지 전송 테스트
    """
    logger.info("메시지 전송 테스트 시작...")
    
    # 정보 메시지 테스트
    logger.info("정보 메시지 전송 테스트...")
    success = telegram_bot.send_message("ℹ️ 테스트 정보 메시지입니다.", "info")
    logger.info(f"정보 메시지 전송 결과: {'성공' if success else '실패'}")
    
    # 경고 메시지 테스트
    logger.info("경고 메시지 전송 테스트...")
    success = telegram_bot.send_message("⚠️ 테스트 경고 메시지입니다.", "warning")
    logger.info(f"경고 메시지 전송 결과: {'성공' if success else '실패'}")
    
    # 오류 메시지 테스트
    logger.info("오류 메시지 전송 테스트...")
    success = telegram_bot.send_message("🚨 테스트 오류 메시지입니다.", "error")
    logger.info(f"오류 메시지 전송 결과: {'성공' if success else '실패'}")
    
    # 거래 알림 테스트
    logger.info("거래 알림 전송 테스트...")
    trade_data = {
        'trade_id': '12345',
        'pair': 'BTC/USDT',
        'side': 'buy',
        'status': 'open',
        'entry_price': 50000.0,
        'quantity': 0.01,
        'stop_loss': 49000.0,
        'take_profit': 52000.0
    }
    success = telegram_bot.send_trade_alert(trade_data)
    logger.info(f"거래 알림 전송 결과: {'성공' if success else '실패'}")
    
    # 성능 보고서 테스트
    logger.info("성능 보고서 전송 테스트...")
    performance_data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'total_trades': 15,
        'win_rate': 60.0,
        'total_profit': 120.50,
        'profit_percent': 2.41,
        'max_drawdown': 5.2
    }
    success = telegram_bot.notifier.send_performance_report(performance_data)
    logger.info(f"성능 보고서 전송 결과: {'성공' if success else '실패'}")
    
    logger.info("메시지 전송 테스트 완료")

async def test_risk_events(telegram_bot, risk_manager):
    """
    리스크 이벤트 테스트
    """
    logger.info("리스크 이벤트 테스트 시작...")
    
    if not risk_manager or not risk_manager.redis_client:
        logger.error("리스크 관리자 또는 Redis 클라이언트가 초기화되지 않았습니다.")
        return
    
    # 드로다운 경고 이벤트 테스트
    logger.info("드로다운 경고 이벤트 테스트...")
    event_data = {
        'type': 'MAX_DRAWDOWN_WARNING',
        'data': {
            'drawdown': 0.12,
            'drawdown_percent': 12.0,
            'current_balance': 8800.0,
            'peak_balance': 10000.0,
            'max_drawdown': 0.15
        },
        'timestamp': datetime.now().isoformat()
    }
    await risk_manager.redis_client.publish('risk_events', json.dumps(event_data))
    logger.info("드로다운 경고 이벤트 발행됨")
    
    # 잠시 대기
    await asyncio.sleep(2)
    
    # 서킷 브레이커 이벤트 테스트
    logger.info("서킷 브레이커 이벤트 테스트...")
    event_data = {
        'type': 'CIRCUIT_BREAKER_TRIGGERED',
        'data': {
            'price_change': -0.06,
            'price_change_percent': -6.0,
            'threshold': 0.05,
            'recovery_time': 3600
        },
        'timestamp': datetime.now().isoformat()
    }
    await risk_manager.redis_client.publish('risk_events', json.dumps(event_data))
    logger.info("서킷 브레이커 이벤트 발행됨")
    
    # 잠시 대기
    await asyncio.sleep(2)
    
    # 킬 스위치 이벤트 테스트
    logger.info("킬 스위치 이벤트 테스트...")
    event_data = {
        'type': 'KILL_SWITCH_ACTIVATED',
        'data': {
            'reason': '테스트를 위한 킬 스위치 활성화'
        },
        'timestamp': datetime.now().isoformat()
    }
    await risk_manager.redis_client.publish('risk_events', json.dumps(event_data))
    logger.info("킬 스위치 이벤트 발행됨")
    
    logger.info("리스크 이벤트 테스트 완료")

async def main():
    """
    메인 함수
    """
    args = parse_arguments()
    
    # project.env 파일에서 환경 변수 로드
    env_file = project_root / "config" / "env" / "project.env"
    
    if env_file.exists():
        logger.info(f"project.env 파일에서 환경 변수를 로드합니다: {env_file}")
        dotenv.load_dotenv(env_file)
    else:
        logger.warning(f"project.env 파일을 찾을 수 없습니다: {env_file}")
    
    # 로그 레벨 설정
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.getLogger().setLevel(log_level)
    
    # 명령행 인수 또는 환경 변수에서 설정 가져오기
    token = args.token or os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = args.chat_id or os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or token == 'your_telegram_bot_token':
        logger.error("텔레그램 봇 토큰이 설정되지 않았습니다.")
        logger.error("project.env 파일에서 TELEGRAM_BOT_TOKEN을 설정하거나 --token 인수를 사용하세요.")
        return
    
    if not chat_id or chat_id == 'your_telegram_chat_id':
        logger.error("텔레그램 채팅 ID가 설정되지 않았습니다.")
        logger.error("project.env 파일에서 TELEGRAM_CHAT_ID를 설정하거나 --chat-id 인수를 사용하세요.")
        return
    
    # 간단한 설정 객체 생성
    config = {
        'risk_management': {
            'max_drawdown': 0.15,
            'stop_loss': 0.035,
            'risk_per_trade': 0.02,
            'daily_trade_limit': 60,
            'circuit_breaker': 0.05
        },
        'redis': {
            'host': 'localhost',
            'port': 6379,
            'db': 0
        }
    }
    
    # 리스크 관리자 초기화
    try:
        risk_manager = await init_risk_manager(config)
        if not risk_manager:
            logger.error("리스크 관리자 초기화 실패")
            return
        logger.info("리스크 관리자 초기화 성공")
    except Exception as e:
        logger.error(f"리스크 관리자 초기화 중 오류 발생: {e}")
        return
    
    # Redis 연결 설정
    try:
        await risk_manager.connect_redis()
        logger.info("Redis 연결 성공")
    except Exception as e:
        logger.error(f"Redis 연결 실패: {e}")
        logger.warning("Redis 연결 없이 계속 진행합니다.")
    
    # 텔레그램 봇 초기화
    telegram_bot = init_telegram_bot(
        token=token,
        chat_id=chat_id,
        risk_manager=risk_manager
    )
    
    if not telegram_bot:
        logger.error("텔레그램 봇 초기화 실패")
        return
    
    # 텔레그램 봇 시작
    telegram_bot.start()
    logger.info("텔레그램 봇이 시작되었습니다.")
    
    # 시작 메시지 전송
    telegram_bot.send_message("🤖 텔레그램 봇 테스트가 시작되었습니다.")
    
    try:
        # 테스트 유형에 따라 테스트 실행
        if args.test in ['all', 'messages']:
            await test_messages(telegram_bot)
        
        if args.test in ['all', 'events']:
            await test_risk_events(telegram_bot, risk_manager)
        
        if args.test in ['all', 'commands']:
            logger.info("명령어 테스트는 텔레그램 앱에서 직접 수행해야 합니다.")
            logger.info("다음 명령어를 테스트해 보세요: /start, /help, /status, /balance, /trades, /risk")
            
            # 명령어 테스트를 위한 대기
            telegram_bot.send_message("명령어 테스트를 시작합니다. 다음 명령어를 테스트해 보세요:\n"
                                     "/start - 시작 메시지\n"
                                     "/help - 도움말\n"
                                     "/status - 봇 상태\n"
                                     "/balance - 계정 잔액\n"
                                     "/trades - 최근 거래\n"
                                     "/risk on - 거래 활성화\n"
                                     "/risk off - 거래 비활성화\n"
                                     "/risk status - 리스크 상태")
            
            # 사용자가 명령어를 테스트할 시간을 줌
            logger.info("명령어 테스트를 위해 60초 동안 대기합니다...")
            await asyncio.sleep(60)
        
        # 테스트 완료 메시지
        telegram_bot.send_message("✅ 텔레그램 봇 테스트가 완료되었습니다.")
        logger.info("텔레그램 봇 테스트가 완료되었습니다.")
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        telegram_bot.send_message(f"❌ 테스트 중 오류 발생: {e}")
    finally:
        # 리소스 정리
        if risk_manager and hasattr(risk_manager, 'close') and callable(risk_manager.close):
            await risk_manager.close()
        
        # 텔레그램 봇 종료
        if telegram_bot:
            telegram_bot.stop()
            logger.info("텔레그램 봇이 종료되었습니다.")

if __name__ == "__main__":
    # 비동기 메인 함수 실행
    asyncio.run(main())
