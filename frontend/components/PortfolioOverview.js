import { useState } from 'react';
import { startBot, stopBot, pauseBot } from '../api/dashboard';

export default function PortfolioOverview({ status }) {
  const [loading, setLoading] = useState(false);
  const [actionError, setActionError] = useState(null);

  if (!status) return null;
  
  const handleBotAction = async (action) => {
    try {
      setLoading(true);
      setActionError(null);
      
      let response;
      switch (action) {
        case 'start':
          response = await startBot();
          break;
        case 'stop':
          response = await stopBot();
          break;
        case 'pause':
          response = await pauseBot();
          break;
        default:
          throw new Error('Invalid action');
      }
      
      // 성공 메시지 표시 또는 페이지 새로고침
      console.log(`Bot ${action} successful:`, response);
      // 실제 구현에서는 상태 업데이트 또는 페이지 새로고침
      
    } catch (error) {
      console.error(`Bot ${action} failed:`, error);
      setActionError(error.message || `Failed to ${action} bot`);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="card">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Portfolio Overview</h2>
        <div className="flex space-x-2">
          {status.status !== 'ACTIVE' && (
            <button
              className="btn btn-success text-sm"
              onClick={() => handleBotAction('start')}
              disabled={loading}
            >
              Start Bot
            </button>
          )}
          {status.status === 'ACTIVE' && (
            <button
              className="btn btn-warning text-sm"
              onClick={() => handleBotAction('pause')}
              disabled={loading}
            >
              Pause Bot
            </button>
          )}
          {status.status !== 'STOPPED' && (
            <button
              className="btn btn-danger text-sm"
              onClick={() => handleBotAction('stop')}
              disabled={loading}
            >
              Stop Bot
            </button>
          )}
        </div>
      </div>
      
      {actionError && (
        <div className="mb-4 p-2 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-md">
          {actionError}
        </div>
      )}
      
      <div className="stats-grid">
        <div className="stat-item">
          <span className="stat-label">Balance</span>
          <span className="stat-value">${status.balance.toFixed(2)}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Status</span>
          <span className={`stat-value status-${status.status.toLowerCase()}`}>
            {status.status}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Active Trades</span>
          <span className="stat-value">{status.active_trades}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Uptime</span>
          <span className="stat-value">{status.uptime}</span>
        </div>
      </div>
      
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-50 dark:bg-slate-700 p-4 rounded-lg">
          <h3 className="text-lg font-medium mb-2">Current Strategy</h3>
          <p className="text-gray-700 dark:text-gray-300">{status.strategy || 'NASOSv5_mod3'}</p>
          <div className="mt-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">Last Updated: </span>
            <span className="text-sm">{status.last_updated || 'N/A'}</span>
          </div>
        </div>
        
        <div className="bg-gray-50 dark:bg-slate-700 p-4 rounded-lg">
          <h3 className="text-lg font-medium mb-2">Risk Management</h3>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <span className="text-sm text-gray-500 dark:text-gray-400">Max Drawdown: </span>
              <span className="text-sm">{status.max_drawdown || '0'}%</span>
            </div>
            <div>
              <span className="text-sm text-gray-500 dark:text-gray-400">Circuit Breaker: </span>
              <span className="text-sm">{status.circuit_breaker ? 'Active' : 'Inactive'}</span>
            </div>
            <div>
              <span className="text-sm text-gray-500 dark:text-gray-400">Position Size: </span>
              <span className="text-sm">{status.position_size || '0'}%</span>
            </div>
            <div>
              <span className="text-sm text-gray-500 dark:text-gray-400">Stop Loss: </span>
              <span className="text-sm">{status.stop_loss || 'Auto'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
