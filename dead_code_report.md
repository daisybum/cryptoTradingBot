# Dead Code 분석 보고서

생성 시간: 2025-05-24 15:55:14

## 요약

- 총 발견된 항목: 248개
- 영향 받은 파일: 45개
- 처리된 파일: 45개
- 변경된 항목: 248개
- 처리 모드: 주석 처리

## 코드 타입별 통계

- method: 92개
- function: 62개
- variable: 46개
- import: 19개
- class: 15개
- attribute: 14개

## 파일별 통계

- src/database/dal_extended.py: 22개
- src/analytics/notification_api.py: 19개
- src/api_server/models/models.py: 16개
- src/database/models.py: 11개
- src/database/dal.py: 9개
- src/database/influx_dal.py: 9개
- src/notifications/templates.py: 9개
- src/risk_manager/api.py: 9개
- src/utils/security.py: 9개
- src/database/repository.py: 8개
- src/api_server/routers/trades.py: 7개
- src/notifications/redis_publisher.py: 7개
- src/utils/ssl_manager.py: 7개
- src/api_server/routers/backtest.py: 6개
- src/api_server/routers/parameters.py: 6개
- src/cli/menu.py: 6개
- src/execution_engine/trading.py: 6개
- src/execution_engine/websocket_manager.py: 6개
- src/notifications/telegram_bot.py: 6개
- src/api_server/routers/bot.py: 5개
- src/api_server/routers/performance.py: 5개
- src/data_collection/historical_data_fetcher.py: 5개
- src/data_collection/models.py: 5개
- src/database/integration.py: 5개
- src/database/connection.py: 4개
- src/risk_manager/risk_manager_telegram.py: 4개
- src/analytics/api.py: 3개
- src/api_server/main.py: 3개
- src/data_collection/data_collector.py: 3개
- src/data_collection/resilient_service.py: 3개
- src/utils/env_loader.py: 3개
- src/analytics/performance.py: 2개
- src/analytics/visualization.py: 2개
- src/api_server/routers/auth.py: 2개
- src/data_collection/async_data_processor.py: 2개
- src/execution_engine/connector.py: 2개
- src/strategy_engine/backtesting.py: 2개
- src/strategy_engine/nasos_strategy.py: 2개
- src/strategy_engine/strategy_evaluator.py: 2개
- src/api_server/auth/auth.py: 1개
- src/notifications/manager.py: 1개
- src/strategy_engine/strategy_manager.py: 1개
- src/utils/config.py: 1개
- src/utils/logger.py: 1개
- src/utils/vault_helper.py: 1개

## 상세 항목 목록

### src/analytics/api.py

- 라인 67: unused function 'get_performance_metrics' (60% confidence)
  ```python
  @router.get("/metrics", response_model=PerformanceMetricsResponse)
  ```

- 라인 117: unused function 'generate_report' (60% confidence)
  ```python
  @router.post("/reports", response_model=ReportGenerationResponse)
  ```

- 라인 120: unused variable 'background_tasks' (100% confidence)
  ```python
      background_tasks: BackgroundTasks
  ```

### src/analytics/notification_api.py

- 라인 98: unused variable 'telegram_active' (60% confidence)
  ```python
      telegram_active: bool = Field(..., description="텔레그램 활성화 상태")
  ```

- 라인 99: unused variable 'redis_publisher_connected' (60% confidence)
  ```python
      redis_publisher_connected: bool = Field(..., description="Redis 발행자 연결 상태")
  ```

- 라인 100: unused variable 'redis_subscriber_connected' (60% confidence)
  ```python
      redis_subscriber_connected: bool = Field(..., description="Redis 구독자 연결 상태")
  ```

- 라인 103: unused variable 'uptime_seconds' (60% confidence)
  ```python
      uptime_seconds: float = Field(..., description="가동 시간 (초)")
  ```

- 라인 122: unused function 'send_general_notification' (60% confidence)
  ```python
  @router.post("/general", response_model=dict)
  ```

- 라인 125: unused variable 'background_tasks' (100% confidence)
  ```python
      background_tasks: BackgroundTasks,
  ```

- 라인 145: unused variable 'background_tasks' (100% confidence)
  ```python
      background_tasks: BackgroundTasks,
  ```

- 라인 165: unused variable 'background_tasks' (100% confidence)
  ```python
      background_tasks: BackgroundTasks,
  ```

- 라인 178: unused function 'send_risk_notification' (60% confidence)
  ```python
  @router.post("/risk", response_model=dict)
  ```

- 라인 181: unused variable 'background_tasks' (100% confidence)
  ```python
      background_tasks: BackgroundTasks,
  ```

- 라인 194: unused function 'send_system_notification' (60% confidence)
  ```python
  @router.post("/system", response_model=dict)
  ```

- 라인 197: unused variable 'background_tasks' (100% confidence)
  ```python
      background_tasks: BackgroundTasks,
  ```

- 라인 210: unused function 'send_performance_notification' (60% confidence)
  ```python
  @router.post("/performance", response_model=dict)
  ```

- 라인 213: unused variable 'background_tasks' (100% confidence)
  ```python
      background_tasks: BackgroundTasks,
  ```

- 라인 226: unused function 'generate_and_send_report' (60% confidence)
  ```python
  @router.post("/report/{report_type}", response_model=dict)
  ```

- 라인 231: unused variable 'background_tasks' (100% confidence)
  ```python
      background_tasks: BackgroundTasks = None,
  ```

- 라인 293: unused function 'get_notification_status' (60% confidence)
  ```python
  @router.get("/status", response_model=NotificationStatus)
  ```

- 라인 305: unused function 'start_notification_system' (60% confidence)
  ```python
  @router.post("/start", response_model=dict)
  ```

- 라인 317: unused function 'stop_notification_system' (60% confidence)
  ```python
  @router.post("/stop", response_model=dict)
  ```

### src/analytics/performance.py

- 라인 12: unused import 'math' (90% confidence)
  ```python
  import math
  ```

- 라인 315: unused variable 'daily_risk_free_rate' (60% confidence)
  ```python
          daily_risk_free_rate = self.risk_free_rate / 365
  ```

### src/analytics/visualization.py

- 라인 70: unused variable 'fig' (60% confidence)
  ```python
              fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
  ```

- 라인 181: unused variable 'fig' (60% confidence)
  ```python
              fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
  ```

### src/api_server/auth/auth.py

- 라인 58: unused attribute 'last_login' (60% confidence)
  ```python
      user.last_login = datetime.utcnow()
  ```

### src/api_server/main.py

- 라인 44: unused function 'root' (60% confidence)
  ```python
  @app.get("/", tags=["root"])
  ```

- 라인 52: unused function 'health_check' (60% confidence)
  ```python
  @app.get("/api/v1/health", tags=["health"])
  ```

- 라인 60: unused function 'protected_route' (60% confidence)
  ```python
  @app.get("/api/v1/protected", tags=["protected"])
  ```

### src/api_server/models/models.py

- 라인 27: unused variable 'last_login' (60% confidence)
  ```python
      last_login = Column(DateTime, nullable=True)
  ```

- 라인 58: unused variable 'active_trades' (60% confidence)
  ```python
      active_trades = Column(Integer, default=0)
  ```

- 라인 103: unused variable 'last_login' (60% confidence)
  ```python
      last_login: Optional[datetime] = None
  ```

- 라인 105: unused class 'Config' (60% confidence)
  ```python
      class Config:
  ```

- 라인 106: unused variable 'orm_mode' (60% confidence)
  ```python
          orm_mode = True
  ```

- 라인 143: unused class 'Config' (60% confidence)
  ```python
      class Config:
  ```

- 라인 144: unused variable 'orm_mode' (60% confidence)
  ```python
          orm_mode = True
  ```

- 라인 150: unused variable 'active_trades' (60% confidence)
  ```python
      active_trades: int
  ```

- 라인 163: unused variable 'active_trades' (60% confidence)
  ```python
      active_trades: Optional[int] = None
  ```

- 라인 171: unused class 'Config' (60% confidence)
  ```python
      class Config:
  ```

- 라인 172: unused variable 'orm_mode' (60% confidence)
  ```python
          orm_mode = True
  ```

- 라인 192: unused class 'Config' (60% confidence)
  ```python
      class Config:
  ```

- 라인 193: unused variable 'orm_mode' (60% confidence)
  ```python
          orm_mode = True
  ```

- 라인 214: unused class 'Config' (60% confidence)
  ```python
      class Config:
  ```

- 라인 215: unused variable 'orm_mode' (60% confidence)
  ```python
          orm_mode = True
  ```

- 라인 219: unused variable 'token_type' (60% confidence)
  ```python
      token_type: str
  ```

### src/api_server/routers/auth.py

- 라인 28: unused function 'login_for_access_token' (60% confidence)
  ```python
  @router.post("/token", response_model=Token)
  ```

- 라인 53: unused function 'register_user' (60% confidence)
  ```python
  @router.post("/register", response_model=UserResponse)
  ```

### src/api_server/routers/backtest.py

- 라인 27: unused function 'get_backtest_results' (60% confidence)
  ```python
  @router.get("/results", response_model=List[BacktestResultResponse])
  ```

- 라인 60: unused function 'get_backtest_result' (60% confidence)
  ```python
  @router.get("/results/{result_id}", response_model=BacktestResultResponse)
  ```

- 라인 77: unused function 'create_backtest_result' (60% confidence)
  ```python
  @router.post("/results", response_model=BacktestResultResponse)
  ```

- 라인 93: unused function 'delete_backtest_result' (60% confidence)
  ```python
  @router.delete("/results/{result_id}")
  ```

- 라인 162: unused function 'upload_backtest_result' (60% confidence)
  ```python
  @router.post("/upload-result")
  ```

- 라인 216: unused function 'compare_backtest_results' (60% confidence)
  ```python
  @router.get("/compare")
  ```

### src/api_server/routers/bot.py

- 라인 24: unused function 'get_bot_status' (60% confidence)
  ```python
  @router.get("/status", response_model=BotStatusResponse)
  ```

- 라인 39: unused function 'create_bot_status' (60% confidence)
  ```python
  @router.post("/status", response_model=BotStatusResponse)
  ```

- 라인 55: unused function 'update_bot_status' (60% confidence)
  ```python
  @router.put("/status", response_model=BotStatusResponse)
  ```

- 라인 110: unused function 'pause_bot' (60% confidence)
  ```python
  @router.post("/pause")
  ```

- 라인 125: unused function 'resume_bot' (60% confidence)
  ```python
  @router.post("/resume")
  ```

### src/api_server/routers/parameters.py

- 라인 24: unused function 'get_parameters' (60% confidence)
  ```python
  @router.get("/", response_model=List[ParameterResponse])
  ```

- 라인 43: unused function 'get_parameter' (60% confidence)
  ```python
  @router.get("/{parameter_id}", response_model=ParameterResponse)
  ```

- 라인 60: unused function 'create_parameter' (60% confidence)
  ```python
  @router.post("/", response_model=ParameterResponse)
  ```

- 라인 88: unused function 'update_parameter' (60% confidence)
  ```python
  @router.put("/{parameter_id}", response_model=ParameterResponse)
  ```

- 라인 116: unused function 'delete_parameter' (60% confidence)
  ```python
  @router.delete("/{parameter_id}")
  ```

- 라인 181: unused function 'update_strategy_parameters' (60% confidence)
  ```python
  @router.put("/strategy/{strategy_name}")
  ```

### src/api_server/routers/performance.py

- 라인 27: unused function 'get_performance_metrics' (60% confidence)
  ```python
  @router.get("/metrics", response_model=PerformanceMetrics)
  ```

- 라인 97: unused function 'get_equity_curve' (60% confidence)
  ```python
  @router.get("/equity-curve")
  ```

- 라인 147: unused function 'get_drawdown' (60% confidence)
  ```python
  @router.get("/drawdown")
  ```

- 라인 197: unused function 'get_monthly_returns' (60% confidence)
  ```python
  @router.get("/monthly-returns")
  ```

- 라인 236: unused function 'get_win_loss_distribution' (60% confidence)
  ```python
  @router.get("/win-loss-distribution")
  ```

### src/api_server/routers/trades.py

- 라인 24: unused function 'get_trades' (60% confidence)
  ```python
  @router.get("/", response_model=List[TradeResponse])
  ```

- 라인 65: unused function 'get_trade' (60% confidence)
  ```python
  @router.get("/{trade_id}", response_model=TradeResponse)
  ```

- 라인 82: unused function 'create_trade' (60% confidence)
  ```python
  @router.post("/", response_model=TradeResponse)
  ```

- 라인 95: unused function 'update_trade' (60% confidence)
  ```python
  @router.put("/{trade_id}", response_model=TradeResponse)
  ```

- 라인 132: unused function 'delete_trade' (60% confidence)
  ```python
  @router.delete("/{trade_id}")
  ```

- 라인 152: unused function 'get_daily_trade_summary' (60% confidence)
  ```python
  @router.get("/summary/daily", response_model=List[dict])
  ```

- 라인 200: unused function 'get_symbol_trade_summary' (60% confidence)
  ```python
  @router.get("/summary/symbols", response_model=List[dict])
  ```

### src/cli/menu.py

- 라인 24: unused import 'Layout' (90% confidence)
  ```python
  from rich.layout import Layout
  ```

- 라인 25: unused import 'Live' (90% confidence)
  ```python
  from rich.live import Live
  ```

- 라인 53: unused attribute 'verbosity' (60% confidence)
  ```python
          self.verbosity = "info"  # 기본 로깅 레벨
  ```

- 라인 487: unused variable 'options' (60% confidence)
  ```python
          options = [
  ```

- 라인 663: unused variable 'options' (60% confidence)
  ```python
          options = [
  ```

- 라인 752: unused variable 'options' (60% confidence)
  ```python
          options = [
  ```

### src/data_collection/async_data_processor.py

- 라인 175: unused method 'set_validation_callback' (60% confidence)
  ```python
      def set_validation_callback(self, callback: Callable[[List], bool]):
  ```

- 라인 184: unused method 'get_stats' (60% confidence)
  ```python
      def get_stats(self) -> Dict:
  ```

### src/data_collection/data_collector.py

- 라인 91: unused attribute 'docker_env' (60% confidence)
  ```python
          self.docker_env = self.env.get('DOCKER_ENV', 'true').lower() == 'true'
  ```

- 라인 92: unused attribute 'local_test' (60% confidence)
  ```python
          self.local_test = self.env.get('LOCAL_TEST', 'false').lower() == 'true'
  ```

- 라인 407: unused method '_get_last_candle_from_db' (60% confidence)
  ```python
      async def _get_last_candle_from_db(self, symbol: str, timeframe: str) -> Optional[List]:
  ```

### src/data_collection/historical_data_fetcher.py

- 라인 18: unused import 'statistics' (90% confidence)
  ```python
  import statistics  # 통계 기능 추가
  ```

- 라인 72: unused attribute 'rate_limit_ms' (60% confidence)
  ```python
          self.rate_limit_ms = 1200  # API 요청 간격 (밀리초)
  ```

- 라인 182: unused method 'fetch_ohlcv_dataframe' (60% confidence)
  ```python
      async def fetch_ohlcv_dataframe(self, symbol: str, timeframe: str, since: Optional[int] = None, limit: int = 1000) -> pd.DataFrame:
  ```

- 라인 276: unused method 'fetch_ohlcv_range' (60% confidence)
  ```python
      async def fetch_ohlcv_range(self, symbol: str, timeframe: str, start: int, end: int, limit: int = 1000) -> List:
  ```

- 라인 351: unused method 'fetch_recent_ohlcv' (60% confidence)
  ```python
      async def fetch_recent_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> List:
  ```

### src/data_collection/models.py

- 라인 26: unused method 'from_list' (60% confidence)
  ```python
      @classmethod
  ```

- 라인 49: unused method 'to_list' (60% confidence)
  ```python
      def to_list(self) -> List:
  ```

- 라인 127: unused method 'add_candle' (60% confidence)
  ```python
      def add_candle(self, candle: OHLCVData) -> None:
  ```

- 라인 152: unused method 'get_candle_at' (60% confidence)
  ```python
      def get_candle_at(self, timestamp: int) -> Optional[OHLCVData]:
  ```

- 라인 168: unused method 'to_dataframe' (60% confidence)
  ```python
      def to_dataframe(self):
  ```

### src/data_collection/resilient_service.py

- 라인 133: unused attribute 'performance_config' (60% confidence)
  ```python
          self.performance_config = test_config.get('performance', {})
  ```

- 라인 552: unused method '_store_to_influxdb' (60% confidence)
  ```python
      def _store_to_influxdb(self, symbol: str, timeframe: str, data: pd.DataFrame):
  ```

- 라인 603: unused variable 's' (100% confidence)
  ```python
              signal.signal(sig, lambda s, f: asyncio.create_task(shutdown(collector)))
  ```

### src/database/connection.py

- 라인 12: unused import 'Engine' (90% confidence)
  ```python
  from sqlalchemy import create_engine, Engine
  ```

- 라인 97: unused attribute 'default_bucket' (60% confidence)
  ```python
              self.default_bucket = bucket
  ```

- 라인 118: unused method 'get_influx_write_api' (60% confidence)
  ```python
      def get_influx_write_api(self):
  ```

- 라인 130: unused method 'get_influx_query_api' (60% confidence)
  ```python
      def get_influx_query_api(self):
  ```

### src/database/dal.py

- 라인 14: unused import 'asc' (90% confidence)
  ```python
  from sqlalchemy import func, and_, or_, desc, asc
  ```

- 라인 87: unused method 'get_by_id' (60% confidence)
  ```python
      def get_by_id(self, record_id: int) -> Optional[T]:
  ```

- 라인 100: unused method 'get_all' (60% confidence)
  ```python
      def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
  ```

- 라인 172: unused method 'get_by_trade_id' (60% confidence)
  ```python
      def get_by_trade_id(self, trade_id: str) -> Optional[Trade]:
  ```

- 라인 185: unused method 'get_open_trades' (60% confidence)
  ```python
      def get_open_trades(self, strategy: Optional[str] = None) -> List[Trade]:
  ```

- 라인 229: unused method 'get_trades_by_status' (60% confidence)
  ```python
      def get_trades_by_status(self, status: str, limit: int = 100) -> List[Trade]:
  ```

- 라인 245: unused method 'get_profit_stats' (60% confidence)
  ```python
      def get_profit_stats(self, strategy: Optional[str] = None,
  ```

- 라인 330: unused method 'get_latest_equity' (60% confidence)
  ```python
      def get_latest_equity(self) -> Optional[EquityCurve]:
  ```

- 라인 340: unused method 'get_equity_by_date_range' (60% confidence)
  ```python
      def get_equity_by_date_range(self, start_date: datetime, end_date: datetime,
  ```

### src/database/dal_extended.py

- 라인 13: unused import 'asc' (90% confidence)
  ```python
  from sqlalchemy import func, and_, or_, desc, asc
  ```

- 라인 28: unused class 'ParamSetDAL' (60% confidence)
  ```python
  class ParamSetDAL(BaseDAL[ParamSet]):
  ```

- 라인 36: unused method 'get_active_params' (60% confidence)
  ```python
      def get_active_params(self, strategy: str) -> Optional[ParamSet]:
  ```

- 라인 52: unused method 'get_params_by_strategy' (60% confidence)
  ```python
      def get_params_by_strategy(self, strategy: str) -> List[ParamSet]:
  ```

- 라인 67: unused method 'activate_param_set' (60% confidence)
  ```python
      def activate_param_set(self, param_id: int) -> bool:
  ```

- 라인 95: unused class 'StatsDailyDAL' (60% confidence)
  ```python
  class StatsDailyDAL(BaseDAL[StatsDaily]):
  ```

- 라인 127: unused method 'get_stats_by_date_range' (60% confidence)
  ```python
      def get_stats_by_date_range(self, start_date: date, end_date: date,
  ```

- 라인 156: unused method 'calculate_daily_stats' (60% confidence)
  ```python
      def calculate_daily_stats(self, target_date: date, strategy: Optional[str] = None,
  ```

- 라인 250: unused class 'OrderDAL' (60% confidence)
  ```python
  class OrderDAL(BaseDAL[Order]):
  ```

- 라인 258: unused method 'get_by_order_id' (60% confidence)
  ```python
      def get_by_order_id(self, order_id: str) -> Optional[Order]:
  ```

- 라인 291: unused method 'get_orders_by_date_range' (60% confidence)
  ```python
      def get_orders_by_date_range(self, start_date: datetime, end_date: datetime,
  ```

- 라인 321: unused class 'FillDAL' (60% confidence)
  ```python
  class FillDAL(BaseDAL[Fill]):
  ```

- 라인 329: unused method 'get_by_fill_id' (60% confidence)
  ```python
      def get_by_fill_id(self, fill_id: str) -> Optional[Fill]:
  ```

- 라인 342: unused method 'get_fills_by_order_id' (60% confidence)
  ```python
      def get_fills_by_order_id(self, order_id: str) -> List[Fill]:
  ```

- 라인 358: unused class 'OrderErrorDAL' (60% confidence)
  ```python
  class OrderErrorDAL(BaseDAL[OrderError]):
  ```

- 라인 366: unused method 'get_errors_by_order_id' (60% confidence)
  ```python
      def get_errors_by_order_id(self, order_id: str) -> List[OrderError]:
  ```

- 라인 381: unused method 'get_recent_errors' (60% confidence)
  ```python
      def get_recent_errors(self, limit: int = 50) -> List[OrderError]:
  ```

- 라인 397: unused class 'IndicatorSnapshotDAL' (60% confidence)
  ```python
  class IndicatorSnapshotDAL(BaseDAL[IndicatorSnapshot]):
  ```

- 라인 422: unused method 'get_snapshots_by_date_range' (60% confidence)
  ```python
      def get_snapshots_by_date_range(self, symbol: str, timeframe: str,
  ```

- 라인 445: unused class 'TradeSessionDAL' (60% confidence)
  ```python
  class TradeSessionDAL(BaseDAL[TradeSession]):
  ```

- 라인 453: unused method 'get_by_session_id' (60% confidence)
  ```python
      def get_by_session_id(self, session_id: str) -> Optional[TradeSession]:
  ```

- 라인 468: unused method 'get_active_sessions' (60% confidence)
  ```python
      def get_active_sessions(self) -> List[TradeSession]:
  ```

### src/database/influx_dal.py

- 라인 14: unused import 'QueryApi' (90% confidence)
  ```python
  from influxdb_client.client.query_api import QueryApi
  ```

- 라인 21: unused class 'InfluxDAL' (60% confidence)
  ```python
  class InfluxDAL:
  ```

- 라인 41: unused method 'write_price_data' (60% confidence)
  ```python
      def write_price_data(self, symbol: str, timeframe: str, timestamp: datetime,
  ```

- 라인 77: unused method 'write_trade_data' (60% confidence)
  ```python
      def write_trade_data(self, trade_id: str, symbol: str, side: str,
  ```

- 라인 131: unused method 'write_indicator_data' (60% confidence)
  ```python
      def write_indicator_data(self, symbol: str, timeframe: str, timestamp: datetime,
  ```

- 라인 168: unused method 'write_performance_data' (60% confidence)
  ```python
      def write_performance_data(self, timestamp: datetime, balance: float,
  ```

- 라인 215: unused method 'get_price_data' (60% confidence)
  ```python
      def get_price_data(self, symbol: str, timeframe: str,
  ```

- 라인 273: unused method 'get_indicator_data' (60% confidence)
  ```python
      def get_indicator_data(self, symbol: str, timeframe: str,
  ```

- 라인 488: unused method 'calculate_performance_metrics' (60% confidence)
  ```python
      def calculate_performance_metrics(self, start_time: datetime,
  ```

### src/database/integration.py

- 라인 27: unused attribute 'fill_repo' (60% confidence)
  ```python
          self.fill_repo = FillRepository()
  ```

- 라인 120: unused method 'record_order_error' (60% confidence)
  ```python
      async def record_order_error(self, order_id: str, error_message: str,
  ```

- 라인 208: unused method 'save_indicator_snapshot' (60% confidence)
  ```python
      async def save_indicator_snapshot(self, snapshot_data: Dict[str, Any]) -> bool:
  ```

- 라인 230: unused method 'get_latest_indicators' (60% confidence)
  ```python
      async def get_latest_indicators(self, symbol: str, timeframe: Union[TimeFrame, str]) -> Optional[Dict[str, Any]]:
  ```

- 라인 368: unused method 'update_session_stats' (60% confidence)
  ```python
      async def update_session_stats(self, session_id: str, stats: Dict[str, Any]) -> bool:
  ```

### src/database/models.py

- 라인 14: unused import 'JSON' (90% confidence)
  ```python
  from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index, JSON, Enum as SQLEnum
  ```

- 라인 38: unused variable 'STOP_LOSS' (60% confidence)
  ```python
      STOP_LOSS = 'stop_loss'       # 손절매 주문
  ```

- 라인 39: unused variable 'TAKE_PROFIT' (60% confidence)
  ```python
      TAKE_PROFIT = 'take_profit'   # 이익 실현 주문
  ```

- 라인 48: unused variable 'M1' (60% confidence)
  ```python
      M1 = '1m'                     # 1분
  ```

- 라인 49: unused variable 'M5' (60% confidence)
  ```python
      M5 = '5m'                     # 5분
  ```

- 라인 50: unused variable 'M15' (60% confidence)
  ```python
      M15 = '15m'                   # 15분
  ```

- 라인 51: unused variable 'M30' (60% confidence)
  ```python
      M30 = '30m'                   # 30분
  ```

- 라인 52: unused variable 'H1' (60% confidence)
  ```python
      H1 = '1h'                     # 1시간
  ```

- 라인 53: unused variable 'H4' (60% confidence)
  ```python
      H4 = '4h'                     # 4시간
  ```

- 라인 54: unused variable 'D1' (60% confidence)
  ```python
      D1 = '1d'                     # 1일
  ```

- 라인 96: unused variable 'child_orders' (60% confidence)
  ```python
      child_orders = relationship("Order", backref=relationship("parent", remote_side=[order_id]))
  ```

### src/database/repository.py

- 라인 181: unused method 'get_order_by_client_id' (60% confidence)
  ```python
      def get_order_by_client_id(self, client_order_id: str) -> Optional[Order]:
  ```

- 라인 204: unused method 'get_order_by_exchange_id' (60% confidence)
  ```python
      def get_order_by_exchange_id(self, exchange_order_id: str) -> Optional[Order]:
  ```

- 라인 227: unused method 'get_orders_by_status' (60% confidence)
  ```python
      def get_orders_by_status(self, status: Union[OrderStatus, str], symbol: Optional[str] = None) -> List[Order]:
  ```

- 라인 298: unused method 'get_orders_by_symbol' (60% confidence)
  ```python
      def get_orders_by_symbol(self, symbol: str, limit: int = 100) -> List[Order]:
  ```

- 라인 448: unused method 'get_order_statistics' (60% confidence)
  ```python
      def get_order_statistics(self, symbol: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
  ```

- 라인 562: unused method 'get_snapshots' (60% confidence)
  ```python
      def get_snapshots(self, symbol: str, timeframe: Union[TimeFrame, str],
  ```

- 라인 754: unused method 'get_active_sessions' (60% confidence)
  ```python
      def get_active_sessions(self) -> List[TradeSession]:
  ```

- 라인 772: unused method 'get_session_by_id' (60% confidence)
  ```python
      def get_session_by_id(self, session_id: str) -> Optional[TradeSession]:
  ```

### src/execution_engine/connector.py

- 라인 21: unused variable 'BINANCE_CONFIG_KEYS' (60% confidence)
  ```python
  BINANCE_CONFIG_KEYS = {
  ```

- 라인 136: unused method 'get_exchange_config' (60% confidence)
  ```python
      def get_exchange_config(self) -> Dict[str, Any]:
  ```

### src/execution_engine/trading.py

- 라인 21: unused import 'DBOrderSide' (90% confidence)
  ```python
  from src.database.models import OrderStatus as DBOrderStatus, OrderType as DBOrderType, OrderSide as DBOrderSide
  ```

- 라인 21: unused import 'DBOrderType' (90% confidence)
  ```python
  from src.database.models import OrderStatus as DBOrderStatus, OrderType as DBOrderType, OrderSide as DBOrderSide
  ```

- 라인 42: unused variable 'STOP_LOSS' (60% confidence)
  ```python
      STOP_LOSS = 'stop_loss'   # 손절매 주문
  ```

- 라인 43: unused variable 'TAKE_PROFIT' (60% confidence)
  ```python
      TAKE_PROFIT = 'take_profit'  # 이익 실현 주문
  ```

- 라인 100: unused attribute 'order_tracker' (60% confidence)
  ```python
          self.order_tracker = None
  ```

- 라인 114: unused attribute 'order_tracker' (60% confidence)
  ```python
                  self.order_tracker = OrderTracker(self.ws_manager, self)
  ```

### src/execution_engine/websocket_manager.py

- 라인 12: unused import 'Coroutine' (90% confidence)
  ```python
  from typing import Dict, Any, Optional, List, Callable, Coroutine
  ```

- 라인 45: unused attribute 'user_socket' (60% confidence)
  ```python
          self.user_socket = None  # 사용자 데이터 스트림 소켓
  ```

- 라인 292: unused variable 'cummulative_quote_qty' (60% confidence)
  ```python
              cummulative_quote_qty = float(msg.get('Z', 0))  # 체결 금액
  ```

- 라인 309: unused variable 'event_time' (60% confidence)
  ```python
              event_time = msg.get('E')
  ```

- 라인 446: unused method 'get_order_status' (60% confidence)
  ```python
      def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
  ```

- 라인 458: unused method 'get_order_history' (60% confidence)
  ```python
      def get_order_history(self, order_id: str) -> List[Dict[str, Any]]:
  ```

### src/notifications/manager.py

- 라인 16: unused import 'NotificationTemplates' (90% confidence)
  ```python
  from src.notifications.templates import NotificationTemplates
  ```

### src/notifications/redis_publisher.py

- 라인 95: unused method 'publish_trade_notification' (60% confidence)
  ```python
      def publish_trade_notification(self, data: Dict[str, Any]) -> bool:
  ```

- 라인 107: unused method 'publish_order_notification' (60% confidence)
  ```python
      def publish_order_notification(self, data: Dict[str, Any]) -> bool:
  ```

- 라인 119: unused method 'publish_risk_notification' (60% confidence)
  ```python
      def publish_risk_notification(self, data: Dict[str, Any]) -> bool:
  ```

- 라인 131: unused method 'publish_system_notification' (60% confidence)
  ```python
      def publish_system_notification(self, data: Dict[str, Any]) -> bool:
  ```

- 라인 143: unused method 'publish_performance_notification' (60% confidence)
  ```python
      def publish_performance_notification(self, data: Dict[str, Any]) -> bool:
  ```

- 라인 155: unused method 'store_notification' (60% confidence)
  ```python
      def store_notification(self, data: Dict[str, Any], expiry: int = 86400) -> bool:
  ```

- 라인 200: unused method 'get_recent_notifications' (60% confidence)
  ```python
      def get_recent_notifications(self, limit: int = 50) -> list:
  ```

### src/notifications/telegram_bot.py

- 라인 12: unused import 'hmac' (90% confidence)
  ```python
  import hmac
  ```

- 라인 13: unused import 'hashlib' (90% confidence)
  ```python
  import hashlib
  ```

- 라인 19: unused import 'Bot' (90% confidence)
  ```python
  from telegram import Update, Bot
  ```

- 라인 21: unused import 'Dispatcher' (90% confidence)
  ```python
  from telegram.ext import (
  ```

- 라인 21: unused import 'Filters' (90% confidence)
  ```python
  from telegram.ext import (
  ```

- 라인 21: unused import 'MessageHandler' (90% confidence)
  ```python
  from telegram.ext import (
  ```

### src/notifications/templates.py

- 라인 19: unused class 'NotificationTemplates' (60% confidence)
  ```python
  class NotificationTemplates:
  ```

- 라인 165: unused method 'trade_open' (60% confidence)
  ```python
      @classmethod
  ```

- 라인 178: unused method 'trade_close' (60% confidence)
  ```python
      @classmethod
  ```

- 라인 191: unused method 'order_placed' (60% confidence)
  ```python
      @classmethod
  ```

- 라인 204: unused method 'order_filled' (60% confidence)
  ```python
      @classmethod
  ```

- 라인 217: unused method 'order_canceled' (60% confidence)
  ```python
      @classmethod
  ```

- 라인 230: unused method 'risk_alert' (60% confidence)
  ```python
      @classmethod
  ```

- 라인 243: unused method 'system_status' (60% confidence)
  ```python
      @classmethod
  ```

- 라인 256: unused method 'performance_report' (60% confidence)
  ```python
      @classmethod
  ```

### src/risk_manager/api.py

- 라인 99: unused function 'root' (60% confidence)
  ```python
  @app.get("/", response_class=HTMLResponse)
  ```

- 라인 148: unused function 'check_trade' (60% confidence)
  ```python
  @app.post("/check-trade", tags=["거래"])
  ```

- 라인 203: unused function 'get_positions' (60% confidence)
  ```python
  @app.get("/positions", tags=["포지션"])
  ```

- 라인 293: unused function 'reset_circuit_breaker' (60% confidence)
  ```python
  @app.post("/circuit-breaker/reset", tags=["서킷 브레이커"])
  ```

- 라인 337: unused function 'check_trade' (60% confidence)
  ```python
  @app.post("/trade/check", tags=["거래"])
  ```

- 라인 364: unused function 'increment_trade_count' (60% confidence)
  ```python
  @app.post("/trade/increment", tags=["거래"])
  ```

- 라인 404: unused function 'publish_event' (60% confidence)
  ```python
  @app.post("/events/publish", tags=["이벤트"])
  ```

- 라인 414: unused function 'startup_event' (60% confidence)
  ```python
  @app.on_event("startup")
  ```

- 라인 440: unused function 'shutdown_event' (60% confidence)
  ```python
  @app.on_event("shutdown")
  ```

### src/risk_manager/risk_manager_telegram.py

- 라인 19: unused function 'setup_telegram_integration' (60% confidence)
  ```python
  async def setup_telegram_integration():
  ```

- 라인 59: unused function 'send_telegram_notification' (60% confidence)
  ```python
  async def send_telegram_notification(title: str, message: str, level: str = "info") -> bool:
  ```

- 라인 79: unused function 'send_telegram_trade_alert' (60% confidence)
  ```python
  async def send_telegram_trade_alert(trade_data: Dict[str, Any]) -> bool:
  ```

- 라인 96: unused function 'send_daily_performance_report' (60% confidence)
  ```python
  async def send_daily_performance_report(performance_data: Dict[str, Any]) -> bool:
  ```

### src/strategy_engine/backtesting.py

- 라인 60: unused attribute 'latest_results' (60% confidence)
  ```python
          self.latest_results = None
  ```

- 라인 168: unused attribute 'latest_results' (60% confidence)
  ```python
              self.latest_results = backtest_results
  ```

### src/strategy_engine/nasos_strategy.py

- 라인 186: unused method 'calculate_custom_stoploss' (60% confidence)
  ```python
      def calculate_custom_stoploss(self, current_profit: float) -> float:
  ```

- 라인 337: unused method 'get_plot_config' (60% confidence)
  ```python
      def get_plot_config(self) -> Dict:
  ```

### src/strategy_engine/strategy_evaluator.py

- 라인 31: unused attribute 'required_indicators' (60% confidence)
  ```python
          self.required_indicators = []
  ```

- 라인 77: unused method 'evaluate_generic_strategy' (60% confidence)
  ```python
      def evaluate_generic_strategy(self, dataframes: Dict[str, pd.DataFrame],
  ```

### src/strategy_engine/strategy_manager.py

- 라인 147: unused method 'evaluate_strategy' (60% confidence)
  ```python
      def evaluate_strategy(self, dataframes: Dict[str, pd.DataFrame],
  ```

### src/utils/config.py

- 라인 145: unused function 'get_config_value' (60% confidence)
  ```python
  def get_config_value(config: Dict[str, Any], key_path: str, default: Optional[Any] = None) -> Any:
  ```

### src/utils/env_loader.py

- 라인 96: unused method 'get_int' (60% confidence)
  ```python
      def get_int(self, key: str, default: int = 0) -> int:
  ```

- 라인 118: unused method 'get_float' (60% confidence)
  ```python
      def get_float(self, key: str, default: float = 0.0) -> float:
  ```

- 라인 140: unused method 'get_bool' (60% confidence)
  ```python
      def get_bool(self, key: str, default: bool = False) -> bool:
  ```

### src/utils/logger.py

- 라인 77: unused function 'get_logger' (60% confidence)
  ```python
  def get_logger(name):
  ```

### src/utils/security.py

- 라인 207: unused method 'delete_secret' (60% confidence)
  ```python
      def delete_secret(self, key: str) -> bool:
  ```

- 라인 277: unused method 'store_api_credentials' (60% confidence)
  ```python
      def store_api_credentials(self, api_key: str, api_secret: str, exchange: str = 'binance') -> bool:
  ```

- 라인 333: unused method 'store_database_credentials' (60% confidence)
  ```python
      def store_database_credentials(self, credentials: Dict[str, str], db_type: str = 'postgresql') -> bool:
  ```

- 라인 383: unused method 'store_telegram_credentials' (60% confidence)
  ```python
      def store_telegram_credentials(self, token: str, chat_id: str) -> bool:
  ```

- 라인 404: unused method 'export_to_env_file' (60% confidence)
  ```python
      def export_to_env_file(self, filepath: str = '.env') -> bool:
  ```

- 라인 443: unused method 'import_from_env_file' (60% confidence)
  ```python
      def import_from_env_file(self, filepath: str = '.env') -> bool:
  ```

- 라인 482: unused function 'validate_api_key' (60% confidence)
  ```python
  def validate_api_key(api_key: str) -> bool:
  ```

- 라인 506: unused function 'validate_api_secret' (60% confidence)
  ```python
  def validate_api_secret(api_secret: str) -> bool:
  ```

- 라인 530: unused function 'generate_secure_password' (60% confidence)
  ```python
  def generate_secure_password(length: int = 16) -> str:
  ```

### src/utils/ssl_manager.py

- 라인 213: unused method 'delete_dns_record' (60% confidence)
  ```python
      def delete_dns_record(self, record_id: str) -> bool:
  ```

- 라인 338: unused class 'SSLManager' (60% confidence)
  ```python
  class SSLManager:
  ```

- 라인 368: unused method 'setup_cloudflare_ssl' (60% confidence)
  ```python
      def setup_cloudflare_ssl(self, mode: str = 'strict') -> bool:
  ```

- 라인 395: unused method 'verify_ssl_configuration' (60% confidence)
  ```python
      def verify_ssl_configuration(self) -> Dict[str, Any]:
  ```

- 라인 498: unused method 'setup_api_subdomain' (60% confidence)
  ```python
      def setup_api_subdomain(self, proxied: bool = True) -> bool:
  ```

- 라인 517: unused method 'setup_dashboard_subdomain' (60% confidence)
  ```python
      def setup_dashboard_subdomain(self, proxied: bool = True) -> bool:
  ```

- 라인 536: unused method 'list_subdomains' (60% confidence)
  ```python
      def list_subdomains(self) -> List[Dict[str, Any]]:
  ```

### src/utils/vault_helper.py

- 라인 57: unused variable 'SECRET_CACHE_TTL' (60% confidence)
  ```python
  SECRET_CACHE_TTL = int(os.environ.get('SECRET_CACHE_TTL', '3600'))  # 초 단위
  ```
