export type OptimizationMode = 'auto' | 'review' | 'plan';
export type AnalysisScope = 'full' | 'selected';

export type ParagraphPreview = {
  index: number;
  preview: string;
  length: number;
};

export type ParagraphPreviewResponse = {
  total_paragraphs: number;
  paragraphs: ParagraphPreview[];
};

export type Suggestion = {
  paragraph_index: number;
  original_text: string;
  suggested_text: string;
  reason: string;
  category: string;
  priority: string;
};

export type UndoSnapshot = {
  content: string;
  key: string;
  label: string;
};

export type ThinkingEventType =
  | 'thinking'
  | 'action'
  | 'observation'
  | 'progress'
  | 'error';

export type ThinkingEvent = {
  id: string;
  type: ThinkingEventType;
  title: string;
  content: string;
  ts: number;
};

export type InlineDiffSeg = {
  type: 'same' | 'remove' | 'add';
  text: string;
};

export type InlinePreviewState = {
  suggestion: Suggestion;
  key: string;
  beforeContent: string;
  afterContent: string;
  label: string;
  range: { start: number; end: number } | null;
};

export const DIMENSIONS: Array<{ id: string; label: string }> = [
  { id: 'coherence', label: '逻辑连贯性' },
  { id: 'character', label: '角色一致性' },
  { id: 'foreshadow', label: '伏笔呼应' },
  { id: 'timeline', label: '时间线一致性' },
  { id: 'style', label: '风格一致性' },
  { id: 'scene', label: '场景描写' },
];

export const priorityColor: Record<string, string> = {
  high: 'text-red-600',
  medium: 'text-orange-600',
  low: 'text-book-text-muted',
};

export const THINKING_LABELS: Record<
  ThinkingEventType,
  { label: string; cls: string }
> = {
  thinking: { label: 'Thinking', cls: 'text-book-primary' },
  action: { label: 'Action', cls: 'text-book-accent' },
  observation: { label: 'Observation', cls: 'text-green-600' },
  progress: { label: 'Progress', cls: 'text-book-text-muted' },
  error: { label: 'Error', cls: 'text-red-600' },
};

type ParagraphSlice = {
  start: number;
  end: number;
  text: string;
};

export const getSuggestionKey = (suggestion: Suggestion): string => {
  return `${suggestion.paragraph_index}:${suggestion.category}:${suggestion.priority}:${(suggestion.original_text || '').length}`;
};

export const splitParagraphs = (text: string): ParagraphSlice[] => {
  const parts: ParagraphSlice[] = [];
  const separator = /\n{2,}/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = separator.exec(text)) !== null) {
    const end = match.index;
    parts.push({
      start: lastIndex,
      end,
      text: text.slice(lastIndex, end),
    });
    lastIndex = match.index + match[0].length;
  }

  parts.push({
    start: lastIndex,
    end: text.length,
    text: text.slice(lastIndex),
  });

  return parts;
};

export const buildUpdatedContent = (
  suggestion: Suggestion,
  current: string
): { content: string; range: { start: number; end: number } } | null => {
  const target = suggestion.original_text || '';
  const replacement = suggestion.suggested_text || '';
  if (!target.trim()) {
    return null;
  }

  const paragraphIndex =
    typeof suggestion.paragraph_index === 'number'
      ? suggestion.paragraph_index
      : -1;
  const paragraphs = splitParagraphs(current);
  const paragraph =
    paragraphIndex >= 0 && paragraphIndex < paragraphs.length
      ? paragraphs[paragraphIndex]
      : null;

  if (paragraph && paragraph.text.includes(target)) {
    const localIndex = paragraph.text.indexOf(target);
    const replacedParagraph =
      paragraph.text.slice(0, localIndex) +
      replacement +
      paragraph.text.slice(localIndex + target.length);
    const updated =
      current.slice(0, paragraph.start) +
      replacedParagraph +
      current.slice(paragraph.end);
    const start = paragraph.start + localIndex;

    return {
      content: updated,
      range: { start, end: start + replacement.length },
    };
  }

  const index = current.indexOf(target);
  if (index < 0) {
    return null;
  }

  return {
    content:
      current.slice(0, index) +
      replacement +
      current.slice(index + target.length),
    range: { start: index, end: index + replacement.length },
  };
};

export const buildSimpleInlineDiff = (
  original: string,
  suggested: string
): InlineDiffSeg[] => {
  const source = String(original || '');
  const target = String(suggested || '');

  if (!source && !target) {
    return [];
  }
  if (source === target) {
    return [{ type: 'same', text: source }];
  }

  const maxPrefix = Math.min(source.length, target.length);
  let prefix = 0;
  while (prefix < maxPrefix && source[prefix] === target[prefix]) {
    prefix += 1;
  }

  const maxSuffix = maxPrefix - prefix;
  let suffix = 0;
  while (
    suffix < maxSuffix &&
    source[source.length - 1 - suffix] ===
      target[target.length - 1 - suffix]
  ) {
    suffix += 1;
  }

  const sourceMiddle = source.slice(prefix, source.length - suffix);
  const targetMiddle = target.slice(prefix, target.length - suffix);
  const head = source.slice(0, prefix);
  const tail = suffix ? source.slice(source.length - suffix) : '';

  const segments: InlineDiffSeg[] = [];
  if (head) {
    segments.push({ type: 'same', text: head });
  }
  if (sourceMiddle) {
    segments.push({ type: 'remove', text: sourceMiddle });
  }
  if (targetMiddle) {
    segments.push({ type: 'add', text: targetMiddle });
  }
  if (tail) {
    segments.push({ type: 'same', text: tail });
  }

  return segments;
};

export const parseRangeInput = (
  text: string,
  maxCount: number
): number[] => {
  const raw = (text || '').trim();
  if (!raw) {
    return [];
  }

  const maxIndex = Math.max(0, Math.floor(maxCount));
  const result = new Set<number>();
  const parts = raw
    .split(/[,\s]+/g)
    .map((part) => part.trim())
    .filter(Boolean);

  for (const part of parts) {
    if (part.includes('-')) {
      const range = part
        .split('-')
        .map((segment) => segment.trim())
        .filter(Boolean);
      if (range.length !== 2) {
        continue;
      }

      const start = Number(range[0]);
      const end = Number(range[1]);
      if (!Number.isFinite(start) || !Number.isFinite(end)) {
        continue;
      }

      const min = Math.max(1, Math.floor(Math.min(start, end)));
      const max = Math.max(1, Math.floor(Math.max(start, end)));
      for (let current = min; current <= max; current += 1) {
        const index = current - 1;
        if (index >= 0 && index < maxIndex) {
          result.add(index);
        }
      }
      continue;
    }

    const value = Number(part);
    if (!Number.isFinite(value)) {
      continue;
    }

    const index = Math.floor(value) - 1;
    if (index >= 0 && index < maxIndex) {
      result.add(index);
    }
  }

  return Array.from(result).sort((left, right) => left - right);
};

export const formatThinkingTimestamp = (timestamp: number): string => {
  try {
    return new Date(timestamp).toLocaleTimeString();
  } catch {
    return '';
  }
};
