#!/bin/bash

# Dockerfile 테스트 스크립트
# 이 스크립트는 Dockerfile을 빌드하고 기본적인 테스트를 수행합니다.

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}NASOSv5_mod3 Bot Dockerfile 테스트 시작${NC}"
echo "========================================"

# 현재 디렉토리가 프로젝트 루트인지 확인
if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}오류: 프로젝트 루트 디렉토리에서 이 스크립트를 실행하세요.${NC}"
    exit 1
fi

# Docker가 설치되어 있는지 확인
if ! command -v docker &> /dev/null; then
    echo -e "${RED}오류: Docker가 설치되어 있지 않습니다.${NC}"
    exit 1
fi

# 이미지 이름 설정
IMAGE_NAME="nasos-bot:test"

echo -e "${YELLOW}1. Docker 이미지 빌드 중...${NC}"
if docker build -t ${IMAGE_NAME} .; then
    echo -e "${GREEN}✓ Docker 이미지 빌드 성공${NC}"
else
    echo -e "${RED}✗ Docker 이미지 빌드 실패${NC}"
    exit 1
fi

echo -e "${YELLOW}2. Docker 이미지 정보 확인${NC}"
docker images ${IMAGE_NAME}

echo -e "${YELLOW}3. Python 버전 확인${NC}"
if docker run --rm ${IMAGE_NAME} python --version; then
    echo -e "${GREEN}✓ Python 버전 확인 성공${NC}"
else
    echo -e "${RED}✗ Python 버전 확인 실패${NC}"
    exit 1
fi

echo -e "${YELLOW}4. 필수 패키지 설치 확인${NC}"
if docker run --rm ${IMAGE_NAME} pip list | grep -E 'ccxt|pandas|numpy|pydantic'; then
    echo -e "${GREEN}✓ 필수 패키지 설치 확인 성공${NC}"
else
    echo -e "${RED}✗ 필수 패키지 설치 확인 실패${NC}"
    exit 1
fi

echo -e "${YELLOW}5. 애플리케이션 구조 확인${NC}"
if docker run --rm ${IMAGE_NAME} ls -la /app; then
    echo -e "${GREEN}✓ 애플리케이션 구조 확인 성공${NC}"
else
    echo -e "${RED}✗ 애플리케이션 구조 확인 실패${NC}"
    exit 1
fi

echo "========================================"
echo -e "${GREEN}NASOSv5_mod3 Bot Dockerfile 테스트 완료${NC}"
echo "Docker 이미지가 성공적으로 빌드되었으며 기본 테스트를 통과했습니다."
echo "다음 명령으로 컨테이너를 실행할 수 있습니다:"
echo "docker run -it --rm ${IMAGE_NAME}"
