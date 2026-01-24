import { useState, useRef, useCallback } from 'react';
import { API_BASE_URL } from '../api/client';

interface UseSSEReturn {
  connect: (url: string, body: any) => Promise<void>;
  disconnect: () => void;
  isConnected: boolean;
  error: Error | null;
}

export const useSSE = (
  onEvent: (event: string, data: any) => void
): UseSSEReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const connectWithParser = useCallback(async (endpoint: string, body: any) => {
    disconnect();
    abortControllerRef.current = new AbortController();
    setError(null);
    setIsConnected(true);

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify(body),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
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
            setError(err);
            onEvent('error', err);
        }
    } finally {
        setIsConnected(false);
    }
  }, [onEvent]);

  const disconnect = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsConnected(false);
  }, []);

  return {
    connect: connectWithParser,
    disconnect,
    isConnected,
    error
  };
};
