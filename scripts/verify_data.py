#!/usr/bin/env python3
"""
InfluxDB 데이터 검증 스크립트

이 스크립트는 InfluxDB에 저장된 데이터의 품질과 완전성을 검증합니다.
데이터 수집 서비스가 올바르게 작동하는지 확인하는 데 사용됩니다.
"""

import os
import sys
import json
import time
import argparse
import pandas as pd
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.env_loader import EnvLoader

def load_config(config_path):
    """
    설정 파일을 로드합니다.
    
    Args:
        config_path: 설정 파일 경로
    
    Returns:
        dict: 설정 정보
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"설정 파일 로드 실패: {e}")
        sys.exit(1)

def connect_to_influxdb(url, token, org):
    """
    InfluxDB에 연결합니다.
    
    Args:
        url: InfluxDB URL
        token: InfluxDB 토큰
        org: InfluxDB 조직
    
    Returns:
        InfluxDBClient: InfluxDB 클라이언트
    """
    try:
        client = InfluxDBClient(url=url, token=token, org=org)
        return client
    except Exception as e:
        print(f"InfluxDB 연결 실패: {e}")
        sys.exit(1)

def query_data(client, bucket, symbol, timeframe, start_time, end_time):
    """
    InfluxDB에서 데이터를 쿼리합니다.
    
    Args:
        client: InfluxDB 클라이언트
        bucket: InfluxDB 버킷
        symbol: 심볼
        timeframe: 타임프레임
        start_time: 시작 시간
        end_time: 종료 시간
    
    Returns:
        pd.DataFrame: 쿼리 결과
    """
    query_api = client.query_api()
    
    # 쿼리 구성
    # 심볼 형식 변환 (BTC/USDT -> BTC_USDT)
    formatted_symbol = symbol.replace('/', '_')
    
    query = f'''
    from(bucket: "{bucket}")
        |> range(start: {start_time}, stop: {end_time})
        |> filter(fn: (r) => r["_measurement"] == "ohlcv")
        |> filter(fn: (r) => r["symbol"] == "{formatted_symbol}")
        |> filter(fn: (r) => r["timeframe"] == "{timeframe}")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    
    try:
        result = query_api.query_data_frame(query)
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return result
    except Exception as e:
        print(f"데이터 쿼리 실패: {e}")
        return pd.DataFrame()

def verify_data_completeness(df, timeframe, start_time, end_time):
    """
    데이터 완전성을 검증합니다.
    
    Args:
        df: 데이터프레임
        timeframe: 타임프레임
        start_time: 시작 시간
        end_time: 종료 시간
    
    Returns:
        tuple: (완전성 점수, 누락된 데이터 수)
    """
    if df.empty:
        return 0.0, "모든 데이터 누락"
    
    # 타임프레임에 따른 예상 데이터 포인트 수 계산
    timeframe_minutes = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "4h": 240,
        "1d": 1440
    }
    
    minutes = timeframe_minutes.get(timeframe, 0)
    if minutes == 0:
        return 0.0, f"지원되지 않는 타임프레임: {timeframe}"
    
    start_dt = pd.to_datetime(start_time)
    end_dt = pd.to_datetime(end_time)
    
    # 예상 데이터 포인트 수
    expected_points = int((end_dt - start_dt).total_seconds() / (minutes * 60))
    
    # 실제 데이터 포인트 수
    actual_points = len(df)
    
    # 완전성 점수 계산
    if expected_points == 0:
        return 0.0, "예상 데이터 포인트 없음"
    
    completeness = actual_points / expected_points
    missing_points = expected_points - actual_points
    
    return completeness, missing_points

def verify_data_quality(df):
    """
    데이터 품질을 검증합니다.
    
    Args:
        df: 데이터프레임
    
    Returns:
        tuple: (품질 점수, 품질 문제 설명)
    """
    if df.empty:
        return 0.0, "데이터 없음"
    
    issues = []
    
    # 필수 필드 확인
    required_fields = ['open', 'high', 'low', 'close', 'volume']
    missing_fields = [field for field in required_fields if field not in df.columns]
    
    if missing_fields:
        issues.append(f"누락된 필드: {', '.join(missing_fields)}")
    
    # 데이터 타입 확인
    for field in [f for f in required_fields if f in df.columns]:
        if not pd.api.types.is_numeric_dtype(df[field]):
            issues.append(f"비숫자 데이터: {field}")
    
    # 이상치 확인
    if 'open' in df.columns and 'close' in df.columns:
        zero_prices = ((df['open'] == 0) | (df['close'] == 0)).sum()
        if zero_prices > 0:
            issues.append(f"0 가격 데이터: {zero_prices}개")
    
    if 'high' in df.columns and 'low' in df.columns:
        invalid_ranges = (df['high'] < df['low']).sum()
        if invalid_ranges > 0:
            issues.append(f"고가 < 저가 데이터: {invalid_ranges}개")
    
    # 중복 데이터 확인
    if '_time' in df.columns:
        duplicates = df.duplicated('_time').sum()
        if duplicates > 0:
            issues.append(f"중복 타임스탬프: {duplicates}개")
    
    # 품질 점수 계산
    if not issues:
        return 1.0, "문제 없음"
    
    # 문제 수에 따른 품질 점수 계산 (간단한 방식)
    quality_score = max(0.0, 1.0 - (len(issues) * 0.2))
    
    return quality_score, "; ".join(issues)

def main():
    parser = argparse.ArgumentParser(description='InfluxDB 데이터 검증')
    parser.add_argument('--config', type=str, default='config/env/project.env',
                        help='환경 설정 파일 경로')
    parser.add_argument('--symbol', type=str, default='BTC_USDT',
                        help='검증할 심볼')
    parser.add_argument('--timeframe', type=str, default='5m',
                        help='검증할 타임프레임')
    parser.add_argument('--hours', type=int, default=24,
                        help='검증할 시간 범위(시간)')
    
    args = parser.parse_args()
    
    # 환경 변수 로드
    env_loader = EnvLoader(env_file=args.config)
    
    # InfluxDB 연결 정보
    influx_url = env_loader.get('INFLUXDB_URL', 'http://localhost:8087')
    influx_token = env_loader.get('INFLUXDB_TOKEN', 'Iuss1256!@')
    influx_org = env_loader.get('INFLUXDB_ORG', 'nasos_org')
    influx_bucket = env_loader.get('INFLUXDB_BUCKET', 'market_data')
    
    print(f"InfluxDB 연결 정보: URL={influx_url}, Org={influx_org}, Bucket={influx_bucket}")
    
    # Docker 환경 확인
    docker_env = env_loader.get('DOCKER_ENV', 'true').lower() == 'true'
    
    # 호스트 시스템에서 실행 중인 경우 URL 조정
    if 'influxdb' in influx_url and not docker_env:
        influx_url = 'http://localhost:8087'
        print(f"호스트 시스템 감지: URL 조정됨 -> {influx_url}")
    # Docker 환경에서 실행 중인 경우 URL 조정
    elif docker_env and 'localhost' in influx_url:
        influx_url = influx_url.replace('localhost', 'influxdb')
        print(f"Docker 환경 감지: URL 조정됨 -> {influx_url}")
    
    
    # 시간 범위 설정
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=args.hours)
    
    # InfluxDB 연결
    client = connect_to_influxdb(influx_url, influx_token, influx_org)
    
    # 데이터 쿼리
    print(f"데이터 검증 중: {args.symbol} {args.timeframe} (지난 {args.hours}시간)")
    print("-" * 50)
    
    df = query_data(
        client,
        influx_bucket,
        args.symbol,
        args.timeframe,
        start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    )
    
    # 데이터 완전성 검증
    completeness, missing_data = verify_data_completeness(df, args.timeframe, start_time, end_time)
    print(f"데이터 완전성: {completeness:.2%}")
    print(f"누락된 데이터: {missing_data}")
    
    # 데이터 품질 검증
    quality, issues = verify_data_quality(df)
    print(f"데이터 품질: {quality:.2%}")
    print(f"품질 문제: {issues}")
    
    # 종합 평가
    overall_score = (completeness + quality) / 2
    print("-" * 50)
    print(f"종합 평가: {overall_score:.2%}")
    
    if overall_score >= 0.9:
        print("결과: 우수")
    elif overall_score >= 0.7:
        print("결과: 양호")
    elif overall_score >= 0.5:
        print("결과: 보통")
    else:
        print("결과: 불량")
    
    # 데이터 샘플 출력
    if not df.empty:
        print("\n데이터 샘플:")
        print(df.head(5))
    
    client.close()

if __name__ == "__main__":
    main()
