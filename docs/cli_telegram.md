# CLI 메뉴 및 텔레그램 알림 시스템

NASOSv5_mod3 트레이딩 봇은 명령줄 인터페이스(CLI)와 텔레그램 알림 시스템을 제공합니다. 이 문서에서는 이러한 기능을 설정하고 사용하는 방법을 설명합니다.

## CLI 메뉴 시스템

CLI 메뉴 시스템은 트레이딩 봇의 다양한 기능에 쉽게 접근할 수 있는 대화형 인터페이스를 제공합니다.

### 설치 및 설정

CLI 메뉴 시스템은 별도의 설치가 필요하지 않습니다. 프로젝트를 클론하고 종속성을 설치한 후 바로 사용할 수 있습니다.

### 사용 방법

CLI 메뉴를 실행하려면 다음 명령을 사용하세요:

```bash
# 프로젝트 루트 디렉토리에서
python scripts/cli.py
```

또는 실행 권한을 부여한 후 직접 실행할 수 있습니다:

```bash
chmod +x scripts/cli.py
./scripts/cli.py
```

### 사용 가능한 명령어

CLI 메뉴는 다음과 같은 명령어를 제공합니다:

- `help` - 사용 가능한 모든 명령어 표시
- `status` - 트레이딩 봇 상태 표시
- `start` - 트레이딩 봇 시작
- `stop` - 트레이딩 봇 중지
- `trades` - 최근 거래 내역 표시
- `balance` - 현재 잔액 정보 표시
- `performance` - 성능 지표 표시
- `risk` - 리스크 관리 설정 변경
- `notify` - 알림 설정 관리
- `exit` - CLI 종료

각 명령어에 대한 자세한 정보는 CLI 내에서 `help` 명령어를 실행하여 확인할 수 있습니다.

## 텔레그램 알림 시스템

텔레그램 알림 시스템은 트레이딩 봇의 중요한 이벤트와 알림을 텔레그램을 통해 실시간으로 받을 수 있는 기능을 제공합니다.

### 설정 방법

1. 텔레그램 봇 생성:
   - 텔레그램에서 [@BotFather](https://t.me/BotFather)를 검색하고 대화를 시작합니다.
   - `/newbot` 명령어를 입력하고 지시에 따라 봇을 생성합니다.
   - 봇 생성이 완료되면 API 토큰을 받게 됩니다. 이 토큰을 안전하게 보관하세요.

2. 채팅 ID 확인:
   - 생성한 봇과 대화를 시작합니다.
   - 웹 브라우저에서 `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`를 방문합니다. (YOUR_BOT_TOKEN을 실제 토큰으로 대체)
   - 봇에게 메시지를 보낸 후 위 URL을 새로고침하면 JSON 응답에서 `chat_id`를 확인할 수 있습니다.

3. 환경 변수 설정:
   - `config/env/project.env` 파일에 다음 변수를 설정합니다:
     ```
     TELEGRAM_BOT_TOKEN=your_telegram_bot_token
     TELEGRAM_CHAT_ID=your_telegram_chat_id
     ```

### 알림 레벨

텔레그램 알림 시스템은 다음과 같은 알림 레벨을 제공합니다:

- `info` - 일반 정보 메시지 (기본값)
- `warning` - 경고 메시지
- `error` - 오류 메시지
- `trade` - 거래 관련 메시지

알림 레벨을 설정하면 해당 레벨 이상의 중요도를 가진 메시지만 받게 됩니다. 예를 들어, `warning` 레벨을 설정하면 `warning`과 `error`, `trade` 메시지는 받지만 `info` 메시지는 받지 않습니다.

### CLI를 통한 알림 관리

CLI 메뉴에서 `notify` 명령어를 사용하여 알림 설정을 관리할 수 있습니다:

- `notify status` - 현재 알림 설정 표시
- `notify test` - 테스트 메시지 전송
- `notify enable` - 알림 활성화
- `notify disable` - 알림 비활성화
- `notify set-level <level>` - 알림 레벨 설정 (info, warning, error, trade)

### 알림 종류

텔레그램 알림 시스템은 다음과 같은 종류의 알림을 제공합니다:

1. **거래 알림**
   - 새로운 거래 시작
   - 거래 종료 (수익/손실 포함)
   - 손절 및 이익 실현 발생

2. **리스크 관리 알림**
   - 킬 스위치 활성화/비활성화
   - 최대 드로다운 도달
   - 리스크 설정 변경

3. **시스템 알림**
   - 봇 시작/중지
   - 오류 및 경고
   - 성능 보고서

## 통합 예제

다음은 CLI 메뉴와 텔레그램 알림 시스템을 함께 사용하는 예제입니다:

1. 트레이딩 봇 상태 확인 및 알림 전송:
   ```
   > status
   === 트레이딩 봇 상태 ===
   활성 거래 세션: 1
   오늘의 거래 수: 5
   오늘의 수익: 12.34 USDT
   리스크 관리자: 활성화
   킬 스위치: 비활성화

   > notify test
   테스트 메시지가 성공적으로 전송되었습니다.
   ```

2. 리스크 설정 변경 및 알림 전송:
   ```
   > risk set-max-dd 15
   최대 드로다운이 15.00%로 설정되었습니다.
   ```
   이 명령은 최대 드로다운을 15%로 설정하고 텔레그램을 통해 알림을 전송합니다.

## 문제 해결

1. **텔레그램 메시지가 전송되지 않는 경우**
   - 봇 토큰과 채팅 ID가 올바르게 설정되었는지 확인하세요.
   - 봇과의 대화가 시작되었는지 확인하세요.
   - `notify test` 명령어를 사용하여 연결을 테스트하세요.

2. **CLI 메뉴가 실행되지 않는 경우**
   - 프로젝트 종속성이 모두 설치되었는지 확인하세요.
   - 실행 권한이 부여되었는지 확인하세요.
   - 로그 파일에서 오류 메시지를 확인하세요.

## 추가 정보

더 자세한 정보는 소스 코드의 다음 파일을 참조하세요:

- `src/cli/menu.py` - CLI 메뉴 시스템 구현
- `src/notifications/telegram.py` - 텔레그램 알림 시스템 구현
