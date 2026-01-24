import axios from 'axios';

// 后端默认端口 8123
export const API_BASE_URL = 'http://localhost:8123/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 响应拦截器处理错误
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// 定义通用的响应类型
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success?: boolean;
}