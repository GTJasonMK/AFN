import axios from 'axios';
import { useToast } from '../components/feedback/Toast';

// 使用相对路径以利用 Vite 代理
export const API_BASE_URL = '/api';
export const AUTH_UNAUTHORIZED_EVENT = 'afn-auth-unauthorized';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,  // 2分钟，LLM调用需要较长时间
  headers: {
    'Content-Type': 'application/json',
  },
});

// 响应拦截器处理错误
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // 主动取消（AbortController / axios cancel）不需要全局 toast
    const code = (error as any)?.code;
    const name = (error as any)?.name;
    if (code === 'ERR_CANCELED' || name === 'CanceledError') {
      return Promise.reject(error);
    }

    // 允许单次请求关闭全局 toast（例如轮询/探测类请求）
    const silent = Boolean((error as any)?.config?.silent);
    if (silent) {
      return Promise.reject(error);
    }

    if (error.response) {
        console.error("Full API Error Response:", error.response.data);
    }
    const message = error.response?.data?.detail || error.message || 'Unknown error';

    // 认证失败：交由 AuthGate 处理，不重复弹 toast
    if (error.response?.status === 401) {
      try {
        window.dispatchEvent(new CustomEvent(AUTH_UNAUTHORIZED_EVENT, { detail: { message } }));
      } catch {
        // ignore
      }
      return Promise.reject(error);
    }

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
