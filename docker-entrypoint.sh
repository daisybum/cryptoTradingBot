#!/bin/bash
set -e

# 환경 변수 파일 로드
if [ -f /app/.env_vars ]; then
    echo "환경 변수 파일 로드 중..."
    source /app/.env_vars
fi

# 첫 번째 인수가 python 또는 python으로 시작하는 명령인 경우
if [ "${1}" = "python" ] || [ "${1:0:7}" = "python " ]; then
    echo "Python 명령 실행: $@"
    exec "$@"
else
    # 기본 명령 실행
    echo "기본 명령 실행: python -m src.main"
    exec python -m src.main
fi
