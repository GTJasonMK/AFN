import { useState, useRef, useCallback } from 'react';
import { API_BASE_URL } from '../api/client';

interface UseSSEReturn {
  connect: (url: string, body: any) => Promise<void>;
  disconnect: () => void;
  isConnected: boolean;
  error: Error | null;
}

const joinUrl = (baseUrl: string, endpoint: string): string => {
  const ep = String(endpoint || '').trim();
  if (!ep) return String(baseUrl || '').trim() || '';
  if (ep.startsWith('http://') || ep.startsWith('https://')) return ep;

  const base = String(baseUrl || '').trim();
  if (!base) return ep;

  const baseNoSlash = base.endsWith('/') ? base.slice(0, -1) : base;
  const endpointWithSlash = ep.startsWith('/') ? ep : `/${ep}`;
  return `${baseNoSlash}${endpointWithSlash}`;
};

const resolveDirectBackendApiBaseUrl = async (): Promise<string | null> => {
  if (typeof window === 'undefined') return null;
  const w = window as any;

  const bridge =
    (w?.api?.isElectron === true && typeof w?.api?.getBackendPort === 'function') ? w.api
      : (w?.electronAPI?.isElectron === true && typeof w?.electronAPI?.getBackendPort === 'function') ? w.electronAPI
        : null;

  if (!bridge) return null;

  try {
    const port = Number(await bridge.getBackendPort());
    if (!Number.isFinite(port) || port <= 0) return null;
    // Electron 后端始终监听本机端口
    return `http://127.0.0.1:${Math.trunc(port)}/api`;
  } catch {
    return null;
  }
};

export const useSSE = (
  onEvent: (event: string, data: any) => void
): UseSSEReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const disconnect = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const connectWithParser = useCallback(async (endpoint: string, body: any) => {
    disconnect();
    abortControllerRef.current = new AbortController();
    setError(null);
    setIsConnected(true);

    try {
      const headers = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      } as const;

      // 优先使用同源 /api（Vite proxy / Electron static proxy），失败后再尝试直连后端端口。
      // 这样可以避免某些环境下对 127.0.0.1:PORT 的直连被拦截/不可达导致的“连接拒绝”。
      const sameOriginUrl = joinUrl(API_BASE_URL, endpoint);
      const directBaseUrl = await resolveDirectBackendApiBaseUrl();
      const directUrl = directBaseUrl ? joinUrl(directBaseUrl, endpoint) : '';

      const candidateUrls = [sameOriginUrl].filter(Boolean);
      if (directUrl && directUrl !== sameOriginUrl) {
        candidateUrls.push(directUrl);
      }

      let response: Response | null = null;
      let lastError: any = null;

      for (const url of candidateUrls) {
        try {
          const res = await fetch(url, {
            method: 'POST',
            credentials: 'include',
            headers,
            body: JSON.stringify(body),
            signal: abortControllerRef.current?.signal,
          });
          if (!res.ok) {
            throw new Error(`HTTP ${res.status}（${res.statusText || 'Request failed'}）：${url}`);
          }
          response = res;
          break;
        } catch (err: any) {
          if (err?.name === 'AbortError') {
            throw err;
          }
          lastError = err;
        }
      }

      if (!response) {
        const tail = lastError instanceof Error ? lastError.message : String(lastError || 'Failed to fetch');
        const attemptedUrls = [...candidateUrls];
        const isConnRefused = /ECONNREFUSED|ERR_CONNECTION_REFUSED/i.test(tail);
        const isFailedFetch = /Failed to fetch|NetworkError|Load failed/i.test(tail);
        const reason = (isConnRefused || isFailedFetch) ? '无法连接后端服务' : 'SSE连接失败';

        // 详细诊断信息放到控制台，避免 toast/弹窗内容过长
        console.warn('[useSSE] connect failed', { attemptedUrls, tail, lastError });

        const err = new Error(`${reason}。请确认后端已启动且可访问（详情见控制台）。`);
        (err as any).attemptedUrls = attemptedUrls;
        (err as any).cause = lastError;
        throw err;
      }
      
      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      
      let currentEvent: string | null = null;
      let currentData: string = '';
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const rawLine of lines) {
          const line = rawLine.replace(/\r$/, '');
          if (line.startsWith('event:')) {
            currentEvent = line.substring('event:'.length).trim();
            continue;
          }
          if (line.startsWith('data:')) {
            const dataPart = line.substring('data:'.length).trimStart();
            // SSE规范：多个data行用换行符连接
            if (currentData.length > 0) {
              currentData += '\n';
            }
            currentData += dataPart;
            continue;
          }
          if (line.trim() === '') {
            if (currentEvent) {
              if (currentData) {
                try {
                  onEvent(currentEvent, JSON.parse(currentData));
                } catch {
                  onEvent(currentEvent, currentData);
                }
              } else {
                onEvent(currentEvent, null);
              }
            }
            currentEvent = null;
            currentData = '';
          }
        }
      }

    } catch (err: any) {
        if (err.name !== 'AbortError') {
            const safeError = err instanceof Error ? err : new Error(String(err || 'Unknown SSE error'));
            setError(safeError);
            onEvent('error', { message: safeError.message, error: safeError });
        }
    } finally {
        setIsConnected(false);
    }
  }, [onEvent, disconnect]);

  return {
    connect: connectWithParser,
    disconnect,
    isConnected,
    error
  };
};
