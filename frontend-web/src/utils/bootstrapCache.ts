type CacheEnvelope<T> = {
  ts: number;
  data: T;
};

const canUseStorage = () => typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined';

export const readBootstrapCache = <T>(key: string, maxAgeMs = 5 * 60 * 1000): T | null => {
  if (!canUseStorage()) return null;
  try {
    const raw = window.sessionStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CacheEnvelope<T>;
    if (!parsed || typeof parsed !== 'object') return null;
    if (!Number.isFinite(parsed.ts)) return null;
    if (Date.now() - parsed.ts > Math.max(0, maxAgeMs)) return null;
    return parsed.data ?? null;
  } catch {
    return null;
  }
};

export const writeBootstrapCache = <T>(key: string, data: T) => {
  if (!canUseStorage()) return;
  try {
    const payload: CacheEnvelope<T> = {
      ts: Date.now(),
      data,
    };
    window.sessionStorage.setItem(key, JSON.stringify(payload));
  } catch {
    // ignore
  }
};

export const clearBootstrapCache = (key: string) => {
  if (!canUseStorage()) return;
  try {
    window.sessionStorage.removeItem(key);
  } catch {
    // ignore
  }
};
