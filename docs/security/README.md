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

### 3. 비밀 자동 교체 메커니즘

시스템은 비밀 정보를 주기적으로 자동 교체하는 메커니즘을 제공합니다.

#### 주요 기능:
- 데이터베이스 비밀번호 자동 교체
- JWT 시크릿 자동 교체
- API 키 교체 알림
- 이전 비밀 백업 및 롤백 지원

#### 설정 방법:
1. `scripts/rotate_secrets.sh` 스크립트를 사용하여 비밀을 교체합니다.
2. 크론 작업을 설정하여 주기적으로 비밀을 교체합니다.

#### 사용 방법:
```bash
# 모든 비밀 교체
./scripts/rotate_secrets.sh --all

# 데이터베이스 비밀번호만 교체
./scripts/rotate_secrets.sh --db

# JWT 시크릿만 교체
./scripts/rotate_secrets.sh --jwt

# API 키 교체 필요성 검토
./scripts/rotate_secrets.sh --api
```

### 4. SSL/TLS 설정

시스템은 모든 서비스에 대해 SSL/TLS를 설정하여 안전한 통신을 보장합니다.

#### 주요 기능:
- 자체 서명 인증서 생성 (개발 환경용)
- Cloudflare를 통한 SSL/TLS 관리 (프로덕션 환경용)
- Nginx 프록시를 통한 HTTPS 지원

#### 설정 방법:
1. `scripts/setup_ssl.sh` 스크립트를 사용하여 SSL/TLS를 설정합니다.
2. 개발 환경에서는 자체 서명 인증서를 사용합니다.
3. 프로덕션 환경에서는 Cloudflare를 통해 SSL/TLS를 관리합니다.

#### 사용 방법:
```bash
# SSL/TLS 설정
./scripts/setup_ssl.sh
```

## 보안 모범 사례

1. **API 키 관리**
   - 모든 API 키는 Vault에 저장합니다.
   - API 키를 코드나 설정 파일에 직접 포함하지 않습니다.
   - 주기적으로 API 키를 교체합니다.

2. **네트워크 보안**
   - 내부 서비스는 외부에 노출하지 않습니다.
   - 필요한 포트만 개방합니다.
   - Cloudflare를 통해 모든 외부 트래픽을 라우팅합니다.
   - 모든 통신은 HTTPS를 통해 이루어집니다.

3. **인증 및 권한 부여**
   - 최소 권한 원칙을 따릅니다.
   - 각 서비스에 대해 별도의 인증 정보를 사용합니다.
   - API 엔드포인트에 적절한 인증을 적용합니다.
   - JWT를 사용하여 API 인증을 구현합니다.

4. **비밀 교체**
   - 모든 비밀은 주기적으로 교체합니다.
   - 비밀 교체 프로세스를 자동화합니다.
   - 이전 비밀을 백업하여 롤백이 가능하도록 합니다.
   - 비밀 교체 일정을 문서화하고 모니터링합니다.

5. **모니터링 및 감사**
   - 모든 보안 이벤트를 로깅합니다.
   - 정기적으로 감사 로그를 검토합니다.
   - 비정상적인 활동에 대한 경고를 설정합니다.
   - 보안 테스트를 정기적으로 실행합니다.

## 보안 테스트

보안 설정을 테스트하려면 다음 스크립트를 실행하세요:

```bash
./scripts/security_test.sh
```

이 스크립트는 다음을 테스트합니다:
- Vault 연결 및 인증
- SSL 인증서 존재 여부
- Cloudflare 설정
- 비밀 교체 메커니즘

## 보안 유틸리티

시스템은 다음과 같은 보안 유틸리티 스크립트를 제공합니다:

1. **security_utils.sh**: Vault를 사용하여 비밀을 관리하는 유틸리티 함수를 제공합니다.
2. **setup_security.sh**: 보안 서비스를 설정합니다.
3. **rotate_secrets.sh**: 비밀을 자동으로 교체합니다.
4. **setup_ssl.sh**: SSL/TLS를 설정합니다.
5. **security_test.sh**: 보안 설정을 테스트합니다.

## 문제 해결

### Vault 관련 문제
- Vault 서버에 연결할 수 없는 경우: `docker-compose ps`로 Vault 컨테이너가 실행 중인지 확인합니다.
- 인증 실패: `.env` 파일에 올바른 `VAULT_TOKEN` 또는 `VAULT_ROLE_ID`와 `VAULT_SECRET_ID`가 설정되어 있는지 확인합니다.
- 비밀 교체 실패: `scripts/rotate_secrets.sh`의 로그를 확인하고 Vault 상태를 점검합니다.

### Cloudflare 관련 문제
- SSL 인증서가 발급되지 않는 경우: Cloudflare API 토큰과 영역 ID가 올바른지 확인합니다.
- DNS 레코드가 생성되지 않는 경우: 컨테이너 레이블이 올바르게 설정되어 있는지 확인합니다.
- Cloudflare Companion이 작동하지 않는 경우: 로그를 확인하고 환경 변수가 올바르게 설정되어 있는지 확인합니다.

### SSL/TLS 관련 문제
- 인증서 오류: 인증서가 올바르게 생성되었는지 확인합니다.
- HTTPS 연결 실패: Nginx 설정을 확인하고 인증서 경로가 올바른지 확인합니다.
- 인증서 만료: 인증서 갱신 프로세스가 설정되어 있는지 확인합니다.
