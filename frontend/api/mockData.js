/**
 * 테스트용 모의 데이터
 */

// 대시보드 상태 데이터
export const mockStatus = {
  status: 'running',
  mode: 'paper',
  uptime: 86400, // 1일 (초 단위)
  balance: 10245.67,
  equity: 10500.23,
  strategy: 'NASOSv5_mod3',
  exchange: 'Binance',
  active_trades: 2,
  profit_today: 125.45,
  profit_today_percentage: 1.23,
  profit_total: 500.23,
  profit_total_percentage: 5.12
};

// 성능 데이터
export const mockPerformance = {
  total_return: 15.75,
  win_rate: 62.5,
  max_drawdown: 8.32,
  sharpe_ratio: 1.85,
  sortino_ratio: 2.34,
  calmar_ratio: 1.89,
  profit_factor: 1.65,
  recovery_factor: 2.1,
  expectancy: 12.45,
  
  // 차트 데이터
  dates: Array.from({ length: 30 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (29 - i));
    return date.toISOString().split('T')[0];
  }),
  
  equity: Array.from({ length: 30 }, (_, i) => {
    return 10000 + Math.floor(Math.random() * 200) * (i + 1);
  }),
  
  profit: Array.from({ length: 30 }, (_, i) => {
    return Math.floor(Math.random() * 100) * (i + 1);
  }),
  
  drawdown: Array.from({ length: 30 }, () => {
    return -(Math.random() * 10).toFixed(2);
  }),
  
  monthly_labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  monthly_returns: [2.5, -1.3, 3.7, 1.2, -0.8, 4.2, 2.1, -2.3, 5.1, 1.7, -1.1, 3.9],
  
  // 거래 통계
  total_trades: 120,
  winning_trades: 75,
  losing_trades: 45,
  avg_holding_time: '4h 23m',
  
  // 심볼 분포
  symbol_labels: ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT'],
  symbol_values: [45, 30, 15, 7, 3],
  
  // 추가 지표
  annual_return: 32.45,
  monthly_return: 2.85,
  daily_return: 0.12,
  volatility: 12.34,
  downside_deviation: 8.76,
  var: 5.43,
  avg_win: 35.67,
  avg_loss: -21.43
};

// 거래 내역 데이터
export const mockTrades = {
  items: Array.from({ length: 20 }, (_, i) => ({
    id: i + 1,
    symbol: ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT'][Math.floor(Math.random() * 5)],
    strategy: 'NASOSv5_mod3',
    entry_price: 1000 + Math.random() * 100,
    exit_price: 1000 + Math.random() * 150,
    entry_time: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
    exit_time: new Date(Date.now() - Math.random() * 20 * 24 * 60 * 60 * 1000).toISOString(),
    amount: Math.random() * 2,
    fee: Math.random() * 5,
    profit: Math.random() * 200 - 50,
    profit_percentage: Math.random() * 10 - 2,
    status: ['closed', 'closed', 'closed', 'open'][Math.floor(Math.random() * 4)],
    trade_type: Math.random() > 0.5 ? 'buy' : 'sell',
    exchange: 'Binance'
  })),
  total: 120,
  page: 1,
  limit: 20,
  pages: 6
};

// 파라미터 데이터
export const mockParameters = [
  { id: 1, name: 'rsi_length', value: '14', description: 'RSI 계산에 사용되는 기간', strategy: 'NASOSv5_mod3' },
  { id: 2, name: 'rsi_overbought', value: '70', description: '과매수 RSI 임계값', strategy: 'NASOSv5_mod3' },
  { id: 3, name: 'rsi_oversold', value: '30', description: '과매도 RSI 임계값', strategy: 'NASOSv5_mod3' },
  { id: 4, name: 'ema_short', value: '12', description: '단기 EMA 기간', strategy: 'NASOSv5_mod3' },
  { id: 5, name: 'ema_long', value: '26', description: '장기 EMA 기간', strategy: 'NASOSv5_mod3' },
  { id: 6, name: 'take_profit', value: '3', description: '익절 비율 (%)', strategy: 'NASOSv5_mod3' },
  { id: 7, name: 'stop_loss', value: '2', description: '손절 비율 (%)', strategy: 'NASOSv5_mod3' },
  { id: 8, name: 'use_trailing_stop', value: 'true', description: '추적 손절매 사용 여부', strategy: 'NASOSv5_mod3' }
];

// 백테스트 결과 데이터
export const mockBacktestResults = {
  items: Array.from({ length: 10 }, (_, i) => ({
    id: i + 1,
    strategy_name: 'NASOSv5_mod3',
    created_at: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
    period: '2023-01-01 ~ 2023-03-31',
    total_trades: 120 + Math.floor(Math.random() * 50),
    win_rate: 50 + Math.random() * 20,
    profit_percent: Math.random() * 30 - 5,
    profit_amount: Math.random() * 3000 - 500,
    max_drawdown: -(Math.random() * 15),
    initial_balance: 10000,
    final_balance: 10000 + Math.random() * 3000 - 500,
    sharpe_ratio: 1 + Math.random() * 2,
    sortino_ratio: 1.5 + Math.random() * 2,
    calmar_ratio: 1 + Math.random() * 1.5,
    profit_factor: 1 + Math.random() * 1.5,
    recovery_factor: 1 + Math.random() * 2,
    winning_trades: Math.floor(70 + Math.random() * 30),
    losing_trades: Math.floor(30 + Math.random() * 20),
    avg_profit: 50 + Math.random() * 30,
    avg_loss: -(20 + Math.random() * 20),
    largest_win: 100 + Math.random() * 200,
    largest_loss: -(50 + Math.random() * 100),
    parameters: {
      rsi_length: 14,
      rsi_overbought: 70,
      rsi_oversold: 30,
      ema_short: 12,
      ema_long: 26,
      take_profit: 3,
      stop_loss: 2,
      use_trailing_stop: true
    },
    equity_curve: {
      dates: Array.from({ length: 90 }, (_, i) => {
        const date = new Date('2023-01-01');
        date.setDate(date.getDate() + i);
        return date.toISOString().split('T')[0];
      }),
      values: Array.from({ length: 90 }, (_, i) => {
        return 10000 + Math.floor(Math.random() * 100) * (i + 1);
      })
    }
  })),
  total: 25,
  page: 1,
  limit: 10,
  pages: 3
};

// 백테스트 실행 결과
export const mockBacktestRun = {
  id: 26,
  status: 'completed',
  message: '백테스트가 성공적으로 완료되었습니다.'
};
