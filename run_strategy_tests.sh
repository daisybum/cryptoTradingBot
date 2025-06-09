#!/bin/bash

# 가상 환경 활성화
source /home/shpark/workspace/altTradingBot/venv/bin/activate

# Python 경로 설정
export PYTHONPATH=/home/shpark/workspace/altTradingBot:$PYTHONPATH

# 테스트 실행
cd /home/shpark/workspace/altTradingBot
python3 -m unittest tests/strategy_tests/test_nasos_v5_mod3.py -v
