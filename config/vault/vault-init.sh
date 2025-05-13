#!/bin/bash

# Vault 초기화 스크립트
# 이 스크립트는 Vault 서버가 시작될 때 자동으로 실행되어 초기 설정을 수행합니다.

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Vault 서버 초기화 중...${NC}"

# Vault가 준비될 때까지 대기
until vault status > /dev/null 2>&1; do
    echo "Vault 서버 시작 대기 중..."
    sleep 1
done

# KV 시크릿 엔진 활성화
if ! vault secrets list | grep -q "kv/"; then
    echo -e "${YELLOW}KV 시크릿 엔진 활성화 중...${NC}"
    vault secrets enable -version=2 -path=kv kv
    echo -e "${GREEN}KV 시크릿 엔진이 활성화되었습니다.${NC}"
fi

# 정책 생성
echo -e "${YELLOW}정책 생성 중...${NC}"
cat > /tmp/nasos-policy.hcl << EOF
path "kv/data/nasos/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "kv/metadata/nasos/*" {
  capabilities = ["list"]
}
EOF

vault policy write nasos-policy /tmp/nasos-policy.hcl
rm /tmp/nasos-policy.hcl

echo -e "${GREEN}nasos-policy 정책이 생성되었습니다.${NC}"

# 앱롤 인증 활성화
if ! vault auth list | grep -q "approle/"; then
    echo -e "${YELLOW}AppRole 인증 활성화 중...${NC}"
    vault auth enable approle
    echo -e "${GREEN}AppRole 인증이 활성화되었습니다.${NC}"
fi

# 앱롤 생성
echo -e "${YELLOW}NASOSv5_mod3 Bot용 AppRole 생성 중...${NC}"
vault write auth/approle/role/nasos-role \
    token_ttl=1h \
    token_max_ttl=24h \
    token_policies=nasos-policy

# 롤 ID 및 시크릿 ID 가져오기
ROLE_ID=$(vault read -format=json auth/approle/role/nasos-role/role-id | jq -r '.data.role_id')
SECRET_ID=$(vault write -format=json -f auth/approle/role/nasos-role/secret-id | jq -r '.data.secret_id')

# 롤 ID 및 시크릿 ID 저장
echo -e "${YELLOW}인증 정보 저장 중...${NC}"
echo "VAULT_ROLE_ID=$ROLE_ID" > /vault/config/credentials.env
echo "VAULT_SECRET_ID=$SECRET_ID" >> /vault/config/credentials.env
chmod 600 /vault/config/credentials.env

echo -e "${GREEN}Vault 초기화가 완료되었습니다!${NC}"
echo -e "${YELLOW}인증 정보는 /vault/config/credentials.env 파일에 저장되었습니다.${NC}"
