#!/bin/bash
# Docker를 사용한 백테스트 명령어 실행 스크립트

# 프로젝트 루트 디렉토리 설정
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 명령어와 인자 파싱
COMMAND=$1
shift
ARGS=$@

echo -e "${GREEN}Docker를 사용한 백테스트 명령 실행: ${COMMAND} ${ARGS}${NC}"

# 필요한 디렉토리 생성
mkdir -p "${PROJECT_ROOT}/user_data/data"
mkdir -p "${PROJECT_ROOT}/user_data/logs"
mkdir -p "${PROJECT_ROOT}/user_data/backtest_results"
mkdir -p "${PROJECT_ROOT}/user_data/hyperopt_results"

# Docker 이미지 확인 및 필요시 다운로드
if ! docker image inspect freqtradeorg/freqtrade:stable &> /dev/null; then
    echo -e "${YELLOW}Freqtrade Docker 이미지 다운로드 중...${NC}"
    docker pull freqtradeorg/freqtrade:stable
fi

# 명령어 실행
echo -e "${BLUE}명령 실행 중: ${COMMAND} ${ARGS}${NC}"
docker run --rm \
    -v "${PROJECT_ROOT}/user_data:/freqtrade/user_data" \
    -v "${PROJECT_ROOT}/config:/freqtrade/config" \
    freqtradeorg/freqtrade:stable \
    ${COMMAND} \
    --config /freqtrade/config/freqtrade.json \
    ${ARGS}

echo -e "${GREEN}명령 실행 완료: ${COMMAND} ${ARGS}${NC}"
