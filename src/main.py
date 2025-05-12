#!/usr/bin/env python3
"""
NASOSv5_mod3 Bot - 바이낸스 알트코인 고빈도 트레이딩 봇

이 모듈은 애플리케이션의 주요 진입점입니다.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from src.utils.config import load_config
from src.utils.logger import setup_logging


def parse_arguments():
    """명령줄 인수를 파싱합니다."""
    parser = argparse.ArgumentParser(description="NASOSv5_mod3 Bot")
    parser.add_argument(
        "--config",
        type=str,
        default="config/default.yml",
        help="설정 파일 경로 (기본값: config/default.yml)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="로그 레벨 (기본값: INFO)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["trade", "backtest", "optimize", "dryrun"],
        default="dryrun",
        help="실행 모드 (기본값: dryrun)",
    )
    return parser.parse_args()


def setup_environment():
    """애플리케이션 환경을 설정합니다."""
    # 프로젝트 루트 디렉토리를 Python 경로에 추가
    project_root = Path(__file__).parent.parent.absolute()
    sys.path.insert(0, str(project_root))

    # 필요한 디렉토리 생성
    os.makedirs(project_root / "logs", exist_ok=True)
    os.makedirs(project_root / "data", exist_ok=True)

    return project_root


def main():
    """애플리케이션의 주요 진입점"""
    # 환경 설정
    project_root = setup_environment()

    # 명령줄 인수 파싱
    args = parse_arguments()

    # 로깅 설정
    setup_logging(log_level=args.log_level)
    logger = logging.getLogger(__name__)

    logger.info("NASOSv5_mod3 Bot 시작 중...")
    logger.info(f"실행 모드: {args.mode}")

    try:
        # 설정 로드
        config_path = project_root / args.config
        config = load_config(config_path)
        logger.info(f"설정 파일 로드됨: {config_path}")

        # 실행 모드에 따라 다른 모듈 실행
        if args.mode == "trade":
            logger.info("거래 모드로 실행 중...")
            # TODO: 거래 모듈 구현
            from src.execution_engine.trading import start_trading
            start_trading(config)
        elif args.mode == "backtest":
            logger.info("백테스트 모드로 실행 중...")
            # TODO: 백테스트 모듈 구현
            from src.strategy_engine.backtesting import run_backtest
            run_backtest(config)
        elif args.mode == "optimize":
            logger.info("최적화 모드로 실행 중...")
            # TODO: 최적화 모듈 구현
            from src.strategy_engine.optimization import run_optimization
            run_optimization(config)
        elif args.mode == "dryrun":
            logger.info("드라이런 모드로 실행 중...")
            # TODO: 드라이런 모듈 구현
            from src.execution_engine.dryrun import start_dryrun
            start_dryrun(config)
        else:
            logger.error(f"알 수 없는 모드: {args.mode}")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"애플리케이션 실행 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
