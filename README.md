# NASOSv5_mod3 Bot - 바이낸스 알트코인 고빈도 트레이딩 봇

## 개요

NASOSv5_mod3 Bot은 바이낸스에서 BTC, ETH 및 상위 50개 시가총액 알트코인을 거래하는 고빈도 트레이딩 봇입니다. 이 봇은 공개 GitHub 전략인 **NASOSv5_mod3**(NotAnotherSMAOffsetStrategy v5 mod3)을 기반으로 구축되었으며, 5분 타임프레임에서 바이낸스 스팟 USDT 페어를 거래합니다.

**목표**: 전략의 역사적 성과(≈ 37,270% 수익, ≈ 11% 최대 드로다운, Sharpe ≈ 2.1)를 실시간 시장에서 재현하면서 실시간 거래와 백테스팅 모두에 사용할 수 있는 견고하고 확장 가능한 인프라를 제공합니다.

## 주요 기능

- **시장 데이터 통합**: Binance 실시간 및 과거 OHLCV 데이터(5분/15분/1시간) 스트리밍
- **전략 엔진(NASOSv5_mod3)**: RSI_fast + SMA 오프셋 조건에서 매수, EWO, EMA, MA_offset으로 필터링
- **자동화된 거래 실행**: Binance API를 통한 주문 실행 및 관리
- **위험 관리**: 글로벌 최대 드로다운 15%, 거래당 손절 3.5%, 거래당 2% 리스크
- **성능 분석**: PostgreSQL 저장, 승률, 수익 요소, Sharpe, Calmar, 최대 드로다운, 노출 % 등 지표 제공

## 기술 스택

| 컴포넌트 | 기술 |
|---------|------|
| 데이터 수집기 | Python 3.11 + CCXT, aiohttp |
| 전략 엔진 | Freqtrade 안정 Docker 이미지 |
| 실행 엔진 | Freqtrade Binance 커넥터 |
| 위험 관리자 | FastAPI 마이크로서비스 + Redis pub/sub |
| 데이터베이스 | PostgreSQL 15 \| InfluxDB 2.x |
| 대시보드 | Grafana 10 \| React (Next.js) |

## 설치 및 사용 방법

### 요구 사항

- Docker 및 Docker Compose
- 바이낸스 API 키 (거래 권한 필요)
- 최소 사양: 2 vCPU / 4 GB RAM (단일 전략)
- 권장 사양: 8 vCPU / 16 GB RAM (50개 이상 페어)

### 빠른 시작

1. 저장소 클론:
   ```bash
   git clone https://github.com/yourusername/nasos-bot.git
   cd nasos-bot
   ```

2. 설정 스크립트 실행:
   ```bash
   ./setup.sh
   ```
   - API 키 입력 요청에 응답
   - 봇이 자동으로 시작됩니다

3. 백테스팅 실행:
   ```bash
   ft backtesting --strategy NASOSv5_mod3
   ```

4. 라이브 트레이딩으로 전환:
   ```bash
   ft trade --config live.json
   ```

5. Grafana URL 방문하여 포트폴리오 및 드로다운 모니터링

## 개발 로드맵

| 월 | 마일스톤 |
|----|---------|
| M0 | 저장소 스캐폴드, Dockerfile, `setup.sh` |
| M1 | 바이낸스 연결, 5분 데이터 파이프라인 라이브 |
| M2 | NASOSv5_mod3 포팅, 백테스트 완료 |
| M3 | 위험 관리자 v1 (거래별 SL, 글로벌 MDD) |
| M4 | CLI 메뉴, 텔레그램 알림 |

## 기여 방법

이 프로젝트에 기여하려면 다음 단계를 따르세요:

1. 이 저장소를 포크합니다
2. 새 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경 사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 보안 모범 사례

- API 키는 거래만 가능하도록 설정하고, 출금 기능은 비활성화하세요
- Docker rootless 모드 사용
- 정기적인 취약점 스캔(Trivy) 및 종속성 모니터링(Snyk)
