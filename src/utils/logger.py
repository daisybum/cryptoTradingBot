"""
로깅 설정 모듈

이 모듈은 애플리케이션 전체에서 사용할 로깅 시스템을 설정합니다.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path


def setup_logging(log_level="INFO", log_file=None):
    """
    애플리케이션 로깅을 설정합니다.

    Args:
        log_level (str): 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file (str, optional): 로그 파일 경로. 기본값은 None으로, 자동 생성됩니다.
    """
    # 로그 레벨 매핑
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    level = log_levels.get(log_level.upper(), logging.INFO)

    # 로그 포맷 설정
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, date_format)

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 파일 핸들러 추가 (지정된 경우 또는 기본 경로 사용)
    try:
        if log_file is None:
            project_root = Path(__file__).parent.parent.parent.absolute()
            logs_dir = project_root / "logs"
            os.makedirs(logs_dir, exist_ok=True)
            log_file = logs_dir / "nasos_bot.log"
        
        # 파일 핸들러 추가 시도
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10485760, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        logging.info(f"로그 파일 설정 완료: {log_file}")
    except PermissionError as e:
        logging.warning(f"로그 파일 권한 오류, 콘솔로그만 사용합니다: {e}")
    except Exception as e:
        logging.warning(f"로그 파일 설정 오류, 콘솔로그만 사용합니다: {e}")

    # 로깅 설정 완료 메시지
    root_logger.info(f"로깅이 {log_level} 레벨로 설정되었습니다.")
    root_logger.info(f"로그 파일: {log_file}")

    return root_logger


def get_logger(name):
    """
    지정된 이름으로 로거를 가져옵니다.

    Args:
        name (str): 로거 이름

    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
    return logging.getLogger(name)
