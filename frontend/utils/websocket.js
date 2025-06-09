import { io } from 'socket.io-client';

// 모의 데이터 사용 여부
const USE_MOCK_WEBSOCKET = true;

let socket = null;
let mockCallbacks = {};
let mockInterval = null;

// 모의 이벤트 데이터
const mockEvents = {
  'trade_update': [
    { id: 1001, symbol: 'BTC/USDT', type: 'buy', price: 42150.25, amount: 0.05, timestamp: Date.now() },
    { id: 1002, symbol: 'ETH/USDT', type: 'sell', price: 2250.75, amount: 0.8, timestamp: Date.now() },
    { id: 1003, symbol: 'SOL/USDT', type: 'buy', price: 105.50, amount: 10, timestamp: Date.now() }
  ],
  'price_update': [
    { symbol: 'BTC/USDT', price: 42150.25, change: 1.2 },
    { symbol: 'ETH/USDT', price: 2250.75, change: -0.5 },
    { symbol: 'BNB/USDT', price: 380.20, change: 0.8 },
    { symbol: 'SOL/USDT', price: 105.50, change: 2.3 },
    { symbol: 'XRP/USDT', price: 0.52, change: -1.1 }
  ],
  'bot_status': [
    { status: 'running', mode: 'paper', active_trades: 2 },
    { status: 'paused', mode: 'paper', active_trades: 1 },
    { status: 'stopped', mode: 'paper', active_trades: 0 }
  ],
  'portfolio_update': [
    { balance: 10245.67, equity: 10500.23, profit_today: 125.45, profit_today_percentage: 1.23 },
    { balance: 10300.42, equity: 10550.18, profit_today: 150.32, profit_today_percentage: 1.45 },
    { balance: 10275.89, equity: 10525.67, profit_today: 135.78, profit_today_percentage: 1.32 }
  ]
};

// 모의 WebSocket 연결
const connectMockWebSocket = () => {
  console.log('Mock WebSocket connected');
  
  // 이벤트 발생 시뮬레이션
  mockInterval = setInterval(() => {
    // 각 이벤트 형식에 대해 랜덤하게 데이터 전송
    Object.keys(mockEvents).forEach(eventName => {
      if (mockCallbacks[eventName]) {
        const eventData = mockEvents[eventName][Math.floor(Math.random() * mockEvents[eventName].length)];
        // 타임스태프 업데이트
        if (eventData.timestamp) {
          eventData.timestamp = Date.now();
        }
        mockCallbacks[eventName].forEach(callback => callback(eventData));
      }
    });
  }, 5000); // 5초마다 이벤트 발생
  
  return {
    on: (event, callback) => {
      if (!mockCallbacks[event]) {
        mockCallbacks[event] = [];
      }
      mockCallbacks[event].push(callback);
    },
    off: (event, callback) => {
      if (mockCallbacks[event]) {
        mockCallbacks[event] = mockCallbacks[event].filter(cb => cb !== callback);
      }
    },
    emit: (event, data) => {
      console.log(`Mock WebSocket emit: ${event}`, data);
      // 서버로 이벤트 전송 시뮬레이션
      setTimeout(() => {
        if (event === 'start_bot') {
          if (mockCallbacks['bot_status']) {
            mockCallbacks['bot_status'].forEach(callback => 
              callback({ status: 'running', mode: 'paper', active_trades: 0 })
            );
          }
        } else if (event === 'stop_bot') {
          if (mockCallbacks['bot_status']) {
            mockCallbacks['bot_status'].forEach(callback => 
              callback({ status: 'stopped', mode: 'paper', active_trades: 0 })
            );
          }
        } else if (event === 'pause_bot') {
          if (mockCallbacks['bot_status']) {
            mockCallbacks['bot_status'].forEach(callback => 
              callback({ status: 'paused', mode: 'paper', active_trades: 0 })
            );
          }
        }
      }, 500);
    },
    disconnect: () => {
      if (mockInterval) {
        clearInterval(mockInterval);
        mockInterval = null;
      }
      mockCallbacks = {};
      console.log('Mock WebSocket disconnected');
    }
  };
};

export const connectWebSocket = (token) => {
  if (socket) {
    // 이미 연결된 경우 기존 소켓 반환
    return socket;
  }

  // 모의 WebSocket 사용
  if (USE_MOCK_WEBSOCKET) {
    socket = connectMockWebSocket();
    return socket;
  }

  // 실제 Socket.IO 연결 코드
  const WS_URL = process.env.WS_URL || 'ws://localhost:8000';
  
  // Socket.IO 클라이언트 생성
  socket = io(WS_URL, {
    auth: {
      token
    },
    transports: ['websocket'],
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    timeout: 20000
  });

  // 연결 이벤트 핸들러
  socket.on('connect', () => {
    console.log('WebSocket connected');
  });

  // 연결 오류 핸들러
  socket.on('connect_error', (error) => {
    console.error('WebSocket connection error:', error);
  });

  // 재연결 시도 핸들러
  socket.on('reconnect_attempt', (attemptNumber) => {
    console.log(`WebSocket reconnection attempt: ${attemptNumber}`);
  });

  // 재연결 실패 핸들러
  socket.on('reconnect_failed', () => {
    console.error('WebSocket reconnection failed');
  });

  // 연결 해제 핸들러
  socket.on('disconnect', (reason) => {
    console.log(`WebSocket disconnected: ${reason}`);
  });

  return socket;
};

export const disconnectWebSocket = () => {
  if (socket) {
    socket.disconnect();
    socket = null;
    console.log('WebSocket disconnected');
  }
};

export const subscribeToEvent = (event, callback) => {
  if (!socket) {
    console.error('WebSocket not connected');
    return;
  }
  
  socket.on(event, callback);
  return () => socket.off(event, callback); // 구독 해제 함수 반환
};

export const emitEvent = (event, data) => {
  if (!socket) {
    console.error('WebSocket not connected');
    return;
  }
  
  socket.emit(event, data);
};
