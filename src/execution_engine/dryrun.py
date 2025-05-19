"""
드라이런 모듈

이 모듈은 실제 거래 없이 거래 실행 엔진을 테스트하는 기능을 제공합니다.
"""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional

from src.execution_engine.connector import BinanceConnector, setup_binance_connector
from src.execution_engine.trading import ExecutionEngine

logger = logging.getLogger(__name__)

class DryRunEngine:
    """드라이런 실행 엔진 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        드라이런 엔진 초기화
        
        Args:
            config: 애플리케이션 설정
        """
        self.config = config
        
        # Freqtrade 설정 강제로 드라이런 모드로 설정
        freqtrade_config = config.get("freqtrade_config", "config/freqtrade.json")
        self.connector = setup_binance_connector(freqtrade_config)
        
        # 설정이 드라이런 모드인지 확인
        if not self.connector.is_dry_run():
            logger.warning("설정이 드라이런 모드가 아닙니다. 강제로 드라이런 모드로 설정합니다.")
            self.connector.config["dry_run"] = True
        
        # 실행 엔진 초기화
        self.engine = ExecutionEngine(config)
        
        # 가상 주문 목록
        self.orders = []
        
        logger.info("드라이런 엔진 초기화됨")
    
    async def start(self):
        """드라이런 엔진 시작"""
        logger.info("드라이런 엔진 시작됨")
        
        # 실행 엔진 시작
        await self.engine.start()
        
        # 테스트 주문 실행
        await self._run_test_orders()
    
    async def stop(self):
        """드라이런 엔진 중지"""
        logger.info("드라이런 엔진 중지됨")
        
        # 실행 엔진 중지
        await self.engine.stop()
    
    async def _run_test_orders(self):
        """테스트 주문 실행"""
        # 테스트할 페어 목록
        test_pairs = self.connector.exchange_config.get("pair_whitelist", ["BTC/USDT"])
        
        # 각 페어에 대해 테스트 주문 실행
        for pair in test_pairs:
            # 매수 주문 테스트
            buy_order = await self.engine.place_order(
                pair=pair,
                side="buy",
                amount=0.01,
                price=None,  # 시장가 주문
                order_type="market"
            )
            
            if buy_order:
                self.orders.append(buy_order)
                logger.info(f"테스트 매수 주문 실행됨: {buy_order}")
            
            # 잠시 대기
            await asyncio.sleep(1)
            
            # 매도 주문 테스트
            sell_order = await self.engine.place_order(
                pair=pair,
                side="sell",
                amount=0.01,
                price=None,  # 시장가 주문
                order_type="market"
            )
            
            if sell_order:
                self.orders.append(sell_order)
                logger.info(f"테스트 매도 주문 실행됨: {sell_order}")
            
            # 잠시 대기
            await asyncio.sleep(1)
            
            # 지정가 주문 테스트
            current_price = 50000.0  # 임의의 가격 (실제로는 현재 시장 가격을 가져와야 함)
            limit_buy_order = await self.engine.place_order(
                pair=pair,
                side="buy",
                amount=0.01,
                price=current_price * 0.95,  # 현재 가격보다 5% 낮게
                order_type="limit"
            )
            
            if limit_buy_order:
                self.orders.append(limit_buy_order)
                logger.info(f"테스트 지정가 매수 주문 실행됨: {limit_buy_order}")
        
        logger.info(f"총 {len(self.orders)}개의 테스트 주문이 실행되었습니다.")
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """주문 목록 반환"""
        return self.orders


def start_dryrun(config: Dict[str, Any]):
    """
    드라이런 실행 시작
    
    Args:
        config: 애플리케이션 설정
    """
    logger.info("드라이런 모드 시작...")
    
    # 이벤트 루프 가져오기
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # 이벤트 루프가 없는 경우 새로 생성
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # 드라이런 엔진 초기화
    engine = DryRunEngine(config)
    
    try:
        # 드라이런 엔진 시작
        loop.run_until_complete(engine.start())
        
        # 잠시 대기 (테스트 주문 처리를 위해)
        loop.run_until_complete(asyncio.sleep(5))
        
        # 주문 결과 출력
        orders = engine.get_orders()
        logger.info(f"드라이런 테스트 결과: {len(orders)}개의 주문이 처리되었습니다.")
        for order in orders:
            logger.info(f"주문 정보: {order}")
        
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.exception(f"드라이런 실행 중 오류 발생: {e}")
    finally:
        # 드라이런 엔진 중지
        loop.run_until_complete(engine.stop())
        
        # 이벤트 루프 종료
        loop.close()
        
    logger.info("드라이런 모드 종료")
