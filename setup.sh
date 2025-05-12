#!/bin/bash

# NASOSv5_mod3 Bot 설정 스크립트
# 이 스크립트는 NASOSv5_mod3 트레이딩 봇의 초기 설정을 도와줍니다.

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 로고 출력
echo -e "${CYAN}"
echo "███╗   ██╗ █████╗ ███████╗ ██████╗ ███████╗██╗   ██╗███████╗    ███╗   ███╗ ██████╗ ██████╗ ██████╗ "
echo "████╗  ██║██╔══██╗██╔════╝██╔═══██╗██╔════╝██║   ██║██╔════╝    ████╗ ████║██╔═══██╗██╔══██╗╚════██╗"
echo "██╔██╗ ██║███████║███████╗██║   ██║███████╗██║   ██║███████╗    ██╔████╔██║██║   ██║██║  ██║ █████╔╝"
echo "██║╚██╗██║██╔══██║╚════██║██║   ██║╚════██║╚██╗ ██╔╝╚════██║    ██║╚██╔╝██║██║   ██║██║  ██║ ╚═══██╗"
echo "██║ ╚████║██║  ██║███████║╚██████╔╝███████║ ╚████╔╝ ███████║    ██║ ╚═╝ ██║╚██████╔╝██████╔╝██████╔╝"
echo "╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝  ╚═══╝  ╚══════╝    ╚═╝     ╚═╝ ╚═════╝ ╚═════╝ ╚═════╝ "
echo -e "${NC}"
echo -e "${YELLOW}바이낸스 알트코인 고빈도 트레이딩 봇 설정 마법사${NC}"
echo -e "${YELLOW}=======================================================${NC}"
echo ""

# 환경 확인
echo -e "${BLUE}[1/5] 환경 확인 중...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}오류: Docker가 설치되어 있지 않습니다.${NC}"
    echo "https://docs.docker.com/get-docker/ 에서 Docker를 설치하세요."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}오류: Docker Compose가 설치되어 있지 않습니다.${NC}"
    echo "https://docs.docker.com/compose/install/ 에서 Docker Compose를 설치하세요."
    exit 1
fi

echo -e "${GREEN}✓ Docker 및 Docker Compose가 설치되어 있습니다.${NC}"

# .env 파일 생성
echo -e "${BLUE}[2/5] 환경 변수 설정 중...${NC}"
if [ -f .env ]; then
    echo -e "${YELLOW}경고: .env 파일이 이미 존재합니다.${NC}"
    read -p "덮어쓰시겠습니까? (y/n): " overwrite_env
    if [ "$overwrite_env" != "y" ]; then
        echo -e "${YELLOW}기존 .env 파일을 유지합니다.${NC}"
    else
        create_env=true
    fi
else
    create_env=true
fi

if [ "$create_env" = true ]; then
    echo "# NASOSv5_mod3 Bot 환경 변수" > .env
    echo "# $(date)" >> .env
    echo "" >> .env
    
    # 바이낸스 API 키 입력
    echo -e "${YELLOW}바이낸스 API 키를 입력하세요 (거래 권한 필요, 출금 권한 비활성화 권장)${NC}"
    read -p "API 키: " binance_api_key
    read -p "API 시크릿: " binance_api_secret
    
    echo "# Binance API 설정" >> .env
    echo "BINANCE_API_KEY=$binance_api_key" >> .env
    echo "BINANCE_API_SECRET=$binance_api_secret" >> .env
    echo "" >> .env
    
    # 데이터베이스 설정
    echo "# 데이터베이스 설정" >> .env
    echo "POSTGRES_USER=nasos_user" >> .env
    echo "POSTGRES_PASSWORD=$(openssl rand -base64 12)" >> .env
    echo "POSTGRES_DB=nasos_bot" >> .env
    echo "INFLUXDB_TOKEN=$(openssl rand -base64 24)" >> .env
    echo "INFLUXDB_ORG=nasos_org" >> .env
    echo "INFLUXDB_BUCKET=market_data" >> .env
    echo "" >> .env
    
    # 텔레그램 설정 (선택 사항)
    echo -e "${YELLOW}텔레그램 알림을 설정하시겠습니까? (y/n)${NC}"
    read -p "> " setup_telegram
    if [ "$setup_telegram" = "y" ]; then
        read -p "텔레그램 봇 토큰: " telegram_token
        read -p "텔레그램 채팅 ID: " telegram_chat_id
        
        echo "# 텔레그램 설정" >> .env
        echo "TELEGRAM_TOKEN=$telegram_token" >> .env
        echo "TELEGRAM_CHAT_ID=$telegram_chat_id" >> .env
        echo "" >> .env
    fi
    
    echo -e "${GREEN}✓ .env 파일이 생성되었습니다.${NC}"
fi

# 디렉토리 구조 확인
echo -e "${BLUE}[3/5] 디렉토리 구조 확인 중...${NC}"
for dir in src config docs tests; do
    if [ ! -d "$dir" ]; then
        echo -e "${YELLOW}$dir 디렉토리가 없습니다. 생성 중...${NC}"
        mkdir -p "$dir"
    fi
done

# 필요한 서브디렉토리 생성
mkdir -p src/{data_collection,strategy_engine,execution_engine,risk_manager,database,api_server,utils}
mkdir -p config/strategies
mkdir -p logs

echo -e "${GREEN}✓ 디렉토리 구조가 준비되었습니다.${NC}"

# Docker 이미지 빌드
echo -e "${BLUE}[4/5] Docker 이미지 빌드 중...${NC}"
echo -e "${YELLOW}참고: 이 과정은 몇 분 정도 소요될 수 있습니다.${NC}"

if [ -f "Dockerfile" ] && [ -f "docker-compose.yml" ]; then
    echo -e "${YELLOW}Docker 이미지를 빌드하시겠습니까? (y/n)${NC}"
    read -p "> " build_docker
    if [ "$build_docker" = "y" ]; then
        docker-compose build
        echo -e "${GREEN}✓ Docker 이미지가 빌드되었습니다.${NC}"
    else
        echo -e "${YELLOW}Docker 이미지 빌드를 건너뜁니다.${NC}"
    fi
else
    echo -e "${YELLOW}Dockerfile 또는 docker-compose.yml이 없습니다.${NC}"
    echo -e "${YELLOW}먼저 이 파일들을 생성한 후 Docker 이미지를 빌드하세요.${NC}"
fi

# 설정 완료
echo -e "${BLUE}[5/5] 설정 완료${NC}"
echo -e "${GREEN}NASOSv5_mod3 Bot 설정이 완료되었습니다!${NC}"
echo ""
echo -e "${YELLOW}다음 단계:${NC}"
echo "1. Dockerfile 및 docker-compose.yml 파일을 확인하세요."
echo "2. 필요한 경우 config/default.yml 파일을 수정하세요."
echo "3. docker-compose up -d 명령으로 봇을 시작하세요."
echo ""
echo -e "${MAGENTA}문의사항이 있으시면 문서를 참조하거나 GitHub 이슈를 생성하세요.${NC}"
echo -e "${YELLOW}행운을 빕니다! 📈${NC}"
