import { useState, useEffect } from 'react';
import DashboardLayout from '../components/DashboardLayout';
import { fetchPerformance } from '../api/dashboard';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
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
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function Performance() {
  const [performance, setPerformance] = useState(null);
  const [timeframe, setTimeframe] = useState('1m');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const loadPerformanceData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const data = await fetchPerformance(timeframe);
        setPerformance(data);
      } catch (err) {
        console.error('Failed to load performance data:', err);
        setError('Failed to load performance data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };
    
    loadPerformanceData();
  }, [timeframe]);
  
  const timeframes = [
    { value: '1d', label: '1 Day' },
    { value: '1w', label: '1 Week' },
    { value: '1m', label: '1 Month' },
    { value: '3m', label: '3 Months' },
    { value: '1y', label: 'Year' },
    { value: 'all', label: 'All Time' }
  ];
  
  // 차트 옵션
  const lineChartOptions = {
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
  
  if (loading && !performance) {
    return (
      <DashboardLayout>
        <h1 className="text-2xl font-bold mb-6">Performance Analysis</h1>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    );
  }
  
  return (
    <DashboardLayout>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Performance Analysis</h1>
        <div className="flex space-x-1">
          {timeframes.map((tf) => (
            <button
              key={tf.value}
              className={`px-2 py-1 text-xs rounded-md ${
                timeframe === tf.value
                  ? 'bg-primary text-white'
                  : 'bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-slate-600'
              }`}
              onClick={() => setTimeframe(tf.value)}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>
      
      {error && (
        <div className="mb-6 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 p-4 rounded-md">
          {error}
        </div>
      )}
      
      {performance && (
        <>
          {/* 요약 통계 */}
          <div className="card mb-6">
            <h2 className="text-xl font-bold mb-4">Performance Summary</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="stat-item">
                <span className="stat-label">Total Return</span>
                <span className={`stat-value ${performance.total_return >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                  {performance.total_return >= 0 ? '+' : ''}{performance.total_return.toFixed(2)}%
                </span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Win Rate</span>
                <span className="stat-value">{performance.win_rate.toFixed(2)}%</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Max Drawdown</span>
                <span className="stat-value text-red-600 dark:text-red-400">{performance.max_drawdown.toFixed(2)}%</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Sharpe Ratio</span>
                <span className="stat-value">{performance.sharpe_ratio.toFixed(2)}</span>
              </div>
            </div>
          </div>
          
          {/* 자산 및 수익 차트 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="card">
              <h2 className="text-lg font-bold mb-4">Equity Curve</h2>
              <div className="h-64">
                <Line
                  options={lineChartOptions}
                  data={{
                    labels: performance.dates || [],
                    datasets: [
                      {
                        label: 'Equity',
                        data: performance.equity || [],
                        borderColor: 'rgb(53, 162, 235)',
                        backgroundColor: 'rgba(53, 162, 235, 0.5)',
                        tension: 0.2,
                        fill: true
                      }
                    ]
                  }}
                />
              </div>
            </div>
            
            <div className="card">
              <h2 className="text-lg font-bold mb-4">Cumulative Profit</h2>
              <div className="h-64">
                <Line
                  options={lineChartOptions}
                  data={{
                    labels: performance.dates || [],
                    datasets: [
                      {
                        label: 'Profit',
                        data: performance.profit || [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.5)',
                        tension: 0.2,
                        fill: true
                      }
                    ]
                  }}
                />
              </div>
            </div>
          </div>
          
          {/* 드로다운 및 월별 수익 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="card">
              <h2 className="text-lg font-bold mb-4">Drawdown</h2>
              <div className="h-64">
                <Line
                  options={{
                    ...lineChartOptions,
                    scales: {
                      ...lineChartOptions.scales,
                      y: {
                        ...lineChartOptions.scales.y,
                        reverse: true,
                        max: 0,
                        ticks: {
                          callback: function(value) {
                            return value + '%';
                          }
                        }
                      }
                    },
                    plugins: {
                      ...lineChartOptions.plugins,
                      tooltip: {
                        ...lineChartOptions.plugins.tooltip,
                        callbacks: {
                          label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                              label += ': ';
                            }
                            if (context.parsed.y !== null) {
                              label += context.parsed.y + '%';
                            }
                            return label;
                          }
                        }
                      }
                    }
                  }}
                  data={{
                    labels: performance.dates || [],
                    datasets: [
                      {
                        label: 'Drawdown',
                        data: performance.drawdown || [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.5)',
                        tension: 0.2,
                        fill: true
                      }
                    ]
                  }}
                />
              </div>
            </div>
            
            <div className="card">
              <h2 className="text-lg font-bold mb-4">Monthly Returns</h2>
              <div className="h-64">
                <Bar
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        display: false
                      },
                      tooltip: {
                        callbacks: {
                          label: function(context) {
                            let label = 'Return: ';
                            if (context.parsed.y !== null) {
                              label += context.parsed.y + '%';
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
                        },
                        ticks: {
                          callback: function(value) {
                            return value + '%';
                          }
                        }
                      }
                    }
                  }}
                  data={{
                    labels: performance.monthly_labels || [],
                    datasets: [
                      {
                        data: performance.monthly_returns || [],
                        backgroundColor: performance.monthly_returns?.map(value => 
                          value >= 0 ? 'rgba(75, 192, 192, 0.7)' : 'rgba(255, 99, 132, 0.7)'
                        ),
                        borderColor: performance.monthly_returns?.map(value => 
                          value >= 0 ? 'rgb(75, 192, 192)' : 'rgb(255, 99, 132)'
                        ),
                        borderWidth: 1
                      }
                    ]
                  }}
                />
              </div>
            </div>
          </div>
          
          {/* 거래 분석 및 심볼 분포 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="card">
              <h2 className="text-lg font-bold mb-4">Trade Analysis</h2>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="stat-item">
                  <span className="stat-label">Total Trades</span>
                  <span className="stat-value">{performance.total_trades}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Winning Trades</span>
                  <span className="stat-value text-green-600 dark:text-green-400">{performance.winning_trades}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Losing Trades</span>
                  <span className="stat-value text-red-600 dark:text-red-400">{performance.losing_trades}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Avg. Holding Time</span>
                  <span className="stat-value">{performance.avg_holding_time}</span>
                </div>
              </div>
              
              <div className="h-48">
                <Doughnut
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        position: 'right',
                        labels: {
                          usePointStyle: true,
                          boxWidth: 6
                        }
                      }
                    }
                  }}
                  data={{
                    labels: ['Winning Trades', 'Losing Trades'],
                    datasets: [
                      {
                        data: [performance.winning_trades, performance.losing_trades],
                        backgroundColor: [
                          'rgba(75, 192, 192, 0.7)',
                          'rgba(255, 99, 132, 0.7)'
                        ],
                        borderColor: [
                          'rgb(75, 192, 192)',
                          'rgb(255, 99, 132)'
                        ],
                        borderWidth: 1
                      }
                    ]
                  }}
                />
              </div>
            </div>
            
            <div className="card">
              <h2 className="text-lg font-bold mb-4">Symbol Distribution</h2>
              <div className="h-64">
                <Doughnut
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        position: 'right',
                        labels: {
                          usePointStyle: true,
                          boxWidth: 6
                        }
                      }
                    }
                  }}
                  data={{
                    labels: performance.symbol_labels || [],
                    datasets: [
                      {
                        data: performance.symbol_values || [],
                        backgroundColor: [
                          'rgba(255, 99, 132, 0.7)',
                          'rgba(54, 162, 235, 0.7)',
                          'rgba(255, 206, 86, 0.7)',
                          'rgba(75, 192, 192, 0.7)',
                          'rgba(153, 102, 255, 0.7)',
                          'rgba(255, 159, 64, 0.7)',
                          'rgba(199, 199, 199, 0.7)',
                          'rgba(83, 102, 255, 0.7)',
                          'rgba(40, 159, 64, 0.7)',
                          'rgba(210, 199, 199, 0.7)'
                        ],
                        borderColor: [
                          'rgb(255, 99, 132)',
                          'rgb(54, 162, 235)',
                          'rgb(255, 206, 86)',
                          'rgb(75, 192, 192)',
                          'rgb(153, 102, 255)',
                          'rgb(255, 159, 64)',
                          'rgb(199, 199, 199)',
                          'rgb(83, 102, 255)',
                          'rgb(40, 159, 64)',
                          'rgb(210, 199, 199)'
                        ],
                        borderWidth: 1
                      }
                    ]
                  }}
                />
              </div>
            </div>
          </div>
          
          {/* 상세 지표 */}
          <div className="card">
            <h2 className="text-lg font-bold mb-4">Performance Metrics</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div>
                <h3 className="text-md font-medium mb-2">Return Metrics</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Total Return</span>
                    <span className={`text-sm font-medium ${performance.total_return >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                      {performance.total_return >= 0 ? '+' : ''}{performance.total_return.toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Annual Return</span>
                    <span className={`text-sm font-medium ${performance.annual_return >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                      {performance.annual_return >= 0 ? '+' : ''}{performance.annual_return.toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Monthly Return</span>
                    <span className={`text-sm font-medium ${performance.monthly_return >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                      {performance.monthly_return >= 0 ? '+' : ''}{performance.monthly_return.toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Daily Return</span>
                    <span className={`text-sm font-medium ${performance.daily_return >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                      {performance.daily_return >= 0 ? '+' : ''}{performance.daily_return.toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>
              
              <div>
                <h3 className="text-md font-medium mb-2">Risk Metrics</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Max Drawdown</span>
                    <span className="text-sm font-medium text-red-600 dark:text-red-400">{performance.max_drawdown.toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Volatility</span>
                    <span className="text-sm font-medium">{performance.volatility.toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Downside Dev.</span>
                    <span className="text-sm font-medium">{performance.downside_deviation.toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Value at Risk</span>
                    <span className="text-sm font-medium text-red-600 dark:text-red-400">{performance.var.toFixed(2)}%</span>
                  </div>
                </div>
              </div>
              
              <div>
                <h3 className="text-md font-medium mb-2">Ratio Metrics</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Sharpe Ratio</span>
                    <span className="text-sm font-medium">{performance.sharpe_ratio.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Sortino Ratio</span>
                    <span className="text-sm font-medium">{performance.sortino_ratio.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Calmar Ratio</span>
                    <span className="text-sm font-medium">{performance.calmar_ratio.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Profit Factor</span>
                    <span className="text-sm font-medium">{performance.profit_factor.toFixed(2)}</span>
                  </div>
                </div>
              </div>
              
              <div>
                <h3 className="text-md font-medium mb-2">Trade Metrics</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Win Rate</span>
                    <span className="text-sm font-medium">{performance.win_rate.toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Avg. Win</span>
                    <span className="text-sm font-medium text-green-600 dark:text-green-400">${performance.avg_win.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Avg. Loss</span>
                    <span className="text-sm font-medium text-red-600 dark:text-red-400">${performance.avg_loss.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Expectancy</span>
                    <span className="text-sm font-medium">${performance.expectancy.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </DashboardLayout>
  );
}
