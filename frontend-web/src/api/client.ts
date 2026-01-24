import axios from 'axios';
import { useToast } from '../components/feedback/Toast';

// 使用相对路径以利用 Vite 代理
export const API_BASE_URL = '/api';

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
    if (error.response) {
        console.error("Full API Error Response:", error.response.data);
    }
    const message = error.response?.data?.detail || error.message || 'Unknown error';
    console.error('API Error:', message);
    
    // Trigger global toast
    // Note: useToast is a hook, but Zustand stores can be used outside components via getState()
    // However, hooks rule applies. We'll use the vanilla store access.
    useToast.getState().addToast(message, 'error');
    
    return Promise.reject(error);
  }
);

// 定义通用的响应类型
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success?: boolean;
}