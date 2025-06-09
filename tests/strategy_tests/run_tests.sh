#!/bin/bash

# 프로젝트 루트 디렉토리 설정
export PYTHONPATH=/home/shpark/workspace/altTradingBot:$PYTHONPATH

# 테스트 실행
python3 -m unittest discover -s tests/strategy_tests
