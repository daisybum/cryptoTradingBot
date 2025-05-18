#!/usr/bin/env python3
"""
데이터 수집 서비스 성능 최적화 스크립트

이 스크립트는 데이터 수집 서비스의 성능을 모니터링하고 최적화하는 데 사용됩니다.
메모리 사용량, CPU 사용량, 네트워크 트래픽 등을 모니터링하고 최적화 권장 사항을 제공합니다.
"""

import os
import re
import json
import time
import argparse
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import sys
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.env_loader import EnvLoader

def get_container_stats(container_name, duration_seconds=60, interval_seconds=5):
    """
    컨테이너 성능 통계를 수집합니다.
    
    Args:
        container_name: Docker 컨테이너 이름
        duration_seconds: 모니터링 기간(초)
        interval_seconds: 측정 간격(초)
    
    Returns:
        pd.DataFrame: 성능 통계 데이터프레임
    """
    stats = []
    iterations = int(duration_seconds / interval_seconds)
    
    print(f"{container_name} 컨테이너 성능 통계 수집 중... ({duration_seconds}초 동안)")
    
    for i in range(iterations):
        try:
            # Docker 통계 명령 실행
            cmd = f"docker stats {container_name} --no-stream --format \"{{{{.CPUPerc}}}} {{{{.MemUsage}}}} {{{{.MemPerc}}}} {{{{.NetIO}}}} {{{{.BlockIO}}}}\""
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"통계 수집 실패: {result.stderr}")
                continue
            
            # 결과 파싱
            output = result.stdout.strip()
            if not output:
                continue
                
            parts = output.split()
            
            if len(parts) >= 5:
                # CPU 사용량 (% 제거)
                cpu_usage = float(parts[0].replace('%', ''))
                
                # 메모리 사용량 (MiB 단위로 변환)
                mem_usage_str = parts[1].split('/')[0].strip()
                mem_unit = mem_usage_str[-3:] if mem_usage_str[-3:] in ['KiB', 'MiB', 'GiB'] else 'MiB'
                mem_value = float(mem_usage_str[:-3])
                
                if mem_unit == 'KiB':
                    mem_usage = mem_value / 1024
                elif mem_unit == 'GiB':
                    mem_usage = mem_value * 1024
                else:
                    mem_usage = mem_value
                
                # 메모리 사용 비율 (% 제거)
                mem_perc = float(parts[2].replace('%', ''))
                
                # 네트워크 I/O (MB 단위로 변환)
                net_io = parts[3].split('/')
                net_in_str = net_io[0].strip()
                net_out_str = net_io[1].strip()
                
                net_in_unit = net_in_str[-2:] if net_in_str[-2:] in ['kB', 'MB', 'GB'] else 'kB'
                net_in_value = float(net_in_str[:-2])
                
                if net_in_unit == 'kB':
                    net_in = net_in_value / 1024
                elif net_in_unit == 'GB':
                    net_in = net_in_value * 1024
                else:
                    net_in = net_in_value
                
                net_out_unit = net_out_str[-2:] if net_out_str[-2:] in ['kB', 'MB', 'GB'] else 'kB'
                net_out_value = float(net_out_str[:-2])
                
                if net_out_unit == 'kB':
                    net_out = net_out_value / 1024
                elif net_out_unit == 'GB':
                    net_out = net_out_value * 1024
                else:
                    net_out = net_out_value
                
                # 블록 I/O (MB 단위로 변환)
                block_io = parts[4].split('/')
                block_in_str = block_io[0].strip()
                block_out_str = block_io[1].strip()
                
                block_in_unit = block_in_str[-2:] if block_in_str[-2:] in ['kB', 'MB', 'GB'] else 'kB'
                block_in_value = float(block_in_str[:-2] or '0')
                
                if block_in_unit == 'kB':
                    block_in = block_in_value / 1024
                elif block_in_unit == 'GB':
                    block_in = block_in_value * 1024
                else:
                    block_in = block_in_value
                
                block_out_unit = block_out_str[-2:] if block_out_str[-2:] in ['kB', 'MB', 'GB'] else 'kB'
                block_out_value = float(block_out_str[:-2] or '0')
                
                if block_out_unit == 'kB':
                    block_out = block_out_value / 1024
                elif block_out_unit == 'GB':
                    block_out = block_out_value * 1024
                else:
                    block_out = block_out_value
                
                # 통계 저장
                stats.append({
                    'timestamp': datetime.now(),
                    'cpu_usage': cpu_usage,
                    'mem_usage': mem_usage,
                    'mem_perc': mem_perc,
                    'net_in': net_in,
                    'net_out': net_out,
                    'block_in': block_in,
                    'block_out': block_out
                })
                
                print(f"측정 {i+1}/{iterations}: CPU {cpu_usage:.1f}%, 메모리 {mem_usage:.1f} MiB ({mem_perc:.1f}%)")
        
        except Exception as e:
            print(f"통계 수집 중 오류 발생: {e}")
        
        # 다음 측정까지 대기
        if i < iterations - 1:
            time.sleep(interval_seconds)
    
    return pd.DataFrame(stats)

def get_container_config(container_name):
    """
    컨테이너 구성 정보를 가져옵니다.
    
    Args:
        container_name: Docker 컨테이너 이름
    
    Returns:
        dict: 컨테이너 구성 정보
    """
    try:
        # Docker 검사 명령 실행
        cmd = f"docker inspect {container_name}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"컨테이너 구성 정보 가져오기 실패: {result.stderr}")
            return {}
        
        # JSON 파싱
        config = json.loads(result.stdout)
        
        if not config or len(config) == 0:
            return {}
        
        return config[0]
    
    except Exception as e:
        print(f"컨테이너 구성 정보 가져오기 중 오류 발생: {e}")
        return {}

def analyze_performance(stats_df, config):
    """
    성능 통계를 분석하고 최적화 권장 사항을 제공합니다.
    
    Args:
        stats_df: 성능 통계 데이터프레임
        config: 컨테이너 구성 정보
    
    Returns:
        dict: 분석 결과 및 권장 사항
    """
    if stats_df.empty:
        return {
            'status': 'error',
            'message': '성능 통계 데이터가 없습니다.'
        }
    
    # CPU 사용량 분석
    avg_cpu = stats_df['cpu_usage'].mean()
    max_cpu = stats_df['cpu_usage'].max()
    
    # 메모리 사용량 분석
    avg_mem = stats_df['mem_usage'].mean()
    max_mem = stats_df['mem_usage'].max()
    avg_mem_perc = stats_df['mem_perc'].mean()
    
    # 네트워크 I/O 분석
    total_net_in = stats_df['net_in'].sum()
    total_net_out = stats_df['net_out'].sum()
    
    # 블록 I/O 분석
    total_block_in = stats_df['block_in'].sum()
    total_block_out = stats_df['block_out'].sum()
    
    # 컨테이너 리소스 제한 확인
    resource_limits = {}
    
    if config and 'HostConfig' in config:
        host_config = config['HostConfig']
        
        # CPU 제한
        if 'NanoCpus' in host_config and host_config['NanoCpus']:
            resource_limits['cpu'] = host_config['NanoCpus'] / 1e9
        elif 'CpuQuota' in host_config and host_config['CpuQuota'] > 0:
            resource_limits['cpu'] = host_config['CpuQuota'] / 100000
        else:
            resource_limits['cpu'] = None
        
        # 메모리 제한
        if 'Memory' in host_config and host_config['Memory'] > 0:
            resource_limits['memory'] = host_config['Memory'] / (1024 * 1024)  # MiB 단위로 변환
        else:
            resource_limits['memory'] = None
    
    # 권장 사항
    recommendations = []
    
    # CPU 권장 사항
    if avg_cpu > 80:
        recommendations.append("CPU 사용량이 매우 높습니다. CPU 리소스를 늘리거나 워크로드를 최적화하세요.")
    elif avg_cpu > 50:
        recommendations.append("CPU 사용량이 높은 편입니다. 성능 병목 현상이 있는지 확인하세요.")
    
    # 메모리 권장 사항
    if avg_mem_perc > 80:
        recommendations.append("메모리 사용량이 매우 높습니다. 메모리 리소스를 늘리거나 메모리 누수를 확인하세요.")
    elif avg_mem_perc > 50:
        recommendations.append("메모리 사용량이 높은 편입니다. 메모리 사용량을 모니터링하세요.")
    
    # 네트워크 I/O 권장 사항
    if total_net_in > 100 or total_net_out > 100:  # 100MB 이상
        recommendations.append("네트워크 I/O가 높습니다. 네트워크 최적화를 고려하세요.")
    
    # 블록 I/O 권장 사항
    if total_block_in > 50 or total_block_out > 50:  # 50MB 이상
        recommendations.append("디스크 I/O가 높습니다. 디스크 액세스를 최적화하거나 SSD 사용을 고려하세요.")
    
    # 리소스 제한 권장 사항
    if 'cpu' in resource_limits and resource_limits['cpu'] is not None:
        if max_cpu > resource_limits['cpu'] * 80:
            recommendations.append(f"CPU 제한({resource_limits['cpu']:.2f} 코어)에 근접하고 있습니다. CPU 제한을 늘리는 것을 고려하세요.")
    
    if 'memory' in resource_limits and resource_limits['memory'] is not None:
        if max_mem > resource_limits['memory'] * 0.8:
            recommendations.append(f"메모리 제한({resource_limits['memory']:.2f} MiB)에 근접하고 있습니다. 메모리 제한을 늘리는 것을 고려하세요.")
    
    # 심볼 및 타임프레임 최적화 권장 사항
    if avg_cpu > 70 or avg_mem_perc > 70:
        recommendations.append("심볼 및 타임프레임 수가 많을 경우 부하가 높을 수 있습니다. 중요한 심볼과 타임프레임만 선택적으로 수집하는 것을 고려하세요.")
    
    # 결과 반환
    return {
        'status': 'success',
        'metrics': {
            'cpu': {
                'avg': avg_cpu,
                'max': max_cpu
            },
            'memory': {
                'avg_mib': avg_mem,
                'max_mib': max_mem,
                'avg_percent': avg_mem_perc
            },
            'network': {
                'total_in_mb': total_net_in,
                'total_out_mb': total_net_out
            },
            'disk': {
                'total_in_mb': total_block_in,
                'total_out_mb': total_block_out
            }
        },
        'resource_limits': resource_limits,
        'recommendations': recommendations
    }

def plot_performance(stats_df, output_file):
    """
    성능 통계를 그래프로 시각화합니다.
    
    Args:
        stats_df: 성능 통계 데이터프레임
        output_file: 출력 파일 경로
    """
    if stats_df.empty:
        print("그래프를 생성할 데이터가 없습니다.")
        return
    
    # 타임스탬프를 인덱스로 설정
    stats_df = stats_df.set_index('timestamp')
    
    # 그래프 생성
    fig, axs = plt.subplots(3, 1, figsize=(10, 12))
    
    # CPU 사용량 그래프
    axs[0].plot(stats_df.index, stats_df['cpu_usage'], 'b-')
    axs[0].set_title('CPU 사용량 (%)')
    axs[0].set_ylim(0, 100)
    axs[0].grid(True)
    
    # 메모리 사용량 그래프
    axs[1].plot(stats_df.index, stats_df['mem_usage'], 'r-')
    axs[1].set_title('메모리 사용량 (MiB)')
    axs[1].grid(True)
    
    # 네트워크 I/O 그래프
    axs[2].plot(stats_df.index, stats_df['net_in'], 'g-', label='네트워크 입력')
    axs[2].plot(stats_df.index, stats_df['net_out'], 'm-', label='네트워크 출력')
    axs[2].set_title('네트워크 I/O (MB)')
    axs[2].legend()
    axs[2].grid(True)
    
    # 그래프 저장
    plt.tight_layout()
    plt.savefig(output_file)
    print(f"성능 그래프가 {output_file}에 저장되었습니다.")

def optimize_config(config_path, analysis_result):
    """
    분석 결과를 기반으로 설정 파일을 최적화합니다.
    
    Args:
        config_path: 설정 파일 경로
        analysis_result: 성능 분석 결과
    
    Returns:
        bool: 최적화 성공 여부
    """
    try:
        if not os.path.exists(config_path):
            print(f"설정 파일이 존재하지 않음: {config_path}")
            return False
        
        # 설정 파일 읽기
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # 성능 분석 결과 확인
        metrics = analysis_result.get('metrics', {})
        recommendations = analysis_result.get('recommendations', [])
        
        # 최적화 적용
        optimized = False
        
        # CPU 또는 메모리 사용량이 높은 경우 최적화
        if 'cpu' in metrics and metrics['cpu']['avg'] > 70 or \
           'memory' in metrics and metrics['memory']['avg_percent'] > 70:
            
            # 심볼 수가 많은 경우 축소
            if 'symbols' in config and len(config['symbols']) > 5:
                # 중요한 심볼만 유지 (예: 상위 5개)
                important_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT"]
                config['symbols'] = [s for s in config['symbols'] if s in important_symbols]
                optimized = True
                print("심볼 수를 축소했습니다.")
            
            # 타임프레임 수가 많은 경우 축소
            if 'timeframes' in config and len(config['timeframes']) > 4:
                # 중요한 타임프레임만 유지 (예: 1m, 5m, 15m, 1h)
                important_timeframes = ["1m", "5m", "15m", "1h"]
                config['timeframes'] = [t for t in config['timeframes'] if t in important_timeframes]
                optimized = True
                print("타임프레임 수를 축소했습니다.")
            
            # 오류 처리 설정 최적화
            if 'error_handling' in config:
                error_handling = config['error_handling']
                
                # 연결 타임아웃 증가
                if 'connection_timeout' in error_handling and error_handling['connection_timeout'] < 15:
                    error_handling['connection_timeout'] = 15
                    optimized = True
                    print("연결 타임아웃을 증가시켰습니다.")
                
                # 회로 차단기 설정 최적화
                if 'circuit_breaker' in error_handling:
                    circuit_breaker = error_handling['circuit_breaker']
                    
                    if 'failure_threshold' in circuit_breaker and circuit_breaker['failure_threshold'] < 3:
                        circuit_breaker['failure_threshold'] = 3
                        optimized = True
                        print("회로 차단기 실패 임계값을 증가시켰습니다.")
                    
                    if 'reset_timeout' in circuit_breaker and circuit_breaker['reset_timeout'] < 60:
                        circuit_breaker['reset_timeout'] = 60
                        optimized = True
                        print("회로 차단기 재설정 타임아웃을 증가시켰습니다.")
        
        # 최적화된 설정 저장
        if optimized:
            # 백업 파일 생성
            backup_path = f"{config_path}.bak"
            with open(backup_path, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"원본 설정 파일이 {backup_path}에 백업되었습니다.")
            
            # 최적화된 설정 저장
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"최적화된 설정이 {config_path}에 저장되었습니다.")
            
            return True
        else:
            print("최적화가 필요하지 않습니다.")
            return False
    
    except Exception as e:
        print(f"설정 최적화 중 오류 발생: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='데이터 수집 서비스 성능 최적화')
    parser.add_argument('--container', type=str, default='nasos-data-collector',
                        help='Docker 컨테이너 이름')
    parser.add_argument('--duration', type=int, default=60,
                        help='모니터링 기간(초)')
    parser.add_argument('--interval', type=int, default=5,
                        help='측정 간격(초)')
    parser.add_argument('--config', type=str, default='config/test_mode.json',
                        help='설정 파일 경로')
    parser.add_argument('--output', type=str, default='logs/performance.png',
                        help='성능 그래프 출력 파일 경로')
    parser.add_argument('--optimize', action='store_true',
                        help='분석 결과를 기반으로 설정 최적화')
    parser.add_argument('--env-file', type=str, default='config/env/project.env',
                        help='환경 설정 파일 경로')
    
    args = parser.parse_args()
    
    # 환경 변수 로드
    env_loader = EnvLoader(env_file=args.env_file)
    
    # 컨테이너 이름 확인 (환경 변수에서 오버라이드 가능)
    container_name = env_loader.get('DATA_COLLECTOR_CONTAINER', args.container)
    
    # 테스트 모드 설정 파일 경로
    config_path = env_loader.get('TEST_MODE_CONFIG', args.config)
    
    # 성능 그래프 출력 파일 경로
    output_path = env_loader.get('PERFORMANCE_GRAPH_PATH', args.output)
    
    try:
        # 성능 통계 수집
        stats_df = get_container_stats(container_name, args.duration, args.interval)
        
        if stats_df.empty:
            print("성능 통계를 수집할 수 없습니다.")
            return
        
        # 컨테이너 구성 정보 가져오기
        config = get_container_config(container_name)
        
        # 성능 분석
        analysis_result = analyze_performance(stats_df, config)
        
        # 분석 결과 출력
        print("\n성능 분석 결과:")
        print("-" * 50)
        
        if analysis_result['status'] == 'success':
            metrics = analysis_result['metrics']
            
            print(f"CPU 사용량: 평균 {metrics['cpu']['avg']:.2f}%, 최대 {metrics['cpu']['max']:.2f}%")
            print(f"메모리 사용량: 평균 {metrics['memory']['avg_mib']:.2f} MiB, 최대 {metrics['memory']['max_mib']:.2f} MiB ({metrics['memory']['avg_percent']:.2f}%)")
            print(f"네트워크 I/O: 입력 {metrics['network']['total_in_mb']:.2f} MB, 출력 {metrics['network']['total_out_mb']:.2f} MB")
            print(f"디스크 I/O: 읽기 {metrics['disk']['total_in_mb']:.2f} MB, 쓰기 {metrics['disk']['total_out_mb']:.2f} MB")
            
            print("\n리소스 제한:")
            resource_limits = analysis_result['resource_limits']
            
            if 'cpu' in resource_limits and resource_limits['cpu'] is not None:
                print(f"CPU 제한: {resource_limits['cpu']:.2f} 코어")
            else:
                print("CPU 제한: 없음")
            
            if 'memory' in resource_limits and resource_limits['memory'] is not None:
                print(f"메모리 제한: {resource_limits['memory']:.2f} MiB")
            else:
                print("메모리 제한: 없음")
            
            print("\n권장 사항:")
            for i, recommendation in enumerate(analysis_result['recommendations'], 1):
                print(f"{i}. {recommendation}")
        else:
            print(f"분석 실패: {analysis_result['message']}")
        
        # 성능 그래프 생성
        plot_performance(stats_df, output_path)
        print(f"성능 그래프 생성됨: {output_path}")
        
        # 설정 최적화
        if args.optimize:
            print("\n설정 최적화 중...")
            success = optimize_config(config_path, analysis_result)
            if success:
                print("설정 최적화 완료")
            else:
                print("설정 최적화 실패")
    
    except KeyboardInterrupt:
        print("\n성능 최적화 프로세스 종료")

if __name__ == "__main__":
    main()
