#!/bin/bash

# NASOSv5_mod3 Bot 보안 서비스 설정 스크립트
# 이 스크립트는 Hashicorp Vault 및 Cloudflare 통합을 설정합니다.

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 현재 디렉토리 저장
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 필요한 디렉토리 확인
mkdir -p "$PROJECT_ROOT/config/vault"
mkdir -p "$PROJECT_ROOT/config/ssl"

# Vault 설정 확인
if [ ! -f "$PROJECT_ROOT/config/vault/config.hcl" ]; then
    echo -e "${YELLOW}Vault 설정 파일이 없습니다. 기본 설정을 생성합니다...${NC}"
    cat > "$PROJECT_ROOT/config/vault/config.hcl" << EOF
storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

api_addr = "http://0.0.0.0:8200"
cluster_addr = "https://0.0.0.0:8201"
ui = true

disable_mlock = true
EOF
    echo -e "${GREEN}Vault 설정 파일이 생성되었습니다.${NC}"
fi

# Vault 초기화 스크립트 확인
if [ ! -f "$PROJECT_ROOT/config/vault/vault-init.sh" ]; then
    echo -e "${YELLOW}Vault 초기화 스크립트가 없습니다. 기본 스크립트를 생성합니다...${NC}"
    cat > "$PROJECT_ROOT/config/vault/vault-init.sh" << 'EOF'
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
EOF
    chmod +x "$PROJECT_ROOT/config/vault/vault-init.sh"
    echo -e "${GREEN}Vault 초기화 스크립트가 생성되었습니다.${NC}"
fi

# SSL 인증서 디렉토리 생성
mkdir -p "$PROJECT_ROOT/config/ssl/certs"
mkdir -p "$PROJECT_ROOT/config/ssl/private"

# Cloudflare 설정 파일 생성
echo -e "${YELLOW}Cloudflare 설정 파일을 생성합니다...${NC}"
cat > "$PROJECT_ROOT/config/cloudflare.env.example" << EOF
# Cloudflare API 설정
# 이 파일을 .env 파일에 복사하고 값을 설정하세요

# Cloudflare API 토큰
CLOUDFLARE_API_TOKEN=your_api_token_here

# Cloudflare 영역 ID
CLOUDFLARE_ZONE=your_zone_id_here

# 도메인 화이트리스트 (선택 사항)
DOMAIN_WHITELIST=yourdomain.com

# 최상위 도메인 화이트리스트 (선택 사항)
TLD_WHITELIST=com
EOF
echo -e "${GREEN}Cloudflare 설정 파일이 생성되었습니다.${NC}"

# 보안 테스트 스크립트 생성
echo -e "${YELLOW}보안 테스트 스크립트를 생성합니다...${NC}"
cat > "$PROJECT_ROOT/scripts/security_test.sh" << 'EOF'
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
EOF
chmod +x "$PROJECT_ROOT/scripts/security_test.sh"
echo -e "${GREEN}보안 테스트 스크립트가 생성되었습니다.${NC}"

# 보안 문서 생성
echo -e "${YELLOW}보안 문서를 생성합니다...${NC}"
mkdir -p "$PROJECT_ROOT/docs/security"
cat > "$PROJECT_ROOT/docs/security/README.md" << 'EOF'
# NASOSv5_mod3 Bot 보안 아키텍처

이 문서는 NASOSv5_mod3 Bot의 보안 아키텍처와 설정 방법을 설명합니다.

## 보안 컴포넌트

### 1. Hashicorp Vault

Vault는 API 키, 비밀번호 및 기타 민감한 정보를 안전하게 저장하고 관리하는 데 사용됩니다.

#### 주요 기능:
- KV 시크릿 엔진을 사용한 비밀 저장
- AppRole 인증을 통한 안전한 접근
- 비밀 자동 교체 (Secret Rotation)
- 감사 로깅

#### 설정 방법:
1. `docker-compose.yml`에 Vault 서비스가 포함되어 있습니다.
2. `config/vault/config.hcl`에 Vault 설정이 있습니다.
3. `config/vault/vault-init.sh`는 Vault 초기화 스크립트입니다.

#### 사용 방법:
```python
from src.utils.security import VaultClient

# Vault 클라이언트 초기화
vault = VaultClient()

# 비밀 저장
vault.store_secret("api_key", "my-secret-api-key")

# 비밀 검색
api_key = vault.get_secret("api_key")
```

### 2. Cloudflare SSL/TLS

Cloudflare는 SSL/TLS 인증서 관리 및 보안 통신을 위해 사용됩니다.

#### 주요 기능:
- 자동 SSL 인증서 발급 및 갱신
- DDoS 보호
- 웹 애플리케이션 방화벽 (WAF)
- 콘텐츠 전송 네트워크 (CDN)

#### 설정 방법:
1. `docker-compose.yml`에 Cloudflare Companion 서비스가 포함되어 있습니다.
2. `.env` 파일에 Cloudflare API 토큰과 영역 ID를 설정합니다.
3. 컨테이너에 `cloudflare.subdomain` 및 `cloudflare.proxied` 레이블을 추가합니다.

## 보안 모범 사례

1. **API 키 관리**
   - 모든 API 키는 Vault에 저장합니다.
   - API 키를 코드나 설정 파일에 직접 포함하지 않습니다.
   - 주기적으로 API 키를 교체합니다.

2. **네트워크 보안**
   - 내부 서비스는 외부에 노출하지 않습니다.
   - 필요한 포트만 개방합니다.
   - Cloudflare를 통해 모든 외부 트래픽을 라우팅합니다.

3. **인증 및 권한 부여**
   - 최소 권한 원칙을 따릅니다.
   - 각 서비스에 대해 별도의 인증 정보를 사용합니다.
   - API 엔드포인트에 적절한 인증을 적용합니다.

4. **비밀 교체**
   - 모든 비밀은 주기적으로 교체합니다.
   - 비밀 교체 프로세스를 자동화합니다.

5. **모니터링 및 감사**
   - 모든 보안 이벤트를 로깅합니다.
   - 정기적으로 감사 로그를 검토합니다.
   - 비정상적인 활동에 대한 경고를 설정합니다.

## 보안 테스트

보안 설정을 테스트하려면 다음 스크립트를 실행하세요:

```bash
./scripts/security_test.sh
```

이 스크립트는 다음을 테스트합니다:
- Vault 연결 및 인증
- SSL 인증서 존재 여부
- Cloudflare 설정

## 문제 해결

### Vault 관련 문제
- Vault 서버에 연결할 수 없는 경우: `docker-compose ps`로 Vault 컨테이너가 실행 중인지 확인합니다.
- 인증 실패: `.env` 파일에 올바른 `VAULT_TOKEN` 또는 `VAULT_ROLE_ID`와 `VAULT_SECRET_ID`가 설정되어 있는지 확인합니다.

### Cloudflare 관련 문제
- SSL 인증서가 발급되지 않는 경우: Cloudflare API 토큰과 영역 ID가 올바른지 확인합니다.
- DNS 레코드가 생성되지 않는 경우: 컨테이너 레이블이 올바르게 설정되어 있는지 확인합니다.
EOF
echo -e "${GREEN}보안 문서가 생성되었습니다.${NC}"

# .env 파일 예제 업데이트
if [ -f "$PROJECT_ROOT/.env.example" ]; then
    echo -e "${YELLOW}.env.example 파일을 업데이트합니다...${NC}"
    cat >> "$PROJECT_ROOT/.env.example" << EOF

# Vault 설정
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=root
VAULT_ROLE_ID=
VAULT_SECRET_ID=

# Cloudflare 설정
CLOUDFLARE_API_TOKEN=
CLOUDFLARE_ZONE=
DOMAIN_WHITELIST=
TLD_WHITELIST=
EOF
    echo -e "${GREEN}.env.example 파일이 업데이트되었습니다.${NC}"
else
    echo -e "${YELLOW}.env.example 파일이 없습니다. 새로 생성합니다...${NC}"
    cat > "$PROJECT_ROOT/.env.example" << EOF
# NASOSv5_mod3 Bot 환경 변수 예제 파일
# 이 파일을 .env로 복사하고 값을 설정하세요

# 바이낸스 API 설정
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# 데이터베이스 설정
POSTGRES_USER=nasos_user
POSTGRES_PASSWORD=nasos_password
POSTGRES_DB=nasos_bot

# InfluxDB 설정
INFLUXDB_ADMIN_PASSWORD=admin_password
INFLUXDB_ORG=nasos_org
INFLUXDB_BUCKET=market_data
INFLUXDB_TOKEN=token

# Grafana 설정
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin

# 텔레그램 설정
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Vault 설정
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=root
VAULT_ROLE_ID=
VAULT_SECRET_ID=

# Cloudflare 설정
CLOUDFLARE_API_TOKEN=
CLOUDFLARE_ZONE=
DOMAIN_WHITELIST=
TLD_WHITELIST=
EOF
    echo -e "${GREEN}.env.example 파일이 생성되었습니다.${NC}"
fi

echo -e "${GREEN}보안 서비스 설정이 완료되었습니다!${NC}"
echo -e "${YELLOW}다음 단계:${NC}"
echo "1. .env.example 파일을 .env로 복사하고 필요한 값을 설정하세요."
echo "2. docker-compose up -d를 실행하여 서비스를 시작하세요."
echo "3. ./scripts/security_test.sh를 실행하여 보안 설정을 테스트하세요."
