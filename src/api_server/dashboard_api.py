#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
웹 대시보드를 위한 FastAPI 백엔드 서비스

이 모듈은 FastAPI를 사용하여 웹 대시보드를 위한 REST API를 구현합니다.
"""

import os
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from src.api_server.models.database import engine, Base, get_db
from src.api_server.auth.auth import (
    authenticate_user, 
    create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from src.utils.logging_config import setup_logging
from datetime import timedelta

# 라우터 임포트
from src.api_server.routers import auth, bot, trades, performance, parameters, backtest

# 로깅 설정
logger = logging.getLogger(__name__)
setup_logging()

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

# FastAPI 앱 생성
app = FastAPI(
    title="NASOSv5_mod3 Trading Bot API",
    description="트레이딩 봇 대시보드를 위한 REST API",
    version="1.0.0",
    docs_url=None,  # 기본 /docs 비활성화 (커스텀 경로 사용)
    redoc_url=None  # 기본 /redoc 비활성화 (커스텀 경로 사용)
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한해야 함
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router)
app.include_router(bot.router)
app.include_router(trades.router)
app.include_router(performance.router)
app.include_router(parameters.router)
app.include_router(backtest.router)

# 루트 엔드포인트
@app.get("/")
async def root():
    """
    API 서버 상태 확인
    """
    return {
        "status": "online",
        "message": "NASOSv5_mod3 Trading Bot API is running",
        "version": "1.0.0"
    }

# 로그인 엔드포인트 (토큰 발급)
@app.post("/token", tags=["authentication"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    사용자 로그인 및 액세스 토큰 발급
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# 커스텀 Swagger UI 경로
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """
    커스텀 Swagger UI
    """
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - API 문서",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

# 서버 시작 이벤트
@app.on_event("startup")
async def startup_event():
    """
    서버 시작 시 실행되는 이벤트 핸들러
    """
    logger.info("Starting up dashboard API server")

# 서버 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    """
    서버 종료 시 실행되는 이벤트 핸들러
    """
    logger.info("Shutting down dashboard API server")

# 직접 실행 시
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
