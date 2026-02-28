import { useCallback, useEffect, useRef } from 'react';

export const useTokenBuffer = (
  onFlushText: (text: string) => void,
  delayMs = 48,
) => {
  const tokensRef = useRef<string[]>([]);
  const timerRef = useRef<number | null>(null);

  const flush = useCallback(() => {
    if (tokensRef.current.length === 0) return;
    const text = tokensRef.current.join('');
    tokensRef.current = [];
    onFlushText(text);
  }, [onFlushText]);

  const reset = useCallback(() => {
    tokensRef.current = [];
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const scheduleFlush = useCallback(() => {
    if (timerRef.current !== null) return;
    timerRef.current = window.setTimeout(() => {
      timerRef.current = null;
      flush();
    }, Math.max(0, Math.floor(delayMs)));
  }, [delayMs, flush]);

  const pushToken = useCallback((token: string) => {
    tokensRef.current.push(String(token ?? ''));
    scheduleFlush();
  }, [scheduleFlush]);

  useEffect(() => {
    return () => reset();
  }, [reset]);

  return { pushToken, flush, reset };
};

