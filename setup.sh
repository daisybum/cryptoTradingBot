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
BOLD='\033[1m'
UNDERLINE='\033[4m'
NC='\033[0m' # No Color

# 변수 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/config"
ENV_FILE="$SCRIPT_DIR/.env"
BACKUP_DIR="$SCRIPT_DIR/backups"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/setup_$(date +%Y%m%d_%H%M%S).log"

# 로그 함수
log() {
    local level=$1
    local message=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    # 로그 디렉토리 생성
    mkdir -p "$LOG_DIR"
    
    # 콘솔 출력
    case $level in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "DEBUG")
            if [ "$DEBUG" = true ]; then
                echo -e "${BLUE}[DEBUG]${NC} $message"
            fi
            ;;
    esac
    
    # 파일에 로그 기록
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# 종료 처리 함수
cleanup() {
    log "INFO" "스크립트 종료 중..."
    # 임시 파일 정리 등 필요한 작업 수행
    log "INFO" "설정 스크립트가 종료되었습니다."
    exit 0
}

# CTRL+C 처리
trap cleanup SIGINT

# 오류 처리 함수
handle_error() {
    log "ERROR" "오류 발생: $1"
    echo -e "${RED}오류: $1${NC}"
    echo -e "${YELLOW}자세한 내용은 로그 파일을 확인하세요: $LOG_FILE${NC}"
    exit 1
}

# 백업 함수
backup_config() {
    log "INFO" "설정 백업 중..."
    
    # 백업 디렉토리 생성
    mkdir -p "$BACKUP_DIR"
    
    # 백업 파일 이름 생성
    local backup_file="$BACKUP_DIR/nasos_config_$(date +%Y%m%d_%H%M%S).tar.gz"
    
    # 설정 파일 백업
    tar -czf "$backup_file" -C "$SCRIPT_DIR" .env config user_data/strategies 2>/dev/null
    
    if [ $? -eq 0 ]; then
        log "INFO" "설정이 백업되었습니다: $backup_file"
        echo -e "${GREEN}✓ 설정이 백업되었습니다: $backup_file${NC}"
    else
        log "ERROR" "설정 백업 실패"
        echo -e "${RED}✗ 설정 백업 실패${NC}"
    fi
}

# 복원 함수
restore_config() {
    log "INFO" "설정 복원 메뉴 시작"
    
    # 백업 디렉토리 확인
    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]; then
        log "WARN" "사용 가능한 백업이 없습니다"
        echo -e "${YELLOW}사용 가능한 백업이 없습니다.${NC}"
        return 1
    fi
    
    # 백업 파일 목록 표시
    echo -e "${BLUE}사용 가능한 백업 파일:${NC}"
    local i=1
    local backup_files=("$BACKUP_DIR"/*.tar.gz)
    
    for file in "${backup_files[@]}"; do
        echo "$i) $(basename "$file") ($(date -r "$file" '+%Y-%m-%d %H:%M:%S'))"
        i=$((i+1))
    done
    
    # 백업 선택
    echo -e "${YELLOW}복원할 백업 번호를 선택하세요 (취소: 0):${NC}"
    read -p "> " backup_choice
    
    if [ "$backup_choice" = "0" ]; then
        log "INFO" "설정 복원 취소됨"
        echo -e "${YELLOW}설정 복원이 취소되었습니다.${NC}"
        return 0
    fi
    
    if ! [[ "$backup_choice" =~ ^[0-9]+$ ]] || [ "$backup_choice" -lt 1 ] || [ "$backup_choice" -gt "${#backup_files[@]}" ]; then
        log "ERROR" "잘못된 선택: $backup_choice"
        echo -e "${RED}잘못된 선택입니다.${NC}"
        return 1
    fi
    
    local selected_backup="${backup_files[$((backup_choice-1))]}"
    log "INFO" "선택된 백업 파일: $selected_backup"
    
    # 복원 확인
    echo -e "${YELLOW}경고: 이 작업은 현재 설정을 덮어씁니다. 계속하시겠습니까? (y/n)${NC}"
    read -p "> " confirm
    
    if [ "$confirm" != "y" ]; then
        log "INFO" "설정 복원 취소됨"
        echo -e "${YELLOW}설정 복원이 취소되었습니다.${NC}"
        return 0
    fi
    
    # 현재 설정 백업
    backup_config
    
    # 백업 파일 복원
    log "INFO" "백업 파일 복원 중: $selected_backup"
    tar -xzf "$selected_backup" -C "$SCRIPT_DIR" .env config user_data/strategies 2>/dev/null
    
    if [ $? -eq 0 ]; then
        log "INFO" "설정이 성공적으로 복원되었습니다"
        echo -e "${GREEN}✓ 설정이 성공적으로 복원되었습니다.${NC}"
    else
        log "ERROR" "설정 복원 실패"
        echo -e "${RED}✗ 설정 복원 실패${NC}"
        return 1
    fi
}

# 로고 출력 함수
show_logo() {
    clear
    echo -e "${CYAN}"
    echo "███╗   ██╗ █████╗ ███████╗ ██████╗ ███████╗██╗   ██╗███████╗    ███╗   ███╗ ██████╗ ██████╗ ██████╗ "
    echo "████╗  ██║██╔══██╗██╔════╝██╔═══██╗██╔════╝██║   ██║██╔════╝    ████╗ ████║██╔═══██╗██╔══██╗╚════██╗"
    echo "██╔██╗ ██║███████║███████╗██║   ██║███████╗██║   ██║███████╗    ██╔████╔██║██║   ██║██║  ██║ █████╔╝"
    echo "██║╚██╗██║██╔══██║╚════██║██║   ██║╚════██║╚██╗ ██╔╝╚════██║    ██║╚██╔╝██║██║   ██║██║  ██║ ╚═══██╗"
    echo "██║ ╚████║██║  ██║███████║╚██████╔╝███████║ ╚████╔╝ ███████║    ██║ ╚═╝ ██║╚██████╔╝██████╔╝██████╔╝"
    echo "╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝  ╚═══╝  ╚══════╝    ╚═╝     ╚═╝ ╚═════╝ ╚═════╝ ╚═════╝ "
    echo -e "${NC}"
    echo -e "${YELLOW}${BOLD}바이낸스 알트코인 고빈도 트레이딩 봇 설정 마법사${NC}"
    echo -e "${YELLOW}=======================================================${NC}"
    echo ""
}

# 메인 함수
main() {
    # 로그 시작
    log "INFO" "NASOSv5_mod3 Bot 설정 스크립트 시작"
    
    # 환경 확인
    check_environment
    
    # 메인 루프
    while true; do
        show_main_menu
        read -p "> " choice
        
        case $choice in
            1)
                setup_new_environment
                ;;
            2)
                update_existing_config
                ;;
            3)
                backup_config
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            4)
                restore_config
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            5)
                docker_container_menu
                ;;
            6)
                check_system_status
                ;;
            7)
                strategy_management_menu
                ;;
            8)
                manage_security_settings
                ;;
            9)
                log "INFO" "NASOSv5_mod3 Bot 설정 스크립트 종료"
                echo -e "${GREEN}NASOSv5_mod3 Bot 설정 스크립트를 종료합니다.${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}잘못된 선택입니다. 다시 시도하세요.${NC}"
                sleep 2
                ;;
        esac
    done
}

function validate_api_key() {
    local api_key=$1
    if [[ ! $api_key =~ ^[A-Za-z0-9]{64}$ ]]; then
        echo -e "${RED}오류: 유효하지 않은 API 키 형식입니다. 바이낸스 API 키는 64자의 영숫자여야 합니다.${NC}"
        return 1
    fi
    return 0
}

function validate_api_secret() {
    local api_secret=$1
    if [[ ! $api_secret =~ ^[A-Za-z0-9]{64}$ ]]; then
        echo -e "${RED}오류: 유효하지 않은 API 시크릿 형식입니다. 바이낸스 API 시크릿은 64자의 영숫자여야 합니다.${NC}"
        return 1
    fi
    return 0
}

function validate_telegram_token() {
    local token=$1
    if [[ ! $token =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
        echo -e "${RED}오류: 유효하지 않은 텔레그램 봇 토큰 형식입니다.${NC}"
        return 1
    fi
    return 0
}

function validate_telegram_chat_id() {
    local chat_id=$1
    if [[ ! $chat_id =~ ^-?[0-9]+$ ]]; then
        echo -e "${RED}오류: 유효하지 않은 텔레그램 채팅 ID 형식입니다.${NC}"
        return 1
    fi
    return 0
}

function backup_config() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="${BACKUP_DIR}/nasos_config_${timestamp}.tar.gz"
    
    mkdir -p "${BACKUP_DIR}"
    
    echo -e "${BLUE}구성 파일 백업 중...${NC}"
    
    # 백업할 파일 및 디렉토리 목록
    local files_to_backup=".env docker-compose.yml config/"
    
    # 백업 파일 생성
    tar -czf "${backup_file}" ${files_to_backup} 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 백업이 성공적으로 생성되었습니다: ${backup_file}${NC}"
        return 0
    else
        echo -e "${RED}백업 생성 중 오류가 발생했습니다.${NC}"
        return 1
    fi
}

function restore_config() {
    local backups=($(ls -1 ${BACKUP_DIR}/*.tar.gz 2>/dev/null))
    local num_backups=${#backups[@]}
    
    if [ $num_backups -eq 0 ]; then
        echo -e "${RED}사용 가능한 백업 파일이 없습니다.${NC}"
        return 1
    fi
    
    echo -e "${BLUE}사용 가능한 백업 파일:${NC}"
    for i in $(seq 0 $(($num_backups-1))); do
        echo "[$i] $(basename ${backups[$i]})"
    done
    
    read -p "복원할 백업 번호를 선택하세요 (0-$(($num_backups-1))): " backup_index
    
    if ! [[ "$backup_index" =~ ^[0-9]+$ ]] || [ $backup_index -lt 0 ] || [ $backup_index -ge $num_backups ]; then
        echo -e "${RED}잘못된 선택입니다.${NC}"
        return 1
    fi
    
    local selected_backup=${backups[$backup_index]}
    echo -e "${YELLOW}경고: 이 작업은 현재 구성을 덮어씁니다.${NC}"
    read -p "계속하시겠습니까? (y/n): " confirm
    
    if [ "$confirm" != "y" ]; then
        echo -e "${YELLOW}복원이 취소되었습니다.${NC}"
        return 1
    fi
    
    echo -e "${BLUE}백업에서 구성 복원 중: $(basename ${selected_backup})${NC}"
    tar -xzf "${selected_backup}" -C ./ 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 구성이 성공적으로 복원되었습니다.${NC}"
        return 0
    else
        echo -e "${RED}구성 복원 중 오류가 발생했습니다.${NC}"
        return 1
    fi
}

function generate_secure_password() {
    local length=${1:-16}
    openssl rand -base64 $length | tr -d '\n'
}

function check_environment() {
    echo -e "${BLUE}[1/5] 환경 확인 중...${NC}"
    
    local all_deps_installed=true
    
    # Docker 확인
    if ! check_dependency "docker" "[https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/) 에서 Docker를 설치하세요."; then
        all_deps_installed=false
    fi
    
    # Docker Compose 확인
    if ! check_dependency "docker-compose" "[https://docs.docker.com/compose/install/](https://docs.docker.com/compose/install/) 에서 Docker Compose를 설치하세요."; then
        all_deps_installed=false
    fi
    
    # Python 확인
    if ! check_dependency "python3" "[https://www.python.org/downloads/](https://www.python.org/downloads/) 에서 Python 3를 설치하세요."; then
        all_deps_installed=false
    fi
    
    # OpenSSL 확인 (비밀번호 생성용)
    if ! check_dependency "openssl" "시스템 패키지 관리자를 통해 OpenSSL을 설치하세요."; then
        all_deps_installed=false
    fi
    
    # 시스템 리소스 확인
    echo -e "${BLUE}시스템 리소스 확인 중...${NC}"
    echo "CPU 코어: $(nproc)"
    echo "가용 메모리: $(free -h | grep Mem | awk '{print $7}')"
    echo "디스크 공간: $(df -h . | grep -v Filesystem | awk '{print $4}') 남음"
    
    if [ "$all_deps_installed" = true ]; then
        echo -e "${GREEN}✓ 모든 필수 종속성이 설치되어 있습니다.${NC}"
    else
        echo -e "${YELLOW}⚠ 일부 종속성이 누락되었습니다. 위 메시지를 확인하세요.${NC}"
    fi
}

function setup_new_environment() {
    print_header
    echo -e "${BLUE}[2/5] 새 환경 설정 중...${NC}"
    
    if [ -f $ENV_FILE ]; then
        echo -e "${YELLOW}경고: $ENV_FILE 파일이 이미 존재합니다.${NC}"
        read -p "덮어쓰시겠습니까? (y/n): " overwrite_env
        if [ "$overwrite_env" != "y" ]; then
            echo -e "${YELLOW}기존 $ENV_FILE 파일을 유지합니다.${NC}"
            return 0
        fi
    fi
    
    echo "# NASOSv5_mod3 Bot 환경 변수" > $ENV_FILE
    echo "# $(date)" >> $ENV_FILE
    echo "" >> $ENV_FILE
    
    # 바이낸스 API 키 입력 및 검증
    while true; do
        echo -e "${YELLOW}바이낸스 API 키를 입력하세요 (거래 권한 필요, 출금 권한 비활성화 권장)${NC}"
        read -p "API 키: " binance_api_key
        
        if validate_api_key "$binance_api_key"; then
            break
        fi
    done
    
    while true; do
        read -p "API 시크릿: " binance_api_secret
        
        if validate_api_secret "$binance_api_secret"; then
            break
        fi
    done
    
    echo "# Binance API 설정" >> $ENV_FILE
    echo "BINANCE_API_KEY=$binance_api_key" >> $ENV_FILE
    echo "BINANCE_API_SECRET=$binance_api_secret" >> $ENV_FILE
    echo "" >> $ENV_FILE
    
    # 데이터베이스 설정
    echo "# 데이터베이스 설정" >> $ENV_FILE
    echo "POSTGRES_USER=nasos_user" >> $ENV_FILE
    
    # 안전한 비밀번호 생성
    local pg_password=$(generate_secure_password 16)
    echo "POSTGRES_PASSWORD=$pg_password" >> $ENV_FILE
    echo "POSTGRES_DB=nasos_bot" >> $ENV_FILE
    
    local influx_token=$(generate_secure_password 24)
    echo "INFLUXDB_TOKEN=$influx_token" >> $ENV_FILE
    echo "INFLUXDB_ORG=nasos_org" >> $ENV_FILE
    echo "INFLUXDB_BUCKET=market_data" >> $ENV_FILE
    echo "" >> $ENV_FILE
    
    # 위험 관리 설정
    echo -e "${YELLOW}위험 관리 설정을 구성하시겠습니까? (y/n)${NC}"
    read -p "> " setup_risk
    if [ "$setup_risk" = "y" ]; then
        echo "# 위험 관리 설정" >> $ENV_FILE
        
        read -p "최대 전역 드로다운 (%): " max_drawdown
        max_drawdown=${max_drawdown:-15}
        echo "MAX_GLOBAL_DRAWDOWN=$max_drawdown" >> $ENV_FILE
        
        read -p "거래당 손절 (%): " stop_loss
        stop_loss=${stop_loss:-3.5}
        echo "PER_TRADE_STOP_LOSS=$stop_loss" >> $ENV_FILE
        
        read -p "거래당 리스크 (%): " risk_per_trade
        risk_per_trade=${risk_per_trade:-2}
        echo "RISK_PER_TRADE=$risk_per_trade" >> $ENV_FILE
        echo "" >> $ENV_FILE
    fi
    
    # 텔레그램 설정 (선택 사항)
    echo -e "${YELLOW}텔레그램 알림을 설정하시겠습니까? (y/n)${NC}"
    read -p "> " setup_telegram
    if [ "$setup_telegram" = "y" ]; then
        while true; do
            read -p "텔레그램 봇 토큰: " telegram_token
            
            if validate_telegram_token "$telegram_token"; then
                break
            fi
        done
        
        while true; do
            read -p "텔레그램 채팅 ID: " telegram_chat_id
            
            if validate_telegram_chat_id "$telegram_chat_id"; then
                break
            fi
        done
        
        echo "# 텔레그램 설정" >> $ENV_FILE
        echo "TELEGRAM_TOKEN=$telegram_token" >> $ENV_FILE
        echo "TELEGRAM_CHAT_ID=$telegram_chat_id" >> $ENV_FILE
        echo "" >> $ENV_FILE
    fi
    
    # 기본 전략 설정
    echo "# 기본 전략 설정" >> $ENV_FILE
    echo "DEFAULT_STRATEGY=NASOSv5_mod3" >> $ENV_FILE
    echo "TIMEFRAME=5m" >> $ENV_FILE
    echo "MAX_OPEN_TRADES=5" >> $ENV_FILE
    echo "" >> $ENV_FILE
    
    echo -e "${GREEN}✓ $ENV_FILE 파일이 생성되었습니다.${NC}"
    
    # 환경 변수 예제 파일 생성
    if [ ! -f $ENV_EXAMPLE_FILE ] || [ "$overwrite_env" = "y" ]; then
        cp $ENV_FILE $ENV_EXAMPLE_FILE
        # 민감한 정보 마스킹
        sed -i 's/BINANCE_API_KEY=.*/BINANCE_API_KEY=your_api_key_here/' $ENV_EXAMPLE_FILE
        sed -i 's/BINANCE_API_SECRET=.*/BINANCE_API_SECRET=your_api_secret_here/' $ENV_EXAMPLE_FILE
        sed -i 's/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=your_secure_password_here/' $ENV_EXAMPLE_FILE
        sed -i 's/INFLUXDB_TOKEN=.*/INFLUXDB_TOKEN=your_influxdb_token_here/' $ENV_EXAMPLE_FILE
        sed -i 's/TELEGRAM_TOKEN=.*/TELEGRAM_TOKEN=your_telegram_token_here/' $ENV_EXAMPLE_FILE
        sed -i 's/TELEGRAM_CHAT_ID=.*/TELEGRAM_CHAT_ID=your_chat_id_here/' $ENV_EXAMPLE_FILE
        
        echo -e "${GREEN}✓ $ENV_EXAMPLE_FILE 예제 파일이 생성되었습니다.${NC}"
    fi
    
    # 디렉토리 구조 확인
    setup_directory_structure
    
    # 구성 백업 제안
    echo -e "${YELLOW}새 환경 설정을 백업하시겠습니까? (y/n)${NC}"
    read -p "> " do_backup
    if [ "$do_backup" = "y" ]; then
        backup_config
    fi
}

function update_existing_config() {
    print_header
    echo -e "${BLUE}기존 설정 업데이트 중...${NC}"
    
    if [ ! -f $ENV_FILE ]; then
        echo -e "${RED}오류: $ENV_FILE 파일이 존재하지 않습니다.${NC}"
        echo -e "${YELLOW}먼저 '새 환경 설정'을 실행하세요.${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}어떤 설정을 업데이트하시겠습니까?${NC}"
    echo "1. Binance API 키"
    echo "2. 데이터베이스 설정"
    echo "3. 위험 관리 설정"
    echo "4. 텔레그램 설정"
    echo "5. 전략 설정"
    echo "0. 취소"
    
    read -p "옵션을 선택하세요 (0-5): " update_option
    
    case $update_option in
        1)
            # Binance API 키 업데이트
            while true; do
                echo -e "${YELLOW}새 바이낸스 API 키를 입력하세요${NC}"
                read -p "API 키: " binance_api_key
                
                if validate_api_key "$binance_api_key"; then
                    break
                fi
            done
            
            while true; do
                read -p "API 시크릿: " binance_api_secret
                
                if validate_api_secret "$binance_api_secret"; then
                    break
                fi
            done
            
            sed -i "s/BINANCE_API_KEY=.*/BINANCE_API_KEY=$binance_api_key/" $ENV_FILE
            sed -i "s/BINANCE_API_SECRET=.*/BINANCE_API_SECRET=$binance_api_secret/" $ENV_FILE
            echo -e "${GREEN}✓ Binance API 키가 업데이트되었습니다.${NC}"
            ;;
        2)
            # 데이터베이스 설정 업데이트
            read -p "PostgreSQL 사용자 이름 [nasos_user]: " pg_user
            pg_user=${pg_user:-nasos_user}
            
            read -p "새 PostgreSQL 비밀번호를 생성하시겠습니까? (y/n): " gen_pg_pwd
            if [ "$gen_pg_pwd" = "y" ]; then
                pg_password=$(generate_secure_password 16)
                echo -e "${GREEN}새 비밀번호: $pg_password${NC}"
            else
                read -p "PostgreSQL 비밀번호: " pg_password
            fi
            
            read -p "PostgreSQL 데이터베이스 이름 [nasos_bot]: " pg_db
            pg_db=${pg_db:-nasos_bot}
            
            read -p "새 InfluxDB 토큰을 생성하시겠습니까? (y/n): " gen_influx_token
            if [ "$gen_influx_token" = "y" ]; then
                influx_token=$(generate_secure_password 24)
                echo -e "${GREEN}새 토큰: $influx_token${NC}"
            else
                read -p "InfluxDB 토큰: " influx_token
            fi
            
            read -p "InfluxDB 조직 이름 [nasos_org]: " influx_org
            influx_org=${influx_org:-nasos_org}
            
            read -p "InfluxDB 버킷 이름 [market_data]: " influx_bucket
            influx_bucket=${influx_bucket:-market_data}
            
            sed -i "s/POSTGRES_USER=.*/POSTGRES_USER=$pg_user/" $ENV_FILE
            sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$pg_password/" $ENV_FILE
            sed -i "s/POSTGRES_DB=.*/POSTGRES_DB=$pg_db/" $ENV_FILE
            sed -i "s/INFLUXDB_TOKEN=.*/INFLUXDB_TOKEN=$influx_token/" $ENV_FILE
            sed -i "s/INFLUXDB_ORG=.*/INFLUXDB_ORG=$influx_org/" $ENV_FILE
            sed -i "s/INFLUXDB_BUCKET=.*/INFLUXDB_BUCKET=$influx_bucket/" $ENV_FILE
            
            echo -e "${GREEN}✓ 데이터베이스 설정이 업데이트되었습니다.${NC}"
            ;;
        3)
            # 위험 관리 설정 업데이트
            read -p "최대 전역 드로다운 (%): " max_drawdown
            read -p "거래당 손절 (%): " stop_loss
            read -p "거래당 리스크 (%): " risk_per_trade
            
            # 기존 설정이 있는지 확인
            if grep -q "MAX_GLOBAL_DRAWDOWN" $ENV_FILE; then
                sed -i "s/MAX_GLOBAL_DRAWDOWN=.*/MAX_GLOBAL_DRAWDOWN=$max_drawdown/" $ENV_FILE
                sed -i "s/PER_TRADE_STOP_LOSS=.*/PER_TRADE_STOP_LOSS=$stop_loss/" $ENV_FILE
                sed -i "s/RISK_PER_TRADE=.*/RISK_PER_TRADE=$risk_per_trade/" $ENV_FILE
            else
                echo "" >> $ENV_FILE
                echo "# 위험 관리 설정" >> $ENV_FILE
                echo "MAX_GLOBAL_DRAWDOWN=$max_drawdown" >> $ENV_FILE
                echo "PER_TRADE_STOP_LOSS=$stop_loss" >> $ENV_FILE
                echo "RISK_PER_TRADE=$risk_per_trade" >> $ENV_FILE
            fi
            
            echo -e "${GREEN}✓ 위험 관리 설정이 업데이트되었습니다.${NC}"
            ;;
        4)
            # 텔레그램 설정 업데이트
            while true; do
                read -p "텔레그램 봇 토큰: " telegram_token
                
                if validate_telegram_token "$telegram_token"; then
                    break
                fi
            done
            
            while true; do
                read -p "텔레그램 채팅 ID: " telegram_chat_id
                
                if validate_telegram_chat_id "$telegram_chat_id"; then
                    break
                fi
            done
            
            # 기존 설정이 있는지 확인
            if grep -q "TELEGRAM_TOKEN" $ENV_FILE; then
                sed -i "s/TELEGRAM_TOKEN=.*/TELEGRAM_TOKEN=$telegram_token/" $ENV_FILE
                sed -i "s/TELEGRAM_CHAT_ID=.*/TELEGRAM_CHAT_ID=$telegram_chat_id/" $ENV_FILE
            else
                echo "" >> $ENV_FILE
                echo "# 텔레그램 설정" >> $ENV_FILE
                echo "TELEGRAM_TOKEN=$telegram_token" >> $ENV_FILE
                echo "TELEGRAM_CHAT_ID=$telegram_chat_id" >> $ENV_FILE
            fi
            
            echo -e "${GREEN}✓ 텔레그램 설정이 업데이트되었습니다.${NC}"
            ;;
        5)
            # 전략 설정 업데이트
            read -p "기본 전략 이름 [NASOSv5_mod3]: " strategy
            strategy=${strategy:-NASOSv5_mod3}
            
            read -p "타임프레임 [5m]: " timeframe
            timeframe=${timeframe:-5m}
            
            read -p "최대 동시 거래 수 [5]: " max_trades
            max_trades=${max_trades:-5}
            
            # 기존 설정이 있는지 확인
            if grep -q "DEFAULT_STRATEGY" $ENV_FILE; then
                sed -i "s/DEFAULT_STRATEGY=.*/DEFAULT_STRATEGY=$strategy/" $ENV_FILE
                sed -i "s/TIMEFRAME=.*/TIMEFRAME=$timeframe/" $ENV_FILE
                sed -i "s/MAX_OPEN_TRADES=.*/MAX_OPEN_TRADES=$max_trades/" $ENV_FILE
            else
                echo "" >> $ENV_FILE
                echo "# 기본 전략 설정" >> $ENV_FILE
                echo "DEFAULT_STRATEGY=$strategy" >> $ENV_FILE
                echo "TIMEFRAME=$timeframe" >> $ENV_FILE
                echo "MAX_OPEN_TRADES=$max_trades" >> $ENV_FILE
            fi
            
            echo -e "${GREEN}✓ 전략 설정이 업데이트되었습니다.${NC}"
            ;;
        0)
            echo -e "${YELLOW}설정 업데이트를 취소합니다.${NC}"
            return 0
            ;;
        *)
            echo -e "${RED}잘못된 옵션입니다.${NC}"
            return 1
            ;;
    esac
    
    # 구성 백업 제안
    echo -e "${YELLOW}업데이트된 설정을 백업하시겠습니까? (y/n)${NC}"
    read -p "> " do_backup
    if [ "$do_backup" = "y" ]; then
        backup_config
    fi
}

function setup_directory_structure() {
    echo -e "${BLUE}[3/5] 디렉토리 구조 확인 중...${NC}"
    
    # 필수 디렉토리 확인 및 생성
    for dir in src config docs tests logs backups; do
        if [ ! -d "$dir" ]; then
            echo -e "${YELLOW}$dir 디렉토리가 없습니다. 생성 중...${NC}"
            mkdir -p "$dir"
        fi
    done
    
    # 필요한 서브디렉토리 생성
    mkdir -p src/{data_collection,strategy_engine,execution_engine,risk_manager,database,api_server,utils}
    mkdir -p config/strategies
    mkdir -p user_data/strategies
    
    # 기본 구성 파일 생성
    if [ ! -f "config/default.yml" ]; then
        echo -e "${YELLOW}기본 구성 파일 생성 중...${NC}"
        cat > config/default.yml << EOL
# NASOSv5_mod3 Bot 기본 구성 파일
# 자동 생성됨: $(date)

# 일반 설정
bot_name: NASOSv5_mod3
dry_run: true  # 실제 거래 비활성화 (테스트용)
max_open_trades: 5
stake_currency: USDT
stake_amount: 100
timeframe: 5m

# 전략 설정
strategy: NASOSv5_mod3
strategy_path: user_data/strategies/

# 거래소 설정
exchange:
  name: binance
  key: \${BINANCE_API_KEY}
  secret: \${BINANCE_API_SECRET}
  ccxt_config:
    enableRateLimit: true
  ccxt_async_config:
    enableRateLimit: true
    timeout: 60000

# 위험 관리 설정
risk_management:
  max_drawdown: 15.0  # 최대 드로다운 (%)
  stop_loss: 3.5      # 손절매 (%)
  risk_per_trade: 2.0
EOL
    fi
    
    echo -e "${GREEN}✓ 디렉토리 구조가 준비되었습니다.${NC}"
}

# 메인 메뉴 표시 함수
function show_main_menu() {
    clear
    show_logo
    
    echo -e "${BLUE}${BOLD}NASOSv5_mod3 Bot 설정 메뉴${NC}"
    echo -e "${YELLOW}=======================================================${NC}"
    echo ""
    echo -e "1) ${GREEN}새 환경 설정${NC}"
    echo -e "2) ${BLUE}기존 설정 업데이트${NC}"
    echo -e "3) ${CYAN}설정 백업${NC}"
    echo -e "4) ${MAGENTA}설정 복원${NC}"
    echo -e "5) ${YELLOW}Docker 컨테이너 관리${NC}"
    echo -e "6) ${BLUE}시스템 상태 확인${NC}"
    echo -e "7) ${GREEN}전략 관리${NC}"
    echo -e "8) ${MAGENTA}보안 설정 관리${NC}"
    echo -e "9) ${RED}종료${NC}"
    echo ""
    echo -e "${YELLOW}선택하세요 (1-9):${NC}"
}

# Docker 컨테이너 관리 메뉴
function docker_container_menu() {
    clear
    show_logo
    
    echo -e "${BLUE}${BOLD}Docker 컨테이너 관리${NC}"
    echo -e "${YELLOW}=======================================================${NC}"
    echo ""
    echo -e "1) ${GREEN}모든 서비스 시작${NC}"
    echo -e "2) ${RED}모든 서비스 중지${NC}"
    echo -e "3) ${BLUE}서비스 상태 확인${NC}"
    echo -e "4) ${YELLOW}로그 보기${NC}"
    echo -e "5) ${CYAN}이미지 빌드${NC}"
    echo -e "6) ${MAGENTA}볼륨 관리${NC}"
    echo -e "7) ${GREEN}돌아가기${NC}"
    echo ""
    echo -e "${YELLOW}선택하세요 (1-7):${NC}"
    
    read -p "> " docker_choice
    
    case $docker_choice in
        1)
            echo -e "${BLUE}모든 서비스를 시작합니다...${NC}"
            docker-compose up -d
            echo -e "${GREEN}✓ 서비스가 시작되었습니다.${NC}"
            read -p "계속하려면 Enter 키를 누르세요..." continue
            ;;
        2)
            echo -e "${YELLOW}모든 서비스를 중지합니다...${NC}"
            docker-compose down
            echo -e "${GREEN}✓ 서비스가 중지되었습니다.${NC}"
            read -p "계속하려면 Enter 키를 누르세요..." continue
            ;;
        3)
            echo -e "${BLUE}서비스 상태:${NC}"
            docker-compose ps
            read -p "계속하려면 Enter 키를 누르세요..." continue
            ;;
        4)
            echo -e "${BLUE}어떤 서비스의 로그를 보시겠습니까?${NC}"
            echo -e "1) 모든 서비스"
            echo -e "2) nasos-bot"
            echo -e "3) freqtrade"
            echo -e "4) postgres"
            echo -e "5) influxdb"
            echo -e "6) redis"
            echo -e "7) grafana"
            read -p "> " log_choice
            
            case $log_choice in
                1) docker-compose logs --tail=100 -f ;;
                2) docker-compose logs --tail=100 -f nasos-bot ;;
                3) docker-compose logs --tail=100 -f freqtrade ;;
                4) docker-compose logs --tail=100 -f postgres ;;
                5) docker-compose logs --tail=100 -f influxdb ;;
                6) docker-compose logs --tail=100 -f redis ;;
                7) docker-compose logs --tail=100 -f grafana ;;
                *) echo -e "${RED}잘못된 선택입니다.${NC}" ;;
            esac
            read -p "계속하려면 Enter 키를 누르세요..." continue
            ;;
        5)
            echo -e "${BLUE}Docker 이미지를 빌드합니다...${NC}"
            docker-compose build
            echo -e "${GREEN}✓ 이미지가 빌드되었습니다.${NC}"
            read -p "계속하려면 Enter 키를 누르세요..." continue
            ;;
        6)
            echo -e "${BLUE}Docker 볼륨:${NC}"
            docker volume ls | grep nasos
            echo ""
            echo -e "${YELLOW}볼륨을 정리하시겠습니까? (위험: 모든 데이터가 삭제됩니다) (y/n)${NC}"
            read -p "> " confirm
            if [ "$confirm" = "y" ]; then
                docker-compose down -v
                echo -e "${GREEN}✓ 볼륨이 정리되었습니다.${NC}"
            fi
            read -p "계속하려면 Enter 키를 누르세요..." continue
            ;;
        7)
            return
            ;;
        *)
            echo -e "${RED}잘못된 선택입니다.${NC}"
            read -p "계속하려면 Enter 키를 누르세요..." continue
            ;;
    esac
    
    docker_container_menu
}

# 시스템 상태 확인 함수
function check_system_status() {
    clear
    show_logo
    
    echo -e "${BLUE}${BOLD}시스템 상태 확인${NC}"
    echo -e "${YELLOW}=======================================================${NC}"
    echo ""
    
    # Docker 상태 확인
    echo -e "${BLUE}Docker 상태:${NC}"
    if docker info &>/dev/null; then
        echo -e "${GREEN}✓ Docker가 실행 중입니다.${NC}"
    else
        echo -e "${RED}✗ Docker가 실행 중이 아닙니다.${NC}"
    fi
    
    # 서비스 상태 확인
    if [ -f "docker-compose.yml" ]; then
        echo -e "\n${BLUE}서비스 상태:${NC}"
        docker-compose ps
    fi
    
    # 디스크 공간 확인
    echo -e "\n${BLUE}디스크 공간:${NC}"
    df -h | grep -E '(Filesystem|/$)'
    
    # 메모리 사용량 확인
    echo -e "\n${BLUE}메모리 사용량:${NC}"
    free -h
    
    # CPU 정보 확인
    echo -e "\n${BLUE}CPU 정보:${NC}"
    lscpu | grep -E '(Model name|CPU\(s\))'
    
    echo ""
    read -p "계속하려면 Enter 키를 누르세요..." continue
}

# 전략 관리 메뉴
function strategy_management_menu() {
    clear
    show_logo
    
    echo -e "${BLUE}${BOLD}전략 관리${NC}"
    echo -e "${YELLOW}=======================================================${NC}"
    echo ""
    echo -e "1) ${GREEN}현재 전략 보기${NC}"
    echo -e "2) ${BLUE}전략 파라미터 수정${NC}"
    echo -e "3) ${YELLOW}백테스트 실행${NC}"
    echo -e "4) ${CYAN}최적화 실행${NC}"
    echo -e "5) ${GREEN}돌아가기${NC}"
    echo ""
    echo -e "${YELLOW}선택하세요 (1-5):${NC}"
    
    read -p "> " strategy_choice
    
    case $strategy_choice in
        1)
            echo -e "${BLUE}현재 전략:${NC}"
            if [ -f "user_data/strategies/NASOSv5_mod3.py" ]; then
                echo -e "${GREEN}✓ NASOSv5_mod3 전략이 설치되어 있습니다.${NC}"
                echo ""
                echo -e "${YELLOW}전략 파일 내용:${NC}"
                head -n 30 user_data/strategies/NASOSv5_mod3.py
                echo -e "${YELLOW}... (생략) ...${NC}"
            else
                echo -e "${RED}✗ NASOSv5_mod3 전략 파일을 찾을 수 없습니다.${NC}"
            fi
            read -p "계속하려면 Enter 키를 누르세요..." continue
            ;;
        2)
            echo -e "${BLUE}전략 파라미터 수정:${NC}"
            echo -e "${YELLOW}아직 구현되지 않았습니다.${NC}"
            read -p "계속하려면 Enter 키를 누르세요..." continue
            ;;
        3)
            echo -e "${BLUE}백테스트 실행:${NC}"
            echo -e "${YELLOW}아직 구현되지 않았습니다.${NC}"
            read -p "계속하려면 Enter 키를 누르세요..." continue
            ;;
        4)
            echo -e "${BLUE}최적화 실행:${NC}"
            echo -e "${YELLOW}아직 구현되지 않았습니다.${NC}"
            read -p "계속하려면 Enter 키를 누르세요..." continue
            ;;
        5)
            return
            ;;
        *)
            echo -e "${RED}잘못된 선택입니다.${NC}"
            read -p "계속하려면 Enter 키를 누르세요..." continue
            ;;
    esac
    
    strategy_management_menu
}

# 메인 함수
function main() {
    # 로그 시작
    log "INFO" "NASOSv5_mod3 Bot 설정 스크립트 시작"
    
    # 환경 확인
    check_environment
    
    # 메인 루프
    while true; do
        show_main_menu
        read -p "> " choice
        
        case $choice in
            1)
                setup_new_environment
                ;;
            2)
                update_existing_config
                ;;
            3)
                backup_config
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            4)
                restore_config
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            5)
                docker_container_menu
                ;;
            6)
                check_system_status
                ;;
            7)
                strategy_management_menu
                ;;
            8)
                manage_security_settings
                ;;
            9)
                log "INFO" "NASOSv5_mod3 Bot 설정 스크립트 종료"
                echo -e "${GREEN}NASOSv5_mod3 Bot 설정 스크립트를 종료합니다.${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}잘못된 선택입니다. 다시 시도하세요.${NC}"
                sleep 2
                ;;
        esac
    done
}

# 보안 설정 관리 메뉴
function manage_security_settings() {
    local choice
    
    while true; do
        clear
        show_logo
        
        echo -e "${MAGENTA}${BOLD}보안 설정 관리 메뉴${NC}"
        echo -e "${YELLOW}=======================================================${NC}"
        echo ""
        echo -e "1) ${GREEN}Vault 서버 초기화${NC}"
        echo -e "2) ${BLUE}API 키 관리${NC}"
        echo -e "3) ${CYAN}데이터베이스 자격 증명 관리${NC}"
        echo -e "4) ${YELLOW}텔레그램 자격 증명 관리${NC}"
        echo -e "5) ${MAGENTA}보안 백업 생성${NC}"
        echo -e "6) ${BLUE}보안 백업 복원${NC}"
        echo -e "7) ${RED}메인 메뉴로 돌아가기${NC}"
        echo ""
        echo -e "${YELLOW}선택하세요 (1-7):${NC}"
        read -p "> " choice
        
        case $choice in
            1)
                initialize_vault_server
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            2)
                manage_api_keys
                ;;
            3)
                manage_database_credentials
                ;;
            4)
                manage_telegram_credentials
                ;;
            5)
                create_security_backup
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            6)
                restore_security_backup
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            7)
                return
                ;;
            *)
                echo -e "${RED}잘못된 선택입니다. 다시 시도하세요.${NC}"
                sleep 2
                ;;
        esac
    done
}

# Vault 서버 초기화 함수
function initialize_vault_server() {
    echo -e "${BLUE}Vault 서버 초기화 중...${NC}"
    
    # 보안 유틸리티 스크립트 소싱
    source "${SCRIPT_DIR}/scripts/security_utils.sh"
    
    # Vault 서버 실행 확인
    if ! check_vault_status; then
        echo -e "${YELLOW}Vault 서버를 시작합니다...${NC}"
        docker-compose up -d vault
        sleep 5
    fi
    
    # Vault 초기화
    initialize_vault
    
    # Vault 초기화 스크립트 실행
    echo -e "${YELLOW}Vault 정책 및 시크릿 엔진 설정 중...${NC}"
    bash "${SCRIPT_DIR}/config/vault/vault-init.sh"
    
    echo -e "${GREEN}Vault 서버가 성공적으로 초기화되었습니다.${NC}"
}

# API 키 관리 함수
function manage_api_keys() {
    local choice
    local exchange
    local api_key
    local api_secret
    
    while true; do
        clear
        show_logo
        
        echo -e "${BLUE}${BOLD}API 키 관리${NC}"
        echo -e "${YELLOW}=======================================================${NC}"
        echo ""
        echo -e "1) ${GREEN}API 키 추가/수정${NC}"
        echo -e "2) ${BLUE}API 키 조회${NC}"
        echo -e "3) ${RED}API 키 삭제${NC}"
        echo -e "4) ${MAGENTA}이전 메뉴로 돌아가기${NC}"
        echo ""
        echo -e "${YELLOW}선택하세요 (1-4):${NC}"
        read -p "> " choice
        
        case $choice in
            1)
                echo -e "${YELLOW}거래소 이름을 입력하세요 (예: binance):${NC}"
                read -p "> " exchange
                echo -e "${YELLOW}API 키를 입력하세요:${NC}"
                read -p "> " api_key
                echo -e "${YELLOW}API 시크릿을 입력하세요:${NC}"
                read -p "> " api_secret
                
                # 보안 유틸리티 스크립트 소싱
                source "${SCRIPT_DIR}/scripts/security_utils.sh"
                
                # API 키 저장
                store_api_credentials "$exchange" "$api_key" "$api_secret"
                
                echo -e "${GREEN}API 키가 성공적으로 저장되었습니다.${NC}"
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            2)
                echo -e "${YELLOW}거래소 이름을 입력하세요 (예: binance):${NC}"
                read -p "> " exchange
                
                # 보안 유틸리티 스크립트 소싱
                source "${SCRIPT_DIR}/scripts/security_utils.sh"
                
                # API 키 조회
                retrieve_api_credentials "$exchange"
                
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            3)
                echo -e "${YELLOW}거래소 이름을 입력하세요 (예: binance):${NC}"
                read -p "> " exchange
                
                # 보안 유틸리티 스크립트 소싱
                source "${SCRIPT_DIR}/scripts/security_utils.sh"
                
                # API 키 삭제
                delete_api_credentials "$exchange"
                
                echo -e "${GREEN}API 키가 성공적으로 삭제되었습니다.${NC}"
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            4)
                return
                ;;
            *)
                echo -e "${RED}잘못된 선택입니다. 다시 시도하세요.${NC}"
                sleep 2
                ;;
        esac
    done
}

# 데이터베이스 자격 증명 관리 함수
function manage_database_credentials() {
    local choice
    local db_type
    local db_host
    local db_port
    local db_name
    local db_user
    local db_password
    
    while true; do
        clear
        show_logo
        
        echo -e "${BLUE}${BOLD}데이터베이스 자격 증명 관리${NC}"
        echo -e "${YELLOW}=======================================================${NC}"
        echo ""
        echo -e "1) ${GREEN}데이터베이스 자격 증명 추가/수정${NC}"
        echo -e "2) ${BLUE}데이터베이스 자격 증명 조회${NC}"
        echo -e "3) ${RED}데이터베이스 자격 증명 삭제${NC}"
        echo -e "4) ${MAGENTA}이전 메뉴로 돌아가기${NC}"
        echo ""
        echo -e "${YELLOW}선택하세요 (1-4):${NC}"
        read -p "> " choice
        
        case $choice in
            1)
                echo -e "${YELLOW}데이터베이스 유형을 입력하세요 (예: postgresql, influxdb):${NC}"
                read -p "> " db_type
                echo -e "${YELLOW}데이터베이스 호스트를 입력하세요:${NC}"
                read -p "> " db_host
                echo -e "${YELLOW}데이터베이스 포트를 입력하세요:${NC}"
                read -p "> " db_port
                echo -e "${YELLOW}데이터베이스 이름을 입력하세요:${NC}"
                read -p "> " db_name
                echo -e "${YELLOW}데이터베이스 사용자를 입력하세요:${NC}"
                read -p "> " db_user
                echo -e "${YELLOW}데이터베이스 비밀번호를 입력하세요:${NC}"
                read -p "> " db_password
                
                # 보안 유틸리티 스크립트 소싱
                source "${SCRIPT_DIR}/scripts/security_utils.sh"
                
                # 데이터베이스 자격 증명 저장
                store_database_credentials "$db_type" "$db_host" "$db_port" "$db_name" "$db_user" "$db_password"
                
                echo -e "${GREEN}데이터베이스 자격 증명이 성공적으로 저장되었습니다.${NC}"
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            2)
                echo -e "${YELLOW}데이터베이스 유형을 입력하세요 (예: postgresql, influxdb):${NC}"
                read -p "> " db_type
                
                # 보안 유틸리티 스크립트 소싱
                source "${SCRIPT_DIR}/scripts/security_utils.sh"
                
                # 데이터베이스 자격 증명 조회
                retrieve_database_credentials "$db_type"
                
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            3)
                echo -e "${YELLOW}데이터베이스 유형을 입력하세요 (예: postgresql, influxdb):${NC}"
                read -p "> " db_type
                
                # 보안 유틸리티 스크립트 소싱
                source "${SCRIPT_DIR}/scripts/security_utils.sh"
                
                # 데이터베이스 자격 증명 삭제
                delete_database_credentials "$db_type"
                
                echo -e "${GREEN}데이터베이스 자격 증명이 성공적으로 삭제되었습니다.${NC}"
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            4)
                return
                ;;
            *)
                echo -e "${RED}잘못된 선택입니다. 다시 시도하세요.${NC}"
                sleep 2
                ;;
        esac
    done
}

# 텔레그램 자격 증명 관리 함수
function manage_telegram_credentials() {
    local choice
    local token
    local chat_id
    
    while true; do
        clear
        show_logo
        
        echo -e "${BLUE}${BOLD}텔레그램 자격 증명 관리${NC}"
        echo -e "${YELLOW}=======================================================${NC}"
        echo ""
        echo -e "1) ${GREEN}텔레그램 자격 증명 추가/수정${NC}"
        echo -e "2) ${BLUE}텔레그램 자격 증명 조회${NC}"
        echo -e "3) ${RED}텔레그램 자격 증명 삭제${NC}"
        echo -e "4) ${MAGENTA}이전 메뉴로 돌아가기${NC}"
        echo ""
        echo -e "${YELLOW}선택하세요 (1-4):${NC}"
        read -p "> " choice
        
        case $choice in
            1)
                echo -e "${YELLOW}텔레그램 봇 토큰을 입력하세요:${NC}"
                read -p "> " token
                echo -e "${YELLOW}텔레그램 채팅 ID를 입력하세요:${NC}"
                read -p "> " chat_id
                
                # 보안 유틸리티 스크립트 소싱
                source "${SCRIPT_DIR}/scripts/security_utils.sh"
                
                # 텔레그램 자격 증명 저장
                store_telegram_credentials "$token" "$chat_id"
                
                echo -e "${GREEN}텔레그램 자격 증명이 성공적으로 저장되었습니다.${NC}"
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            2)
                # 보안 유틸리티 스크립트 소싱
                source "${SCRIPT_DIR}/scripts/security_utils.sh"
                
                # 텔레그램 자격 증명 조회
                retrieve_telegram_credentials
                
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            3)
                # 보안 유틸리티 스크립트 소싱
                source "${SCRIPT_DIR}/scripts/security_utils.sh"
                
                # 텔레그램 자격 증명 삭제
                delete_telegram_credentials
                
                echo -e "${GREEN}텔레그램 자격 증명이 성공적으로 삭제되었습니다.${NC}"
                read -p "계속하려면 Enter 키를 누르세요..." continue
                ;;
            4)
                return
                ;;
            *)
                echo -e "${RED}잘못된 선택입니다. 다시 시도하세요.${NC}"
                sleep 2
                ;;
        esac
    done
}

# 보안 백업 생성 함수
function create_security_backup() {
    echo -e "${BLUE}보안 백업 생성 중...${NC}"
    
    # 보안 유틸리티 스크립트 소싱
    source "${SCRIPT_DIR}/scripts/security_utils.sh"
    
    # 백업 디렉토리 생성
    local backup_dir="${SCRIPT_DIR}/backups/security"
    mkdir -p "$backup_dir"
    
    # 백업 파일 이름 생성
    local backup_file="${backup_dir}/security_backup_$(date +%Y%m%d_%H%M%S).json"
    
    # Vault 백업 생성
    backup_vault "$backup_file"
    
    echo -e "${GREEN}보안 백업이 성공적으로 생성되었습니다: ${backup_file}${NC}"
}

# 보안 백업 복원 함수
function restore_security_backup() {
    echo -e "${BLUE}보안 백업 복원 중...${NC}"
    
    # 보안 유틸리티 스크립트 소싱
    source "${SCRIPT_DIR}/scripts/security_utils.sh"
    
    # 백업 디렉토리 확인
    local backup_dir="${SCRIPT_DIR}/backups/security"
    if [ ! -d "$backup_dir" ]; then
        echo -e "${RED}백업 디렉토리가 존재하지 않습니다: ${backup_dir}${NC}"
        return 1
    fi
    
    # 백업 파일 목록 표시
    echo -e "${YELLOW}사용 가능한 백업 파일:${NC}"
    local i=1
    local backup_files=("$backup_dir"/*.json)
    
    if [ ${#backup_files[@]} -eq 0 ]; then
        echo -e "${RED}백업 파일이 없습니다.${NC}"
        return 1
    fi
    
    for file in "${backup_files[@]}"; do
        echo -e "$i) $(basename "$file")"
        i=$((i+1))
    done
    
    # 백업 파일 선택
    echo -e "${YELLOW}복원할 백업 파일 번호를 선택하세요:${NC}"
    read -p "> " choice
    
    if [ -z "$choice" ] || ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt ${#backup_files[@]} ]; then
        echo -e "${RED}잘못된 선택입니다.${NC}"
        return 1
    fi
    
    local selected_file="${backup_files[$((choice-1))]}"
    
    # 백업 복원 확인
    echo -e "${YELLOW}다음 백업 파일을 복원합니다: $(basename "$selected_file")${NC}"
    echo -e "${RED}경고: 이 작업은 현재 저장된 모든 보안 정보를 덮어씁니다.${NC}"
    echo -e "${YELLOW}계속하시겠습니까? (y/n)${NC}"
    read -p "> " confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo -e "${YELLOW}백업 복원이 취소되었습니다.${NC}"
        return 0
    fi
    
    # Vault 백업 복원
    restore_vault "$selected_file"
    
    echo -e "${GREEN}보안 백업이 성공적으로 복원되었습니다.${NC}"
}

# 스크립트 실행
main