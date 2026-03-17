import { scheduleIdleTask } from './scheduleIdleTask';

type CacheEnvelope<T> = {
  ts: number;
  data: T;
};

const canUseStorage = () => typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined';
const BOOTSTRAP_WRITE_DEBOUNCE_MS = 300;

type PendingBootstrapWrite = {
  data: unknown;
  timerId: number | null;
  cancelIdle: (() => void) | null;
};

const pendingWrites = new Map<string, PendingBootstrapWrite>();
const lastCommittedDataPayloads = new Map<string, string>();

const cancelPendingWrite = (key: string) => {
  const pending = pendingWrites.get(key);
  if (!pending) return;
  if (pending.timerId !== null) {
    window.clearTimeout(pending.timerId);
  }
  pending.cancelIdle?.();
  pendingWrites.delete(key);
};

const commitBootstrapWrite = (key: string, data: unknown) => {
  try {
    const serializedData = JSON.stringify(data);
    if (lastCommittedDataPayloads.get(key) === serializedData) return;

    const payload = JSON.stringify({
      ts: Date.now(),
      data,
    } satisfies CacheEnvelope<unknown>);

    window.sessionStorage.setItem(key, payload);
    lastCommittedDataPayloads.set(key, serializedData);
  } catch {
    // ignore
  }
};

export const readBootstrapCache = <T>(key: string, maxAgeMs = 5 * 60 * 1000): T | null => {
  if (!canUseStorage()) return null;
  try {
    const raw = window.sessionStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CacheEnvelope<T>;
    if (!parsed || typeof parsed !== 'object') return null;
    if (!Number.isFinite(parsed.ts)) return null;
    if (Date.now() - parsed.ts > Math.max(0, maxAgeMs)) return null;
    try {
      lastCommittedDataPayloads.set(key, JSON.stringify(parsed.data ?? null));
    } catch {
      // ignore
    }
    return parsed.data ?? null;
  } catch {
    return null;
  }
};

export const writeBootstrapCache = <T>(key: string, data: T) => {
  if (!canUseStorage()) return;

  cancelPendingWrite(key);

  const pending: PendingBootstrapWrite = {
    data,
    timerId: null,
    cancelIdle: null,
  };

  pending.timerId = window.setTimeout(() => {
    pending.timerId = null;
    pending.cancelIdle = scheduleIdleTask(() => {
      pending.cancelIdle = null;
      commitBootstrapWrite(key, pending.data);
      pendingWrites.delete(key);
    }, { timeout: 1200 });
  }, BOOTSTRAP_WRITE_DEBOUNCE_MS);

  pendingWrites.set(key, pending);
};

export const clearBootstrapCache = (key: string) => {
  if (!canUseStorage()) return;
  cancelPendingWrite(key);
  lastCommittedDataPayloads.delete(key);
  try {
    window.sessionStorage.removeItem(key);
  } catch {
    // ignore
  }
};
