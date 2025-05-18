#!/usr/bin/env python3
"""
데이터 수집 서비스 로그 모니터링 스크립트

이 스크립트는 데이터 수집 서비스의 로그를 주기적으로 확인하고 오류를 감지합니다.
오류가 발견되면 알림을 보냅니다.
"""

import os
import re
import time
import argparse
import subprocess
import sys
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.env_loader import EnvLoader

# 오류 패턴 정의
ERROR_PATTERNS = [
    r'ERROR',
    r'CRITICAL',
    r'FATAL',
    r'Exception',
    r'Error:',
    r'Failed',
    r'Timeout',
    r'Connection refused',
    r'Connection reset',
    r'WebSocket 연결 실패',
    r'시크릿 읽기 실패',
    r'인증 실패'
]

# 컴파일된 정규식 패턴
COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in ERROR_PATTERNS]

def check_logs(container_name, lines=100):
    """
    컨테이너 로그를 확인하고 오류를 감지합니다.
    
    Args:
        container_name: 확인할 Docker 컨테이너 이름
        lines: 확인할 로그 라인 수
    
    Returns:
        tuple: (오류 발견 여부, 오류 메시지 목록)
    """
    try:
        # Docker 로그 가져오기
        cmd = f"docker logs --tail {lines} {container_name}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            return True, [f"로그 가져오기 실패: {result.stderr}"]
        
        log_lines = result.stdout.splitlines()
        
        # 오류 패턴 검색
        errors = []
        for line in log_lines:
            for pattern in COMPILED_PATTERNS:
                if pattern.search(line):
                    errors.append(line)
                    break
        
        return len(errors) > 0, errors
    
    except Exception as e:
        return True, [f"로그 확인 중 오류 발생: {str(e)}"]

def check_container_status(container_name):
    """
    컨테이너 상태를 확인합니다.
    
    Args:
        container_name: 확인할 Docker 컨테이너 이름
    
    Returns:
        tuple: (컨테이너 실행 중 여부, 상태 메시지)
    """
    try:
        cmd = f"docker inspect --format='{{{{.State.Status}}}}' {container_name}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, f"컨테이너 상태 확인 실패: {result.stderr}"
        
        status = result.stdout.strip()
        
        if status == "running":
            return True, "컨테이너가 정상적으로 실행 중입니다."
        else:
            return False, f"컨테이너 상태: {status}"
    
    except Exception as e:
        return False, f"컨테이너 상태 확인 중 오류 발생: {str(e)}"

def send_notification(message):
    """
    알림을 보냅니다. (실제 구현은 필요에 따라 이메일, Slack 등으로 확장)
    
    Args:
        message: 알림 메시지
    """
    print(f"[알림] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(message)
    print("-" * 50)
    
    # 여기에 실제 알림 로직 구현 (이메일, Slack 등)
    # 예: send_email(message) 또는 send_slack_message(message)

def monitor_logs(container_name, interval_minutes=5, log_lines=100):
    """
    주기적으로 로그를 모니터링합니다.
    
    Args:
        container_name: 모니터링할 Docker 컨테이너 이름
        interval_minutes: 모니터링 간격(분)
        log_lines: 확인할 로그 라인 수
    """
    print(f"로그 모니터링 시작: {container_name}")
    print(f"간격: {interval_minutes}분, 로그 라인 수: {log_lines}")
    print("-" * 50)
    
    while True:
        # 컨테이너 상태 확인
        container_running, status_message = check_container_status(container_name)
        
        if not container_running:
            send_notification(f"컨테이너 문제 감지: {status_message}")
        else:
            # 로그 확인
            has_errors, errors = check_logs(container_name, log_lines)
            
            if has_errors:
                error_message = f"오류 감지됨 ({len(errors)}개):\n"
                error_message += "\n".join(errors[:10])  # 처음 10개 오류만 표시
                
                if len(errors) > 10:
                    error_message += f"\n... 외 {len(errors) - 10}개 더 있음"
                
                send_notification(error_message)
            else:
                print(f"[정상] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 오류 없음")
        
        # 다음 확인까지 대기
        time.sleep(interval_minutes * 60)

def main():
    parser = argparse.ArgumentParser(description='Docker 컨테이너 로그 모니터링')
    parser.add_argument('--container', type=str, default='nasos-data-collector',
                        help='모니터링할 Docker 컨테이너 이름')
    parser.add_argument('--interval', type=int, default=5,
                        help='모니터링 간격(분)')
    parser.add_argument('--lines', type=int, default=100,
                        help='확인할 로그 라인 수')
    parser.add_argument('--config', type=str, default='config/env/project.env',
                        help='환경 설정 파일 경로')
    
    args = parser.parse_args()
    
    # 환경 변수 로드
    env_loader = EnvLoader(env_file=args.config)
    
    # 로그 레벨 설정
    log_level = env_loader.get('LOG_LEVEL', 'INFO')
    print(f"로그 레벨: {log_level}")
    
    # 컨테이너 이름 확인 (환경 변수에서 오버라이드 가능)
    container_name = env_loader.get('DATA_COLLECTOR_CONTAINER', args.container)
    
    try:
        monitor_logs(container_name, args.interval, args.lines)
    except KeyboardInterrupt:
        print("\n모니터링 종료")

if __name__ == "__main__":
    main()
