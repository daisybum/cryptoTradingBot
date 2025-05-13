#!/bin/bash

# NASOSv5_mod3 Bot 보안 유틸리티 스크립트
# 이 스크립트는 Vault를 사용하여 API 키 및 기타 비밀 정보를 관리합니다.

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Vault 주소 및 토큰 설정
export VAULT_ADDR=${VAULT_ADDR:-"http://127.0.0.1:8200"}
export VAULT_TOKEN=${VAULT_TOKEN:-"root"}

# Vault CLI 명령어 실행 함수
vault_cmd() {
    # 컨테이너 상태 확인
    CONTAINER_STATUS=$(docker inspect -f '{{.State.Status}}' nasos-vault 2>/dev/null)
    
    # 컨테이너가 존재하지 않거나 재시작 중이면 조치 취함
    if [ -z "$CONTAINER_STATUS" ] || [ "$CONTAINER_STATUS" = "restarting" ]; then
        echo -e "${YELLOW}Vault 컨테이너 상태 확인 중... ($CONTAINER_STATUS)${NC}"
        
        if [ -z "$CONTAINER_STATUS" ]; then
            echo -e "${YELLOW}Vault 컨테이너가 없습니다. 시작합니다...${NC}"
            docker-compose -f "$(dirname "$0")/../docker-compose.yml" up -d vault
        elif [ "$CONTAINER_STATUS" = "restarting" ]; then
            echo -e "${YELLOW}Vault 컨테이너가 재시작 중입니다. 재구성합니다...${NC}"
            docker-compose -f "$(dirname "$0")/../docker-compose.yml" stop vault
            sleep 2
            docker-compose -f "$(dirname "$0")/../docker-compose.yml" up -d vault
        fi
        
        echo -e "${YELLOW}Vault 컨테이너 준비 중... 10초 대기${NC}"
        sleep 10
    fi
    
    # 명령어 실행
    MAX_RETRIES=3
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        RESULT=$(docker exec -i nasos-vault vault "$@" 2>&1)
        EXIT_CODE=$?
        
        if [ $EXIT_CODE -eq 0 ]; then
            echo "$RESULT"
            return 0
        fi
        
        # 오류 처리
        if echo "$RESULT" | grep -q "Error response from daemon: Container .* is restarting"; then
            RETRY_COUNT=$((RETRY_COUNT+1))
            echo -e "${YELLOW}컨테이너가 재시작 중입니다. 재시도 $RETRY_COUNT/$MAX_RETRIES...${NC}"
            sleep 5
        else
            # 다른 오류는 바로 반환
            echo "$RESULT"
            return $EXIT_CODE
        fi
    done
    
    echo -e "${RED}최대 재시도 횟수를 초과했습니다.${NC}"
    return 1
}

# Vault 상태 확인
check_vault_status() {
    echo -e "${BLUE}Vault 상태 확인 중...${NC}"
    
    # Docker 실행 확인
    if ! docker ps | grep -q nasos-vault; then
        echo -e "${YELLOW}Vault 컨테이너가 실행 중이 아닙니다. 자동으로 시작합니다...${NC}"
        docker-compose -f "$(dirname "$0")/../docker-compose.yml" up -d vault
        echo -e "${YELLOW}Vault 컨테이너 시작 중... 10초 대기${NC}"
        sleep 10
    fi
    
    # 컨테이너 상태 확인
    CONTAINER_STATUS=$(docker inspect -f '{{.State.Status}}' nasos-vault 2>/dev/null)
    if [ "$CONTAINER_STATUS" = "restarting" ]; then
        echo -e "${YELLOW}Vault 컨테이너가 재시작 중입니다. 컨테이너를 재구성합니다...${NC}"
        docker-compose -f "$(dirname "$0")/../docker-compose.yml" stop vault
        sleep 2
        docker-compose -f "$(dirname "$0")/../docker-compose.yml" up -d vault
        echo -e "${YELLOW}Vault 컨테이너 재시작 중... 10초 대기${NC}"
        sleep 10
    fi
    
    # Vault 상태 확인
    MAX_RETRIES=3
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -s "${VAULT_ADDR}/v1/sys/health" &> /dev/null; then
            echo -e "${GREEN}Vault 서버가 실행 중입니다.${NC}"
            return 0
        fi
        
        RETRY_COUNT=$((RETRY_COUNT+1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo -e "${YELLOW}Vault 서버에 연결 실패. 재시도 $RETRY_COUNT/$MAX_RETRIES...${NC}"
            sleep 3
        fi
    done
    
    echo -e "${RED}Vault 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.${NC}"
    return 1
}

# Vault 초기화
initialize_vault() {
    echo -e "${BLUE}Vault 초기화 중...${NC}"
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    # KV 시크릿 엔진 활성화
    if ! vault_cmd secrets list | grep -q "kv/"; then
        echo -e "${YELLOW}KV 시크릿 엔진 활성화 중...${NC}"
        vault_cmd secrets enable -version=2 -path=kv kv
        echo -e "${GREEN}KV 시크릿 엔진이 활성화되었습니다.${NC}"
    fi
    
    # API 키 경로 생성
    vault_cmd kv put kv/api/info description="API 키 저장소"
    
    # 데이터베이스 자격 증명 경로 생성
    vault_cmd kv put kv/db/info description="데이터베이스 자격 증명 저장소"
    
    # 텔레그램 자격 증명 경로 생성
    vault_cmd kv put kv/telegram/info description="텔레그램 자격 증명 저장소"
    
    echo -e "${GREEN}Vault가 성공적으로 초기화되었습니다.${NC}"
    return 0
}

# API 자격 증명 저장
store_api_credentials() {
    local exchange=$1
    local api_key=$2
    local api_secret=$3
    
    echo -e "${BLUE}${exchange} API 자격 증명 저장 중...${NC}"
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # API 자격 증명 저장
    vault_cmd kv put kv/api/${exchange} api_key="${api_key}" api_secret="${api_secret}"
    
    echo -e "${GREEN}${exchange} API 자격 증명이 안전하게 저장되었습니다.${NC}"
    return 0
}

# API 자격 증명 조회
retrieve_api_credentials() {
    local exchange=$1
    
    echo -e "${BLUE}${exchange} API 자격 증명 조회 중...${NC}"
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # API 자격 증명 조회
    if vault_cmd kv get kv/api/${exchange} &> /dev/null; then
        vault_cmd kv get -format=json kv/api/${exchange} | jq -r '.data.data'
        return 0
    else
        echo -e "${RED}${exchange} API 자격 증명을 찾을 수 없습니다.${NC}"
        return 1
    fi
}

# API 자격 증명 삭제
delete_api_credentials() {
    local exchange=$1
    
    echo -e "${BLUE}${exchange} API 자격 증명 삭제 중...${NC}"
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # API 자격 증명 삭제
    if vault_cmd kv get kv/api/${exchange} &> /dev/null; then
        vault_cmd kv delete kv/api/${exchange}
        echo -e "${GREEN}${exchange} API 자격 증명이 삭제되었습니다.${NC}"
        return 0
    else
        echo -e "${RED}${exchange} API 자격 증명을 찾을 수 없습니다.${NC}"
        return 1
    fi
}

# 데이터베이스 자격 증명 저장
store_database_credentials() {
    local db_type=$1
    local db_host=$2
    local db_port=$3
    local db_name=$4
    local db_user=$5
    local db_password=$6
    
    echo -e "${BLUE}${db_type} 데이터베이스 자격 증명 저장 중...${NC}"
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # 데이터베이스 자격 증명 저장
    vault_cmd kv put kv/db/${db_type} host="${db_host}" port="${db_port}" name="${db_name}" user="${db_user}" password="${db_password}"
    
    echo -e "${GREEN}${db_type} 데이터베이스 자격 증명이 안전하게 저장되었습니다.${NC}"
    return 0
}

# 데이터베이스 자격 증명 조회
retrieve_database_credentials() {
    local db_type=$1
    
    echo -e "${BLUE}${db_type} 데이터베이스 자격 증명 조회 중...${NC}"
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # 데이터베이스 자격 증명 조회
    if vault_cmd kv get kv/db/${db_type} &> /dev/null; then
        vault_cmd kv get -format=json kv/db/${db_type} | jq -r '.data.data'
        return 0
    else
        echo -e "${RED}${db_type} 데이터베이스 자격 증명을 찾을 수 없습니다.${NC}"
        return 1
    fi
}

# 데이터베이스 자격 증명 삭제
delete_database_credentials() {
    local db_type=$1
    
    echo -e "${BLUE}${db_type} 데이터베이스 자격 증명 삭제 중...${NC}"
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # 데이터베이스 자격 증명 삭제
    if vault_cmd kv get kv/db/${db_type} &> /dev/null; then
        vault_cmd kv delete kv/db/${db_type}
        echo -e "${GREEN}${db_type} 데이터베이스 자격 증명이 삭제되었습니다.${NC}"
        return 0
    else
        echo -e "${RED}${db_type} 데이터베이스 자격 증명을 찾을 수 없습니다.${NC}"
        return 1
    fi
}

# 텔레그램 자격 증명 저장
store_telegram_credentials() {
    local token=$1
    local chat_id=$2
    
    echo -e "${BLUE}텔레그램 자격 증명 저장 중...${NC}"
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # 텔레그램 자격 증명 저장
    vault_cmd kv put kv/telegram token="${token}" chat_id="${chat_id}"
    
    echo -e "${GREEN}텔레그램 자격 증명이 안전하게 저장되었습니다.${NC}"
    return 0
}

# 텔레그램 자격 증명 조회
retrieve_telegram_credentials() {
    echo -e "${BLUE}텔레그램 자격 증명 조회 중...${NC}"
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # 텔레그램 자격 증명 조회
    if vault_cmd kv get kv/telegram &> /dev/null; then
        vault_cmd kv get -format=json kv/telegram | jq -r '.data.data'
        return 0
    else
        echo -e "${RED}텔레그램 자격 증명을 찾을 수 없습니다.${NC}"
        return 1
    fi
}

# 텔레그램 자격 증명 삭제
delete_telegram_credentials() {
    echo -e "${BLUE}텔레그램 자격 증명 삭제 중...${NC}"
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # 텔레그램 자격 증명 삭제
    if vault_cmd kv get kv/telegram &> /dev/null; then
        vault_cmd kv delete kv/telegram
        echo -e "${GREEN}텔레그램 자격 증명이 삭제되었습니다.${NC}"
        return 0
    else
        echo -e "${RED}텔레그램 자격 증명을 찾을 수 없습니다.${NC}"
        return 1
    fi
}

# Vault 백업 생성
backup_vault() {
    local backup_file=$1
    
    echo -e "${BLUE}Vault 백업 생성 중...${NC}"
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # 모든 시크릿 경로 가져오기
    local paths=()
    while IFS= read -r path; do
        paths+=("$path")
    done < <(vault_cmd kv list -format=json kv/ | jq -r '.[]')
    
    # 백업 데이터 생성
    local backup_data="{"
    local first=true
    
    for path in "${paths[@]}"; do
        # 경로가 비어있으면 건너뛰기
        if [ -z "$path" ]; then
            continue
        fi
        
        # 시크릿 데이터 가져오기
        local secret_data=$(vault_cmd kv get -format=json kv/${path} | jq -r '.data.data')
        
        # 백업 데이터에 추가
        if [ "$first" = true ]; then
            first=false
        else
            backup_data+=","
        fi
        
        backup_data+="\"${path}\":${secret_data}"
    done
    
    backup_data+="}"
    
    # 백업 파일 저장
    echo "$backup_data" > "$backup_file"
    
    echo -e "${GREEN}Vault 백업이 성공적으로 생성되었습니다: ${backup_file}${NC}"
    return 0
}

# Vault 백업 복원
restore_vault() {
    local backup_file=$1
    
    echo -e "${BLUE}Vault 백업 복원 중...${NC}"
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # 백업 파일 확인
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}백업 파일을 찾을 수 없습니다: ${backup_file}${NC}"
        return 1
    fi
    
    # 백업 데이터 로드
    local backup_data=$(cat "$backup_file")
    
    # 모든 경로 처리
    local paths=($(echo "$backup_data" | jq -r 'keys[]'))
    
    for path in "${paths[@]}"; do
        # 경로가 비어있으면 건너뛰기
        if [ -z "$path" ]; then
            continue
        fi
        
        # 시크릿 데이터 가져오기
        local secret_data=$(echo "$backup_data" | jq -r ".[\"${path}\"]")
        
        # 시크릿 복원
        local key_value_pairs=()
        while IFS= read -r key_value; do
            key=$(echo "$key_value" | cut -d= -f1)
            value=$(echo "$key_value" | cut -d= -f2-)
            key_value_pairs+=("${key}=${value}")
        done < <(echo "$secret_data" | jq -r 'to_entries | map("\(.key)=\(.value)") | .[]')
        
        # Vault에 시크릿 저장
        vault_cmd kv put "kv/${path}" "${key_value_pairs[@]}"
        
        echo -e "${GREEN}시크릿 복원됨: kv/${path}${NC}"
    done
    
    echo -e "${GREEN}Vault 백업이 성공적으로 복원되었습니다.${NC}"
    return 0
}

# API 키 유효성 검사 (바이낸스)
validate_binance_api_credentials() {
    local api_key=$1
    local api_secret=$2
    
    echo -e "${BLUE}바이낸스 API 자격 증명 유효성 검사 중...${NC}"
    
    # API 키 형식 검사
    if [ -z "$api_key" ] || [ ${#api_key} -lt 10 ]; then
        echo -e "${RED}잘못된 API 키 형식입니다.${NC}"
        return 1
    fi
    
    # API 시크릿 형식 검사
    if [ -z "$api_secret" ] || [ ${#api_secret} -lt 10 ]; then
        echo -e "${RED}잘못된 API 시크릿 형식입니다.${NC}"
        return 1
    fi
    
    # TODO: 실제 API 호출을 통한 유효성 검사 추가
    
    echo -e "${GREEN}바이낸스 API 자격 증명이 유효합니다.${NC}"
    return 0
}

# 데이터베이스 연결 테스트
test_database_connection() {
    local db_type=$1
    local db_host=$2
    local db_port=$3
    local db_name=$4
    local db_user=$5
    local db_password=$6
    
    echo -e "${BLUE}${db_type} 데이터베이스 연결 테스트 중...${NC}"
    
    case "$db_type" in
        postgresql)
            if command -v psql &> /dev/null; then
                PGPASSWORD="$db_password" psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" -c "\q" &> /dev/null
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}PostgreSQL 데이터베이스 연결 성공!${NC}"
                    return 0
                else
                    echo -e "${RED}PostgreSQL 데이터베이스 연결 실패!${NC}"
                    return 1
                fi
            else
                echo -e "${YELLOW}psql 명령어를 찾을 수 없습니다. PostgreSQL 클라이언트가 설치되어 있는지 확인하세요.${NC}"
                return 1
            fi
            ;;
        influxdb)
            if command -v influx &> /dev/null; then
                influx -host "$db_host" -port "$db_port" -username "$db_user" -password "$db_password" -database "$db_name" -execute "SHOW DATABASES" &> /dev/null
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}InfluxDB 데이터베이스 연결 성공!${NC}"
                    return 0
                else
                    echo -e "${RED}InfluxDB 데이터베이스 연결 실패!${NC}"
                    return 1
                fi
            else
                echo -e "${YELLOW}influx 명령어를 찾을 수 없습니다. InfluxDB 클라이언트가 설치되어 있는지 확인하세요.${NC}"
                return 1
            fi
            ;;
        *)
            echo -e "${RED}지원되지 않는 데이터베이스 유형: ${db_type}${NC}"
            return 1
            ;;
    esac
}

# 안전한 비밀번호 생성
generate_secure_password() {
    local length=${1:-32}
    
    if command -v openssl &> /dev/null; then
        openssl rand -base64 "$length" | tr -d '/+=' | cut -c1-"$length"
    else
        # 대체 방법
        cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w "$length" | head -n 1
    fi
}

# Vault 초기화
initialize_vault() {
    echo -e "${BLUE}Vault 초기화 중...${NC}"
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # KV 시크릿 엔진 활성화
    echo -e "${BLUE}KV 시크릿 엔진 활성화 중...${NC}"
    vault_cmd secrets enable -version=2 -path=kv kv || true
    
    # 정책 생성
    echo -e "${BLUE}정책 생성 중...${NC}"
    
    # 정책 파일 생성
    POLICY_FILE="$(dirname "$0")/../tmp/nasos-policy.hcl"
    mkdir -p "$(dirname "$0")/../tmp"
    
    cat > "$POLICY_FILE" << EOF
path "kv/data/nasos/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
EOF
    
    # 정책 파일을 컨테이너로 복사
    docker cp "$POLICY_FILE" nasos-vault:/tmp/nasos-policy.hcl
    
    # 컨테이너 내에서 정책 적용
    vault_cmd policy write nasos-policy /tmp/nasos-policy.hcl
    
    # 정리
    rm -f "$POLICY_FILE"
    
    echo -e "${GREEN}✓ Vault가 성공적으로 초기화되었습니다.${NC}"
    return 0
}

# 비밀 저장
store_secret() {
    local key=$1
    local value=$2
    local description=$3
    
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # 비밀 저장
    echo -e "${BLUE}비밀 저장 중: $key${NC}"
    vault kv put -address="$VAULT_ADDR" kv/nasos/$key value="$value" description="$description"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 비밀이 성공적으로 저장되었습니다: $key${NC}"
        return 0
    else
        echo -e "${RED}✗ 비밀 저장 실패: $key${NC}"
        return 1
    fi
}

# 비밀 검색
get_secret() {
    local key=$1
    
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # 비밀 검색
    echo -e "${BLUE}비밀 검색 중: $key${NC}"
    local result=$(vault kv get -address="$VAULT_ADDR" -format=json kv/nasos/$key 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        # JSON 파싱 (jq 사용)
        if command -v jq &> /dev/null; then
            echo "$result" | jq -r '.data.data.value'
        else
            # jq가 없는 경우 간단한 파싱
            echo "$result" | grep -o '"value": *"[^"]*"' | cut -d'"' -f4
        fi
        return 0
    else
        echo -e "${RED}✗ 비밀을 찾을 수 없습니다: $key${NC}" >&2
        return 1
    fi
}

# 비밀 목록 조회
list_secrets() {
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # 비밀 목록 조회
    echo -e "${BLUE}비밀 목록 조회 중...${NC}"
    local result=$(vault kv list -address="$VAULT_ADDR" -format=json kv/nasos/ 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}저장된 비밀 목록:${NC}"
        
        # JSON 파싱 (jq 사용)
        if command -v jq &> /dev/null; then
            echo "$result" | jq -r '.[]'
        else
            # jq가 없는 경우 간단한 파싱
            echo "$result" | grep -o '"[^"]*"' | tr -d '"' | grep -v "^$"
        fi
        return 0
    else
        echo -e "${YELLOW}저장된 비밀이 없습니다.${NC}"
        return 1
    fi
}

# 비밀 삭제
delete_secret() {
    local key=$1
    
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    # 비밀 삭제
    echo -e "${BLUE}비밀 삭제 중: $key${NC}"
    vault kv delete -address="$VAULT_ADDR" kv/nasos/$key
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 비밀이 성공적으로 삭제되었습니다: $key${NC}"
        return 0
    else
        echo -e "${RED}✗ 비밀 삭제 실패: $key${NC}"
        return 1
    fi
}

# 환경 변수 파일에서 비밀 로드
load_secrets_from_env() {
    # .env 파일 확인
    if [ ! -f "$SECRETS_FILE" ]; then
        echo -e "${RED}오류: .env 파일을 찾을 수 없습니다.${NC}"
        return 1
    fi
    
    # Vault 초기화
    if ! initialize_vault; then
        return 1
    fi
    
    echo -e "${BLUE}.env 파일에서 비밀 로드 중...${NC}"
    
    # 백업 디렉토리 생성
    mkdir -p "$SECRETS_BACKUP_DIR"
    
    # .env 파일 백업
    local backup_file="$SECRETS_BACKUP_DIR/env_backup_$(date +%Y%m%d_%H%M%S).env"
    cp "$SECRETS_FILE" "$backup_file"
    chmod 600 "$backup_file"
    
    # .env 파일에서 비밀 로드
    while IFS='=' read -r key value || [ -n "$key" ]; do
        # 주석 및 빈 줄 건너뛰기
        if [[ $key =~ ^# ]] || [ -z "$key" ]; then
            continue
        fi
        
        # 키와 값 정리
        key=$(echo "$key" | tr -d ' ')
        value=$(echo "$value" | tr -d ' ' | tr -d '"' | tr -d "'")
        
        # 비밀 저장
        if [ -n "$key" ] && [ -n "$value" ]; then
            store_secret "$key" "$value" "Loaded from .env file"
        fi
    done < "$SECRETS_FILE"
    
    echo -e "${GREEN}✓ 비밀이 성공적으로 로드되었습니다.${NC}"
    return 0
}

# 비밀을 환경 변수 파일로 내보내기
export_secrets_to_env() {
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    echo -e "${BLUE}비밀을 .env 파일로 내보내는 중...${NC}"
    
    # 백업 디렉토리 생성
    mkdir -p "$SECRETS_BACKUP_DIR"
    
    # 기존 .env 파일 백업
    if [ -f "$SECRETS_FILE" ]; then
        local backup_file="$SECRETS_BACKUP_DIR/env_backup_$(date +%Y%m%d_%H%M%S).env"
        cp "$SECRETS_FILE" "$backup_file"
        chmod 600 "$backup_file"
    fi
    
    # 새 .env 파일 생성
    echo "# NASOSv5_mod3 Bot 환경 변수" > "$SECRETS_FILE"
    echo "# 생성 시간: $(date)" >> "$SECRETS_FILE"
    echo "# 주의: 이 파일에는 민감한 정보가 포함되어 있습니다. 안전하게 보관하세요." >> "$SECRETS_FILE"
    echo "" >> "$SECRETS_FILE"
    
    # 비밀 목록 가져오기
    local secrets=$(vault kv list -address="$VAULT_ADDR" -format=json kv/nasos/ 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}내보낼 비밀이 없습니다.${NC}"
        return 1
    fi
    
    # JSON 파싱 (jq 사용)
    if command -v jq &> /dev/null; then
        local keys=$(echo "$secrets" | jq -r '.[]')
    else
        # jq가 없는 경우 간단한 파싱
        local keys=$(echo "$secrets" | grep -o '"[^"]*"' | tr -d '"' | grep -v "^$")
    fi
    
    # 각 비밀을 .env 파일에 추가
    for key in $keys; do
        local value=$(get_secret "$key")
        if [ -n "$value" ]; then
            echo "$key=$value" >> "$SECRETS_FILE"
        fi
    done
    
    # 파일 권한 설정
    chmod 600 "$SECRETS_FILE"
    
    echo -e "${GREEN}✓ 비밀이 성공적으로 내보내졌습니다: $SECRETS_FILE${NC}"
    return 0
}

# 암호화된 백업 생성
create_encrypted_backup() {
    local password=$1
    local backup_file="$SECRETS_BACKUP_DIR/vault_backup_$(date +%Y%m%d_%H%M%S).enc"
    
    # 백업 디렉토리 생성
    mkdir -p "$SECRETS_BACKUP_DIR"
    
    # Vault 상태 확인
    if ! check_vault_status; then
        return 1
    fi
    
    echo -e "${BLUE}암호화된 백업 생성 중...${NC}"
    
    # 비밀 목록 가져오기
    local secrets=$(vault kv list -address="$VAULT_ADDR" -format=json kv/nasos/ 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}백업할 비밀이 없습니다.${NC}"
        return 1
    fi
    
    # 임시 파일 생성
    local temp_file=$(mktemp)
    
    # JSON 파싱 (jq 사용)
    if command -v jq &> /dev/null; then
        local keys=$(echo "$secrets" | jq -r '.[]')
    else
        # jq가 없는 경우 간단한 파싱
        local keys=$(echo "$secrets" | grep -o '"[^"]*"' | tr -d '"' | grep -v "^$")
    fi
    
    # 각 비밀을 임시 파일에 추가
    echo "{" > "$temp_file"
    local first=true
    for key in $keys; do
        local value=$(get_secret "$key")
        if [ -n "$value" ]; then
            if [ "$first" = true ]; then
                first=false
            else
                echo "," >> "$temp_file"
            fi
            echo "  \"$key\": \"$value\"" >> "$temp_file"
        fi
    done
    echo "}" >> "$temp_file"
    
    # 파일 암호화 (openssl 사용)
    openssl enc -aes-256-cbc -salt -in "$temp_file" -out "$backup_file" -k "$password"
    
    # 임시 파일 삭제
    rm "$temp_file"
    
    if [ -f "$backup_file" ]; then
        echo -e "${GREEN}✓ 암호화된 백업이 성공적으로 생성되었습니다: $backup_file${NC}"
        return 0
    else
        echo -e "${RED}✗ 암호화된 백업 생성 실패${NC}"
        return 1
    fi
}

# 암호화된 백업에서 복원
restore_from_encrypted_backup() {
    local backup_file=$1
    local password=$2
    
    # 백업 파일 확인
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}오류: 백업 파일을 찾을 수 없습니다: $backup_file${NC}"
        return 1
    fi
    
    # Vault 초기화
    if ! initialize_vault; then
        return 1
    fi
    
    echo -e "${BLUE}암호화된 백업에서 복원 중...${NC}"
    
    # 임시 파일 생성
    local temp_file=$(mktemp)
    
    # 파일 복호화 (openssl 사용)
    openssl enc -aes-256-cbc -d -in "$backup_file" -out "$temp_file" -k "$password"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}오류: 백업 파일을 복호화할 수 없습니다. 비밀번호가 올바른지 확인하세요.${NC}"
        rm "$temp_file"
        return 1
    fi
    
    # JSON 파싱 (jq 사용)
    if command -v jq &> /dev/null; then
        local keys=$(jq -r 'keys[]' "$temp_file")
        
        for key in $keys; do
            local value=$(jq -r ".[\"$key\"]" "$temp_file")
            if [ -n "$value" ]; then
                store_secret "$key" "$value" "Restored from backup"
            fi
        done
    else
        # jq가 없는 경우 간단한 파싱 (제한적)
        echo -e "${YELLOW}경고: jq가 설치되어 있지 않아 제한된 복원을 수행합니다.${NC}"
        
        # 간단한 파싱 (제한적)
        while IFS=':' read -r key value || [ -n "$key" ]; do
            # 키와 값 정리
            key=$(echo "$key" | tr -d ' ' | tr -d '"' | tr -d ',')
            value=$(echo "$value" | tr -d ' ' | tr -d '"' | tr -d ',')
            
            # 비밀 저장
            if [ -n "$key" ] && [ -n "$value" ]; then
                store_secret "$key" "$value" "Restored from backup"
            fi
        done < <(grep -o '"[^"]*": *"[^"]*"' "$temp_file")
    fi
    
    # 임시 파일 삭제
    rm "$temp_file"
    
    echo -e "${GREEN}✓ 백업에서 성공적으로 복원되었습니다.${NC}"
    
    # .env 파일로 내보내기
    export_secrets_to_env
    
    return 0
}

# API 키 검증 (바이낸스)
validate_api_key() {
    local api_key=$1
    
    # 기본 검증
    if [ -z "$api_key" ]; then
        echo -e "${RED}오류: API 키가 비어 있습니다.${NC}"
        return 1
    fi
    
    # 길이 검증
    if [ ${#api_key} -lt 10 ]; then
        echo -e "${RED}오류: API 키가 너무 짧습니다.${NC}"
        return 1
    fi
    
    # 형식 검증 (바이낸스 API 키는 일반적으로 영숫자)
    if ! [[ $api_key =~ ^[a-zA-Z0-9]+$ ]]; then
        echo -e "${RED}오류: API 키에 유효하지 않은 문자가 포함되어 있습니다.${NC}"
        return 1
    fi
    
    return 0
}

# API 시크릿 검증 (바이낸스)
validate_api_secret() {
    local api_secret=$1
    
    # 기본 검증
    if [ -z "$api_secret" ]; then
        echo -e "${RED}오류: API 시크릿이 비어 있습니다.${NC}"
        return 1
    fi
    
    # 길이 검증
    if [ ${#api_secret} -lt 10 ]; then
        echo -e "${RED}오류: API 시크릿이 너무 짧습니다.${NC}"
        return 1
    fi
    
    # 형식 검증 (바이낸스 API 시크릿은 일반적으로 영숫자)
    if ! [[ $api_secret =~ ^[a-zA-Z0-9]+$ ]]; then
        echo -e "${RED}오류: API 시크릿에 유효하지 않은 문자가 포함되어 있습니다.${NC}"
        return 1
    fi
    
    return 0
}

# 안전한 비밀번호 생성
generate_secure_password() {
    local length=${1:-16}
    
    # openssl 사용 (더 안전)
    if command -v openssl &> /dev/null; then
        openssl rand -base64 $((length * 3 / 4)) | tr -dc 'a-zA-Z0-9!@#$%^&*()_+' | head -c $length
    else
        # 대체 방법
        tr -dc 'a-zA-Z0-9!@#$%^&*()_+' < /dev/urandom | head -c $length
    fi
}

# 메인 함수 (직접 실행 시)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # 명령줄 인수 처리
    case "$1" in
        init)
            initialize_vault
            ;;
        store)
            if [ -z "$2" ] || [ -z "$3" ]; then
                echo "사용법: $0 store <key> <value> [description]"
                exit 1
            fi
            store_secret "$2" "$3" "${4:-No description}"
            ;;
        get)
            if [ -z "$2" ]; then
                echo "사용법: $0 get <key>"
                exit 1
            fi
            get_secret "$2"
            ;;
        list)
            list_secrets
            ;;
        delete)
            if [ -z "$2" ]; then
                echo "사용법: $0 delete <key>"
                exit 1
            fi
            delete_secret "$2"
            ;;
        load)
            load_secrets_from_env
            ;;
        export)
            export_secrets_to_env
            ;;
        backup)
            if [ -z "$2" ]; then
                echo "사용법: $0 backup <password>"
                exit 1
            fi
            create_encrypted_backup "$2"
            ;;
        restore)
            if [ -z "$2" ] || [ -z "$3" ]; then
                echo "사용법: $0 restore <backup_file> <password>"
                exit 1
            fi
            restore_from_encrypted_backup "$2" "$3"
            ;;
        help|--help|-h)
            echo "사용법: $0 <command> [options]"
            echo ""
            echo "명령어:"
            echo "  init                    Vault 초기화"
            echo "  store <key> <value>     비밀 저장"
            echo "  get <key>               비밀 검색"
            echo "  list                    비밀 목록 조회"
            echo "  delete <key>            비밀 삭제"
            echo "  load                    .env 파일에서 비밀 로드"
            echo "  export                  비밀을 .env 파일로 내보내기"
            echo "  backup <password>       암호화된 백업 생성"
            echo "  restore <file> <pwd>    암호화된 백업에서 복원"
            echo "  help                    도움말 표시"
            ;;
        *)
            echo "알 수 없는 명령어: $1"
            echo "도움말을 보려면 '$0 help'를 실행하세요."
            exit 1
            ;;
    esac
fi
