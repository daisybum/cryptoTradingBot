# NASOSv5_mod3 Bot 문서

NASOSv5_mod3 Bot은 바이낸스에서 BTC, ETH 및 상위 50개 시가총액 알트코인을 거래하는 고빈도 트레이딩 봇입니다.

## 목차

- [설치 가이드](installation.md)
- [구성 가이드](configuration.md)
- [사용 방법](usage.md)
- [전략 설명](strategy.md)
- [API 참조](api.md)
- [문제 해결](troubleshooting.md)

## 프로젝트 개요

NASOSv5_mod3 Bot은 공개 GitHub 전략인 **NASOSv5_mod3**(NotAnotherSMAOffsetStrategy v5 mod3)을 기반으로 구축되었으며, 5분 타임프레임에서 바이낸스 스팟 USDT 페어를 거래합니다.

**목표**: 전략의 역사적 성과(≈ 37,270% 수익, ≈ 11% 최대 드로다운, Sharpe ≈ 2.1)를 실시간 시장에서 재현하면서 실시간 거래와 백테스팅 모두에 사용할 수 있는 견고하고 확장 가능한 인프라를 제공합니다.

## 주요 기능

- **시장 데이터 통합**: Binance 실시간 및 과거 OHLCV 데이터(5분/15분/1시간) 스트리밍
- **전략 엔진(NASOSv5_mod3)**: RSI_fast + SMA 오프셋 조건에서 매수, EWO, EMA, MA_offset으로 필터링
- **자동화된 거래 실행**: Binance API를 통한 주문 실행 및 관리
- **위험 관리**: 글로벌 최대 드로다운 15%, 거래당 손절 3.5%, 거래당 2% 리스크
- **성능 분석**: PostgreSQL 저장, 승률, 수익 요소, Sharpe, Calmar, 최대 드로다운, 노출 % 등 지표 제공
