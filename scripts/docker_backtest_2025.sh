#!/bin/bash
# Docker를 사용한 2025년 데이터 백테스트 실행 스크립트

# 프로젝트 루트 디렉토리 설정
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Docker를 사용한 2025년 데이터 백테스트 준비 시작...${NC}"

# 필요한 디렉토리 생성
mkdir -p "${PROJECT_ROOT}/user_data/data"
mkdir -p "${PROJECT_ROOT}/user_data/logs"
mkdir -p "${PROJECT_ROOT}/user_data/backtest_results"

# Docker 이미지 확인 및 필요시 다운로드
if ! docker image inspect freqtradeorg/freqtrade:stable &> /dev/null; then
    echo -e "${YELLOW}Freqtrade Docker 이미지 다운로드 중...${NC}"
    docker pull freqtradeorg/freqtrade:stable
fi

# 현재 날짜 계산 (2025년 1월 1일부터 현재까지)
CURRENT_DATE=$(date +%Y%m%d)
START_DATE="20250101"

# 데이터 다운로드
echo -e "${BLUE}2025년 백테스트 데이터 다운로드 중...${NC}"
docker run --rm \
    -v "${PROJECT_ROOT}/user_data:/freqtrade/user_data" \
    -v "${PROJECT_ROOT}/config:/freqtrade/config" \
    freqtradeorg/freqtrade:stable \
    download-data \
    --config /freqtrade/config/freqtrade.json \
    --pairs BTC/USDT ETH/USDT BNB/USDT SOL/USDT XRP/USDT ADA/USDT AVAX/USDT DOT/USDT LINK/USDT \
    --timeframes 5m 15m 1h \
    --timerange "${START_DATE}-${CURRENT_DATE}" \
    --exchange binance

# 백테스트 실행
echo -e "${BLUE}2025년 데이터로 백테스트 실행 중...${NC}"
docker run --rm \
    -v "${PROJECT_ROOT}/user_data:/freqtrade/user_data" \
    -v "${PROJECT_ROOT}/config:/freqtrade/config" \
    freqtradeorg/freqtrade:stable \
    backtesting \
    --strategy NASOSv5_mod3 \
    --config /freqtrade/config/freqtrade.json \
    --timerange "${START_DATE}-${CURRENT_DATE}" \
    --timeframe 5m

echo -e "${GREEN}2025년 데이터 백테스트 완료!${NC}"
