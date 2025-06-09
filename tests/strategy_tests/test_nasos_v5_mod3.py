#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
NASOSv5_mod3 전략 단위 테스트
"""

import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

# 전략 클래스 가져오기
from user_data.strategies.NASOSv5_mod3 import NASOSv5_mod3


class TestNASOSv5Mod3Strategy(unittest.TestCase):
    """NASOSv5_mod3 전략에 대한 단위 테스트"""

    def setUp(self):
        """테스트 데이터 및 전략 인스턴스 설정"""
        # 전략 인스턴스 생성
        self.strategy = NASOSv5_mod3(config={})
        
        # 테스트 데이터프레임 생성
        self.test_data = self.create_test_dataframe()
        
        # 데이터 프로세서 모의 객체 설정
        self.strategy.dp = MagicMock()
        self.strategy.dp.get_pair_dataframe = MagicMock(return_value=self.test_data)

    def create_test_dataframe(self):
        """테스트용 OHLCV 데이터프레임 생성"""
        # 100개의 캔들 데이터 생성
        np.random.seed(42)  # 재현 가능한 결과를 위한 시드 설정
        
        # 가격 데이터 생성 (BTC 가격 범위 시뮬레이션)
        base_price = 20000
        price_volatility = 1000
        
        # 랜덤 가격 변동 생성
        random_changes = np.random.normal(0, 1, 100).cumsum() * price_volatility / 10
        closes = base_price + random_changes
        
        # 고가는 종가보다 0-2% 높게, 저가는 종가보다 0-2% 낮게 설정
        highs = closes * (1 + np.random.random(100) * 0.02)
        lows = closes * (1 - np.random.random(100) * 0.02)
        opens = closes.copy()
        opens[1:] = closes[:-1]  # 이전 종가를 다음 시가로 설정
        
        # 거래량 데이터 생성
        volumes = np.random.random(100) * 10 + 1  # 1-11 범위의 거래량
        
        # 데이터프레임 생성
        df = pd.DataFrame({
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })
        
        return df

    def test_populate_indicators(self):
        """지표 계산 테스트"""
        # 지표 계산 실행
        df = self.strategy.populate_indicators(self.test_data.copy(), {})
        
        # 필수 지표가 계산되었는지 확인
        self.assertIn('rsi_fast', df.columns, "RSI Fast 지표가 계산되지 않았습니다")
        self.assertIn('rsi_slow', df.columns, "RSI Slow 지표가 계산되지 않았습니다")
        self.assertIn('rsi', df.columns, "RSI 지표가 계산되지 않았습니다")
        self.assertIn('EWO', df.columns, "EWO 지표가 계산되지 않았습니다")
        self.assertIn('sma_9', df.columns, "SMA 9 지표가 계산되지 않았습니다")
        self.assertIn('ema_100', df.columns, "EMA 100 지표가 계산되지 않았습니다")
        self.assertIn('hma_50', df.columns, "HMA 50 지표가 계산되지 않았습니다")
        
        # 기본 이동평균 확인
        base_length = int(self.strategy.base_nb_candles_buy.value)
        ma_col = f"ma_{base_length}"
        self.assertIn(ma_col, df.columns, f"{ma_col} 지표가 계산되지 않았습니다")
        
        # 펌핑 지표 확인
        self.assertIn('ispumping', df.columns, "ispumping 지표가 계산되지 않았습니다")
        self.assertIn('islongpumping', df.columns, "islongpumping 지표가 계산되지 않았습니다")
        self.assertIn('recentispumping', df.columns, "recentispumping 지표가 계산되지 않았습니다")
        
        # 지표 값 범위 확인
        self.assertTrue(all(0 <= x <= 100 for x in df['rsi_fast'].dropna()), "RSI Fast 값이 유효 범위(0-100)를 벗어났습니다")
        self.assertTrue(all(0 <= x <= 100 for x in df['rsi_slow'].dropna()), "RSI Slow 값이 유효 범위(0-100)를 벗어났습니다")
        
        # 펌핑 지표가 0 또는 1인지 확인
        self.assertTrue(all(x in [0, 1] for x in df['ispumping'].dropna()), "ispumping 값이 유효하지 않습니다 (0 또는 1이어야 함)")
        self.assertTrue(all(x in [0, 1] for x in df['islongpumping'].dropna()), "islongpumping 값이 유효하지 않습니다 (0 또는 1이어야 함)")
        self.assertTrue(all(x in [0, 1] for x in df['recentispumping'].dropna()), "recentispumping 값이 유효하지 않습니다 (0 또는 1이어야 함)")

    def test_populate_buy_trend(self):
        """매수 신호 생성 테스트"""
        # 지표 계산
        df = self.strategy.populate_indicators(self.test_data.copy(), {})
        
        # 매수 신호 생성
        df = self.strategy.populate_buy_trend(df, {})
        
        # 매수 컬럼이 존재하는지 확인
        self.assertIn('buy', df.columns, "buy 컬럼이 생성되지 않았습니다")
        self.assertIn('buy_tag', df.columns, "buy_tag 컬럼이 생성되지 않았습니다")
        
        # 매수 신호가 0 또는 1인지 확인
        self.assertTrue(all(x in [0, 1] for x in df['buy']), "buy 값이 유효하지 않습니다 (0 또는 1이어야 함)")
        
        # 매수 태그가 올바른지 확인
        buy_tags = df.loc[df['buy'] == 1, 'buy_tag'].unique()
        for tag in buy_tags:
            self.assertIn(tag, ['ewo_bear', 'ewo_bull'], f"유효하지 않은 매수 태그: {tag}")

    def test_populate_sell_trend(self):
        """매도 신호 생성 테스트"""
        # 지표 계산
        df = self.strategy.populate_indicators(self.test_data.copy(), {})
        
        # 매도 신호 생성
        df = self.strategy.populate_sell_trend(df, {})
        
        # 매도 컬럼이 존재하는지 확인
        self.assertIn('sell', df.columns, "sell 컬럼이 생성되지 않았습니다")
        
        # 매도 신호가 0 또는 1인지 확인
        self.assertTrue(all(x in [0, 1] for x in df['sell']), "sell 값이 유효하지 않습니다 (0 또는 1이어야 함)")

    def test_custom_stoploss(self):
        """커스텀 손절매 로직 테스트"""
        # freqtrade.strategy에서 stoploss_from_open 함수 가져오기
        from freqtrade.strategy import stoploss_from_open
        
        # 다양한 수익률에 대한 손절매 값 테스트
        test_cases = [
            # (현재 수익률, 예상 손절매 결과)
            (-0.05, 1),  # 손실 상태: 기본 손절매 사용
            (self.strategy.pPF_1.value - 0.001, 1),  # 첫 번째 임계값 직전: 기본 손절매 사용
            (self.strategy.pPF_1.value + 0.001, self.strategy.pSL_1.value),  # 첫 번째 임계값 직후: 첫 번째 손절매 수준
            ((self.strategy.pPF_1.value + self.strategy.pPF_2.value) / 2, (self.strategy.pSL_1.value + self.strategy.pSL_2.value) / 2),  # 중간: 보간된 손절매
            (self.strategy.pPF_2.value + 0.001, self.strategy.pHSL.value),  # 두 번째 임계값 이후: 최종 손절매 수준
        ]
        
        # 테스트 케이스 실행
        for current_profit, expected_sl in test_cases:
            # 손절매 계산
            sl_result = self.strategy.custom_stoploss(
                pair="BTC/USDT",
                trade=None,
                current_time=None,
                current_rate=None,
                current_profit=current_profit
            )
            
            # 손절매 값이 예상과 일치하는지 확인
            if expected_sl == 1:
                self.assertEqual(sl_result, expected_sl, f"수익률 {current_profit}에 대한 손절매 값이 예상과 다릅니다 (예상: {expected_sl}, 실제: {sl_result})")
            else:
                # custom_stoploss 메서드의 로직에 따라 예상 결과 계산
                if current_profit < self.strategy.pPF_1.value:
                    expected_result = 1.0
                elif current_profit < self.strategy.pPF_2.value:
                    # 선형 보간 계산
                    profit_range = self.strategy.pPF_2.value - self.strategy.pPF_1.value
                    if profit_range > 0:
                        sl_profit = self.strategy.pSL_1.value + (
                            (current_profit - self.strategy.pPF_1.value) * 
                            (self.strategy.pSL_2.value - self.strategy.pSL_1.value) / profit_range
                        )
                    else:
                        sl_profit = self.strategy.pSL_1.value
                    expected_result = stoploss_from_open(sl_profit, current_profit)
                else:
                    expected_result = stoploss_from_open(self.strategy.pHSL.value, current_profit)
                
                # 결과 비교 (더 넓은 허용 오차 사용)
                self.assertAlmostEqual(sl_result, expected_result, places=2, 
                                     msg=f"수익률 {current_profit}에 대한 손절매 값이 예상과 다릅니다 (예상: {expected_result}, 실제: {sl_result})")
                
                # 디버깅을 위해 값 출력
                print(f"수익률: {current_profit:.4f}, 예상: {expected_result:.6f}, 실제: {sl_result:.6f}")

    def test_confirm_trade_entry(self):
        """거래 진입 확인 로직 테스트"""
        # 슬리피지 없는 경우 (가격이 마지막 종가와 동일)
        self.strategy.entry_retries = {}
        result = self.strategy.confirm_trade_entry(
            pair="BTC/USDT",
            order_type="limit",
            amount=0.1,
            rate=self.test_data['close'].iloc[-1],
            time_in_force="GTC",
            current_time=None
        )
        self.assertTrue(result, "슬리피지 없는 경우에도 거래가 확인되지 않았습니다")
        
        # 허용 가능한 슬리피지 (2%)
        self.strategy.entry_retries = {}
        result = self.strategy.confirm_trade_entry(
            pair="BTC/USDT",
            order_type="limit",
            amount=0.1,
            rate=self.test_data['close'].iloc[-1] * 1.02,
            time_in_force="GTC",
            current_time=None
        )
        self.assertTrue(result, "허용 가능한 슬리피지에서 거래가 확인되지 않았습니다")
        
        # 허용 불가능한 슬리피지 (5%)
        self.strategy.entry_retries = {}
        result = self.strategy.confirm_trade_entry(
            pair="BTC/USDT",
            order_type="limit",
            amount=0.1,
            rate=self.test_data['close'].iloc[-1] * 1.05,
            time_in_force="GTC",
            current_time=None
        )
        self.assertFalse(result, "허용 불가능한 슬리피지에서 거래가 확인되었습니다")
        self.assertEqual(self.strategy.entry_retries.get("BTC/USDT", 0), 1, "재시도 카운터가 증가하지 않았습니다")
        
        # 최대 재시도 횟수 초과 테스트
        self.strategy.entry_retries = {"BTC/USDT": 3}
        result = self.strategy.confirm_trade_entry(
            pair="BTC/USDT",
            order_type="limit",
            amount=0.1,
            rate=self.test_data['close'].iloc[-1] * 1.05,
            time_in_force="GTC",
            current_time=None
        )
        self.assertFalse(result, "최대 재시도 횟수 초과 후에도 거래가 확인되었습니다")
        self.assertEqual(self.strategy.entry_retries.get("BTC/USDT", 0), 0, "최대 재시도 후 카운터가 초기화되지 않았습니다")


if __name__ == '__main__':
    unittest.main()
