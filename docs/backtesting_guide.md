# 백테스팅 프레임워크 사용 가이드

이 문서는 암호화폐 트레이딩 봇의 백테스팅 프레임워크 사용법을 설명합니다. 백테스팅 프레임워크는 트레이딩 전략의 성능을 과거 데이터를 기반으로 평가하고 최적화하는 도구입니다.

## 목차

1. [개요](#개요)
2. [설치 및 설정](#설치-및-설정)
3. [명령줄 인터페이스](#명령줄-인터페이스)
4. [데이터 다운로드](#데이터-다운로드)
5. [백테스트 실행](#백테스트-실행)
6. [하이퍼파라미터 최적화](#하이퍼파라미터-최적화)
7. [워크포워드 테스팅](#워크포워드-테스팅)
8. [결과 시각화](#결과-시각화)
9. [예제 스크립트](#예제-스크립트)
10. [문제 해결](#문제-해결)

## 개요

백테스팅 프레임워크는 다음 기능을 제공합니다:

- 과거 OHLCV 데이터 다운로드
- 트레이딩 전략 백테스트 실행
- 하이퍼파라미터 최적화
- 워크포워드 테스팅
- 결과 시각화 및 분석

이 프레임워크는 [Freqtrade](https://www.freqtrade.io/)를 기반으로 하며, 백테스트 실행 및 데이터 관리에 Freqtrade의 기능을 활용합니다.

## 설치 및 설정

### 사전 요구사항

- Python 3.8 이상
- Freqtrade 설치
- 필요한 Python 패키지: pandas, numpy, matplotlib, seaborn

### Freqtrade 설정

백테스팅 프레임워크는 `config/freqtrade.json` 파일에 정의된 설정을 사용합니다. 이 파일에는 거래쌍, 거래 매개변수, 거래소 설정 등이 포함되어 있습니다.

## 명령줄 인터페이스

백테스팅 프레임워크는 명령줄 인터페이스를 통해 사용할 수 있습니다:

```bash
python src/strategy_engine/run_backtest.py [command] [options]
```

사용 가능한 명령:

- `download-data`: 백테스트용 과거 데이터 다운로드
- `backtest`: 백테스트 실행
- `hyperopt`: 하이퍼파라미터 최적화 실행
- `walkforward`: 워크포워드 테스팅 실행

기본 옵션:

- `--config`: Freqtrade 설정 파일 경로
- `--datadir`: 백테스트 데이터 디렉토리
- `--strategy`: 백테스트할 전략 이름

## 데이터 다운로드

과거 OHLCV 데이터를 다운로드하려면:

```bash
python src/strategy_engine/run_backtest.py download-data \
  --pairs BTC/USDT,ETH/USDT \
  --timeframes 5m,15m,1h \
  --start-date 20230101 \
  --end-date 20231231
```

옵션:

- `--pairs`: 다운로드할 거래쌍 (쉼표로 구분)
- `--timeframes`: 다운로드할 타임프레임 (쉼표로 구분)
- `--start-date`: 시작 날짜 (YYYYMMDD 형식)
- `--end-date`: 종료 날짜 (YYYYMMDD 형식)

## 백테스트 실행

전략 백테스트를 실행하려면:

```bash
python src/strategy_engine/run_backtest.py backtest \
  --strategy NASOSv5_mod3 \
  --timerange 20230101-20231231 \
  --stake-amount 100 \
  --max-open-trades 5 \
  --visualize
```

옵션:

- `--timerange`: 백테스트 시간 범위 (YYYYMMDD-YYYYMMDD 형식)
- `--parameter-file`: 전략 매개변수 파일
- `--stake-amount`: 거래당 주문 금액
- `--max-open-trades`: 최대 동시 거래 수
- `--visualize`: 백테스트 결과 시각화 활성화

## 하이퍼파라미터 최적화

전략 매개변수를 최적화하려면:

```bash
python src/strategy_engine/run_backtest.py hyperopt \
  --strategy NASOSv5_mod3 \
  --timerange 20230101-20230630 \
  --epochs 100 \
  --spaces buy,sell \
  --hyperopt-loss SharpeHyperOptLoss \
  --max-open-trades 5
```

옵션:

- `--epochs`: 최적화 반복 횟수
- `--spaces`: 최적화할 공간 (쉼표로 구분, 예: buy,sell,roi,stoploss)
- `--hyperopt-loss`: 최적화에 사용할 손실 함수

## 워크포워드 테스팅

워크포워드 테스팅을 실행하려면:

```bash
python src/strategy_engine/run_backtest.py walkforward \
  --strategy NASOSv5_mod3 \
  --start-date 20230101 \
  --end-date 20231231 \
  --window-size 30 \
  --step-size 7 \
  --optimize-epochs 50 \
  --optimize-spaces buy,sell \
  --max-open-trades 5 \
  --visualize
```

옵션:

- `--window-size`: 최적화 창 크기 (일 단위)
- `--step-size`: 창 이동 크기 (일 단위)
- `--optimize-epochs`: 최적화 반복 횟수
- `--optimize-spaces`: 최적화할 공간 (쉼표로 구분)

## 결과 시각화

백테스트 결과는 다음과 같은 차트로 시각화됩니다:

1. **자본금 곡선**: 시간에 따른 자본금 변화
2. **월별 수익률**: 월별 성과 분석
3. **드로다운 분석**: 자본금 감소 기간 분석
4. **거래쌍별 성능**: 각 거래쌍의 성과 비교
5. **승/패 분포**: 수익/손실 거래 분포 분석

시각화된 결과는 `results/` 디렉토리에 저장됩니다.

## 예제 스크립트

예제 스크립트를 실행하려면:

```bash
python scripts/backtest_example.py
```

이 스크립트는 다음 단계를 수행합니다:

1. 과거 데이터 다운로드
2. NASOSv5_mod3 전략 백테스트 실행
3. 결과 요약 출력
4. 결과 시각화 및 보고서 생성

## 문제 해결

### 일반적인 문제

1. **데이터 다운로드 실패**
   - 인터넷 연결 확인
   - 거래소 API 제한 확인
   - 올바른 거래쌍 형식 사용 (예: BTC/USDT)

2. **백테스트 실행 오류**
   - Freqtrade 설정 파일 확인
   - 전략 클래스 존재 여부 확인
   - 필요한 데이터가 다운로드되었는지 확인

3. **최적화 실패**
   - 충분한 메모리 확보
   - 에폭 수 감소
   - 최적화 공간 축소

### 로그 확인

백테스팅 프레임워크는 실행 중 자세한 로그를 출력합니다. 오류가 발생하면 로그 메시지를 확인하여 문제를 진단할 수 있습니다.

## 추가 자료

- [Freqtrade 문서](https://www.freqtrade.io/en/latest/)
- [백테스팅 모범 사례](https://www.freqtrade.io/en/latest/backtesting/)
- [하이퍼파라미터 최적화 가이드](https://www.freqtrade.io/en/latest/hyperopt/)
