#!/bin/bash

# Docker Compose 테스트 스크립트
# 이 스크립트는 Docker Compose 구성을 테스트합니다.

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}NASOSv5_mod3 Bot Docker Compose 테스트 시작${NC}"
echo "========================================"

# 현재 디렉토리가 프로젝트 루트인지 확인
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}오류: 프로젝트 루트 디렉토리에서 이 스크립트를 실행하세요.${NC}"
    exit 1
fi

# Docker Compose가 설치되어 있는지 확인
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}오류: Docker Compose가 설치되어 있지 않습니다.${NC}"
    exit 1
fi

# .env 파일이 있는지 확인
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}경고: .env 파일이 없습니다. 테스트용 .env 파일을 생성합니다.${NC}"
    cat > .env << EOF
# 테스트용 환경 변수
POSTGRES_USER=nasos_user
POSTGRES_PASSWORD=nasos_password
POSTGRES_DB=nasos_bot
INFLUXDB_ORG=nasos_org
INFLUXDB_BUCKET=market_data
INFLUXDB_TOKEN=test_token
INFLUXDB_ADMIN_PASSWORD=admin_password
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
VAULT_ROOT_TOKEN=root
EOF
    echo -e "${GREEN}✓ 테스트용 .env 파일이 생성되었습니다.${NC}"
fi

echo -e "${YELLOW}1. Docker Compose 구성 검증 중...${NC}"
if docker-compose config; then
    echo -e "${GREEN}✓ Docker Compose 구성이 유효합니다.${NC}"
else
    echo -e "${RED}✗ Docker Compose 구성이 유효하지 않습니다.${NC}"
    exit 1
fi

echo -e "${YELLOW}2. 필수 디렉토리 확인 중...${NC}"
for dir in config logs data; do
    if [ ! -d "$dir" ]; then
        echo -e "${YELLOW}$dir 디렉토리가 없습니다. 생성 중...${NC}"
        mkdir -p "$dir"
    fi
done
echo -e "${GREEN}✓ 필수 디렉토리가 존재합니다.${NC}"

echo -e "${YELLOW}3. 필수 서비스 시작 테스트 중...${NC}"
echo -e "${YELLOW}참고: 이 테스트는 필수 서비스만 시작하고 10초 후에 중지합니다.${NC}"

# 필수 서비스만 시작
echo "postgres redis 서비스 시작 중..."
if docker-compose up -d postgres redis; then
    echo -e "${GREEN}✓ 필수 서비스가 성공적으로 시작되었습니다.${NC}"
    
    # 10초 대기
    echo "서비스 상태 확인 중... (10초 대기)"
    sleep 10
    
    # 서비스 상태 확인
    docker-compose ps
    
    # 서비스 중지
    echo "서비스 중지 중..."
    docker-compose down
    echo -e "${GREEN}✓ 서비스가 성공적으로 중지되었습니다.${NC}"
else
    echo -e "${RED}✗ 필수 서비스 시작에 실패했습니다.${NC}"
    docker-compose down
    exit 1
fi

echo "========================================"
echo -e "${GREEN}NASOSv5_mod3 Bot Docker Compose 테스트 완료${NC}"
echo "Docker Compose 구성이 성공적으로 검증되었습니다."
echo ""
echo "전체 환경을 시작하려면 다음 명령을 실행하세요:"
echo "docker-compose up -d"
echo ""
echo "특정 서비스만 시작하려면 다음 명령을 실행하세요:"
echo "docker-compose up -d <서비스 이름>"
echo ""
echo "Freqtrade를 포함하여 시작하려면 다음 명령을 실행하세요:"
echo "docker-compose --profile freqtrade up -d"
