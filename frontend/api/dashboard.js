import axios from 'axios';

// 모의 데이터 가져오기
import {
  mockStatus,
  mockPerformance,
  mockTrades,
  mockParameters,
  mockBacktestResults,
  mockBacktestRun
} from './mockData';

// API 기본 URL 설정
const API_URL = process.env.API_URL || 'http://localhost:8000';

// 모의 데이터 사용 여부 설정
const USE_MOCK_DATA = true;

// 에러 핸들링 함수
const handleError = (error) => {
  console.error('API Error:', error);
  if (error.response) {
    // 서버가 응답을 반환한 경우
    console.error('Response data:', error.response.data);
    console.error('Response status:', error.response.status);
    
    // 401 Unauthorized 에러 처리 (토큰 만료 등)
    if (error.response.status === 401) {
      // 로컬 스토리지에서 토큰 제거
      localStorage.removeItem('token');
      // 로그인 페이지로 리다이렉트
      window.location.href = '/login';
    }
    
    throw error.response.data;
  } else if (error.request) {
    // 요청은 보냈지만 응답을 받지 못한 경우
    throw new Error('서버에 연결할 수 없습니다. 네트워크 연결을 확인하세요.');
  } else {
    // 요청 설정 중 오류가 발생한 경우
    throw new Error('요청 설정 중 오류가 발생했습니다.');
  }
};

// 봇 상태 조회
export const fetchStatus = async () => {
  try {
    if (USE_MOCK_DATA) {
      return mockStatus;
    }
    const response = await axios.get(`${API_URL}/api/bot/status`);
    return response.data;
  } catch (error) {
    if (USE_MOCK_DATA) {
      console.warn('Using mock data for bot status');
      return mockStatus;
    }
    return handleError(error);
  }
};

// 성능 데이터 조회
export const fetchPerformance = async (period = '1m') => {
  try {
    if (USE_MOCK_DATA) {
      console.log(`Fetching performance data for period: ${period} (mock)`);
      return mockPerformance;
    }
    const response = await axios.get(`${API_URL}/api/performance/summary?period=${period}`);
    return response.data;
  } catch (error) {
    if (USE_MOCK_DATA) {
      console.warn('Using mock data for performance');
      return mockPerformance;
    }
    return handleError(error);
  }
};

// 거래 내역 조회
export const fetchTrades = async (page = 1, limit = 10) => {
  try {
    if (USE_MOCK_DATA) {
      console.log(`Fetching trades for page ${page}, limit ${limit} (mock)`);
      return mockTrades;
    }
    const response = await axios.get(`${API_URL}/api/trades?page=${page}&limit=${limit}`);
    return response.data;
  } catch (error) {
    if (USE_MOCK_DATA) {
      console.warn('Using mock data for trades');
      return mockTrades;
    }
    return handleError(error);
  }
};

// 백테스트 결과 조회
export const fetchBacktestResults = async (page = 1, limit = 10) => {
  try {
    if (USE_MOCK_DATA) {
      console.log(`Fetching backtest results for page ${page}, limit ${limit} (mock)`);
      return mockBacktestResults;
    }
    const response = await axios.get(`${API_URL}/api/backtest/results?page=${page}&limit=${limit}`);
    return response.data;
  } catch (error) {
    if (USE_MOCK_DATA) {
      console.warn('Using mock data for backtest results');
      return mockBacktestResults;
    }
    return handleError(error);
  }
};

// 백테스트 결과 상세 정보 조회
export const fetchBacktestDetail = async (id) => {
  try {
    if (USE_MOCK_DATA) {
      console.log(`Fetching backtest detail for ID: ${id} (mock)`);
      // 해당 ID의 백테스트 결과 찾기
      const result = mockBacktestResults.items.find(item => item.id === parseInt(id)) || mockBacktestResults.items[0];
      return result;
    }
    const response = await axios.get(`${API_URL}/api/backtest/results/${id}`);
    return response.data;
  } catch (error) {
    if (USE_MOCK_DATA) {
      console.warn(`Using mock data for backtest detail (ID: ${id})`);
      return mockBacktestResults.items[0];
    }
    return handleError(error);
  }
};

// 백테스트 실행
export const runBacktest = async (params) => {
  try {
    if (USE_MOCK_DATA) {
      console.log('Running backtest with params (mock):', params);
      return mockBacktestRun;
    }
    const response = await axios.post(`${API_URL}/api/backtest/run`, params);
    return response.data;
  } catch (error) {
    if (USE_MOCK_DATA) {
      console.warn('Using mock data for backtest run');
      return mockBacktestRun;
    }
    return handleError(error);
  }
};

// 전략 파라미터 조회
export const fetchParameters = async () => {
  try {
    if (USE_MOCK_DATA) {
      console.log('Fetching strategy parameters (mock)');
      return mockParameters;
    }
    const response = await axios.get(`${API_URL}/api/parameters`);
    return response.data;
  } catch (error) {
    if (USE_MOCK_DATA) {
      console.warn('Using mock data for parameters');
      return mockParameters;
    }
    return handleError(error);
  }
};

// 전략 파라미터 업데이트
export const updateParameters = async (parameters) => {
  try {
    if (USE_MOCK_DATA) {
      console.log('Updating parameters (mock):', parameters);
      return { success: true, message: '파라미터가 성공적으로 업데이트되었습니다.' };
    }
    const response = await axios.put(`${API_URL}/api/parameters`, parameters);
    return response.data;
  } catch (error) {
    if (USE_MOCK_DATA) {
      console.warn('Using mock success response for parameter update');
      return { success: true, message: '파라미터가 성공적으로 업데이트되었습니다.' };
    }
    return handleError(error);
  }
};

// 봇 시작
export const startBot = async () => {
  try {
    if (USE_MOCK_DATA) {
      console.log('Starting bot (mock)');
      return { success: true, message: '봇이 성공적으로 시작되었습니다.' };
    }
    const response = await axios.post(`${API_URL}/api/bot/start`);
    return response.data;
  } catch (error) {
    if (USE_MOCK_DATA) {
      console.warn('Using mock success response for bot start');
      return { success: true, message: '봇이 성공적으로 시작되었습니다.' };
    }
    return handleError(error);
  }
};

// 봇 정지
export const stopBot = async () => {
  try {
    if (USE_MOCK_DATA) {
      console.log('Stopping bot (mock)');
      return { success: true, message: '봇이 성공적으로 정지되었습니다.' };
    }
    const response = await axios.post(`${API_URL}/api/bot/stop`);
    return response.data;
  } catch (error) {
    if (USE_MOCK_DATA) {
      console.warn('Using mock success response for bot stop');
      return { success: true, message: '봇이 성공적으로 정지되었습니다.' };
    }
    return handleError(error);
  }
};

// 봇 일시 중지
export const pauseBot = async () => {
  try {
    if (USE_MOCK_DATA) {
      console.log('Pausing bot (mock)');
      return { success: true, message: '봇이 성공적으로 일시 중지되었습니다.' };
    }
    const response = await axios.post(`${API_URL}/api/bot/pause`);
    return response.data;
  } catch (error) {
    if (USE_MOCK_DATA) {
      console.warn('Using mock success response for bot pause');
      return { success: true, message: '봇이 성공적으로 일시 중지되었습니다.' };
    }
    return handleError(error);
  }
};
