#!/bin/bash

# NASOSv5_mod3 Bot SSL/TLS 설정 스크립트
# 이 스크립트는 SSL/TLS 인증서를 생성하고 설정합니다.

# 현재 디렉토리 저장
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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

# 필요한 디렉토리 생성
create_directories() {
    log "${BLUE}SSL/TLS 디렉토리 생성 중...${NC}"
    
    mkdir -p "$PROJECT_ROOT/config/ssl/certs"
    mkdir -p "$PROJECT_ROOT/config/ssl/private"
    
    log "${GREEN}SSL/TLS 디렉토리가 생성되었습니다.${NC}"
}

# 자체 서명 인증서 생성 (개발 환경용)
generate_self_signed_cert() {
    log "${BLUE}자체 서명 인증서 생성 중...${NC}"
    
    # 이미 인증서가 있는지 확인
    if [ -f "$PROJECT_ROOT/config/ssl/certs/server.crt" ] && [ -f "$PROJECT_ROOT/config/ssl/private/server.key" ]; then
        log "${YELLOW}인증서가 이미 존재합니다. 재생성하려면 기존 인증서를 삭제하세요.${NC}"
        return 0
    fi
    
    # 개인 키 생성
    openssl genrsa -out "$PROJECT_ROOT/config/ssl/private/server.key" 2048
    
    # CSR 생성
    openssl req -new -key "$PROJECT_ROOT/config/ssl/private/server.key" \
        -out "$PROJECT_ROOT/config/ssl/certs/server.csr" \
        -subj "/C=KR/ST=Seoul/L=Seoul/O=NASOSv5_mod3/OU=Development/CN=localhost"
    
    # 자체 서명 인증서 생성
    openssl x509 -req -days 365 -in "$PROJECT_ROOT/config/ssl/certs/server.csr" \
        -signkey "$PROJECT_ROOT/config/ssl/private/server.key" \
        -out "$PROJECT_ROOT/config/ssl/certs/server.crt"
    
    # CSR 파일 삭제
    rm "$PROJECT_ROOT/config/ssl/certs/server.csr"
    
    # 권한 설정
    chmod 600 "$PROJECT_ROOT/config/ssl/private/server.key"
    chmod 644 "$PROJECT_ROOT/config/ssl/certs/server.crt"
    
    log "${GREEN}자체 서명 인증서가 생성되었습니다.${NC}"
}

# Cloudflare 설정 확인
check_cloudflare_config() {
    log "${BLUE}Cloudflare 설정 확인 중...${NC}"
    
    # Cloudflare 환경 변수 파일 확인
    if [ ! -f "$PROJECT_ROOT/config/cloudflare.env" ]; then
        if [ -f "$PROJECT_ROOT/config/cloudflare.env.example" ]; then
            log "${YELLOW}Cloudflare 환경 변수 파일이 없습니다. 예제 파일을 복사합니다...${NC}"
            cp "$PROJECT_ROOT/config/cloudflare.env.example" "$PROJECT_ROOT/config/cloudflare.env"
            log "${YELLOW}$PROJECT_ROOT/config/cloudflare.env 파일을 편집하여 API 토큰과 영역 ID를 설정하세요.${NC}"
        else
            log "${RED}Cloudflare 환경 변수 예제 파일이 없습니다.${NC}"
            return 1
        fi
    fi
    
    # Cloudflare API 토큰 및 영역 ID 확인
    if [ -f "$PROJECT_ROOT/config/cloudflare.env" ]; then
        source "$PROJECT_ROOT/config/cloudflare.env"
        
        if [ -z "$CLOUDFLARE_API_TOKEN" ] || [ "$CLOUDFLARE_API_TOKEN" = "your_api_token_here" ]; then
            log "${YELLOW}Cloudflare API 토큰이 설정되지 않았습니다.${NC}"
            log "${YELLOW}$PROJECT_ROOT/config/cloudflare.env 파일을 편집하여 API 토큰을 설정하세요.${NC}"
        else
            log "${GREEN}Cloudflare API 토큰이 설정되었습니다.${NC}"
        fi
        
        if [ -z "$CLOUDFLARE_ZONE" ] || [ "$CLOUDFLARE_ZONE" = "your_zone_id_here" ]; then
            log "${YELLOW}Cloudflare 영역 ID가 설정되지 않았습니다.${NC}"
            log "${YELLOW}$PROJECT_ROOT/config/cloudflare.env 파일을 편집하여 영역 ID를 설정하세요.${NC}"
        else
            log "${GREEN}Cloudflare 영역 ID가 설정되었습니다.${NC}"
        fi
    fi
    
    log "${GREEN}Cloudflare 설정 확인 완료${NC}"
}

# Docker Compose 파일에 SSL 설정 추가
update_docker_compose() {
    log "${BLUE}Docker Compose 파일 업데이트 중...${NC}"
    
    # Docker Compose 파일 확인
    if [ ! -f "$PROJECT_ROOT/docker-compose.yml" ]; then
        log "${RED}Docker Compose 파일이 없습니다.${NC}"
        return 1
    fi
    
    # 이미 SSL 설정이 있는지 확인
    if grep -q "443:443" "$PROJECT_ROOT/docker-compose.yml"; then
        log "${YELLOW}Docker Compose 파일에 이미 SSL 설정이 있습니다.${NC}"
    else
        log "${YELLOW}Docker Compose 파일에 SSL 설정을 추가해야 합니다.${NC}"
        log "${YELLOW}다음 설정을 api-server 서비스에 추가하세요:${NC}"
        echo "ports:"
        echo "  - \"443:443\""
        echo "volumes:"
        echo "  - ./config/ssl:/app/ssl"
    fi
    
    log "${GREEN}Docker Compose 파일 업데이트 완료${NC}"
}

# Nginx 설정 생성 (프록시 서버용)
generate_nginx_config() {
    log "${BLUE}Nginx 설정 생성 중...${NC}"
    
    # Nginx 설정 디렉토리 생성
    mkdir -p "$PROJECT_ROOT/config/nginx"
    
    # Nginx 설정 파일 생성
    cat > "$PROJECT_ROOT/config/nginx/default.conf" << EOF
server {
    listen 80;
    server_name _;
    
    # HTTP를 HTTPS로 리디렉션
    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name _;
    
    # SSL 인증서 설정
    ssl_certificate /etc/nginx/ssl/certs/server.crt;
    ssl_certificate_key /etc/nginx/ssl/private/server.key;
    
    # SSL 설정 최적화
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;
    
    # HSTS 설정
    add_header Strict-Transport-Security "max-age=63072000; includeSubdomains; preload";
    
    # API 서버로 프록시
    location / {
        proxy_pass http://api-server:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    
    # Docker Compose 파일에 Nginx 서비스 추가 안내
    log "${GREEN}Nginx 설정이 생성되었습니다.${NC}"
    log "${YELLOW}Docker Compose 파일에 Nginx 서비스를 추가하려면 다음 설정을 사용하세요:${NC}"
    echo "  # Nginx 프록시 서버"
    echo "  nginx:"
    echo "    image: nginx:alpine"
    echo "    container_name: nasos-nginx"
    echo "    restart: unless-stopped"
    echo "    ports:"
    echo "      - \"80:80\""
    echo "      - \"443:443\""
    echo "    volumes:"
    echo "      - ./config/nginx:/etc/nginx/conf.d"
    echo "      - ./config/ssl/certs:/etc/nginx/ssl/certs:ro"
    echo "      - ./config/ssl/private:/etc/nginx/ssl/private:ro"
    echo "    depends_on:"
    echo "      - api-server"
    echo "    networks:"
    echo "      - nasos-network"
}

# 메인 함수
main() {
    log "${BLUE}SSL/TLS 설정 시작...${NC}"
    
    # 필요한 디렉토리 생성
    create_directories
    
    # 자체 서명 인증서 생성 (개발 환경용)
    generate_self_signed_cert
    
    # Cloudflare 설정 확인
    check_cloudflare_config
    
    # Docker Compose 파일 업데이트
    update_docker_compose
    
    # Nginx 설정 생성 (프록시 서버용)
    generate_nginx_config
    
    log "${GREEN}SSL/TLS 설정이 완료되었습니다.${NC}"
    log "${YELLOW}프로덕션 환경에서는 Cloudflare를 통해 SSL/TLS를 설정하는 것이 좋습니다.${NC}"
}

# 스크립트가 직접 실행된 경우 메인 함수 호출
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
