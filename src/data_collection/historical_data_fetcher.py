"""
역사적 데이터 검색 모듈

이 모듈은 Binance REST API를 사용하여 과거 OHLCV 데이터를 검색하고 캐싱합니다.
"""

import os
import time
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import ccxt.async_support as ccxt
import pandas as pd
import aiohttp
import aiofiles
# DEAD CODE: import statistics  # 통계 기능 추가

from src.utils.error_handler import RetryWithBackoff, CircuitBreaker, robust_operation
from src.utils.env_loader import get_env_loader

# 로깅 설정
logger = logging.getLogger(__name__)

class HistoricalDataFetcher:
    """
    역사적 데이터 검색 클래스
    
    이 클래스는 Binance REST API를 사용하여 과거 OHLCV 데이터를 검색하고 캐싱합니다.
    """
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, cache_dir: Optional[str] = None):
        """
        역사적 데이터 검색기 초기화
        
        Args:
            api_key: Binance API 키 (기본값: 환경 변수에서 로드)
            api_secret: Binance API 시크릿 (기본값: 환경 변수에서 로드)
            cache_dir: 캐시 디렉토리 경로 (기본값: 'cache/ohlcv')
        """
        # 환경 변수 로더
        self.env = get_env_loader()
        
        # Binance API 키 및 시크릿
        # 직접 환경 변수에서 API 키 가져오기
        self.api_key = api_key or os.environ.get('BINANCE_API_KEY') or self.env.get('BINANCE_API_KEY')
        self.api_secret = api_secret or os.environ.get('BINANCE_API_SECRET') or self.env.get('BINANCE_API_SECRET')
        
        logger.info(f"API 키: {self.api_key[:5]}...{self.api_key[-5:] if self.api_key else '없음'}")
        
        if not self.api_key or not self.api_secret:
            logger.warning("Binance API 키 또는 시크릿이 설정되지 않았습니다. 일부 기능이 제한될 수 있습니다.")
        
        # Binance Exchange 인스턴스 생성
        self.exchange = ccxt.binance({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # 현물 거래소 사용
                'adjustForTimeDifference': True,
            }
        })
        
        # 캐시 디렉토리 설정
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'cache', 'ohlcv')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 요청 제한 설정
        self.limit = 1000  # 한 번에 가져올 최대 캔들 수
# DEAD CODE:         self.rate_limit_ms = 1200  # API 요청 간격 (밀리초)
        self.retry_delay = 1000  # 재시도 지연 시간 (밀리초)
        self.api_delay = 1000  # API 요청 간 지연 시간 (밀리초)
        
        # 타임프레임 매핑 (타임프레임 -> 밀리초)
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
        
        # 캐시 초기화
        self.cache = {}
        self.cache_timestamps = {}
        
        # 속도 제한 관리
        self.rate_limits = {
            'ohlcv': {
                'count': 0,
                'last_reset': time.time(),
                'window_size': 60,  # 60초 윈도우
                'limit': 1200  # 분당 1200 요청
            }
        }
        
        # 회로 차단기
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            reset_timeout=60
        )
        
        logger.info("역사적 데이터 검색기 초기화 완료")
    
    async def close(self):
        """
        리소스 정리
        """
        if self.exchange:
            await self.exchange.close()
        
        logger.info("역사적 데이터 검색기 종료")
    
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
        # 캐시 키 생성
        cache_key = f"{symbol}_{timeframe}_{since}_{limit}"
        
        # 캐시에서 데이터 확인
        cached_data = await self._get_from_cache(cache_key)
        if cached_data is not None:
            logger.debug(f"캐시에서 데이터 로드: {symbol} {timeframe}")
            return cached_data
        
        # 속도 제한 확인
        if not self._check_rate_limit(10, 'ohlcv'):  # OHLCV 요청 가중치: 10
            logger.warning(f"속도 제한 초과: {symbol} {timeframe}")
            # 동적 대기 시간 계산 (남은 시간의 일부)
            rate_limit = self.rate_limits['ohlcv']
            current_time = time.time()
            remaining_time = rate_limit['window_size'] - (current_time - rate_limit['last_reset'])
            wait_time = max(5, min(30, remaining_time / 2))  # 최소 5초, 최대 30초
            logger.info(f"속도 제한으로 인해 {wait_time:.1f}초 대기 중...")
            await asyncio.sleep(wait_time)
        
        # 데이터 검색
        try:
            logger.info(f"과거 데이터 검색 중: {symbol} {timeframe}")
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            
            # 속도 제한 업데이트
            self._update_rate_limit(10, 'ohlcv')
            
            # 데이터 캐싱
            await self._save_to_cache(cache_key, ohlcv)
            
            logger.info(f"과거 데이터 검색 성공: {symbol} {timeframe} ({len(ohlcv)} 캔들)")
            return ohlcv
        except ccxt.NetworkError as e:
            logger.error(f"네트워크 오류: {e}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"거래소 오류: {e}")
            raise
        except Exception as e:
            logger.error(f"과거 데이터 검색 중 오류 발생: {e}")
            raise
    
# DEAD CODE:     async def fetch_ohlcv_dataframe(self, symbol: str, timeframe: str, since: Optional[int] = None, limit: int = 1000) -> pd.DataFrame:
        """
        OHLCV 데이터를 DataFrame으로 검색
        
        Args:
            symbol: 심볼 (예: BTC/USDT)
            timeframe: 타임프레임 (예: 5m)
            since: 시작 시간 (밀리초 타임스탬프)
            limit: 조회할 캔들 수
        
        Returns:
            pd.DataFrame: OHLCV 데이터 DataFrame
        """
        ohlcv = await self.fetch_ohlcv(symbol, timeframe, since, limit)
        
        if not ohlcv:
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        return df
    
    async def fetch_complete_history(self, symbol: str, timeframe: str, days: int = 30) -> List:
        """
        지정된 기간 동안의 완전한 역사적 데이터를 검색합니다.
        
        Args:
            symbol: 심볼 (예: BTC/USDT)
            timeframe: 타임프레임 (예: 5m)
            days: 과거 일수
        
        Returns:
            List: OHLCV 데이터 목록
        """
        logger.info(f"완전한 역사 데이터 검색 시작: {symbol} {timeframe} (기간: {days}일)")
        
        # 시작 시간 계산 (현재 시간 - days일)
        since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        # 타임프레임 간격 (밀리초)
        interval_ms = self._timeframe_to_milliseconds(timeframe)
        
        # 결과 저장 리스트
        all_data = []
        
        # 현재 시간
        now = int(datetime.now().timestamp() * 1000)
        
        # 시작 시간부터 현재까지 데이터 조회
        current_since = since
        
        while current_since < now:
            try:
                # 캐시 확인
                cache_key = f"{symbol}_{timeframe}_{current_since}"
                if cache_key in self.cache:
                    ohlcv = self.cache[cache_key]
                    logger.debug(f"캐시에서 데이터 로드: {symbol} {timeframe} {len(ohlcv)} 캔들")
                else:
                    # API에서 데이터 조회 - 직접 호출
                    try:
                        ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, current_since, self.limit)
                    except Exception as e:
                        logger.error(f"역사 데이터 조회 중 오류 발생: {symbol} {timeframe} - {e}")
                        raise
                    
                    # 캐시에 저장
                    self.cache[cache_key] = ohlcv
                    logger.debug(f"API에서 데이터 로드: {symbol} {timeframe} {len(ohlcv)} 캔들")
                
                if not ohlcv:
                    break
                
                # 결과에 추가
                all_data.extend(ohlcv)
                
                # 다음 시작 시간 설정 (마지막 캔들 시간 + 1)
                if ohlcv:
                    current_since = ohlcv[-1][0] + 1
                else:
                    current_since += interval_ms * self.limit
                
                # 레이트 리밋 방지를 위한 딜레이
                await asyncio.sleep(self.api_delay / 1000)  # 초 단위로 변환
            except Exception as e:
                logger.error(f"완전한 역사 데이터 검색 중 오류 발생: {symbol} {timeframe} - {e}")
                # 오류 발생 시 잠시 대기 후 재시도
                await asyncio.sleep(self.retry_delay / 1000)  # 초 단위로 변환
        
        logger.info(f"완전한 역사 데이터 검색 완료: {symbol} {timeframe} (총 {len(all_data)} 캔들)")
        return all_data
        
# DEAD CODE:     async def fetch_ohlcv_range(self, symbol: str, timeframe: str, start: int, end: int, limit: int = 1000) -> List:
        """
        지정된 시간 범위 내의 OHLCV 데이터를 검색합니다.
        
        Args:
            symbol: 심볼 (예: BTC/USDT)
            timeframe: 타임프레임 (예: 5m)
            start: 시작 시간 (밀리초 타임스탬프)
            end: 종료 시간 (밀리초 타임스탬프)
            limit: 최대 캔들 수
        
        Returns:
            List: OHLCV 데이터 목록
        """
        logger.info(f"시간 범위 OHLCV 데이터 검색: {symbol} {timeframe} (시작: {datetime.fromtimestamp(start/1000).isoformat()}, 종료: {datetime.fromtimestamp(end/1000).isoformat()})")
        
        # 타임프레임 간격 (밀리초)
        interval_ms = self._timeframe_to_milliseconds(timeframe)
        
        # 결과 저장 리스트
        all_data = []
        
        # 시작 시간부터 종료 시간까지 데이터 조회
        current_since = start
        
        while current_since < end and len(all_data) < limit:
            try:
                # 남은 데이터 수 계산
                remaining_limit = limit - len(all_data)
                fetch_limit = min(remaining_limit, self.limit)
                
                # 캐시 확인
                cache_key = f"{symbol}_{timeframe}_{current_since}"
                if cache_key in self.cache:
                    ohlcv = self.cache[cache_key]
                    logger.debug(f"캐시에서 데이터 로드: {symbol} {timeframe} {len(ohlcv)} 캔들")
                else:
                    # API에서 데이터 조회 - 직접 호출
                    try:
                        ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, current_since, fetch_limit)
                    except Exception as e:
                        logger.error(f"시간 범위 데이터 조회 중 오류 발생: {symbol} {timeframe} - {e}")
                        raise
                    
                    # 캐시에 저장
                    self.cache[cache_key] = ohlcv
                    logger.debug(f"API에서 데이터 로드: {symbol} {timeframe} {len(ohlcv)} 캔들")
                
                if not ohlcv:
                    break
                
                # 종료 시간 이전의 데이터만 추가
                filtered_ohlcv = [candle for candle in ohlcv if candle[0] <= end]
                all_data.extend(filtered_ohlcv)
                
                # 다음 시작 시간 설정 (마지막 캔들 시간 + 1)
                if ohlcv:
                    current_since = ohlcv[-1][0] + 1
                else:
                    current_since += interval_ms * fetch_limit
                
                # 레이트 리밋 방지를 위한 딜레이
                await asyncio.sleep(self.api_delay / 1000)
            except Exception as e:
                logger.error(f"시간 범위 데이터 조회 중 오류 발생: {symbol} {timeframe} - {e}")
                # 오류 발생 시 잠시 대기 후 재시도
                await asyncio.sleep(self.retry_delay / 1000)
        
        # 결과가 너무 많은 경우 제한
        if len(all_data) > limit:
            all_data = all_data[:limit]
        
        logger.info(f"시간 범위 OHLCV 데이터 검색 완료: {symbol} {timeframe} (총 {len(all_data)} 캔들)")
        return all_data
    
# DEAD CODE:     async def fetch_recent_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> List:
        """
        최근 OHLCV 데이터를 검색합니다.
        
        Args:
            symbol: 심볼 (예: BTC/USDT)
            timeframe: 타임프레임 (예: 5m)
            limit: 캔들 수
        
        Returns:
            List: OHLCV 데이터 목록
        """
        logger.info(f"최근 OHLCV 데이터 검색: {symbol} {timeframe} (캔들 수: {limit})")
        
        try:
            # 캐시 확인
            cache_key = f"{symbol}_{timeframe}_recent_{limit}"
            
            # 캐시 만료 시간 확인 (최근 데이터는 짧은 시간만 캐싱)
            if cache_key in self.cache and cache_key in self.cache_timestamps:
                cache_age = time.time() - self.cache_timestamps.get(cache_key, 0)
                # 1분 이상 지난 캐시는 무효화
                if cache_age < 60:
                    ohlcv = self.cache[cache_key]
                    logger.debug(f"캐시에서 최근 데이터 로드: {symbol} {timeframe} {len(ohlcv)} 캔들")
                    return ohlcv
            
            # API에서 데이터 조회 - 직접 호출
            try:
                ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, None, limit)
            except Exception as e:
                logger.error(f"최근 데이터 조회 중 오류 발생: {symbol} {timeframe} - {e}")
                raise
            
            # 캐시에 저장
            self.cache[cache_key] = ohlcv
            self.cache_timestamps[cache_key] = time.time()
            
            logger.info(f"최근 OHLCV 데이터 검색 완료: {symbol} {timeframe} (총 {len(ohlcv)} 캔들)")
            return ohlcv
        except Exception as e:
            logger.error(f"최근 OHLCV 데이터 검색 중 오류 발생: {symbol} {timeframe} - {e}")
            return []
    
    async def check_missing_data(self, symbol: str, timeframe: str, last_timestamp: int) -> List:
        """
        누락된 데이터를 확인하고 가져옵니다.
        
        Args:
            symbol: 심볼 (예: BTC/USDT)
            timeframe: 타임프레임 (예: 5m)
            last_timestamp: 마지막 캔들 시간 (밀리초 타임스탬프)
        
        Returns:
            List: 누락된 OHLCV 데이터 목록
        """
        logger.info(f"누락된 데이터 확인 중: {symbol} {timeframe} (마지막 시간: {datetime.fromtimestamp(last_timestamp/1000).isoformat()})")
        
        # 현재 시간
        now = int(datetime.now().timestamp() * 1000)
        
        # 타임프레임 간격 (밀리초)
        timeframe_ms = self._timeframe_to_milliseconds(timeframe)
        
        # 예상되는 캔들 수
        expected_candles = (now - last_timestamp) // timeframe_ms
        
        # 누락된 데이터가 없는 경우
        if expected_candles <= 0:
            logger.info(f"누락된 데이터 없음: {symbol} {timeframe}")
            return []
        
        try:
            # 캐시 확인
            cache_key = f"{symbol}_{timeframe}_{last_timestamp+1}"
            if cache_key in self.cache:
                ohlcv = self.cache[cache_key]
                logger.debug(f"캐시에서 누락 데이터 로드: {symbol} {timeframe} {len(ohlcv)} 캔들")
            else:
                # API에서 데이터 조회 - 직접 호출
                try:
                    ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, last_timestamp + 1, min(int(expected_candles * 1.2), self.limit))
                except Exception as e:
                    logger.error(f"누락된 데이터 조회 중 오류 발생: {symbol} {timeframe} - {e}")
                    raise
                
                # 캐시에 저장
                self.cache[cache_key] = ohlcv
                logger.debug(f"API에서 누락 데이터 로드: {symbol} {timeframe} {len(ohlcv)} 캔들")
            
            logger.info(f"누락된 데이터 검색 완료: {symbol} {timeframe} (총 {len(ohlcv)} 캔들)")
            return ohlcv
        except Exception as e:
            logger.error(f"누락된 데이터 조회 중 오류 발생: {symbol} {timeframe} - {e}")
            return []
    
    def _check_rate_limit(self, weight: int, endpoint_type: str = 'ohlcv') -> bool:
        """
        속도 제한 확인
        
        Args:
            weight: 요청 가중치
            endpoint_type: 엔드포인트 유형
        
        Returns:
            bool: 요청 가능 여부
        """
        rate_limit = self.rate_limits[endpoint_type]
        current_time = time.time()
        
        # 윈도우 리셋
        if current_time - rate_limit['last_reset'] > rate_limit['window_size']:
            rate_limit['count'] = 0
            rate_limit['last_reset'] = current_time
        
        # 요청 가능 여부 확인
        return rate_limit['count'] + weight <= rate_limit['limit']
    
    def _update_rate_limit(self, weight: int, endpoint_type: str = 'ohlcv'):
        """
        속도 제한 업데이트
        
        Args:
            weight: 요청 가중치
            endpoint_type: 엔드포인트 유형
        """
        rate_limit = self.rate_limits[endpoint_type]
        rate_limit['count'] += weight
    
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
    
    async def _get_from_cache(self, key: str) -> Optional[List]:
        """
        캐시에서 데이터 가져오기
        
        Args:
            key: 캐시 키
        
        Returns:
            Optional[List]: 캐시된 데이터 또는 None
        """
        # 메모리 캐시 확인
        if key in self.cache:
            return self.cache[key]
        
        # 파일 캐시 확인
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(cache_file):
            try:
                async with aiofiles.open(cache_file, 'r') as f:
                    data = json.loads(await f.read())
                    self.cache[key] = data
                    return data
            except Exception as e:
                logger.error(f"캐시 파일 로드 실패: {e}")
        
        return None
    
    async def _save_to_cache(self, key: str, data: List):
        """
        데이터를 캐시에 저장
        
        Args:
            key: 캐시 키
            data: 저장할 데이터
        """
        # 메모리 캐시에 저장
        self.cache[key] = data
        
        # 파일 캐시에 저장
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        try:
            async with aiofiles.open(cache_file, 'w') as f:
                await f.write(json.dumps(data))
        except Exception as e:
            logger.error(f"캐시 파일 저장 실패: {e}")
