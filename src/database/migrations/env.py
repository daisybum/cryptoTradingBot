"""
Alembic 마이그레이션 환경 설정
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# 프로젝트 루트 경로를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# 모델 임포트
from src.database.models import Base
from src.database.connection import get_db_manager

# Alembic 설정 객체
config = context.config

# 로깅 설정 해석
fileConfig(config.config_file_name)

# 메타데이터 객체 설정
target_metadata = Base.metadata

def run_migrations_offline():
    """
    오프라인 모드에서 마이그레이션 실행
    
    이 시나리오에서는 데이터베이스에 직접 연결하지 않고 SQL 스크립트를 생성합니다.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """
    온라인 모드에서 마이그레이션 실행
    
    이 시나리오에서는 데이터베이스에 직접 연결하여 마이그레이션을 실행합니다.
    """
    # 데이터베이스 연결 설정 가져오기
    db_manager = get_db_manager()
    if db_manager and db_manager.pg_engine:
        connectable = db_manager.pg_engine
    else:
        # 데이터베이스 관리자가 초기화되지 않은 경우 설정에서 엔진 생성
        connectable = engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
