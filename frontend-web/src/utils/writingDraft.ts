export type LocalDraft = {
  content: string;
  updatedAt: string;
};

export const getWritingDraftKey = (projectId: string, chapterNumber: number) =>
  `afn:writing_draft:${projectId}:${chapterNumber}`;

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
    return true;
  } catch {
    // 浏览器可能禁用本地存储或容量不足
    return false;
  }
};

export const removeWritingDraft = (key: string): void => {
  try {
    localStorage.removeItem(key);
  } catch {
    // ignore
  }
};

export const hasWritingDraft = (key: string): boolean => {
  try {
    return localStorage.getItem(key) !== null;
  } catch {
    return false;
  }
};

