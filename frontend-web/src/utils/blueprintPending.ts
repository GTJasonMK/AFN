export type BlueprintPendingKind = 'novel' | 'coding';

type PendingEnvelope = {
  ts: number;
};

const KEY_PREFIX = 'afn:web:blueprint_pending';
const DEFAULT_TTL_MS = 45 * 60 * 1000;

const normalizeProjectId = (projectId: string): string => String(projectId || '').trim();

const canUseLocalStorage = (): boolean =>
  typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';

export const getBlueprintPendingKey = (kind: BlueprintPendingKind, projectId: string): string =>
  `${KEY_PREFIX}:${kind}:${normalizeProjectId(projectId)}:v1`;

export const markBlueprintGenerationPending = (kind: BlueprintPendingKind, projectId: string): void => {
  if (!canUseLocalStorage()) return;
  const id = normalizeProjectId(projectId);
  if (!id) return;
  try {
    const envelope: PendingEnvelope = { ts: Date.now() };
    window.localStorage.setItem(getBlueprintPendingKey(kind, id), JSON.stringify(envelope));
  } catch {
    // ignore
  }
};

export const clearBlueprintGenerationPending = (kind: BlueprintPendingKind, projectId: string): void => {
  if (!canUseLocalStorage()) return;
  const id = normalizeProjectId(projectId);
  if (!id) return;
  try {
    window.localStorage.removeItem(getBlueprintPendingKey(kind, id));
  } catch {
    // ignore
  }
};

export const hasRecentBlueprintGenerationPending = (
  kind: BlueprintPendingKind,
  projectId: string,
  ttlMs: number = DEFAULT_TTL_MS,
): boolean => {
  if (!canUseLocalStorage()) return false;
  const id = normalizeProjectId(projectId);
  if (!id) return false;

  try {
    const raw = window.localStorage.getItem(getBlueprintPendingKey(kind, id));
    if (!raw) return false;

    const parsed = JSON.parse(raw) as Partial<PendingEnvelope> | null;
    const ts = Number(parsed?.ts || 0);
    if (!Number.isFinite(ts) || ts <= 0) return false;

    return Date.now() - ts <= Math.max(0, ttlMs);
  } catch {
    return false;
  }
};

