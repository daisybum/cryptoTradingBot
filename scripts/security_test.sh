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

# 보안 유틸리티 스크립트 로드
if [ -f "$SCRIPT_DIR/security_utils.sh" ]; then
    source "$SCRIPT_DIR/security_utils.sh"
fi

# 테스트 결과 카운터
TOTAL_TESTS=0
PASSED_TESTS=0
WARNING_TESTS=0
FAILED_TESTS=0

# 테스트 결과 기록 함수
record_test_result() {
    local result=$1
    local test_name=$2
    
    TOTAL_TESTS=$((TOTAL_TESTS+1))
    
    case $result in
        "pass")
            PASSED_TESTS=$((PASSED_TESTS+1))
            echo -e "${GREEN}✓ 통과: $test_name${NC}"
            ;;
        "warn")
            WARNING_TESTS=$((WARNING_TESTS+1))
            echo -e "${YELLOW}⚠ 경고: $test_name${NC}"
            ;;
        "fail")
            FAILED_TESTS=$((FAILED_TESTS+1))
            echo -e "${RED}✗ 실패: $test_name${NC}"
            ;;
    esac
}

echo -e "${BLUE}보안 테스트 시작...${NC}"

# Vault 연결 테스트
echo -e "\n${BLUE}[1/5] Vault 연결 및 인증 테스트${NC}"

# Vault 서버 연결 테스트
echo -e "${YELLOW}Vault 서버 연결 테스트 중...${NC}"
if curl -s http://localhost:8200/v1/sys/health > /dev/null; then
    record_test_result "pass" "Vault 서버 연결"
else
    record_test_result "fail" "Vault 서버 연결 (Vault 서버가 실행 중인지 확인하세요)"
fi

# Vault 인증 테스트
echo -e "${YELLOW}Vault 인증 테스트 중...${NC}"
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
    if [ -n "$VAULT_TOKEN" ]; then
        if curl -s -H "X-Vault-Token: $VAULT_TOKEN" http://localhost:8200/v1/sys/health > /dev/null; then
            record_test_result "pass" "Vault 토큰 인증"
        else
            record_test_result "fail" "Vault 토큰 인증 (토큰이 유효하지 않음)"
        fi
    elif [ -n "$VAULT_ROLE_ID" ] && [ -n "$VAULT_SECRET_ID" ]; then
        # AppRole 인증 테스트
        if command -v vault >/dev/null 2>&1; then
            # 임시 토큰 생성
            TEMP_TOKEN=$(VAULT_ADDR=http://localhost:8200 vault write -field=token auth/approle/login role_id="$VAULT_ROLE_ID" secret_id="$VAULT_SECRET_ID" 2>/dev/null)
            if [ -n "$TEMP_TOKEN" ]; then
                record_test_result "pass" "Vault AppRole 인증"
            else
                record_test_result "fail" "Vault AppRole 인증 (역할 ID 또는 시크릿 ID가 유효하지 않음)"
            fi
        else
            record_test_result "warn" "Vault AppRole 인증 (vault CLI가 설치되지 않아 테스트할 수 없음)"
        fi
    else
        record_test_result "warn" "Vault 인증 (인증 정보가 설정되지 않음)"
    fi
else
    record_test_result "warn" "Vault 인증 (.env 파일이 없음)"
fi

# Vault KV 시크릿 엔진 테스트
echo -e "${YELLOW}Vault KV 시크릿 엔진 테스트 중...${NC}"
if command -v vault >/dev/null 2>&1 && [ -n "$VAULT_TOKEN" ]; then
    if VAULT_ADDR=http://localhost:8200 VAULT_TOKEN=$VAULT_TOKEN vault secrets list | grep -q "kv/"; then
        record_test_result "pass" "Vault KV 시크릿 엔진"
    else
        record_test_result "warn" "Vault KV 시크릿 엔진 (활성화되지 않음)"
    fi
else
    record_test_result "warn" "Vault KV 시크릿 엔진 (테스트 불가)"
fi

# SSL/TLS 테스트
echo -e "\n${BLUE}[2/5] SSL/TLS 설정 테스트${NC}"

# SSL 인증서 테스트
echo -e "${YELLOW}SSL 인증서 테스트 중...${NC}"
if [ -d "$PROJECT_ROOT/config/ssl/certs" ]; then
    if [ "$(ls -A "$PROJECT_ROOT/config/ssl/certs")" ]; then
        # 인증서 유효성 검사
        CERT_FILE=$(find "$PROJECT_ROOT/config/ssl/certs" -name "*.crt" -o -name "*.pem" | head -n 1)
        if [ -n "$CERT_FILE" ] && command -v openssl >/dev/null 2>&1; then
            CERT_INFO=$(openssl x509 -in "$CERT_FILE" -text -noout 2>/dev/null)
            if [ $? -eq 0 ]; then
                # 인증서 만료일 확인
                EXPIRY_DATE=$(echo "$CERT_INFO" | grep "Not After" | cut -d: -f2-)
                EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s 2>/dev/null)
                CURRENT_EPOCH=$(date +%s)
                DAYS_LEFT=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))
                
                if [ $DAYS_LEFT -lt 0 ]; then
                    record_test_result "fail" "SSL 인증서 (만료됨)"
                elif [ $DAYS_LEFT -lt 30 ]; then
                    record_test_result "warn" "SSL 인증서 ($DAYS_LEFT일 후 만료 예정)"
                else
                    record_test_result "pass" "SSL 인증서 (유효, $DAYS_LEFT일 후 만료)"
                fi
            else
                record_test_result "fail" "SSL 인증서 (유효하지 않은 형식)"
            fi
        else
            record_test_result "pass" "SSL 인증서 존재"
        fi
    else
        record_test_result "warn" "SSL 인증서 (디렉토리가 비어 있음)"
    fi
else
    record_test_result "fail" "SSL 인증서 (디렉토리가 없음)"
fi

# SSL 개인 키 테스트
echo -e "${YELLOW}SSL 개인 키 테스트 중...${NC}"
if [ -d "$PROJECT_ROOT/config/ssl/private" ]; then
    if [ "$(ls -A "$PROJECT_ROOT/config/ssl/private")" ]; then
        KEY_FILE=$(find "$PROJECT_ROOT/config/ssl/private" -name "*.key" | head -n 1)
        if [ -n "$KEY_FILE" ] && command -v openssl >/dev/null 2>&1; then
            # 개인 키 유효성 검사
            if openssl rsa -in "$KEY_FILE" -check -noout >/dev/null 2>&1; then
                record_test_result "pass" "SSL 개인 키"
            else
                record_test_result "fail" "SSL 개인 키 (유효하지 않음)"
            fi
        else
            record_test_result "pass" "SSL 개인 키 존재"
        fi
    else
        record_test_result "warn" "SSL 개인 키 (디렉토리가 비어 있음)"
    fi
else
    record_test_result "fail" "SSL 개인 키 (디렉토리가 없음)"
fi

# Nginx 설정 테스트
echo -e "${YELLOW}Nginx 설정 테스트 중...${NC}"
if [ -d "$PROJECT_ROOT/config/nginx" ]; then
    if [ "$(ls -A "$PROJECT_ROOT/config/nginx")" ]; then
        record_test_result "pass" "Nginx 설정"
    else
        record_test_result "warn" "Nginx 설정 (디렉토리가 비어 있음)"
    fi
else
    record_test_result "warn" "Nginx 설정 (디렉토리가 없음)"
fi

# Cloudflare 설정 테스트
echo -e "\n${BLUE}[3/5] Cloudflare 설정 테스트${NC}"
echo -e "${YELLOW}Cloudflare 설정 테스트 중...${NC}"

# Cloudflare 환경 변수 테스트
if [ -f "$PROJECT_ROOT/config/cloudflare.env" ]; then
    source "$PROJECT_ROOT/config/cloudflare.env"
    if [ -n "$CLOUDFLARE_API_TOKEN" ] && [ "$CLOUDFLARE_API_TOKEN" != "your_api_token_here" ]; then
        record_test_result "pass" "Cloudflare API 토큰"
    else
        record_test_result "warn" "Cloudflare API 토큰 (설정되지 않음)"
    fi
    
    if [ -n "$CLOUDFLARE_ZONE" ] && [ "$CLOUDFLARE_ZONE" != "your_zone_id_here" ]; then
        record_test_result "pass" "Cloudflare 영역 ID"
    else
        record_test_result "warn" "Cloudflare 영역 ID (설정되지 않음)"
    fi
else
    record_test_result "warn" "Cloudflare 설정 (cloudflare.env 파일이 없음)"
fi

# Cloudflare Companion 컨테이너 테스트
echo -e "${YELLOW}Cloudflare Companion 컨테이너 테스트 중...${NC}"
if command -v docker >/dev/null 2>&1; then
    if docker ps | grep -q "nasos-cloudflare"; then
        record_test_result "pass" "Cloudflare Companion 컨테이너"
    else
        record_test_result "warn" "Cloudflare Companion 컨테이너 (실행 중이 아님)"
    fi
else
    record_test_result "warn" "Cloudflare Companion 컨테이너 (Docker가 설치되지 않아 테스트할 수 없음)"
fi

# 비밀 교체 메커니즘 테스트
echo -e "\n${BLUE}[4/5] 비밀 교체 메커니즘 테스트${NC}"

# 비밀 교체 스크립트 테스트
echo -e "${YELLOW}비밀 교체 스크립트 테스트 중...${NC}"
if [ -f "$SCRIPT_DIR/rotate_secrets.sh" ]; then
    if [ -x "$SCRIPT_DIR/rotate_secrets.sh" ]; then
        record_test_result "pass" "비밀 교체 스크립트"
    else
        chmod +x "$SCRIPT_DIR/rotate_secrets.sh"
        record_test_result "warn" "비밀 교체 스크립트 (실행 권한이 없어 자동으로 추가함)"
    fi
else
    record_test_result "fail" "비밀 교체 스크립트 (파일이 없음)"
fi

# 비밀 교체 크론 작업 테스트
echo -e "${YELLOW}비밀 교체 크론 작업 테스트 중...${NC}"
if command -v crontab >/dev/null 2>&1; then
    if crontab -l 2>/dev/null | grep -q "rotate_secrets"; then
        record_test_result "pass" "비밀 교체 크론 작업"
    else
        record_test_result "warn" "비밀 교체 크론 작업 (설정되지 않음)"
    fi
else
    record_test_result "warn" "비밀 교체 크론 작업 (crontab이 설치되지 않아 테스트할 수 없음)"
fi

# 보안 유틸리티 테스트
echo -e "\n${BLUE}[5/5] 보안 유틸리티 테스트${NC}"

# security_utils.sh 테스트
echo -e "${YELLOW}보안 유틸리티 스크립트 테스트 중...${NC}"
if [ -f "$SCRIPT_DIR/security_utils.sh" ]; then
    if [ -x "$SCRIPT_DIR/security_utils.sh" ]; then
        record_test_result "pass" "보안 유틸리티 스크립트"
    else
        chmod +x "$SCRIPT_DIR/security_utils.sh"
        record_test_result "warn" "보안 유틸리티 스크립트 (실행 권한이 없어 자동으로 추가함)"
    fi
else
    record_test_result "fail" "보안 유틸리티 스크립트 (파일이 없음)"
fi

# setup_ssl.sh 테스트
echo -e "${YELLOW}SSL 설정 스크립트 테스트 중...${NC}"
if [ -f "$SCRIPT_DIR/setup_ssl.sh" ]; then
    if [ -x "$SCRIPT_DIR/setup_ssl.sh" ]; then
        record_test_result "pass" "SSL 설정 스크립트"
    else
        chmod +x "$SCRIPT_DIR/setup_ssl.sh"
        record_test_result "warn" "SSL 설정 스크립트 (실행 권한이 없어 자동으로 추가함)"
    fi
else
    record_test_result "fail" "SSL 설정 스크립트 (파일이 없음)"
fi

# 테스트 결과 요약
echo -e "\n${BLUE}보안 테스트 결과 요약${NC}"
echo -e "${GREEN}통과: $PASSED_TESTS/$TOTAL_TESTS${NC}"
echo -e "${YELLOW}경고: $WARNING_TESTS/$TOTAL_TESTS${NC}"
echo -e "${RED}실패: $FAILED_TESTS/$TOTAL_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ] && [ $WARNING_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}모든 보안 테스트가 통과되었습니다!${NC}"
elif [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${YELLOW}보안 테스트가 경고와 함께 완료되었습니다. 경고 사항을 확인하세요.${NC}"
else
    echo -e "\n${RED}일부 보안 테스트가 실패했습니다. 실패 사항을 해결하세요.${NC}"
fi

echo -e "\n${BLUE}보안 테스트 완료!${NC}"
