"""
pytest 구성 파일 - 테스트를 위한 픽스처 및 공통 설정
"""
import pytest


@pytest.fixture
def sample_ohlcv_data():
    """샘플 OHLCV 데이터 픽스처"""
    return [
        # timestamp, open, high, low, close, volume
        [1625097600000, 35000.0, 35500.0, 34800.0, 35200.0, 100.0],
        [1625097900000, 35200.0, 35800.0, 35100.0, 35600.0, 150.0],
        [1625098200000, 35600.0, 36000.0, 35400.0, 35900.0, 200.0],
    ]


@pytest.fixture
def mock_binance_api():
    """Binance API 모킹 픽스처"""
    # 실제 구현은 나중에 추가
    pass
