#!/bin/bash

# NASOSv5_mod3 Bot 비밀 자동 교체 스크립트
# 이 스크립트는 Vault에 저장된 비밀을 주기적으로 교체합니다.

# 현재 디렉토리 저장
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 보안 유틸리티 스크립트 로드
source "$SCRIPT_DIR/security_utils.sh"

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 로그 함수
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 비밀 교체 함수
rotate_secret() {
    local path=$1
    local key=$2
    local generator=$3
    
    log "${BLUE}비밀 교체 중: $path/$key${NC}"
    
    # 현재 비밀 백업
    local current_value
    if ! current_value=$(get_secret "$path" "$key" 2>/dev/null); then
        log "${YELLOW}현재 비밀이 없습니다. 새로 생성합니다.${NC}"
        current_value=""
    fi
    
    # 새 비밀 생성
    local new_value
    if [ -n "$generator" ] && [ -x "$generator" ]; then
        # 외부 생성기 스크립트 사용
        new_value=$("$generator")
    else
        # 기본 비밀번호 생성기 사용
        new_value=$(generate_secure_password 32)
    fi
    
    # 새 비밀 저장
    if store_secret "$path" "$key" "$new_value"; then
        log "${GREEN}비밀이 성공적으로 교체되었습니다: $path/$key${NC}"
        
        # 백업 저장 (롤백용)
        if [ -n "$current_value" ]; then
            store_secret "$path/backup" "$key" "$current_value"
            log "${BLUE}이전 비밀이 백업되었습니다: $path/backup/$key${NC}"
        fi
        
        return 0
    else
        log "${RED}비밀 교체 실패: $path/$key${NC}"
        return 1
    fi
}

# 데이터베이스 비밀번호 교체
rotate_database_passwords() {
    log "${BLUE}데이터베이스 비밀번호 교체 중...${NC}"
    
    # PostgreSQL 비밀번호 교체
    rotate_secret "db" "postgres_password" ""
    
    # InfluxDB 비밀번호 교체
    rotate_secret "db" "influxdb_password" ""
    
    # Redis 비밀번호 교체
    rotate_secret "db" "redis_password" ""
    
    log "${GREEN}데이터베이스 비밀번호 교체 완료${NC}"
}

# API 키 교체
rotate_api_keys() {
    log "${BLUE}API 키 교체 중...${NC}"
    
    # 여기서는 API 키를 자동으로 교체할 수 없으므로 알림만 제공
    log "${YELLOW}API 키는 수동으로 교체해야 합니다.${NC}"
    log "${YELLOW}다음 API 키를 교체하는 것이 좋습니다:${NC}"
    
    # 저장된 API 키 목록 조회
    local api_paths
    api_paths=$(list_secrets "api")
    
    for path in $api_paths; do
        local exchange=$(basename "$path")
        local created_time
        created_time=$(vault_cmd kv metadata get -format=json "kv/$path" | jq -r '.data.created_time')
        local days_old
        days_old=$(( ( $(date +%s) - $(date -d "$created_time" +%s) ) / 86400 ))
        
        if [ "$days_old" -gt 90 ]; then
            log "${RED}$exchange API 키가 $days_old일 지났습니다. 교체가 필요합니다.${NC}"
        elif [ "$days_old" -gt 60 ]; then
            log "${YELLOW}$exchange API 키가 $days_old일 지났습니다. 곧 교체가 필요합니다.${NC}"
        fi
    done
    
    log "${GREEN}API 키 검토 완료${NC}"
}

# JWT 시크릿 교체
rotate_jwt_secret() {
    log "${BLUE}JWT 시크릿 교체 중...${NC}"
    
    # JWT 시크릿 교체
    rotate_secret "auth" "jwt_secret" ""
    
    log "${GREEN}JWT 시크릿 교체 완료${NC}"
}

# 모든 비밀 교체
rotate_all_secrets() {
    log "${BLUE}모든 비밀 교체 시작...${NC}"
    
    # Vault 상태 확인
    if ! check_vault_status; then
        log "${RED}Vault 서버에 연결할 수 없습니다. 비밀 교체를 중단합니다.${NC}"
        return 1
    fi
    
    # 데이터베이스 비밀번호 교체
    rotate_database_passwords
    
    # JWT 시크릿 교체
    rotate_jwt_secret
    
    # API 키 검토
    rotate_api_keys
    
    log "${GREEN}모든 비밀 교체 완료${NC}"
    return 0
}

# 메인 함수
main() {
    # 명령줄 인수 처리
    case "$1" in
        --all)
            rotate_all_secrets
            ;;
        --db)
            rotate_database_passwords
            ;;
        --jwt)
            rotate_jwt_secret
            ;;
        --api)
            rotate_api_keys
            ;;
        --help)
            echo "사용법: $0 [옵션]"
            echo "옵션:"
            echo "  --all    모든 비밀 교체"
            echo "  --db     데이터베이스 비밀번호 교체"
            echo "  --jwt    JWT 시크릿 교체"
            echo "  --api    API 키 검토"
            echo "  --help   도움말 표시"
            ;;
        *)
            echo "사용법: $0 [옵션]"
            echo "옵션을 보려면 --help를 사용하세요."
            exit 1
            ;;
    esac
}

# 스크립트가 직접 실행된 경우 메인 함수 호출
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
