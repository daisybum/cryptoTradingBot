"""
Resilient Data Collection Service

This module provides a wrapper around the standard data collection service,
adding enhanced error handling, circuit breakers, and fallback mechanisms.
"""

import os
import sys
import json
import asyncio
import signal
import logging
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

from src.utils.logger import setup_logging
from src.utils.env_loader import get_env_loader
from src.data_collection.data_collector import DataCollector
from src.utils.error_handler import robust_operation, load_error_handling_config
from src.utils.vault_helper import get_vault_client, get_list_secret, get_string_secret

# Environment variables and configuration
env = get_env_loader()
test_mode = env.get('TEST_MODE', 'false').lower() == 'true'

# Logging setup
log_level = env.get('LOG_LEVEL', 'INFO')
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
log_file = os.path.join(log_dir, f'resilient_collector_{datetime.now().strftime("%Y%m%d")}.log')
logger = setup_logging(log_level, log_file)

# Load test configuration if in test mode
test_config = {}
if test_mode:
    # 기본 경로를 Docker 컨테이너 경로와 로컬 경로 모두 시도
    default_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config', 'test_mode.json'),  # 프로젝트 루트 기준 경로
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'test_mode.json')  # 로컬 상대 경로
    ]
    
    # 환경 변수에서 경로를 가져오거나 기본 경로 목록 사용
    test_config_path = env.get('TEST_CONFIG_PATH')
    
    # 파일 열기 시도
    config_loaded = False
    if test_config_path:
        try:
            with open(test_config_path, 'r') as f:
                test_config = json.load(f)
                logger.info(f"테스트 설정 로드 완료: {test_config_path}")
                config_loaded = True
        except Exception as e:
            logger.warning(f"지정된 경로에서 테스트 설정 로드 실패: {test_config_path} - {e}")
    
    # 지정된 경로에서 로드 실패한 경우 기본 경로 목록 시도
    if not config_loaded:
        for path in default_paths:
            try:
                with open(path, 'r') as f:
                    test_config = json.load(f)
                    logger.info(f"테스트 설정 로드 완료: {path}")
                    config_loaded = True
                    break
            except Exception as e:
                logger.warning(f"테스트 설정 로드 실패: {path} - {e}")
    
    # 모든 경로에서 로드 실패한 경우 기본 설정 사용
    if not config_loaded:
        logger.warning("테스트 설정 파일을 찾을 수 없어 기본 설정을 사용합니다.")
        test_config = {
            "use_mock_data": True,
            "symbols": ["BTC/USDT", "ETH/USDT"],
            "timeframes": ["5m", "15m", "1h"],
            "mock_data": {
                "price_volatility": 0.02,
                "volume_volatility": 0.05,
                "trend_bias": 0.0
            },
            "health_check": {
                "interval": 60,
                "timeout": 5,
                "max_failures": 3
            },
            "circuit_breaker": {
                "failure_threshold": 5,
                "recovery_timeout": 60,
                "half_open_timeout": 30
            },
            "retry": {
                "max_retries": 3,
                "base_delay": 2.0,
                "max_delay": 30.0
            },
            "fallback": {
                "use_cache": True,
                "cache_ttl": 3600
            }
        }

class ResilientDataCollector:
    """
    Resilient wrapper around the standard DataCollector with enhanced error handling.
    """
    
    def __init__(self):
        """Initialize the resilient data collector."""
        # Initialize Vault client for secure access to secrets
        self.vault_client = get_vault_client()
        
        # Get configuration from Vault with fallback to environment variables
        api_key = get_string_secret('BINANCE_API_KEY', env.get('BINANCE_API_KEY', ''))
        api_secret = get_string_secret('BINANCE_API_SECRET', env.get('BINANCE_API_SECRET', ''))
        
        # Get trading symbols and timeframes from Vault with fallback to test config
        default_symbols = test_config.get('symbols', ['BTC/USDT', 'ETH/USDT'])
        default_timeframes = test_config.get('timeframes', ['5m', '15m', '1h'])
        
        self.symbols = get_list_secret('TRADING_SYMBOLS', default_symbols)
        self.timeframes = get_list_secret('TIMEFRAMES', default_timeframes)
        
        # Initialize the underlying collector with the retrieved secrets
        self.collector = DataCollector(api_key=api_key, api_secret=api_secret)
        
        # Initialize other configuration parameters
        self.is_running = False
        self.use_mock_data = test_mode and test_config.get('use_mock_data', False)
        self.mock_data_config = test_config.get('mock_data', {})
        self.health_check_config = test_config.get('health_check', {})
        self.performance_config = test_config.get('performance', {})
        
        # Initialize cache for fallback data
        self.data_cache = {}
        
        logger.info(f"Initialized ResilientDataCollector (test_mode={test_mode}, use_mock_data={self.use_mock_data})")
        logger.info(f"Configured with {len(self.symbols)} symbols and {len(self.timeframes)} timeframes")
    
    async def start(self):
        """Start the resilient data collection service."""
        if self.is_running:
            logger.warning("Resilient data collector is already running")
            return
        
        self.is_running = True
        logger.info("Starting resilient data collection service")
        
        tasks = []
        
        # Add health check task if enabled
        if self.health_check_config.get('enabled', False):
            tasks.append(asyncio.create_task(self._health_check_loop()))
        
        # Start the underlying collector with robust error handling
        try:
            if self.use_mock_data:
                logger.info("Using mock data instead of real data collection")
                tasks.append(asyncio.create_task(self._mock_data_loop()))
            else:
                # Start the standard collector with our robust wrapper
                await self._start_collector_with_resilience()
        except Exception as e:
            logger.error(f"Failed to start data collector: {e}")
            if self.use_mock_data:
                logger.info("Falling back to mock data generation")
                tasks.append(asyncio.create_task(self._mock_data_loop()))
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Resilient data collection tasks cancelled")
        except Exception as e:
            logger.error(f"Error in resilient data collection: {e}")
        finally:
            await self.stop()
    
    @robust_operation()
    async def _start_collector_with_resilience(self):
        """Start the standard collector with robust error handling."""
        await self.collector.start()
    
    async def stop(self):
        """Stop the resilient data collection service."""
        if not self.is_running:
            return
        
        self.is_running = False
        logger.info("Stopping resilient data collection service")
        
        try:
            await self.collector.stop()
        except Exception as e:
            logger.error(f"Error stopping data collector: {e}")
        
        logger.info("Resilient data collection service stopped")
    
    async def _health_check_loop(self):
        """Periodic health check loop."""
        interval = self.health_check_config.get('interval', 60)
        timeout = self.health_check_config.get('timeout', 5)
        max_failures = self.health_check_config.get('max_failures', 3)
        failure_count = 0
        
        logger.info(f"Starting health check loop (interval={interval}s, timeout={timeout}s, max_failures={max_failures})")
        
        while self.is_running:
            try:
                health_status = await self._perform_health_check(timeout)
                
                if health_status['healthy']:
                    if failure_count > 0:
                        logger.info(f"Health check recovered after {failure_count} failures")
                        failure_count = 0
                else:
                    failure_count += 1
                    logger.warning(f"Health check failed ({failure_count}/{max_failures}): {health_status['reason']}")
                    
                    if failure_count >= max_failures:
                        logger.error(f"Health check failed {failure_count} times, attempting recovery")
                        await self._attempt_recovery(health_status)
                        failure_count = 0
            except Exception as e:
                logger.error(f"Error in health check: {e}")
                failure_count += 1
            
            await asyncio.sleep(interval)
    
    async def _perform_health_check(self, timeout: int) -> Dict[str, Any]:
        """
        Perform a comprehensive health check on the data collector.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Dict[str, Any]: Health status with 'healthy' boolean and 'reason' string
        """
        result = {
            'healthy': True,
            'reason': '',
            'components': {}
        }
        
        try:
            # 1. Check Vault connectivity
            try:
                # Try to access a simple secret as a connectivity test
                self.vault_client.get_secret_with_fallback('health_check', None)
                result['components']['vault'] = {'status': 'ok'}
            except Exception as e:
                result['components']['vault'] = {'status': 'error', 'message': str(e)}
                result['healthy'] = False
                result['reason'] = f"Vault connectivity issue: {str(e)}"
            
            # 2. Check InfluxDB connectivity
            try:
                influx_url = self.collector.influx_url
                influx_org = self.collector.influx_org
                
                if not influx_url or not influx_org:
                    result['components']['influxdb'] = {'status': 'error', 'message': 'Configuration incomplete'}
                    result['healthy'] = False
                    result['reason'] = "InfluxDB configuration is incomplete"
                else:
                    # In a real implementation, you would check actual connectivity
                    # For now, we just check if the configuration exists
                    result['components']['influxdb'] = {'status': 'ok'}
            except Exception as e:
                result['components']['influxdb'] = {'status': 'error', 'message': str(e)}
                result['healthy'] = False
                result['reason'] = f"InfluxDB issue: {str(e)}"
            
            # 3. Check data processing status
            if self.use_mock_data:
                # For mock data, check if we have recent entries in the cache
                if not self.data_cache:
                    result['components']['data_processing'] = {'status': 'warning', 'message': 'No data in cache'}
                else:
                    # Check the age of the most recent entry
                    newest_entry = max(
                        (entry['timestamp'] for entry in self.data_cache.values()),
                        default=datetime.min
                    )
                    age_seconds = (datetime.now() - newest_entry).total_seconds()
                    
                    if age_seconds > 300:  # 5 minutes
                        result['components']['data_processing'] = {
                            'status': 'warning', 
                            'message': f'Data is stale ({age_seconds:.1f}s old)'
                        }
                    else:
                        result['components']['data_processing'] = {'status': 'ok'}
            else:
                # For real data collection, we would check the collector's status
                # This is a placeholder for a real implementation
                result['components']['data_processing'] = {'status': 'ok'}
            
            # 4. Check memory usage
            try:
                import psutil
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                if memory_mb > 500:  # 500 MB threshold
                    result['components']['memory'] = {
                        'status': 'warning', 
                        'message': f'High memory usage: {memory_mb:.1f} MB'
                    }
                else:
                    result['components']['memory'] = {'status': 'ok', 'value': f'{memory_mb:.1f} MB'}
            except Exception as e:
                result['components']['memory'] = {'status': 'unknown', 'message': str(e)}
            
            return result
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {'healthy': False, 'reason': f"Health check error: {e}", 'components': {}}
    
    async def _attempt_recovery(self, health_status: Dict[str, Any]):
        """Attempt to recover from an unhealthy state."""
        logger.info(f"Attempting recovery of data collector: {health_status['reason']}")
        
        try:
            # Check which components need recovery
            components = health_status.get('components', {})
            
            # 1. Handle Vault issues
            if components.get('vault', {}).get('status') == 'error':
                logger.info("Attempting to reconnect to Vault")
                # Clear the vault client cache and reinitialize
                from src.utils.vault_helper import clear_cache
                clear_cache()
                self.vault_client = get_vault_client()
            
            # 2. Handle InfluxDB issues
            if components.get('influxdb', {}).get('status') == 'error':
                logger.info("Attempting to reconnect to InfluxDB")
                # In a real implementation, you would reinitialize the InfluxDB connection
            
            # 3. Handle data processing issues
            if not self.use_mock_data:
                # For real data collection, restart the collector
                logger.info("Restarting data collector")
                await self.collector.stop()
                await asyncio.sleep(5)
                await self._start_collector_with_resilience()
            
            # 4. Handle memory issues
            if components.get('memory', {}).get('status') == 'warning':
                logger.info("Attempting to reduce memory usage")
                # Clear caches and request garbage collection
                self.data_cache.clear()
                import gc
                gc.collect()
            
            logger.info("Recovery actions completed")
        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
            
            # If recovery fails, try a more aggressive approach
            if not self.use_mock_data:
                logger.warning("Attempting aggressive recovery by restarting the collector")
                try:
                    await self.collector.stop()
                    await asyncio.sleep(10)  # Longer wait
                    await self._start_collector_with_resilience()
                except Exception as e2:
                    logger.error(f"Aggressive recovery failed: {e2}")
            
            # If we're using mock data and recovery failed, switch to a simpler mock data generation
            if self.use_mock_data:
                logger.warning("Switching to simplified mock data generation")
                self.mock_data_config['price_volatility'] = 0.01
                self.mock_data_config['volume_volatility'] = 0.02
                self.data_cache.clear()
    
    async def _mock_data_loop(self):
        """
        Generate and store mock OHLCV data.
        """
        logger.info("Starting mock data generation loop")
        
        # Use symbols and timeframes from Vault integration
        symbols = self.symbols
        timeframes = self.timeframes
        
        logger.debug(f"Generating mock data for symbols: {symbols}")
        logger.debug(f"Generating mock data for timeframes: {timeframes}")
        
        price_volatility = self.mock_data_config.get('price_volatility', 0.02)
        volume_volatility = self.mock_data_config.get('volume_volatility', 0.05)
        trend_bias = self.mock_data_config.get('trend_bias', 0.0)
        
        # Set random seed for reproducibility if specified
        if 'seed' in self.mock_data_config:
            random.seed(self.mock_data_config['seed'])
            np.random.seed(self.mock_data_config['seed'])
        
        # Base prices for different symbols
        base_prices = {
            'BTC/USDT': 50000.0,
            'ETH/USDT': 3000.0
        }
        
        # Use default values for symbols not in the dictionary
        for symbol in symbols:
            if symbol not in base_prices:
                base_prices[symbol] = 100.0
        
        while self.is_running:
            current_time = datetime.now()
            
            for symbol in symbols:
                base_price = base_prices[symbol]
                
                for timeframe in timeframes:
                    try:
                        # Generate mock OHLCV data
                        mock_data = self._generate_mock_ohlcv(
                            symbol=symbol,
                            timeframe=timeframe,
                            base_price=base_price,
                            current_time=current_time,
                            price_volatility=price_volatility,
                            volume_volatility=volume_volatility,
                            trend_bias=trend_bias
                        )
                        
                        # Store mock data (in a real implementation, this would go to InfluxDB)
                        self._store_mock_data(symbol, timeframe, mock_data)
                        
                        logger.debug(f"Generated mock data for {symbol} {timeframe}")
                    except Exception as e:
                        logger.error(f"Error generating mock data for {symbol} {timeframe}: {e}")
            
            # Determine sleep time based on shortest timeframe
            sleep_time = 60  # Default to 1 minute
            if '1m' in timeframes:
                sleep_time = 60
            elif '5m' in timeframes:
                sleep_time = 60  # Still update every minute but with 5m data
            
            await asyncio.sleep(sleep_time)
    
    def _generate_mock_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        base_price: float,
        current_time: datetime,
        price_volatility: float = 0.02,
        volume_volatility: float = 0.05,
        trend_bias: float = 0.0
    ) -> pd.DataFrame:
        """
        Generate mock OHLCV data for a symbol and timeframe.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe (e.g., '5m', '1h')
            base_price: Base price to generate around
            current_time: Current time
            price_volatility: Price volatility factor
            volume_volatility: Volume volatility factor
            trend_bias: Trend bias (-1.0 to 1.0, where 0 is neutral)
            
        Returns:
            pd.DataFrame: DataFrame with OHLCV data
        """
        # Determine number of candles based on timeframe
        if timeframe.endswith('m'):
            minutes = int(timeframe[:-1])
            num_candles = 60 // minutes  # Candles per hour
        elif timeframe.endswith('h'):
            hours = int(timeframe[:-1])
            num_candles = 24 // hours  # Candles per day
        else:
            num_candles = 24  # Default to daily candles
        
        # Limit to a reasonable number
        num_candles = min(num_candles, 24)
        
        # Calculate time delta based on timeframe
        if timeframe.endswith('m'):
            delta = timedelta(minutes=int(timeframe[:-1]))
        elif timeframe.endswith('h'):
            delta = timedelta(hours=int(timeframe[:-1]))
        elif timeframe.endswith('d'):
            delta = timedelta(days=int(timeframe[:-1]))
        else:
            delta = timedelta(hours=1)  # Default to 1 hour
        
        # Generate timestamps
        timestamps = [(current_time - delta * i).timestamp() * 1000 for i in range(num_candles)]
        timestamps.reverse()  # Oldest first
        
        # Generate price data with random walk and trend bias
        price = base_price
        prices = []
        
        for _ in range(num_candles):
            # Random price change with trend bias
            change = np.random.normal(trend_bias, price_volatility) * price
            price += change
            
            # Generate OHLC based on this price
            open_price = price
            high_price = price * (1 + abs(np.random.normal(0, price_volatility * 0.5)))
            low_price = price * (1 - abs(np.random.normal(0, price_volatility * 0.5)))
            close_price = price * (1 + np.random.normal(0, price_volatility * 0.3))
            
            # Ensure high >= open/close >= low
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            # Generate volume
            volume = base_price * 10 * (1 + np.random.normal(0, volume_volatility))
            
            prices.append([open_price, high_price, low_price, close_price, volume])
        
        # Create DataFrame
        df = pd.DataFrame(
            prices,
            columns=['open', 'high', 'low', 'close', 'volume'],
            index=timestamps
        )
        
        return df
    
    def _store_mock_data(self, symbol: str, timeframe: str, data: pd.DataFrame):
        """
        Store mock OHLCV data (in memory for this example).
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            data: OHLCV data
        """
        key = f"{symbol}_{timeframe}"
        self.data_cache[key] = {
            'data': data,
            'timestamp': datetime.now()
        }
        
        # In a real implementation, you would store this in InfluxDB
        # For example:
        # self._store_to_influxdb(symbol, timeframe, data)
    
    def _store_to_influxdb(self, symbol: str, timeframe: str, data: pd.DataFrame):
        """
        Store OHLCV data to InfluxDB.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            data: OHLCV data
        """
        # This is a placeholder for actual InfluxDB storage
        # In a real implementation, you would use the collector's InfluxDB client
        pass


async def main():
    """
    메인 함수 - 복원력 있는 데이터 수집기를 시작합니다.
    """
    # 로깅 설정
    setup_logging()
    logger.info("복원력 있는 데이터 수집기 시작 중...")
    
    # 환경 변수 확인
    required_vars = ['VAULT_ADDR', 'VAULT_TOKEN']
    missing_vars = [var for var in required_vars if not env.get(var)]
    
    if missing_vars:
        logger.error(f"필수 환경 변수가 없습니다: {', '.join(missing_vars)}")
        logger.info("환경 변수를 설정하거나 init_vault.py를 실행하여 Vault를 초기화하세요.")
        return
    
    # Vault 연결 확인
    try:
        vault_client = get_vault_client()
        # 간단한 연결 테스트
        get_string_secret('health_check', 'ok')
        logger.info("Vault 연결 성공")
    except Exception as e:
        logger.error(f"Vault 연결 실패: {e}")
        logger.info("init_vault.py를 실행하여 Vault를 초기화하세요.")
        return
    
    # 데이터 수집기 초기화 및 실행
    collector = None
    try:
        # 데이터 수집기 초기화
        collector = ResilientDataCollector()
        logger.info("데이터 수집기 초기화 완료")
        
        # 시그널 핸들러 등록
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, lambda s, f: asyncio.create_task(shutdown(collector)))
        
        # 데이터 수집기 시작
        await collector.start()
        
    except Exception as e:
        logger.error(f"데이터 수집기 실행 오류: {e}")
        if collector:
            await collector.stop()


async def shutdown(collector):
    """
    안전하게 서비스를 종료합니다.
    
    Args:
        collector: 데이터 수집기 인스턴스
    """
    logger.info("서비스 종료 중...")
    if collector:
        await collector.stop()
    logger.info("서비스 종료 완료")


def signal_handler():
    """Signal handler for graceful shutdown."""
    logger.info("Shutdown signal received")
    
    # Get the event loop
    loop = asyncio.get_event_loop()
    
    # Stop the loop
    loop.stop()


if __name__ == "__main__":
    # Set up signal handlers
    loop = asyncio.get_event_loop()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        # Run the main function
        loop.run_until_complete(main())
    finally:
        # Close the event loop
        loop.close()
        logger.info("Event loop closed")
