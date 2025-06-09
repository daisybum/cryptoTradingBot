import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import DashboardLayout from '../components/DashboardLayout';
import PortfolioOverview from '../components/PortfolioOverview';
import TradeHistory from '../components/TradeHistory';
import PerformanceCharts from '../components/PerformanceCharts';
import { fetchStatus, fetchPerformance } from '../api/dashboard';
import { connectWebSocket, subscribeToEvent } from '../utils/websocket';

export default function Dashboard() {
  const { user } = useAuth();
  const [status, setStatus] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const [statusData, performanceData] = await Promise.all([
          fetchStatus(),
          fetchPerformance()
        ]);
        
        setStatus(statusData);
        setPerformance(performanceData);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
        setError('Failed to load dashboard data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };
    
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 60000); // 1분마다 갱신
    
    return () => clearInterval(interval);
  }, []);
  
  // WebSocket 연결 설정
  useEffect(() => {
    if (!user) return;
    
    const token = localStorage.getItem('token');
    if (!token) return;
    
    // WebSocket 연결
    const socket = connectWebSocket(token);
    
    // 상태 업데이트 이벤트 구독
    const unsubscribeStatus = subscribeToEvent('status_update', (data) => {
      console.log('Received status update:', data);
      setStatus(data);
    });
    
    // 성능 업데이트 이벤트 구독
    const unsubscribePerformance = subscribeToEvent('performance_update', (data) => {
      console.log('Received performance update:', data);
      setPerformance(data);
    });
    
    return () => {
      unsubscribeStatus();
      unsubscribePerformance();
    };
  }, [user]);
  
  if (loading && !status && !performance) {
    return (
      <DashboardLayout>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    );
  }
  
  return (
    <DashboardLayout>
      <h1 className="text-2xl font-bold mb-6">NASOSv5_mod3 Trading Dashboard</h1>
      
      {error && (
        <div className="bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 p-4 rounded-md mb-6">
          {error}
        </div>
      )}
      
      <PortfolioOverview status={status} />
      
      <div className="mt-6">
        <PerformanceCharts performance={performance} />
      </div>
      
      <div className="mt-6">
        <TradeHistory />
      </div>
    </DashboardLayout>
  );
}
