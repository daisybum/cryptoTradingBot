#!/bin/bash

# NASOSv5_mod3 Bot 보안 테스트 스크립트
# 이 스크립트는 보안 설정을 테스트합니다.

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 현재 디렉토리 저장
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}보안 테스트 시작...${NC}"

# Vault 연결 테스트
echo -e "${YELLOW}Vault 연결 테스트 중...${NC}"
if curl -s http://localhost:8200/v1/sys/health > /dev/null; then
    echo -e "${GREEN}Vault 연결 성공!${NC}"
else
    echo -e "${RED}Vault 연결 실패!${NC}"
    echo "Vault 서버가 실행 중인지 확인하세요."
    exit 1
fi

# Vault 인증 테스트
echo -e "${YELLOW}Vault 인증 테스트 중...${NC}"
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
    if [ -n "$VAULT_TOKEN" ]; then
        if curl -s -H "X-Vault-Token: $VAULT_TOKEN" http://localhost:8200/v1/sys/health > /dev/null; then
            echo -e "${GREEN}Vault 인증 성공!${NC}"
        else
            echo -e "${RED}Vault 인증 실패!${NC}"
            echo "Vault 토큰이 유효한지 확인하세요."
        fi
    else
        echo -e "${YELLOW}Vault 토큰이 설정되지 않았습니다.${NC}"
    fi
else
    echo -e "${YELLOW}.env 파일이 없습니다.${NC}"
fi

# SSL 인증서 테스트
echo -e "${YELLOW}SSL 인증서 테스트 중...${NC}"
if [ -d "$PROJECT_ROOT/config/ssl/certs" ]; then
    if [ "$(ls -A "$PROJECT_ROOT/config/ssl/certs")" ]; then
        echo -e "${GREEN}SSL 인증서가 존재합니다!${NC}"
    else
        echo -e "${YELLOW}SSL 인증서 디렉토리가 비어 있습니다.${NC}"
    fi
else
    echo -e "${RED}SSL 인증서 디렉토리가 없습니다!${NC}"
fi

# Cloudflare 설정 테스트
echo -e "${YELLOW}Cloudflare 설정 테스트 중...${NC}"
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
    if [ -n "$CLOUDFLARE_API_TOKEN" ] && [ -n "$CLOUDFLARE_ZONE" ]; then
        echo -e "${GREEN}Cloudflare 설정이 존재합니다!${NC}"
    else
        echo -e "${YELLOW}Cloudflare 설정이 완전하지 않습니다.${NC}"
    fi
else
    echo -e "${YELLOW}.env 파일이 없습니다.${NC}"
fi

echo -e "${BLUE}보안 테스트 완료!${NC}"
