import { useState, useEffect } from 'react';
import DashboardLayout from '../components/DashboardLayout';
import { fetchBacktestResults } from '../api/dashboard';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

// Chart.js 등록
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function Backtest() {
  const [backtests, setBacktests] = useState([]);
  const [selectedBacktest, setSelectedBacktest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  useEffect(() => {
    const loadBacktestResults = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetchBacktestResults(page, 10);
        setBacktests(response.items || []);
        setTotalPages(Math.ceil((response.total || 0) / 10));
        
        // 첫 번째 백테스트 선택
        if (response.items && response.items.length > 0 && !selectedBacktest) {
          setSelectedBacktest(response.items[0]);
        }
      } catch (err) {
        console.error('Failed to load backtest results:', err);
        setError('Failed to load backtest results. Please try again later.');
      } finally {
        setLoading(false);
      }
    };
    
    loadBacktestResults();
  }, [page]);
  
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage);
    }
  };
  
  const handleBacktestSelect = (backtest) => {
    setSelectedBacktest(backtest);
  };
  
  // 차트 옵션
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          usePointStyle: true,
          boxWidth: 6
        }
      },
      tooltip: {
        usePointStyle: true,
        callbacks: {
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD'
              }).format(context.parsed.y);
            }
            return label;
          }
        }
      }
    },
    scales: {
      x: {
        grid: {
          display: false
        }
      },
      y: {
        grid: {
          color: 'rgba(200, 200, 200, 0.2)'
        }
      }
    }
  };
  
  if (loading && backtests.length === 0) {
    return (
      <DashboardLayout>
        <h1 className="text-2xl font-bold mb-6">Backtest Results</h1>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    );
  }
  
  return (
    <DashboardLayout>
      <h1 className="text-2xl font-bold mb-6">Backtest Results</h1>
      
      {error && (
        <div className="mb-6 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 p-4 rounded-md">
          {error}
        </div>
      )}
      
      {backtests.length === 0 ? (
        <div className="card">
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No backtest results found.
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 백테스트 목록 */}
          <div className="lg:col-span-1">
            <div className="card">
              <h2 className="text-xl font-bold mb-4">Recent Backtests</h2>
              
              <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
                {backtests.map((backtest) => (
                  <div
                    key={backtest.id}
                    className={`p-4 rounded-lg cursor-pointer transition-colors ${
                      selectedBacktest && selectedBacktest.id === backtest.id
                        ? 'bg-primary bg-opacity-10 border-l-4 border-primary'
                        : 'bg-gray-50 dark:bg-slate-700 hover:bg-gray-100 dark:hover:bg-slate-600'
                    }`}
                    onClick={() => handleBacktestSelect(backtest)}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-medium">{backtest.strategy_name}</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {new Date(backtest.created_at).toLocaleString()}
                        </p>
                      </div>
                      <span className={`text-sm font-medium ${
                        backtest.profit_percent >= 0
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}>
                        {backtest.profit_percent >= 0 ? '+' : ''}{backtest.profit_percent.toFixed(2)}%
                      </span>
                    </div>
                    
                    <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Period: </span>
                        <span>{backtest.period}</span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Trades: </span>
                        <span>{backtest.total_trades}</span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Win Rate: </span>
                        <span>{backtest.win_rate.toFixed(2)}%</span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Max DD: </span>
                        <span className="text-red-600 dark:text-red-400">{backtest.max_drawdown.toFixed(2)}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              {/* 페이지네이션 */}
              <div className="flex items-center justify-center space-x-2 mt-4">
                <button
                  className="px-3 py-1 rounded-md bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-300 disabled:opacity-50"
                  onClick={() => handlePageChange(page - 1)}
                  disabled={page === 1}
                >
                  Previous
                </button>
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Page {page} of {totalPages}
                </span>
                <button
                  className="px-3 py-1 rounded-md bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-300 disabled:opacity-50"
                  onClick={() => handlePageChange(page + 1)}
                  disabled={page === totalPages}
                >
                  Next
                </button>
              </div>
            </div>
          </div>
          
          {/* 백테스트 상세 정보 */}
          <div className="lg:col-span-2">
            {selectedBacktest ? (
              <div className="space-y-6">
                <div className="card">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h2 className="text-xl font-bold">{selectedBacktest.strategy_name}</h2>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {new Date(selectedBacktest.created_at).toLocaleString()}
                      </p>
                    </div>
                    <span className={`text-lg font-bold ${
                      selectedBacktest.profit_percent >= 0
                        ? 'text-green-600 dark:text-green-400'
                        : 'text-red-600 dark:text-red-400'
                    }`}>
                      {selectedBacktest.profit_percent >= 0 ? '+' : ''}{selectedBacktest.profit_percent.toFixed(2)}%
                      <span className="text-sm ml-1">
                        (${selectedBacktest.profit_amount.toFixed(2)})
                      </span>
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="stat-item">
                      <span className="stat-label">Initial Balance</span>
                      <span className="stat-value">${selectedBacktest.initial_balance.toFixed(2)}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Final Balance</span>
                      <span className="stat-value">${selectedBacktest.final_balance.toFixed(2)}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Total Trades</span>
                      <span className="stat-value">{selectedBacktest.total_trades}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Win Rate</span>
                      <span className="stat-value">{selectedBacktest.win_rate.toFixed(2)}%</span>
                    </div>
                  </div>
                  
                  <div className="h-64">
                    {selectedBacktest.equity_curve && (
                      <Line
                        options={chartOptions}
                        data={{
                          labels: selectedBacktest.equity_curve.dates || [],
                          datasets: [
                            {
                              label: 'Equity',
                              data: selectedBacktest.equity_curve.values || [],
                              borderColor: 'rgb(53, 162, 235)',
                              backgroundColor: 'rgba(53, 162, 235, 0.5)',
                              tension: 0.2,
                              fill: true
                            }
                          ]
                        }}
                      />
                    )}
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="card">
                    <h3 className="text-lg font-bold mb-4">Performance Metrics</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Sharpe Ratio</span>
                        <span className="font-medium">{selectedBacktest.sharpe_ratio.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Sortino Ratio</span>
                        <span className="font-medium">{selectedBacktest.sortino_ratio.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Calmar Ratio</span>
                        <span className="font-medium">{selectedBacktest.calmar_ratio.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Max Drawdown</span>
                        <span className="font-medium text-red-600 dark:text-red-400">{selectedBacktest.max_drawdown.toFixed(2)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Profit Factor</span>
                        <span className="font-medium">{selectedBacktest.profit_factor.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Recovery Factor</span>
                        <span className="font-medium">{selectedBacktest.recovery_factor.toFixed(2)}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="card">
                    <h3 className="text-lg font-bold mb-4">Trade Statistics</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Winning Trades</span>
                        <span className="font-medium text-green-600 dark:text-green-400">{selectedBacktest.winning_trades}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Losing Trades</span>
                        <span className="font-medium text-red-600 dark:text-red-400">{selectedBacktest.losing_trades}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Avg. Profit</span>
                        <span className="font-medium">${selectedBacktest.avg_profit.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Avg. Loss</span>
                        <span className="font-medium">${selectedBacktest.avg_loss.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Largest Win</span>
                        <span className="font-medium text-green-600 dark:text-green-400">${selectedBacktest.largest_win.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Largest Loss</span>
                        <span className="font-medium text-red-600 dark:text-red-400">${selectedBacktest.largest_loss.toFixed(2)}</span>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="card">
                  <h3 className="text-lg font-bold mb-4">Strategy Parameters</h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    {selectedBacktest.parameters && Object.entries(selectedBacktest.parameters).map(([key, value]) => (
                      <div key={key} className="bg-gray-50 dark:bg-slate-700 p-3 rounded-lg">
                        <span className="block text-sm text-gray-500 dark:text-gray-400">{key}</span>
                        <span className="block font-medium">{typeof value === 'boolean' ? (value ? 'Enabled' : 'Disabled') : value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="card">
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  Select a backtest to view details
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
