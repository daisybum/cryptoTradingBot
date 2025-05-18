#!/bin/bash
# 로컬 테스트 환경 설정 스크립트

# 프로젝트 루트 디렉토리
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "프로젝트 루트: $PROJECT_ROOT"

# 환경 변수 설정
export LOCAL_TEST=true
export DOCKER_ENV=false

# InfluxDB 설정
export INFLUXDB_URL=http://localhost:8086
export INFLUXDB_TOKEN=my-token
export INFLUXDB_ORG=nasos_org
export INFLUXDB_BUCKET=market_data

# Vault 설정
export VAULT_ADDR=http://localhost:8202
export VAULT_TOKEN=root

# Binance API 설정 (테스트용 더미 값)
export BINANCE_API_KEY=dummy_api_key
export BINANCE_API_SECRET=dummy_api_secret

# 환경 변수 출력
echo "환경 변수 설정 완료:"
echo "LOCAL_TEST: $LOCAL_TEST"
echo "DOCKER_ENV: $DOCKER_ENV"
echo "INFLUXDB_URL: $INFLUXDB_URL"
echo "INFLUXDB_ORG: $INFLUXDB_ORG"
echo "INFLUXDB_BUCKET: $INFLUXDB_BUCKET"
echo "VAULT_ADDR: $VAULT_ADDR"

echo "환경 변수 설정이 완료되었습니다. 이제 데이터 수집 서비스를 실행할 수 있습니다."
echo "사용 방법: source scripts/setup_local_env.sh"
