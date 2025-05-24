# 텔레그램 봇 통합 가이드

이 문서는 트레이딩 봇의 텔레그램 봇 통합에 대한 설정 및 사용 방법을 설명합니다.

## 개요

텔레그램 봇 통합은 다음 기능을 제공합니다:

- 거래 알림 (진입/청산)
- 오류 및 경고 알림
- 리스크 이벤트 알림 (드로다운 > 10% 등)
- 일일 성능 요약
- 원격 명령 실행 (상태 확인, 거래 비활성화 등)

## 설정 방법

### 1. 텔레그램 봇 토큰 발급

1. 텔레그램 앱에서 [@BotFather](https://t.me/BotFather)를 검색하여 대화를 시작합니다.
2. `/newbot` 명령을 입력하여 새 봇을 생성합니다.
3. 봇 이름과 사용자 이름을 입력합니다.
4. BotFather가 제공하는 API 토큰을 복사합니다.

### 2. 환경 변수 설정

`project.env` 파일에 다음 환경 변수를 추가합니다:

```
# 텔레그램 설정
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
TELEGRAM_AUTHORIZED_USERS=user_id1,user_id2
```

- `TELEGRAM_BOT_TOKEN`: BotFather에서 발급받은 API 토큰
- `TELEGRAM_CHAT_ID`: 알림을 받을 채팅 ID
- `TELEGRAM_AUTHORIZED_USERS`: 명령 실행이 허용된 사용자 ID 목록 (쉼표로 구분)

### 3. 채팅 ID 찾기

채팅 ID를 찾는 방법:

1. 생성한 봇과 대화를 시작합니다.
2. 봇에게 메시지를 보냅니다.
3. 웹 브라우저에서 `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`를 방문합니다.
   (여기서 `<YOUR_TOKEN>`은 봇 토큰으로 대체)
4. 응답에서 `chat` 객체 내의 `id` 값을 찾습니다.

### 4. 의존성 설치

필요한 패키지를 설치합니다:

```bash
pip install -r requirements.txt
```

## 봇 실행

텔레그램 봇을 실행하려면 다음 명령을 사용합니다:

```bash
python scripts/run_telegram_bot.py
```

추가 옵션:

```bash
python scripts/run_telegram_bot.py --debug  # 디버그 모드 활성화
python scripts/run_telegram_bot.py --token YOUR_TOKEN --chat-id YOUR_CHAT_ID  # 환경 변수 대신 직접 지정
python scripts/run_telegram_bot.py --auth-users 123456789,987654321  # 인증된 사용자 ID 지정
```

## 사용 가능한 명령어

봇은 다음 명령어를 지원합니다:

- `/start` - 시작 메시지 표시
- `/help` - 도움말 표시
- `/status` - 현재 봇 상태 확인
- `/balance` - 현재 잔액 확인
- `/trades` - 최근 거래 내역 확인
- `/risk on` - 거래 활성화
- `/risk off` - 거래 비활성화
- `/risk status` - 현재 리스크 상태 확인

## 알림 유형

봇은 다음 유형의 알림을 전송합니다:

### 거래 알림

거래가 시작되거나 종료될 때 전송됩니다.

```
🟢 거래 알림
ID: 12345
페어: BTC/USDT
방향: BUY
상태: OPEN
진입가: 50000.0
수량: 0.01
손절가: 49000.0
이익실현가: 52000.0
```

### 리스크 알림

리스크 이벤트가 발생할 때 전송됩니다.

```
⚠️ 경고
드로다운 경고 임계값 접근: 12.50% (최대 허용의 83.3%)
```

### 일일 성능 요약

매일 거래 세션이 종료될 때 전송됩니다.

```
📊 일일 성능 요약
날짜: 2025-05-22
총 거래: 15
승률: 60.0%
총 수익: 120.50 USDT (2.41%)
최대 드로다운: 5.2%
```

## 보안 고려사항

- 인증된 사용자만 명령을 실행할 수 있습니다.
- 중요한 명령은 추가 확인 과정을 거칩니다.
- 봇 토큰과 채팅 ID는 안전하게 보관해야 합니다.

## 문제 해결

### 봇이 응답하지 않는 경우

1. 봇 토큰이 올바른지 확인합니다.
2. 봇이 실행 중인지 확인합니다.
3. 로그 파일에서 오류 메시지를 확인합니다.

### 명령이 실행되지 않는 경우

1. 사용자 ID가 인증된 사용자 목록에 있는지 확인합니다.
2. 명령 구문이 올바른지 확인합니다.
3. 리스크 관리자와 실행 엔진이 초기화되었는지 확인합니다.
