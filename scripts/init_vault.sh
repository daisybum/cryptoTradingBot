#!/bin/bash
# Vault 초기화 스크립트
# 이 스크립트는 Vault 서비스를 초기화하고 필요한 시크릿을 설정합니다.

set -e

# 환경 변수 설정
VAULT_ADDR=${VAULT_ADDR:-"http://localhost:8202"}
VAULT_TOKEN=${VAULT_TOKEN:-"root"}
VAULT_MOUNT_POINT=${VAULT_MOUNT_POINT:-"kv"}
VAULT_PATH_PREFIX=${VAULT_PATH_PREFIX:-"nasos"}

echo "Vault 초기화 시작 (${VAULT_ADDR})"

# Vault 상태 확인
echo "Vault 상태 확인 중..."
vault_status=$(curl -s -o /dev/null -w "%{http_code}" ${VAULT_ADDR}/v1/sys/health || echo "000")

if [ "$vault_status" = "000" ]; then
  echo "Vault 서비스에 연결할 수 없습니다. 서비스가 실행 중인지 확인하세요."
  exit 1
fi

# Vault 인증
echo "Vault 인증 중..."
export VAULT_ADDR
export VAULT_TOKEN

# Python 스크립트 실행
echo "Vault 초기화 스크립트 실행 중..."
python3 /home/shpark/workspace/altTradingBot/scripts/init_vault.py

echo "Vault 초기화 완료"
