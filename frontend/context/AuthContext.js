import { createContext, useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import jwtDecode from 'jwt-decode';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const router = useRouter();

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('token');
    if (token) {
      try {
        // Verify token expiration
        const decodedToken = jwtDecode(token);
        const currentTime = Date.now() / 1000;
        
        if (decodedToken.exp < currentTime) {
          // Token expired
          logout();
        } else {
          // Set user from token
          setUser({
            id: decodedToken.sub,
            username: decodedToken.username,
            email: decodedToken.email,
            role: decodedToken.role
          });
          
          // Set default Authorization header
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        }
      } catch (error) {
        console.error('Invalid token:', error);
        logout();
      }
    }
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    try {
      setLoading(true);
      setError(null);
      
      // 백엔드 API 연결 전 테스트용 계정 정보
      // 실제 환경에서는 이 부분을 제거하고 API 호출 코드를 사용해야 함
      if (username === 'test' && password === 'password123') {
        // 테스트용 토큰 생성 (실제 JWT 형식은 아님)
        const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0IiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwicm9sZSI6InVzZXIiLCJleHAiOjk5OTk5OTk5OTl9';
        
        // Store token in localStorage
        localStorage.setItem('token', mockToken);
        
        // Set user
        setUser({
          id: '1',
          username: 'test',
          email: 'test@example.com',
          role: 'user'
        });
        
        return true;
      }
      
      // 백엔드 API 연결 시 사용할 코드 (현재는 비활성화)
      /*
      const response = await axios.post('/api/auth/login', { username, password });
      const { access_token } = response.data;
      
      // Store token in localStorage
      localStorage.setItem('token', access_token);
      
      // Set default Authorization header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      // Decode token and set user
      const decodedToken = jwtDecode(access_token);
      setUser({
        id: decodedToken.sub,
        username: decodedToken.username,
        email: decodedToken.email,
        role: decodedToken.role
      });
      */
      
      // 테스트 계정이 아닌 경우 오류 발생
      if (!(username === 'test' && password === 'password123')) {
        throw new Error('Invalid credentials');
      }
      
      return true;
    } catch (error) {
      console.error('Login error:', error);
      setError(error.response?.data?.detail || 'Login failed. Please check your credentials.');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const register = async (username, email, password) => {
    try {
      setLoading(true);
      setError(null);
      
      await axios.post('/api/auth/register', { username, email, password });
      return true;
    } catch (error) {
      console.error('Registration error:', error);
      setError(error.response?.data?.detail || 'Registration failed. Please try again.');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    // Remove token from localStorage
    localStorage.removeItem('token');
    
    // Remove Authorization header
    delete axios.defaults.headers.common['Authorization'];
    
    // Clear user state
    setUser(null);
    
    // Redirect to login page
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, loading, error, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
