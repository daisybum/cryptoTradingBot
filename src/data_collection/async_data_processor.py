"""
비동기 데이터 처리 모듈

이 모듈은 비동기 큐를 사용하여 OHLCV 데이터를 효율적으로 처리합니다.
"""

import os
import time
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from datetime import datetime, timedelta
import pandas as pd
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from src.utils.error_handler import RetryWithBackoff, CircuitBreaker, robust_operation

# 로깅 설정
logger = logging.getLogger(__name__)

class AsyncDataProcessor:
    """
    비동기 데이터 처리 클래스
    
    이 클래스는 비동기 큐를 사용하여 OHLCV 데이터를 효율적으로 처리합니다.
    """
    
    def __init__(self, influx_client: InfluxDBClient, influx_bucket: str, influx_org: str, 
                 batch_size: int = 100, max_queue_size: int = 10000):
        """
        비동기 데이터 처리기 초기화
        
        Args:
            influx_client: InfluxDB 클라이언트
            influx_bucket: InfluxDB 버킷
            influx_org: InfluxDB 조직
            batch_size: 배치 처리 크기
            max_queue_size: 최대 큐 크기
        """
        # InfluxDB 설정
        self.influx_client = influx_client
        self.influx_bucket = influx_bucket
        self.influx_org = influx_org
        
        # InfluxDB 쓰기 API
        self.write_api = influx_client.write_api(write_options=SYNCHRONOUS)
        
        # 데이터 처리 큐
        self.queue = asyncio.Queue(maxsize=max_queue_size)
        
        # 배치 처리 설정
        self.batch_size = batch_size
        
        # 작업 중단 플래그
        self.is_running = False
        
        # 처리 통계
        self.stats = {
            'processed_items': 0,
            'failed_items': 0,
            'last_processed_time': None,
            'batch_times': [],
            'queue_sizes': []
        }
        
        # 데이터 유효성 검사 콜백
        self.validation_callback = None
        
        # 재시도 핸들러
        self.retry_handler = RetryWithBackoff(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0,
            backoff_factor=2.0
        )
        
        # 회로 차단기
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            reset_timeout=60
        )
        
        # 작업자 태스크
        self.worker_tasks = []
        
        # 모니터링 태스크
        self.monitor_task = None
        
        logger.info("비동기 데이터 처리기 초기화 완료")
    
    async def start(self, num_workers: int = 2):
        """
        데이터 처리 시작
        
        Args:
            num_workers: 작업자 수
        """
        if self.is_running:
            logger.warning("데이터 처리기가 이미 실행 중입니다.")
            return
        
        self.is_running = True
        
        # 작업자 태스크 생성
        self.worker_tasks = []
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(i))
            self.worker_tasks.append(task)
        
        # 모니터링 태스크 생성
        self.monitor_task = asyncio.create_task(self._monitor_queue())
        
        logger.info(f"데이터 처리 시작됨 (작업자: {num_workers}개)")
    
    async def stop(self):
        """
        데이터 처리 중지
        """
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 모든 작업자 태스크 취소
        for task in self.worker_tasks:
            task.cancel()
        
        # 모니터링 태스크 취소
        if self.monitor_task:
            self.monitor_task.cancel()
        
        # 태스크 완료 대기
        try:
            if self.worker_tasks:
                await asyncio.gather(*self.worker_tasks, return_exceptions=True)
            if self.monitor_task:
                await self.monitor_task
        except asyncio.CancelledError:
            pass
        
        self.worker_tasks = []
        self.monitor_task = None
        
        logger.info("데이터 처리 중지됨")
    
    async def add_item(self, item: Dict):
        """
        처리할 항목 추가
        
        Args:
            item: 처리할 항목 (딕셔너리)
        """
        await self.queue.put(item)
    
    async def add_ohlcv(self, symbol: str, timeframe: str, data: List, source: str = 'unknown'):
        """
        OHLCV 데이터 추가
        
        Args:
            symbol: 심볼 (예: BTC/USDT)
            timeframe: 타임프레임 (예: 5m)
            data: OHLCV 데이터 [time, open, high, low, close, volume]
            source: 데이터 소스 (예: 'websocket', 'historical')
        """
        item = {
            'symbol': symbol,
            'timeframe': timeframe,
            'data': data,
            'source': source
        }
        await self.add_item(item)
    
# DEAD CODE:     def set_validation_callback(self, callback: Callable[[List], bool]):
        """
        데이터 유효성 검사 콜백 설정
        
        Args:
            callback: 유효성 검사 콜백 함수
        """
        self.validation_callback = callback
    
# DEAD CODE:     def get_stats(self) -> Dict:
        """
        처리 통계 조회
        
        Returns:
            Dict: 처리 통계 정보
        """
        stats = self.stats.copy()
        stats['current_queue_size'] = self.queue.qsize()
        stats['is_running'] = self.is_running
        
        # 평균 배치 처리 시간 계산
        if self.stats['batch_times']:
            stats['avg_batch_time'] = sum(self.stats['batch_times']) / len(self.stats['batch_times'])
        else:
            stats['avg_batch_time'] = 0
        
        # 평균 큐 크기 계산
        if self.stats['queue_sizes']:
            stats['avg_queue_size'] = sum(self.stats['queue_sizes']) / len(self.stats['queue_sizes'])
        else:
            stats['avg_queue_size'] = 0
        
        return stats
    
    async def _worker(self, worker_id: int):
        """
        데이터 처리 작업자
        
        Args:
            worker_id: 작업자 ID
        """
        logger.info(f"작업자 {worker_id} 시작됨")
        
        batch = []
        last_batch_time = time.time()
        
        try:
            while self.is_running:
                try:
                    # 큐에서 항목 가져오기
                    item = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                    
                    # 유효성 검사
                    if self.validation_callback and 'data' in item:
                        if not self.validation_callback(item['data']):
                            logger.warning(f"유효하지 않은 데이터: {item['symbol']} {item['timeframe']} - {item['data']}")
                            self.stats['failed_items'] += 1
                            self.queue.task_done()
                            continue
                    
                    # 배치에 항목 추가
                    batch.append(item)
                    
                    # 배치 처리 조건 확인
                    current_time = time.time()
                    batch_full = len(batch) >= self.batch_size
                    batch_timeout = current_time - last_batch_time >= 5.0  # 5초 타임아웃
                    
                    if batch_full or batch_timeout:
                        if batch:
                            # 배치 처리
                            await self._process_batch(batch)
                            
                            # 배치 초기화
                            batch = []
                            last_batch_time = current_time
                
                except asyncio.TimeoutError:
                    # 타임아웃 시 배치 처리
                    current_time = time.time()
                    if batch and current_time - last_batch_time >= 5.0:
                        await self._process_batch(batch)
                        batch = []
                        last_batch_time = current_time
                
                except asyncio.CancelledError:
                    # 취소 시 남은 배치 처리
                    if batch:
                        await self._process_batch(batch)
                    raise
                
                except Exception as e:
                    logger.error(f"작업자 {worker_id} 오류 발생: {e}")
                    self.stats['failed_items'] += len(batch)
                    
                    # 각 항목에 대해 작업 완료 표시
                    for _ in range(len(batch)):
                        self.queue.task_done()
                    
                    # 배치 초기화
                    batch = []
                    last_batch_time = time.time()
        
        except asyncio.CancelledError:
            logger.info(f"작업자 {worker_id} 취소됨")
            
            # 남은 배치 처리
            if batch:
                try:
                    await self._process_batch(batch)
                except Exception as e:
                    logger.error(f"작업자 {worker_id} 종료 중 오류 발생: {e}")
        
        except Exception as e:
            logger.error(f"작업자 {worker_id} 예외 발생: {e}")
        
        finally:
            logger.info(f"작업자 {worker_id} 종료됨")
    
    @robust_operation(circuit_breaker=True, retry=True)
    async def _process_batch(self, batch: List[Dict]):
        """
        배치 처리
        
        Args:
            batch: 처리할 항목 배치
        """
        start_time = time.time()
        
        try:
            # 포인트 목록 생성
            points = []
            
            for item in batch:
                symbol = item['symbol']
                timeframe = item['timeframe']
                data = item['data']
                
                # 심볼 형식 변환 (BTC/USDT -> BTC_USDT)
                formatted_symbol = symbol.replace('/', '_')
                
                # 시간 변환
                timestamp = datetime.fromtimestamp(data[0] / 1000)
                
                # InfluxDB 포인트 생성
                point = Point("ohlcv") \
                    .tag("symbol", formatted_symbol) \
                    .tag("timeframe", timeframe) \
                    .field("time", data[0]) \
                    .field("open", float(data[1])) \
                    .field("high", float(data[2])) \
                    .field("low", float(data[3])) \
                    .field("close", float(data[4])) \
                    .field("volume", float(data[5])) \
                    .time(timestamp)
                
                points.append(point)
            
            # InfluxDB에 데이터 쓰기
            self.write_api.write(bucket=self.influx_bucket, org=self.influx_org, record=points)
            
            # 통계 업데이트
            self.stats['processed_items'] += len(batch)
            self.stats['last_processed_time'] = datetime.now().isoformat()
            
            # 배치 처리 시간 기록
            batch_time = time.time() - start_time
            self.stats['batch_times'].append(batch_time)
            
            # 최근 10개 배치 시간만 유지
            if len(self.stats['batch_times']) > 10:
                self.stats['batch_times'].pop(0)
            
            # 각 항목에 대해 작업 완료 표시
            for _ in range(len(batch)):
                self.queue.task_done()
            
            logger.debug(f"배치 처리 완료: {len(batch)}개 항목, {batch_time:.3f}초")
        
        except Exception as e:
            logger.error(f"배치 처리 중 오류 발생: {e}")
            
            # 각 항목에 대해 작업 완료 표시
            for _ in range(len(batch)):
                self.queue.task_done()
            
            # 통계 업데이트
            self.stats['failed_items'] += len(batch)
            
            raise
    
    async def _monitor_queue(self):
        """
        큐 모니터링
        """
        try:
            while self.is_running:
                # 큐 크기 기록
                queue_size = self.queue.qsize()
                self.stats['queue_sizes'].append(queue_size)
                
                # 최근 10개 큐 크기만 유지
                if len(self.stats['queue_sizes']) > 10:
                    self.stats['queue_sizes'].pop(0)
                
                # 큐 크기 경고
                if queue_size > self.queue.maxsize * 0.8:
                    logger.warning(f"큐 크기가 너무 큽니다: {queue_size}/{self.queue.maxsize}")
                
                # 10초마다 확인
                await asyncio.sleep(10)
        
        except asyncio.CancelledError:
            logger.info("큐 모니터링 작업 취소됨")
        
        except Exception as e:
            logger.error(f"큐 모니터링 중 오류 발생: {e}")
    
    async def wait_empty(self, timeout: Optional[float] = None):
        """
        큐가 비워질 때까지 대기
        
        Args:
            timeout: 타임아웃 (초)
        """
        try:
            await asyncio.wait_for(self.queue.join(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"큐 비우기 타임아웃: {self.queue.qsize()}개 항목 남음")
            raise
