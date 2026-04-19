export interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  isStreaming?: boolean;
}

export type InspirationChatBootstrapSnapshot = {
  messages: Array<Pick<Message, 'id' | 'role' | 'content'>>;
  showBlueprintBtn: boolean;
  conversationState: any;
  options?: any[];
};

export const INSPIRATION_CHAT_BOOTSTRAP_TTL_MS = 10 * 60 * 1000;
export const INSPIRATION_CHAT_PERSIST_TTL_MS = 180 * 24 * 60 * 60 * 1000;

export const getInspirationChatBootstrapKey = (mode: 'novel' | 'coding', projectId: string) =>
  `afn:web:inspiration-chat:${mode}:${projectId}:bootstrap:v1`;

export const getInspirationChatPersistKey = (mode: 'novel' | 'coding', projectId: string) =>
  `afn:web:inspiration-chat:${mode}:${projectId}:state:v1`;

export type InspirationChatPersistEnvelope = {
  ts: number;
  conversationState: any;
  showBlueprintBtn: boolean;
};

type MaybeStructuredJson = Record<string, unknown> | unknown[] | null;

export const isPlainObject = (value: unknown): value is Record<string, unknown> =>
  Boolean(value) && typeof value === 'object' && !Array.isArray(value);

const canUseLocalStorage = () =>
  typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';

export const normalizeTextNewlines = (raw: string): string => {
  const text = String(raw ?? '');
  let normalized = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

  if (normalized.includes('\\n') || normalized.includes('\\r')) {
    normalized = normalized
      .replace(/\\r\\n/g, '\n')
      .replace(/\\n/g, '\n')
      .replace(/\\r/g, '\n');
  }

  return normalized;
};

export const readPersistedInspirationChatState = (
  key: string,
  maxAgeMs: number = INSPIRATION_CHAT_PERSIST_TTL_MS,
): InspirationChatPersistEnvelope | null => {
  if (!canUseLocalStorage()) return null;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as InspirationChatPersistEnvelope;
    if (!parsed || typeof parsed !== 'object') return null;
    if (!Number.isFinite(parsed.ts)) return null;
    if (Date.now() - parsed.ts > Math.max(0, maxAgeMs)) return null;
    if (!parsed.conversationState || typeof parsed.conversationState !== 'object') return null;
    return {
      ts: parsed.ts,
      conversationState: parsed.conversationState,
      showBlueprintBtn: Boolean(parsed.showBlueprintBtn),
    };
  } catch {
    return null;
  }
};

export const writePersistedInspirationChatState = (
  key: string,
  payload: Omit<InspirationChatPersistEnvelope, 'ts'>,
) => {
  if (!canUseLocalStorage()) return;
  try {
    const envelope: InspirationChatPersistEnvelope = {
      ts: Date.now(),
      conversationState: payload.conversationState,
      showBlueprintBtn: Boolean(payload.showBlueprintBtn),
    };
    window.localStorage.setItem(key, JSON.stringify(envelope));
  } catch {
    // ignore
  }
};

export const tryParseJsonFromText = (raw: string): MaybeStructuredJson => {
  const trimmed = String(raw || '').replace(/^\uFEFF/, '').trim();
  if (!trimmed) return null;

  const fenceMatch = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
  const candidate = (fenceMatch ? fenceMatch[1] : trimmed).trim();

  const startsLikeJson =
    (candidate.startsWith('{') && candidate.endsWith('}')) ||
    (candidate.startsWith('[') && candidate.endsWith(']'));
  if (!startsLikeJson) return null;

  try {
    return JSON.parse(candidate) as any;
  } catch {
    return null;
  }
};

export const pickFirstNonEmptyString = (value: unknown): string | null => {
  if (typeof value !== 'string') return null;
  const text = value.trim();
  return text ? text : null;
};

const deriveDisplayTextFromStructuredPayload = (
  payload: MaybeStructuredJson,
  role: Message['role'],
  depth: number = 0,
): string | null => {
  if (!payload) return null;
  if (depth >= 2) return null;

  if (role === 'user' && isPlainObject(payload)) {
    const userText =
      pickFirstNonEmptyString(payload.text) ??
      (isPlainObject(payload.user_input) ? pickFirstNonEmptyString(payload.user_input.text) : null);
    return userText;
  }

  if (Array.isArray(payload)) {
    const asStrings = payload
      .map((item) => (typeof item === 'string' ? item.trim() : ''))
      .filter(Boolean);
    if (asStrings.length > 0) return asStrings.join('\n');
    return null;
  }

  if (!isPlainObject(payload)) return null;

  const primaryKeys = [
    'ai_message',
    'message',
    'text',
    'answer',
    'content',
    'reply',
    'final_answer',
    'final',
    'output',
  ];

  for (const key of primaryKeys) {
    const picked = pickFirstNonEmptyString(payload[key]);
    if (picked) {
      const nested = tryParseJsonFromText(picked);
      return nested
        ? (deriveDisplayTextFromStructuredPayload(nested, role, depth + 1) ?? normalizeTextNewlines(picked))
        : normalizeTextNewlines(picked);
    }
  }

  const progressSummary = pickFirstNonEmptyString(payload.progress_summary);
  if (progressSummary) return normalizeTextNewlines(progressSummary);

  return null;
};

export const normalizeMessageContentForDisplay = (
  role: Message['role'],
  rawContent: unknown,
): string => {
  const text = String(rawContent ?? '');
  const parsed = tryParseJsonFromText(text);
  const derived = deriveDisplayTextFromStructuredPayload(parsed, role);
  return derived ?? text;
};

export type WorkspacePane = 'conversation' | 'guide';

export const WORKSPACE_PANE_ITEMS: Array<{
  id: WorkspacePane;
  label: string;
  hint: string;
}> = [
  {
    id: 'conversation',
    label: '对话区',
    hint: '继续推进灵感对话，保持上下文连续。',
  },
  {
    id: 'guide',
    label: '引导区',
    hint: '查看当前进度与生成提示，不把它们堆到主对话下面。',
  },
];
