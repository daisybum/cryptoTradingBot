#!/usr/bin/env python3
"""
NASOSv5_mod3 트레이딩 봇 CLI 실행 스크립트

이 스크립트는 트레이딩 봇의 CLI 메뉴를 실행합니다.
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트 경로를 Python 경로에 추가
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from src.cli.menu import main

if __name__ == "__main__":
    main()
