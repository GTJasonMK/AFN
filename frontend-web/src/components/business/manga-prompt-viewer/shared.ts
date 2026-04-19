export type BatchProgressState = {
  current: number;
  total: number;
  message: string;
} | null;

export const safeJson = (value: any) => {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value ?? '');
  }
};

export const widthRatioToSpan = (widthRatio: any): number => {
  const value = String(widthRatio || '').trim();
  if (value === 'full') return 12;
  if (value === 'two_thirds') return 8;
  if (value === 'half') return 6;
  if (value === 'third') return 4;
  return 6;
};

export const aspectRatioToCss = (aspectRatio: any): string | undefined => {
  const value = String(aspectRatio || '').trim();
  const matched = value.match(/^\s*(\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)\s*$/);
  if (!matched) return undefined;
  return `${matched[1]} / ${matched[2]}`;
};
