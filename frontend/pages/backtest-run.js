import { useState } from 'react';
import { useRouter } from 'next/router';
import DashboardLayout from '../components/DashboardLayout';
import { runBacktest } from '../api/dashboard';

export default function BacktestRun() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  // 폼 상태
  const [formData, setFormData] = useState({
    strategy: 'NASOSv5_mod3',
    symbol: 'BTC/USDT',
    timeframe: '5m',
    startDate: '',
    endDate: '',
    initialCapital: 10000,
    feeRate: 0.1,
    parameters: {}
  });
  
  // 전략 목록
  const strategies = [
    { value: 'NASOSv5_mod3', label: 'NASOS v5 (Modified 3)' },
    { value: 'RSI_Strategy', label: 'RSI Strategy' },
    { value: 'MACD_Strategy', label: 'MACD Strategy' }
  ];
  
  // 심볼 목록
  const symbols = [
    { value: 'BTC/USDT', label: 'BTC/USDT' },
    { value: 'ETH/USDT', label: 'ETH/USDT' },
    { value: 'BNB/USDT', label: 'BNB/USDT' },
    { value: 'SOL/USDT', label: 'SOL/USDT' },
    { value: 'XRP/USDT', label: 'XRP/USDT' }
  ];
  
  // 타임프레임 목록
  const timeframes = [
    { value: '1m', label: '1 Minute' },
    { value: '5m', label: '5 Minutes' },
    { value: '15m', label: '15 Minutes' },
    { value: '30m', label: '30 Minutes' },
    { value: '1h', label: '1 Hour' },
    { value: '4h', label: '4 Hours' },
    { value: '1d', label: '1 Day' }
  ];
  
  // 입력 변경 핸들러
  const handleInputChange = (e) => {
    const { name, value, type } = e.target;
    
    // 숫자 입력 필드 처리
    if (type === 'number') {
      setFormData({
        ...formData,
        [name]: parseFloat(value)
      });
    } else {
      setFormData({
        ...formData,
        [name]: value
      });
    }
  };
  
  // 파라미터 변경 핸들러
  const handleParameterChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    // 체크박스 처리
    if (type === 'checkbox') {
      setFormData({
        ...formData,
        parameters: {
          ...formData.parameters,
          [name]: checked
        }
      });
    } 
    // 숫자 처리
    else if (type === 'number') {
      setFormData({
        ...formData,
        parameters: {
          ...formData.parameters,
          [name]: parseFloat(value)
        }
      });
    } 
    // 텍스트 처리
    else {
      setFormData({
        ...formData,
        parameters: {
          ...formData.parameters,
          [name]: value
        }
      });
    }
  };
  
  // 폼 제출 핸들러
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);
      
      // 백테스트 실행 API 호출
      const result = await runBacktest(formData);
      
      setSuccess(`백테스트가 성공적으로 실행되었습니다. 백테스트 ID: ${result.id}`);
      
      // 3초 후 백테스트 결과 페이지로 이동
      setTimeout(() => {
        router.push('/backtest');
      }, 3000);
    } catch (err) {
      console.error('백테스트 실행 오류:', err);
      setError(err.message || '백테스트 실행 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };
  
  // 현재 날짜 구하기 (기본값 설정용)
  const today = new Date().toISOString().split('T')[0];
  // 30일 전 날짜 구하기 (기본값 설정용)
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
  const thirtyDaysAgoStr = thirtyDaysAgo.toISOString().split('T')[0];
  
  return (
    <DashboardLayout>
      <h1 className="text-2xl font-bold mb-6">Run Backtest</h1>
      
      {error && (
        <div className="mb-6 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 p-4 rounded-md">
          {error}
        </div>
      )}
      
      {success && (
        <div className="mb-6 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-200 p-4 rounded-md">
          {success}
        </div>
      )}
      
      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* 기본 설정 */}
            <div>
              <h2 className="text-lg font-bold mb-4">Basic Settings</h2>
              
              <div className="space-y-4">
                {/* 전략 선택 */}
                <div>
                  <label className="form-label" htmlFor="strategy">Strategy</label>
                  <select
                    id="strategy"
                    name="strategy"
                    className="form-select"
                    value={formData.strategy}
                    onChange={handleInputChange}
                    required
                  >
                    {strategies.map((strategy) => (
                      <option key={strategy.value} value={strategy.value}>
                        {strategy.label}
                      </option>
                    ))}
                  </select>
                </div>
                
                {/* 심볼 선택 */}
                <div>
                  <label className="form-label" htmlFor="symbol">Symbol</label>
                  <select
                    id="symbol"
                    name="symbol"
                    className="form-select"
                    value={formData.symbol}
                    onChange={handleInputChange}
                    required
                  >
                    {symbols.map((symbol) => (
                      <option key={symbol.value} value={symbol.value}>
                        {symbol.label}
                      </option>
                    ))}
                  </select>
                </div>
                
                {/* 타임프레임 선택 */}
                <div>
                  <label className="form-label" htmlFor="timeframe">Timeframe</label>
                  <select
                    id="timeframe"
                    name="timeframe"
                    className="form-select"
                    value={formData.timeframe}
                    onChange={handleInputChange}
                    required
                  >
                    {timeframes.map((timeframe) => (
                      <option key={timeframe.value} value={timeframe.value}>
                        {timeframe.label}
                      </option>
                    ))}
                  </select>
                </div>
                
                {/* 시작 날짜 */}
                <div>
                  <label className="form-label" htmlFor="startDate">Start Date</label>
                  <input
                    type="date"
                    id="startDate"
                    name="startDate"
                    className="form-input"
                    value={formData.startDate || thirtyDaysAgoStr}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                
                {/* 종료 날짜 */}
                <div>
                  <label className="form-label" htmlFor="endDate">End Date</label>
                  <input
                    type="date"
                    id="endDate"
                    name="endDate"
                    className="form-input"
                    value={formData.endDate || today}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                
                {/* 초기 자본 */}
                <div>
                  <label className="form-label" htmlFor="initialCapital">Initial Capital (USDT)</label>
                  <input
                    type="number"
                    id="initialCapital"
                    name="initialCapital"
                    className="form-input"
                    value={formData.initialCapital}
                    onChange={handleInputChange}
                    min="100"
                    step="100"
                    required
                  />
                </div>
                
                {/* 수수료율 */}
                <div>
                  <label className="form-label" htmlFor="feeRate">Fee Rate (%)</label>
                  <input
                    type="number"
                    id="feeRate"
                    name="feeRate"
                    className="form-input"
                    value={formData.feeRate}
                    onChange={handleInputChange}
                    min="0"
                    max="1"
                    step="0.01"
                    required
                  />
                </div>
              </div>
            </div>
            
            {/* 전략 파라미터 */}
            <div>
              <h2 className="text-lg font-bold mb-4">Strategy Parameters</h2>
              
              {formData.strategy === 'NASOSv5_mod3' && (
                <div className="space-y-4">
                  <div>
                    <label className="form-label" htmlFor="rsi_length">RSI Length</label>
                    <input
                      type="number"
                      id="rsi_length"
                      name="rsi_length"
                      className="form-input"
                      value={formData.parameters.rsi_length || 14}
                      onChange={handleParameterChange}
                      min="2"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="form-label" htmlFor="rsi_overbought">RSI Overbought</label>
                    <input
                      type="number"
                      id="rsi_overbought"
                      name="rsi_overbought"
                      className="form-input"
                      value={formData.parameters.rsi_overbought || 70}
                      onChange={handleParameterChange}
                      min="50"
                      max="100"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="form-label" htmlFor="rsi_oversold">RSI Oversold</label>
                    <input
                      type="number"
                      id="rsi_oversold"
                      name="rsi_oversold"
                      className="form-input"
                      value={formData.parameters.rsi_oversold || 30}
                      onChange={handleParameterChange}
                      min="0"
                      max="50"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="form-label" htmlFor="ema_short">EMA Short</label>
                    <input
                      type="number"
                      id="ema_short"
                      name="ema_short"
                      className="form-input"
                      value={formData.parameters.ema_short || 12}
                      onChange={handleParameterChange}
                      min="2"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="form-label" htmlFor="ema_long">EMA Long</label>
                    <input
                      type="number"
                      id="ema_long"
                      name="ema_long"
                      className="form-input"
                      value={formData.parameters.ema_long || 26}
                      onChange={handleParameterChange}
                      min="2"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="form-label" htmlFor="take_profit">Take Profit (%)</label>
                    <input
                      type="number"
                      id="take_profit"
                      name="take_profit"
                      className="form-input"
                      value={formData.parameters.take_profit || 3}
                      onChange={handleParameterChange}
                      min="0.1"
                      step="0.1"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="form-label" htmlFor="stop_loss">Stop Loss (%)</label>
                    <input
                      type="number"
                      id="stop_loss"
                      name="stop_loss"
                      className="form-input"
                      value={formData.parameters.stop_loss || 2}
                      onChange={handleParameterChange}
                      min="0.1"
                      step="0.1"
                      required
                    />
                  </div>
                  
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="use_trailing_stop"
                      name="use_trailing_stop"
                      className="form-checkbox h-5 w-5"
                      checked={formData.parameters.use_trailing_stop || false}
                      onChange={handleParameterChange}
                    />
                    <label className="ml-2" htmlFor="use_trailing_stop">Use Trailing Stop</label>
                  </div>
                </div>
              )}
              
              {formData.strategy === 'RSI_Strategy' && (
                <div className="space-y-4">
                  <div>
                    <label className="form-label" htmlFor="rsi_length">RSI Length</label>
                    <input
                      type="number"
                      id="rsi_length"
                      name="rsi_length"
                      className="form-input"
                      value={formData.parameters.rsi_length || 14}
                      onChange={handleParameterChange}
                      min="2"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="form-label" htmlFor="rsi_overbought">RSI Overbought</label>
                    <input
                      type="number"
                      id="rsi_overbought"
                      name="rsi_overbought"
                      className="form-input"
                      value={formData.parameters.rsi_overbought || 70}
                      onChange={handleParameterChange}
                      min="50"
                      max="100"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="form-label" htmlFor="rsi_oversold">RSI Oversold</label>
                    <input
                      type="number"
                      id="rsi_oversold"
                      name="rsi_oversold"
                      className="form-input"
                      value={formData.parameters.rsi_oversold || 30}
                      onChange={handleParameterChange}
                      min="0"
                      max="50"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="form-label" htmlFor="take_profit">Take Profit (%)</label>
                    <input
                      type="number"
                      id="take_profit"
                      name="take_profit"
                      className="form-input"
                      value={formData.parameters.take_profit || 3}
                      onChange={handleParameterChange}
                      min="0.1"
                      step="0.1"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="form-label" htmlFor="stop_loss">Stop Loss (%)</label>
                    <input
                      type="number"
                      id="stop_loss"
                      name="stop_loss"
                      className="form-input"
                      value={formData.parameters.stop_loss || 2}
                      onChange={handleParameterChange}
                      min="0.1"
                      step="0.1"
                      required
                    />
                  </div>
                </div>
              )}
              
              {formData.strategy === 'MACD_Strategy' && (
                <div className="space-y-4">
                  <div>
                    <label className="form-label" htmlFor="fast_length">Fast Length</label>
                    <input
                      type="number"
                      id="fast_length"
                      name="fast_length"
                      className="form-input"
                      value={formData.parameters.fast_length || 12}
                      onChange={handleParameterChange}
                      min="2"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="form-label" htmlFor="slow_length">Slow Length</label>
                    <input
                      type="number"
                      id="slow_length"
                      name="slow_length"
                      className="form-input"
                      value={formData.parameters.slow_length || 26}
                      onChange={handleParameterChange}
                      min="2"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="form-label" htmlFor="signal_length">Signal Length</label>
                    <input
                      type="number"
                      id="signal_length"
                      name="signal_length"
                      className="form-input"
                      value={formData.parameters.signal_length || 9}
                      onChange={handleParameterChange}
                      min="2"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="form-label" htmlFor="take_profit">Take Profit (%)</label>
                    <input
                      type="number"
                      id="take_profit"
                      name="take_profit"
                      className="form-input"
                      value={formData.parameters.take_profit || 3}
                      onChange={handleParameterChange}
                      min="0.1"
                      step="0.1"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="form-label" htmlFor="stop_loss">Stop Loss (%)</label>
                    <input
                      type="number"
                      id="stop_loss"
                      name="stop_loss"
                      className="form-input"
                      value={formData.parameters.stop_loss || 2}
                      onChange={handleParameterChange}
                      min="0.1"
                      step="0.1"
                      required
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
          
          <div className="flex justify-end">
            <button
              type="submit"
              className="btn-primary"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="animate-spin inline-block h-4 w-4 mr-2 border-t-2 border-b-2 border-white rounded-full"></span>
                  Running...
                </>
              ) : 'Run Backtest'}
            </button>
          </div>
        </form>
      </div>
    </DashboardLayout>
  );
}
