#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
데이터베이스 연결 및 세션 관리
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 데이터베이스 URL 설정
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trading_bot.db")

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 정의
Base = declarative_base()

# 데이터베이스 의존성 주입 함수
def get_db():
    """
    FastAPI 의존성 주입을 위한 데이터베이스 세션 제공 함수
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
