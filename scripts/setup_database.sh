#!/bin/bash

# 스크립트 실행 디렉토리 설정
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 로그 출력 함수
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# 에러 처리 함수
error_exit() {
    log "오류: $1"
    exit 1
}

# 환경 변수 로드
if [ -f "$PROJECT_ROOT/.env" ]; then
    log "환경 변수 파일 로드 중..."
    source "$PROJECT_ROOT/.env"
else
    log "환경 변수 파일이 없습니다. 기본값을 사용합니다."
fi

# 데이터베이스 연결 정보
DB_HOST=${POSTGRES_HOST:-"postgres"}
DB_PORT=${POSTGRES_PORT:-"5432"}
DB_NAME=${POSTGRES_DB:-"crpytodb"}
DB_USER=${POSTGRES_USER:-"hirvahapjh1"}
DB_PASSWORD=${POSTGRES_PASSWORD:-""}

# 데이터베이스 존재 여부 확인
log "데이터베이스 존재 여부 확인 중..."
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    log "데이터베이스 '$DB_NAME'이(가) 이미 존재합니다."
else
    log "데이터베이스 '$DB_NAME'을(를) 생성합니다..."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE $DB_NAME WITH OWNER = $DB_USER ENCODING = 'UTF8' CONNECTION LIMIT = -1;" || error_exit "데이터베이스 생성 실패"
    log "데이터베이스가 성공적으로 생성되었습니다."
fi

# Alembic 마이그레이션 실행
log "데이터베이스 마이그레이션 실행 중..."
cd "$PROJECT_ROOT/migrations" || error_exit "마이그레이션 디렉토리로 이동 실패"
alembic upgrade head || error_exit "마이그레이션 실패"
log "데이터베이스 마이그레이션이 성공적으로 완료되었습니다."

# 인덱스 생성 및 최적화
log "데이터베이스 인덱스 생성 및 최적화 중..."
python -m src.database.init_db --optimize || error_exit "인덱스 생성 실패"
log "인덱스가 성공적으로 생성되었습니다."

# 데이터 보존 정책 설정
log "데이터 보존 정책 설정 중..."
python -m src.database.init_db --retention || error_exit "데이터 보존 정책 설정 실패"
log "데이터 보존 정책이 성공적으로 설정되었습니다."

# InfluxDB 설정 (이미 init_db에 포함되어 있음)
log "InfluxDB 설정 확인 중..."

# 완료 메시지
log "데이터베이스 설정이 완료되었습니다."
log "이제 다음 명령으로 데이터베이스 백업을 실행할 수 있습니다:"
log "  python -m src.database.init_db --backup"
log "데이터베이스 복원 방법:"
log "  python -m src.database.init_db --restore --pg-backup-file=<백업파일경로> --influx-backup-dir=<백업디렉토리경로>"
