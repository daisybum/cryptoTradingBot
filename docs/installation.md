# 설치 가이드

NASOSv5_mod3 Bot은 Docker를 사용하여 쉽게 설치하고 실행할 수 있습니다. 이 가이드는 봇을 설치하고 실행하는 데 필요한 단계를 안내합니다.

## 요구 사항

- Docker 및 Docker Compose
- 바이낸스 API 키 (거래 권한 필요)
- 최소 사양: 2 vCPU / 4 GB RAM (단일 전략)
- 권장 사양: 8 vCPU / 16 GB RAM (50개 이상 페어)
- 바이낸스 싱가포르 엔드포인트까지 80ms 미만의 지연 시간

## 설치 단계

### 1. 저장소 클론

```bash
git clone https://github.com/yourusername/nasos-bot.git
cd nasos-bot
```

### 2. 설정 스크립트 실행

```bash
./setup.sh
```

설정 스크립트는 다음을 수행합니다:
- 바이낸스 API 키 입력 요청
- Docker 환경 구성
- Hashicorp Vault를 사용한 API 키 보안 저장
- 데이터베이스 스키마 초기화
- 초기 구성을 위한 컬러 CLI 메뉴 제공

### 3. 컨테이너 시작

```bash
docker-compose up -d
```

이 명령은 다음 서비스를 시작합니다:
- 데이터 수집기
- 전략 엔진 (Freqtrade)
- 실행 엔진
- 위험 관리자
- PostgreSQL
- InfluxDB
- Grafana
- API 서버

## 보안 고려 사항

- API 키는 거래만 가능하도록 설정하고, 출금 기능은 비활성화하세요
- Docker rootless 모드 사용을 권장합니다
- 정기적인 취약점 스캔(Trivy) 및 종속성 모니터링(Snyk)을 수행하세요

## 문제 해결

설치 중 문제가 발생하면 다음을 확인하세요:

1. Docker 및 Docker Compose가 최신 버전인지 확인
2. 포트 충돌이 없는지 확인
3. API 키에 적절한 권한이 있는지 확인
4. 로그 파일 확인: `docker-compose logs -f`

자세한 문제 해결 정보는 [문제 해결](troubleshooting.md) 페이지를 참조하세요.
