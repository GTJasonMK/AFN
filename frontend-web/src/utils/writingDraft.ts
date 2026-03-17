export type LocalDraft = {
  content: string;
  updatedAt: string;
};

const WRITING_DRAFT_PREFIX = 'afn:writing_draft:';
const projectDraftIndex = new Map<string, Set<number>>();

export const getWritingDraftKey = (projectId: string, chapterNumber: number) =>
  `${WRITING_DRAFT_PREFIX}${projectId}:${chapterNumber}`;

const parseWritingDraftKey = (key: string): { projectId: string; chapterNumber: number } | null => {
  const raw = String(key || '');
  if (!raw.startsWith(WRITING_DRAFT_PREFIX)) return null;
  const rest = raw.slice(WRITING_DRAFT_PREFIX.length);
  const lastColon = rest.lastIndexOf(':');
  if (lastColon <= 0) return null;

  const projectId = rest.slice(0, lastColon).trim();
  const chapterNumber = Number(rest.slice(lastColon + 1));
  if (!projectId || !Number.isFinite(chapterNumber) || chapterNumber <= 0) return null;
  return { projectId, chapterNumber };
};

const updateProjectDraftIndex = (key: string, present: boolean) => {
  const parsed = parseWritingDraftKey(key);
  if (!parsed) return;

  const existing = projectDraftIndex.get(parsed.projectId);
  if (!existing) return;

  if (present) {
    existing.add(parsed.chapterNumber);
    return;
  }

  existing.delete(parsed.chapterNumber);
};

export const getProjectWritingDraftSet = (projectId: string): ReadonlySet<number> => {
  const normalizedProjectId = String(projectId || '').trim();
  if (!normalizedProjectId) return new Set<number>();

  const cached = projectDraftIndex.get(normalizedProjectId);
  if (cached) return cached;

  const chapterNumbers = new Set<number>();
  try {
    for (let idx = 0; idx < localStorage.length; idx += 1) {
      const key = localStorage.key(idx);
      if (!key) continue;
      const parsed = parseWritingDraftKey(key);
      if (!parsed || parsed.projectId !== normalizedProjectId) continue;
      chapterNumbers.add(parsed.chapterNumber);
    }
  } catch {
    // ignore
  }

  projectDraftIndex.set(normalizedProjectId, chapterNumbers);
  return chapterNumbers;
};

export const readWritingDraft = (key: string): LocalDraft | null => {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<LocalDraft>;
    if (!parsed || typeof parsed.content !== 'string') return null;
    return {
      content: parsed.content,
      updatedAt: typeof parsed.updatedAt === 'string' ? parsed.updatedAt : new Date().toISOString(),
    };
  } catch {
    return null;
  }
};

export const writeWritingDraft = (key: string, content: string): boolean => {
  try {
    const payload: LocalDraft = { content, updatedAt: new Date().toISOString() };
    localStorage.setItem(key, JSON.stringify(payload));
    updateProjectDraftIndex(key, true);
    return true;
  } catch {
    // 浏览器可能禁用本地存储或容量不足
    return false;
  }
};

export const removeWritingDraft = (key: string): void => {
  try {
    localStorage.removeItem(key);
    updateProjectDraftIndex(key, false);
  } catch {
    // ignore
  }
};

export const hasWritingDraft = (key: string): boolean => {
  const parsed = parseWritingDraftKey(key);
  if (parsed) {
    const cached = projectDraftIndex.get(parsed.projectId);
    if (cached) return cached.has(parsed.chapterNumber);
  }
  try {
    return localStorage.getItem(key) !== null;
  } catch {
    return false;
  }
};
