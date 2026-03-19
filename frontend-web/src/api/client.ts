import axios from 'axios';
import { useToast } from '../components/feedback/Toast';

// 使用相对路径以利用 Vite 代理
export const API_BASE_URL = '/api';
export const AUTH_UNAUTHORIZED_EVENT = 'afn-auth-unauthorized';
// 长耗时操作（蓝图/大纲/章节等）建议用更长的请求超时。
// 后端通常会有自己的超时保护（例如蓝图 8 分钟），前端不应过早超时导致“看起来失败但后台已成功”的错觉。
export const LONG_TASK_TIMEOUT_MS = 10 * 60 * 1000; // 10分钟

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,  // 2分钟，LLM调用需要较长时间
  // Cookie 登录（后端默认写入 HttpOnly Cookie）需要携带凭证
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

const formatValidationItem = (item: unknown): string => {
  if (!item || typeof item !== 'object') {
    return typeof item === 'string' ? item : '';
  }

  const record = item as { msg?: unknown; loc?: unknown };
  const msg = typeof record.msg === 'string' ? record.msg.trim() : '';
  if (!msg) return '';

  const loc = Array.isArray(record.loc)
    ? record.loc.map((entry) => String(entry).trim()).filter(Boolean).join('.')
    : '';

  return loc ? `${loc}: ${msg}` : msg;
};

export const extractApiErrorMessage = (error: any, fallback = 'Unknown error'): string => {
  const detail = error?.response?.data?.detail;

  if (typeof detail === 'string' && detail.trim()) {
    return detail.trim();
  }

  if (Array.isArray(detail)) {
    const merged = detail.map((item) => formatValidationItem(item)).filter(Boolean).slice(0, 3).join('；');
    if (merged) return merged;
  }

  if (detail && typeof detail === 'object') {
    try {
      const text = JSON.stringify(detail);
      if (text && text !== '{}') return text;
    } catch {
      // ignore
    }
  }

  const message = error?.response?.data?.message;
  if (typeof message === 'string' && message.trim()) {
    return message.trim();
  }

  const errorMessage = error?.message;
  if (typeof errorMessage === 'string' && errorMessage.trim()) {
    return errorMessage.trim();
  }

  return fallback;
};

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

    const status = Number(error.response?.status || 0);
    const message = extractApiErrorMessage(error);

    // 认证失败：无论是否 silent，都通知 AuthGate 处理（silent 仅控制 toast）
    if (status === 401) {
      try {
        window.dispatchEvent(new CustomEvent(AUTH_UNAUTHORIZED_EVENT, { detail: { message } }));
      } catch {
        // ignore
      }
      return Promise.reject(error);
    }

    // 允许单次请求关闭全局 toast（例如轮询/探测类请求）
    const silent = Boolean((error as any)?.config?.silent);
    if (silent) {
      return Promise.reject(error);
    }

    if (import.meta.env.DEV && error.response) {
      console.error('Full API Error Response:', error.response.data);
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
