#!/usr/bin/env python3
"""
데이터 수집 서비스 자동 복구 스크립트

이 스크립트는 데이터 수집 서비스에 문제가 발생했을 때 자동으로 복구하는 기능을 제공합니다.
서비스가 중단되거나 오류가 발생하면 자동으로 재시작합니다.
"""

import os
import re
import time
import json
import argparse
import subprocess
import sys
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.env_loader import EnvLoader

# 심각한 오류 패턴 정의
CRITICAL_ERROR_PATTERNS = [
    r'CRITICAL',
    r'FATAL',
    r'WebSocket 연결 실패',
    r'Connection refused',
    r'Connection reset',
    r'Too many reconnection attempts',
    r'Circuit breaker opened',
    r'Maximum retries exceeded'
]

# 컴파일된 정규식 패턴
COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in CRITICAL_ERROR_PATTERNS]

def check_for_critical_errors(container_name, lines=100):
    """
    컨테이너 로그에서 심각한 오류를 확인합니다.
    
    Args:
        container_name: 확인할 Docker 컨테이너 이름
        lines: 확인할 로그 라인 수
    
    Returns:
        tuple: (심각한 오류 발견 여부, 오류 메시지 목록)
    """
    try:
        # Docker 로그 가져오기
        cmd = f"docker logs --tail {lines} {container_name}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            return True, [f"로그 가져오기 실패: {result.stderr}"]
        
        log_lines = result.stdout.splitlines()
        
        # 심각한 오류 패턴 검색
        critical_errors = []
        for line in log_lines:
            for pattern in COMPILED_PATTERNS:
                if pattern.search(line):
                    critical_errors.append(line)
                    break
        
        return len(critical_errors) > 0, critical_errors
    
    except Exception as e:
        return True, [f"로그 확인 중 오류 발생: {str(e)}"]

def check_container_health(container_name):
    """
    컨테이너 상태와 건강 상태를 확인합니다.
    
    Args:
        container_name: 확인할 Docker 컨테이너 이름
    
    Returns:
        tuple: (컨테이너 정상 여부, 상태 메시지)
    """
    try:
        # 컨테이너 상태 확인
        cmd = f"docker inspect --format='{{{{.State.Status}}}}' {container_name}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, f"컨테이너 상태 확인 실패: {result.stderr}"
        
        status = result.stdout.strip()
        
        if status != "running":
            return False, f"컨테이너가 실행 중이 아님: {status}"
        
        # 재시작 횟수 확인
        cmd = f"docker inspect --format='{{{{.RestartCount}}}}' {container_name}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            restart_count = int(result.stdout.strip())
            if restart_count > 5:  # 재시작 횟수가 많으면 문제가 있을 수 있음
                return False, f"컨테이너가 너무 자주 재시작됨: {restart_count}회"
        
        return True, "컨테이너가 정상적으로 실행 중입니다."
    
    except Exception as e:
        return False, f"컨테이너 상태 확인 중 오류 발생: {str(e)}"

def restart_container(container_name):
    """
    컨테이너를 재시작합니다.
    
    Args:
        container_name: 재시작할 Docker 컨테이너 이름
    
    Returns:
        tuple: (재시작 성공 여부, 결과 메시지)
    """
    try:
        print(f"컨테이너 재시작 중: {container_name}")
        
        # 컨테이너 재시작
        cmd = f"docker restart {container_name}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, f"컨테이너 재시작 실패: {result.stderr}"
        
        # 재시작 후 상태 확인
        time.sleep(5)  # 재시작 완료를 위한 대기
        
        is_healthy, status_message = check_container_health(container_name)
        
        if is_healthy:
            return True, "컨테이너가 성공적으로 재시작되었습니다."
        else:
            return False, f"컨테이너 재시작 후 상태 확인 실패: {status_message}"
    
    except Exception as e:
        return False, f"컨테이너 재시작 중 오류 발생: {str(e)}"

def reset_test_mode(config_path, enable_test_mode=True):
    """
    테스트 모드 설정을 변경합니다.
    
    Args:
        config_path: 설정 파일 경로
        enable_test_mode: 테스트 모드 활성화 여부
    
    Returns:
        tuple: (설정 변경 성공 여부, 결과 메시지)
    """
    try:
        if not os.path.exists(config_path):
            return False, f"설정 파일이 존재하지 않음: {config_path}"
        
        # 설정 파일 읽기
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # 설정 변경
        config['test_mode'] = enable_test_mode
        config['use_mock_data'] = enable_test_mode
        
        # 설정 파일 저장
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return True, f"테스트 모드 설정 변경 완료: {enable_test_mode}"
    
    except Exception as e:
        return False, f"테스트 모드 설정 변경 중 오류 발생: {str(e)}"

def auto_recovery(container_name, config_path, check_interval=60, max_restarts=3):
    """
    자동 복구 프로세스를 실행합니다.
    
    Args:
        container_name: 모니터링할 Docker 컨테이너 이름
        config_path: 설정 파일 경로
        check_interval: 확인 간격(초)
        max_restarts: 최대 재시작 횟수
    """
    print(f"자동 복구 프로세스 시작: {container_name}")
    print(f"간격: {check_interval}초, 최대 재시작 횟수: {max_restarts}")
    print("-" * 50)
    
    restart_count = 0
    last_restart_time = None
    
    while True:
        current_time = datetime.now()
        
        # 재시작 카운터 리셋 (24시간마다)
        if last_restart_time and (current_time - last_restart_time).total_seconds() > 86400:
            restart_count = 0
        
        # 컨테이너 상태 확인
        is_healthy, status_message = check_container_health(container_name)
        
        if not is_healthy:
            print(f"[문제 감지] {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"상태: {status_message}")
            
            if restart_count < max_restarts:
                # 컨테이너 재시작
                success, message = restart_container(container_name)
                restart_count += 1
                last_restart_time = current_time
                
                print(f"재시작 결과: {message}")
                print(f"재시작 횟수: {restart_count}/{max_restarts}")
            else:
                # 최대 재시작 횟수 초과 - 테스트 모드로 전환
                print(f"최대 재시작 횟수 초과. 테스트 모드로 전환 중...")
                success, message = reset_test_mode(config_path, True)
                
                if success:
                    # 테스트 모드로 전환 후 컨테이너 재시작
                    restart_container(container_name)
                
                print(f"테스트 모드 전환 결과: {message}")
                
                # 재시작 카운터 리셋
                restart_count = 0
                last_restart_time = current_time
        else:
            # 심각한 오류 확인
            has_critical_errors, errors = check_for_critical_errors(container_name)
            
            if has_critical_errors:
                print(f"[심각한 오류 감지] {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"오류: {errors[:3]}")  # 처음 3개 오류만 표시
                
                if restart_count < max_restarts:
                    # 컨테이너 재시작
                    success, message = restart_container(container_name)
                    restart_count += 1
                    last_restart_time = current_time
                    
                    print(f"재시작 결과: {message}")
                    print(f"재시작 횟수: {restart_count}/{max_restarts}")
                else:
                    # 최대 재시작 횟수 초과 - 테스트 모드로 전환
                    print(f"최대 재시작 횟수 초과. 테스트 모드로 전환 중...")
                    success, message = reset_test_mode(config_path, True)
                    
                    if success:
                        # 테스트 모드로 전환 후 컨테이너 재시작
                        restart_container(container_name)
                    
                    print(f"테스트 모드 전환 결과: {message}")
                    
                    # 재시작 카운터 리셋
                    restart_count = 0
                    last_restart_time = current_time
            else:
                print(f"[정상] {current_time.strftime('%Y-%m-%d %H:%M:%S')} - 문제 없음")
        
        # 다음 확인까지 대기
        time.sleep(check_interval)

def main():
    parser = argparse.ArgumentParser(description='데이터 수집 서비스 자동 복구')
    parser.add_argument('--container', type=str, default='nasos-data-collector',
                        help='모니터링할 Docker 컨테이너 이름')
    parser.add_argument('--config', type=str, default='config/test_mode.json',
                        help='설정 파일 경로')
    parser.add_argument('--interval', type=int, default=60,
                        help='확인 간격(초)')
    parser.add_argument('--max-restarts', type=int, default=3,
                        help='최대 재시작 횟수')
    parser.add_argument('--env-file', type=str, default='config/env/project.env',
                        help='환경 설정 파일 경로')
    
    args = parser.parse_args()
    
    # 환경 변수 로드
    env_loader = EnvLoader(env_file=args.env_file)
    
    # 컨테이너 이름 확인 (환경 변수에서 오버라이드 가능)
    container_name = env_loader.get('DATA_COLLECTOR_CONTAINER', args.container)
    
    # 테스트 모드 설정 파일 경로
    config_path = env_loader.get('TEST_MODE_CONFIG', args.config)
    
    try:
        auto_recovery(container_name, config_path, args.interval, args.max_restarts)
    except KeyboardInterrupt:
        print("\n자동 복구 프로세스 종료")

if __name__ == "__main__":
    main()
