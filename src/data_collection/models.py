"""
Binance 데이터 모델 정의

이 모듈은 OHLCV 데이터 및 관련 데이터 구조를 정의합니다.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class OHLCVData:
    """
    OHLCV 데이터 클래스
    
    캔들 데이터를 표현하는 데이터 클래스입니다.
    """
    timestamp: int  # 밀리초 단위 타임스탬프
    open: float     # 시가
    high: float     # 고가
    low: float      # 저가
    close: float    # 종가
    volume: float   # 거래량
    
    @classmethod
    def from_list(cls, data: List) -> 'OHLCVData':
        """
        리스트에서 OHLCV 데이터 생성
        
        Args:
            data: OHLCV 데이터 리스트 [time, open, high, low, close, volume]
        
        Returns:
            OHLCVData: OHLCV 데이터 객체
        """
        if len(data) < 6:
            raise ValueError("OHLCV 데이터는 최소 6개의 요소가 필요합니다.")
        
        return cls(
            timestamp=int(data[0]),
            open=float(data[1]),
            high=float(data[2]),
            low=float(data[3]),
            close=float(data[4]),
            volume=float(data[5])
        )
    
    def to_list(self) -> List:
        """
        OHLCV 데이터를 리스트로 변환
        
        Returns:
            List: OHLCV 데이터 리스트 [time, open, high, low, close, volume]
        """
        return [
            self.timestamp,
            self.open,
            self.high,
            self.low,
            self.close,
            self.volume
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        OHLCV 데이터를 딕셔너리로 변환
        
        Returns:
            Dict: OHLCV 데이터 딕셔너리
        """
        return {
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'datetime': datetime.fromtimestamp(self.timestamp / 1000).isoformat()
        }
    
    def is_valid(self) -> bool:
        """
        OHLCV 데이터 유효성 검사
        
        Returns:
            bool: 유효성 여부
        """
        # 타임스탬프 확인
        if self.timestamp <= 0:
            return False
        
        # 가격 데이터 확인
        if self.open < 0 or self.high < 0 or self.low < 0 or self.close < 0:
            return False
        
        # 거래량 확인
        if self.volume < 0:
            return False
        
        # 고가가 저가보다 낮은 경우
        if self.high < self.low:
            return False
        
        # 고가가 시가나 종가보다 낮은 경우
        if self.high < self.open or self.high < self.close:
            return False
        
        # 저가가 시가나 종가보다 높은 경우
        if self.low > self.open or self.low > self.close:
            return False
        
        return True


@dataclass
class MarketData:
    """
    시장 데이터 클래스
    
    특정 심볼과 타임프레임에 대한 OHLCV 데이터 모음입니다.
    """
    symbol: str                # 심볼 (예: BTC/USDT)
    timeframe: str             # 타임프레임 (예: 5m)
    candles: List[OHLCVData]   # OHLCV 캔들 목록
    
    def add_candle(self, candle: OHLCVData) -> None:
        """
        캔들 추가
        
        Args:
            candle: 추가할 OHLCV 캔들
        """
        # 유효성 검사
        if not candle.is_valid():
            raise ValueError("유효하지 않은 OHLCV 데이터입니다.")
        
        # 중복 검사
        for existing_candle in self.candles:
            if existing_candle.timestamp == candle.timestamp:
                # 기존 캔들 업데이트
                existing_index = self.candles.index(existing_candle)
                self.candles[existing_index] = candle
                return
        
        # 새 캔들 추가
        self.candles.append(candle)
        
        # 타임스탬프 기준 정렬
        self.candles.sort(key=lambda x: x.timestamp)
    
    def get_candle_at(self, timestamp: int) -> Optional[OHLCVData]:
        """
        특정 타임스탬프의 캔들 조회
        
        Args:
            timestamp: 조회할 타임스탬프
        
        Returns:
            Optional[OHLCVData]: 해당 타임스탬프의 캔들 또는 None
        """
        for candle in self.candles:
            if candle.timestamp == timestamp:
                return candle
        
        return None
    
    def to_dataframe(self):
        """
        데이터프레임으로 변환
        
        Returns:
            pandas.DataFrame: OHLCV 데이터프레임
        """
        import pandas as pd
        
        # 캔들 데이터를 딕셔너리 목록으로 변환
        data = [candle.to_dict() for candle in self.candles]
        
        # 데이터프레임 생성
        df = pd.DataFrame(data)
        
        # 타임스탬프를 인덱스로 설정
        if not df.empty and 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('datetime', inplace=True)
        
        return df
