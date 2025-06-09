import { useState } from 'react';
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

export default function PerformanceCharts({ performance }) {
  const [timeframe, setTimeframe] = useState('1m');
  
  if (!performance) return null;
  
  const timeframes = [
    { value: '1d', label: '1 Day' },
    { value: '1w', label: '1 Week' },
    { value: '1m', label: '1 Month' },
    { value: '3m', label: '3 Months' },
    { value: '1y', label: 'Year' },
    { value: 'all', label: 'All Time' }
  ];
  
  // 성능 데이터 준비
  const labels = performance.dates || [];
  const equityData = performance.equity || [];
  const profitData = performance.profit || [];
  const drawdownData = performance.drawdown || [];
  
  // 차트 옵션
  const commonOptions = {
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
  
  // 자산 차트 데이터
  const equityChartData = {
    labels,
    datasets: [
      {
        label: 'Equity',
        data: equityData,
        borderColor: 'rgb(53, 162, 235)',
        backgroundColor: 'rgba(53, 162, 235, 0.5)',
        tension: 0.2,
        fill: true
      }
    ]
  };
  
  // 수익 차트 데이터
  const profitChartData = {
    labels,
    datasets: [
      {
        label: 'Profit',
        data: profitData,
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
        tension: 0.2,
        fill: true
      }
    ]
  };
  
  // 드로다운 차트 데이터
  const drawdownChartData = {
    labels,
    datasets: [
      {
        label: 'Drawdown',
        data: drawdownData,
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
        tension: 0.2,
        fill: true
      }
    ]
  };
  
  return (
    <div className="card">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Performance</h2>
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
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow-sm">
          <h3 className="text-lg font-medium mb-2">Equity</h3>
          <div className="h-64">
            <Line options={commonOptions} data={equityChartData} />
          </div>
        </div>
        
        <div className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow-sm">
          <h3 className="text-lg font-medium mb-2">Profit</h3>
          <div className="h-64">
            <Line options={commonOptions} data={profitChartData} />
          </div>
        </div>
      </div>
      
      <div className="mt-6">
        <div className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow-sm">
          <h3 className="text-lg font-medium mb-2">Drawdown</h3>
          <div className="h-64">
            <Line 
              options={{
                ...commonOptions,
                scales: {
                  ...commonOptions.scales,
                  y: {
                    ...commonOptions.scales.y,
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
                  ...commonOptions.plugins,
                  tooltip: {
                    ...commonOptions.plugins.tooltip,
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
              data={drawdownChartData} 
            />
          </div>
        </div>
      </div>
      
      <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="stat-item">
          <span className="stat-label">Total Return</span>
          <span className="stat-value text-success-dark dark:text-success-light">
            {performance.total_return ? `${performance.total_return.toFixed(2)}%` : 'N/A'}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Win Rate</span>
          <span className="stat-value">
            {performance.win_rate ? `${performance.win_rate.toFixed(2)}%` : 'N/A'}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Max Drawdown</span>
          <span className="stat-value text-danger-dark dark:text-danger-light">
            {performance.max_drawdown ? `${performance.max_drawdown.toFixed(2)}%` : 'N/A'}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Sharpe Ratio</span>
          <span className="stat-value">
            {performance.sharpe_ratio ? performance.sharpe_ratio.toFixed(2) : 'N/A'}
          </span>
        </div>
      </div>
    </div>
  );
}
