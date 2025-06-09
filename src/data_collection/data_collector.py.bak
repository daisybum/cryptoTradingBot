"""
데이터 수집 모듈

이 모듈은 Binance WebSocket API를 사용하여 실시간 OHLCV 데이터를 수집하고 InfluxDB에 저장합니다.
"""

import os
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from src.data_collection.websocket_manager import WebSocketManager
from src.data_collection.historical_data_fetcher import HistoricalDataFetcher
from src.data_collection.async_data_processor import AsyncDataProcessor
from src.utils.env_loader import get_env_loader
from src.utils.error_handler import RetryWithBackoff, CircuitBreaker

# 로깅 설정
logger = logging.getLogger(__name__)

class DataCollector:
    """
    데이터 수집 클래스
    
    이 클래스는 Binance WebSocket API를 사용하여 실시간 OHLCV 데이터를 수집하고 InfluxDB에 저장합니다.
    """
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, use_websocket_only: bool = True):
        """
        데이터 수집기 초기화
        
        Args:
            api_key: Binance API 키 (기본값: 환경 변수에서 로드)
            api_secret: Binance API 시크릿 (기본값: 환경 변수에서 로드)
            use_websocket_only: WebSocket만 사용하여 데이터 수집 (기본값: True)
        """
        # 환경 변수 로더
        self.env = get_env_loader()
        
        # Binance API 키 및 시크릿
        # 직접 환경 변수에서 API 키 가져오기
        self.api_key = api_key or os.environ.get('BINANCE_API_KEY') or self.env.get('BINANCE_API_KEY')
        self.api_secret = api_secret or os.environ.get('BINANCE_API_SECRET') or self.env.get('BINANCE_API_SECRET')
        
        logger.debug(f"API 키: {self.api_key[:5]}...{self.api_key[-5:] if self.api_key else '없음'}")
        
        if not self.api_key or not self.api_secret:
            logger.warning("Binance API 키 또는 시크릿이 설정되지 않았습니다. 일부 기능이 제한될 수 있습니다.")
        
        # WebSocket만 사용 여부
        self.use_websocket_only = use_websocket_only
        
        # 수집할 심볼 목록 (상위 50개 알트코인 + BTC, ETH)
        self.symbols = self.env.get_list('TRADING_SYMBOLS', ['BTC/USDT', 'ETH/USDT'])
        
        # 수집할 타임프레임 목록
        self.timeframes = self.env.get_list('TIMEFRAMES', ['5m', '15m', '1h'])
        
        # 타임프레임을 밀리초로 변환하는 딕셔너리
        self.timeframe_ms = {
            '1m': 60 * 1000,
            '3m': 3 * 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '30m': 30 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '2h': 2 * 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '6h': 6 * 60 * 60 * 1000,
            '8h': 8 * 60 * 60 * 1000,
            '12h': 12 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000,
            '3d': 3 * 24 * 60 * 60 * 1000,
            '1w': 7 * 24 * 60 * 60 * 1000,
            '1M': 30 * 24 * 60 * 60 * 1000
        }
        
        # InfluxDB 연결 설정
        # project.env 파일에서 설정값 가져오기
        self.influx_url = self.env.get('INFLUXDB_URL', 'http://influxdb:8086')
        self.influx_token = self.env.get('INFLUXDB_TOKEN', '')
        self.influx_org = self.env.get('INFLUXDB_ORG', 'nasos_org')
        self.influx_bucket = self.env.get('INFLUXDB_BUCKET', 'market_data')
        logger.info(f"InfluxDB 설정 사용: {self.influx_url}")
        
        # Docker 환경 설정 확인
        self.docker_env = self.env.get('DOCKER_ENV', 'true').lower() == 'true'
        self.local_test = self.env.get('LOCAL_TEST', 'false').lower() == 'true'
        
        # 기존 코드와의 호환성을 위한 속성 추가
        self.bucket = self.influx_bucket
        self.org = self.influx_org
        
        # InfluxDB 클라이언트
        self.influx_client = InfluxDBClient(
            url=self.influx_url,
            token=self.influx_token,
            org=self.influx_org
        )
        
        # InfluxDB 쓰기 API
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
        
        # HTTP 세션
        self.session = None
        
        # 컴포넌트 초기화
        self.ws_manager = None  # WebSocket 관리자
        self.historical_fetcher = None  # 역사적 데이터 검색기
        self.data_processor = None  # 데이터 처리기
        
        # 재시도 설정
        self.max_retries = 5
        self.retry_delay = 1  # 초 단위
        
        # 회로 차단기
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            reset_timeout=60
        )
        
        # 작업 중단 플래그
        self.is_running = False
        
        # 캐시 디렉토리 생성
        os.makedirs('cache/ohlcv', exist_ok=True)
        
        logger.info(f"데이터 수집기 초기화 완료: {len(self.symbols)} 심볼, {len(self.timeframes)} 타임프레임")
    
    async def start(self):
        """
        데이터 수집 시작
        """
        if self.is_running:
            logger.warning("데이터 수집이 이미 실행 중입니다.")
            return
        
        self.is_running = True
        
        # HTTP 세션 초기화
        # self.session = aiohttp.ClientSession()
        
        # 역사적 데이터 검색기 초기화
        self.historical_fetcher = HistoricalDataFetcher(
            api_key=self.api_key,
            api_secret=self.api_secret
        )
        
        # 데이터 처리기 초기화
        self.data_processor = AsyncDataProcessor(
            influx_client=self.influx_client,
            influx_bucket=self.influx_bucket,
            influx_org=self.influx_org
        )
        await self.data_processor.start()
        
        # WebSocket 관리자 초기화
        self.ws_manager = WebSocketManager()
        # 메시지 핸들러 등록
        self.ws_manager.message_handlers['kline'] = self._handle_websocket_message
        await self.ws_manager.start()
        
        logger.info("데이터 수집 시작됨")
        
        # 작업 시작
        tasks = []
        
        # WebSocket 스트림 시작
        tasks.append(asyncio.create_task(self._start_websocket_streams()))
        
        # 누락된 데이터 확인
        tasks.append(asyncio.create_task(self._check_missing_data()))
        
        # 작업 완료 대기
        await asyncio.gather(*tasks)
    
    async def stop(self):
        """
        데이터 수집 중지
        """
        if not self.is_running:
            logger.warning("데이터 수집이 이미 중지되었습니다.")
            return
        
        self.is_running = False
        
        # WebSocket 관리자 중지
        if self.ws_manager:
            await self.ws_manager.stop()
        
        # 데이터 처리기 중지
        if self.data_processor:
            await self.data_processor.stop()
        
        # 역사적 데이터 검색기 중지
        if self.historical_fetcher:
            await self.historical_fetcher.close()
        
        # HTTP 세션 종료
        # if self.session:
        #     await self.session.close()
        
        logger.info("데이터 수집 중지됨")
    
    async def _start_websocket_streams(self):
        """
        WebSocket 스트림 시작
        """
        logger.info("WebSocket 스트림 시작 중...")
        
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                # 심볼 형식 변환 (BTC/USDT -> btcusdt)
                formatted_symbol = symbol.replace('/', '').lower()
                
                # 스트림 이름 생성
                stream_name = f"{formatted_symbol}_{timeframe}"
                
                # WebSocket 스트림 구독
                await self.ws_manager.subscribe_kline(
                    symbol=formatted_symbol,
                    interval=timeframe,
                    stream_name=stream_name
                )
                
                logger.info(f"WebSocket 스트림 연결됨: {symbol} {timeframe}")
    
    async def _check_missing_data(self):
        """
        누락된 데이터 확인 및 채우기
        
        주기적으로 데이터베이스를 확인하여 누락된 데이터를 식별하고 채웁니다.
        """
        while self.is_running:
            try:
                logger.info("누락된 데이터 확인 중...")
                
                # WebSocket만 사용하는 경우 과거 데이터 로드 건너뛰기
                if self.use_websocket_only:
                    logger.info("WebSocket만 사용하여 데이터 수집 중입니다. 과거 데이터 로드를 건너뜁니다.")
                else:
                    for symbol in self.symbols:
                        for timeframe in self.timeframes:
                            # 마지막 캔들 시간 확인
                            last_timestamp = await self._get_last_candle_time(symbol, timeframe)
                            
                            if last_timestamp is None:
                                # 데이터가 없는 경우 과거 30일 데이터 로드
                                logger.info(f"{symbol} {timeframe} 데이터가 없음. 과거 30일 데이터 로드 중...")
                                await self.fetch_complete_history(symbol, timeframe, days=30)
                            else:
                                # 현재 시간
                                now = datetime.now().timestamp() * 1000
                                
                                # 타임프레임 간격 (밀리초)
                                interval_ms = self._timeframe_to_milliseconds(timeframe)
                                
                                # 예상되는 다음 캔들 시간
                                expected_next_time = last_timestamp + interval_ms
                                
                                # 현재 시간과의 차이
                                time_diff = now - expected_next_time
                                
                                # 누락된 캔들이 있는 경우
                                if time_diff > interval_ms:
                                    # 누락된 데이터 로드
                                    logger.info(f"{symbol} {timeframe} 누락된 데이터 감지. 마지막 시간: {datetime.fromtimestamp(last_timestamp/1000).isoformat()}")
                                    
                                    # 누락된 데이터 검색
                                    missing_data = await self.historical_fetcher.check_missing_data(
                                        symbol=symbol,
                                        timeframe=timeframe,
                                        last_timestamp=last_timestamp
                                    )
                                    
                                    if missing_data:
                                        # 첫 번째 캔들은 이미 저장된 것이므로 제외
                                        for candle in missing_data[1:]:
                                            await self.data_processor.add_ohlcv(
                                                symbol=symbol,
                                                timeframe=timeframe,
                                                data=candle,
                                                source='historical_missing'
                                            )
                                        
                                        logger.info(f"{symbol} {timeframe} 누락된 데이터 {len(missing_data)-1}개 채움")
                
                # 데이터 처리기 큐가 비워질 때까지 대기 (최대 10초)
                try:
                    await asyncio.wait_for(self.data_processor.wait_empty(), timeout=10)
                except asyncio.TimeoutError:
                    logger.warning("데이터 처리 큐 비우기 타임아웃")
                
                # 30분마다 확인
                await asyncio.sleep(30 * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"누락된 데이터 확인 중 오류 발생: {e}")
                await asyncio.sleep(60)  # 오류 발생 시 1분 후 재시도
    
    async def _handle_websocket_message(self, message: Dict):
        """
        WebSocket 메시지 처리
        
        Args:
            message: WebSocket 메시지
        """
        try:
            # 메시지 형식 확인 (바이낸스 WebSocket API 형식)
            if 'e' not in message or message['e'] != 'kline' or 'k' not in message:
                logger.warning(f"잘못된 WebSocket 메시지 형식: {message}")
                return
            
            # 캥들 데이터 추출
            kline = message['k']
            
            # 심볼 형식 변환 (BTCUSDT -> BTC/USDT)
            symbol = message['s'].upper()
            base = symbol[:-4]  # BTC
            quote = symbol[-4:]  # USDT
            formatted_symbol = f"{base}/{quote}"
            
            # 타임프레임
            timeframe = kline['i']
            
            # 캥들 완료 여부
            is_closed = kline['x']
            
            # 캥들 데이터 추출
            timestamp = kline['t']  # 시작 시간
            open_price = float(kline['o'])  # 시가
            high_price = float(kline['h'])  # 고가
            low_price = float(kline['l'])  # 저가
            close_price = float(kline['c'])  # 종가
            volume = float(kline['v'])  # 거래량
            
            # OHLCV 데이터 생성
            ohlcv = [
                timestamp,
                open_price,
                high_price,
                low_price,
                close_price,
                volume
            ]
            
            # 완료된 캔들만 처리
            if is_closed:
                # 데이터 처리기에 추가
                await self.data_processor.add_ohlcv(
                    symbol=formatted_symbol,
                    timeframe=timeframe,
                    data=ohlcv,
                    source='websocket'
                )
                
                logger.debug(f"WebSocket 캔들 데이터 처리됨: {formatted_symbol} {timeframe} {datetime.fromtimestamp(timestamp/1000).isoformat()}")
        except Exception as e:
            logger.error(f"WebSocket 메시지 처리 중 오류 발생: {e}")
    
    async def _get_last_candle_time(self, symbol: str, timeframe: str) -> Optional[int]:
        """
        마지막 캔들 시간 가져오기
        
        Args:
            symbol: 심볼 (예: BTC/USDT)
            timeframe: 타임프레임 (예: 5m)
        
        Returns:
            Optional[int]: 마지막 캔들 시간 (밀리초 타임스탬프) 또는 None
        """
        try:
            # InfluxDB에서 마지막 캔들 시간 조회
            query = f'''
                from(bucket: "{self.influx_bucket}")
                |> range(start: -30d)
                |> filter(fn: (r) => r._measurement == "ohlcv")
                |> filter(fn: (r) => r.symbol == "{symbol}")
                |> filter(fn: (r) => r.timeframe == "{timeframe}")
                |> filter(fn: (r) => r._field == "close")
                |> last()
            '''
            
            result = self.influx_client.query_api().query(query=query, org=self.influx_org)
            
            # 결과 확인
            if not result or len(result) == 0:
                return None
            
            # 마지막 레코드 추출
            for table in result:
                for record in table.records:
                    # 시간 추출
                    timestamp = int(record.get_time().timestamp() * 1000)
                    return timestamp
            
            return None
        except Exception as e:
            logger.error(f"마지막 캔들 시간 조회 중 오류 발생: {e}")
            return None
    
    async def _get_last_candle_from_db(self, symbol: str, timeframe: str) -> Optional[List]:
        """
        데이터베이스에서 마지막 캔들 가져오기
        
        Args:
            symbol: 심볼 (예: BTC/USDT)
            timeframe: 타임프레임 (예: 5m)
        
        Returns:
            Optional[List]: 마지막 OHLCV 캔들 또는 None
        """
        try:
            # InfluxDB에서 마지막 캔들 조회
            query = f'''
                from(bucket: "{self.influx_bucket}")
                |> range(start: -30d)
                |> filter(fn: (r) => r._measurement == "ohlcv")
                |> filter(fn: (r) => r.symbol == "{symbol}")
                |> filter(fn: (r) => r.timeframe == "{timeframe}")
                |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> last()
            '''
            
            result = self.influx_client.query_api().query(query=query, org=self.influx_org)
            
            # 결과 확인
            if not result or len(result) == 0:
                return None
            
            # 마지막 레코드 추출
            for table in result:
                for record in table.records:
                    # OHLCV 데이터 추출
                    timestamp = int(record.get_time().timestamp() * 1000)
                    open_price = record.values.get('open', 0.0)
                    high_price = record.values.get('high', 0.0)
                    low_price = record.values.get('low', 0.0)
                    close_price = record.values.get('close', 0.0)
                    volume = record.values.get('volume', 0.0)
                    
                    # OHLCV 데이터 반환
                    return [timestamp, open_price, high_price, low_price, close_price, volume]
            
            return None
        except Exception as e:
            logger.error(f"마지막 캔들 조회 중 오류 발생: {e}")
            return None
    
    def _timeframe_to_milliseconds(self, timeframe: str) -> int:
        """
        타임프레임을 밀리초로 변환
        
        Args:
            timeframe: 타임프레임 (예: 5m)
        
        Returns:
            int: 밀리초
        """
        if timeframe in self.timeframe_ms:
            return self.timeframe_ms[timeframe]
        
        # 기본값: 1시간
        logger.warning(f"알 수 없는 타임프레임: {timeframe}, 기본값 1시간 사용")
        return 60 * 60 * 1000
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str, since: Optional[int] = None, limit: int = 1000) -> List:
        """
        OHLCV 데이터 검색
        
        Args:
            symbol: 심볼 (예: BTC/USDT)
            timeframe: 타임프레임 (예: 5m)
            since: 시작 시간 (밀리초 타임스탬프)
            limit: 조회할 캔들 수
        
        Returns:
            List: OHLCV 데이터 목록
        """
        try:
            # HistoricalDataFetcher를 사용하여 OHLCV 데이터 조회
            ohlcv = await self.historical_fetcher.fetch_ohlcv(symbol, timeframe, since, limit)
            
            # 조회한 데이터를 데이터 처리기에 추가
            for candle in ohlcv:
                await self.data_processor.add_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    data=candle,
                    source='historical'
                )
            
            logger.info(f"OHLCV 데이터 조회 성공: {symbol} {timeframe} ({len(ohlcv)} 캔들)")
            return ohlcv
        except Exception as e:
            logger.error(f"과거 데이터 조회 중 오류 발생: {e}")
            return []
    
    async def fetch_complete_history(self, symbol, timeframe, days=30):
        """
        지정된 기간 동안의 완전한 역사적 데이터 검색
        
        Args:
            symbol: 심볼 (예: BTC/USDT)
            timeframe: 타임프레임 (예: 5m)
            days: 과거 일수
        
        Returns:
            List: OHLCV 데이터 목록
        """
        try:
            # HistoricalDataFetcher를 사용하여 완전한 역사 데이터 조회
            all_data = await self.historical_fetcher.fetch_complete_history(symbol, timeframe, days)
            
            # 조회한 데이터를 데이터 처리기에 추가
            for candle in all_data:
                await self.data_processor.add_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    data=candle,
                    source='historical'
                )
            
            logger.info(f"완전한 역사 데이터 조회 성공: {symbol} {timeframe} ({len(all_data)} 캔들)")
            return all_data
        except Exception as e:
            logger.error(f"완전한 역사 데이터 조회 중 오류 발생: {e}")
            return []
