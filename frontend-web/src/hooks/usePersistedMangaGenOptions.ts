import { useCallback, useMemo } from 'react';
import { usePersistedState } from './usePersistedState';

export type MangaGenStyle = 'manga' | 'anime' | 'comic' | 'webtoon' | 'custom';
export type MangaGenLanguage = 'chinese' | 'japanese' | 'english' | 'korean';
export type MangaStartFromStage =
  | 'auto'
  | 'extraction'
  | 'planning'
  | 'storyboard'
  | 'prompt_building'
  | 'page_prompt_building';

export type MangaGenOptions = {
  genStyle: MangaGenStyle;
  customStyle: string;
  genLanguage: MangaGenLanguage;
  minPages: number;
  maxPages: number;
  usePortraits: boolean;
  autoGeneratePortraits: boolean;
  autoGeneratePageImages: boolean;
  pagePromptConcurrency: number;
  startFromStage: MangaStartFromStage;
  forceRestart: boolean;
};

const DEFAULT_CUSTOM_STYLE = '漫画风格, 黑白漫画, 网点纸, 日式漫画, 精细线条, 高对比度';

const STYLE_OPTIONS: readonly MangaGenStyle[] = ['manga', 'anime', 'comic', 'webtoon', 'custom'] as const;
const LANGUAGE_OPTIONS: readonly MangaGenLanguage[] = ['chinese', 'japanese', 'english', 'korean'] as const;
const START_STAGE_OPTIONS: readonly MangaStartFromStage[] = [
  'auto',
  'extraction',
  'planning',
  'storyboard',
  'prompt_building',
  'page_prompt_building',
] as const;

const isOneOf = <T extends string>(value: unknown, allowed: readonly T[]): value is T =>
  typeof value === 'string' && allowed.includes(value as T);

const clampInt = (value: unknown, min: number, max: number, fallback: number) => {
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(min, Math.min(max, Math.floor(n)));
};

const DEFAULT_OPTIONS: MangaGenOptions = {
  genStyle: 'manga',
  customStyle: DEFAULT_CUSTOM_STYLE,
  genLanguage: 'chinese',
  minPages: 8,
  maxPages: 15,
  usePortraits: true,
  autoGeneratePortraits: true,
  autoGeneratePageImages: false,
  pagePromptConcurrency: 5,
  startFromStage: 'auto',
  forceRestart: false,
};

const createDefaultOptions = (): MangaGenOptions => ({ ...DEFAULT_OPTIONS });

const parsePersistedOptions = (raw: string): MangaGenOptions => {
  const defaults = createDefaultOptions();

  try {
    const d = JSON.parse(raw) as any;
    const opts: MangaGenOptions = { ...defaults };

    const styleMode = d?.styleMode;
    const style = d?.style;
    const customStyle = d?.customStyle;

    if (isOneOf(styleMode, STYLE_OPTIONS)) {
      opts.genStyle = styleMode;
    } else if (isOneOf(style, STYLE_OPTIONS)) {
      opts.genStyle = style;
    } else if (typeof style === 'string' && style.trim()) {
      // 兼容：旧数据可能直接把 style 写成完整描述字符串
      opts.genStyle = 'custom';
      opts.customStyle = style.trim();
    }

    if (typeof customStyle === 'string' && customStyle.trim()) {
      opts.customStyle = customStyle.trim();
    }

    const language = d?.language;
    if (isOneOf(language, LANGUAGE_OPTIONS)) opts.genLanguage = language;

    const minPages = clampInt(d?.minPages, 3, 30, opts.minPages);
    const maxPages = clampInt(d?.maxPages, 3, 30, opts.maxPages);
    opts.minPages = Math.min(minPages, maxPages);
    opts.maxPages = Math.max(minPages, maxPages);

    if (typeof d?.usePortraits === 'boolean') opts.usePortraits = d.usePortraits;
    if (typeof d?.autoGeneratePortraits === 'boolean') opts.autoGeneratePortraits = d.autoGeneratePortraits;
    if (typeof d?.autoGeneratePageImages === 'boolean') opts.autoGeneratePageImages = d.autoGeneratePageImages;

    opts.pagePromptConcurrency = clampInt(d?.pagePromptConcurrency, 1, 20, opts.pagePromptConcurrency);

    const startFromStage = d?.startFromStage;
    if (isOneOf(startFromStage, START_STAGE_OPTIONS)) opts.startFromStage = startFromStage;

    if (typeof d?.forceRestart === 'boolean') opts.forceRestart = d.forceRestart;

    return opts;
  } catch {
    return defaults;
  }
};

const serializePersistedOptions = (options: MangaGenOptions): string => {
  const normalizedCustomStyle = (options.customStyle || '').trim();
  const styleValue = options.genStyle === 'custom' ? (normalizedCustomStyle || 'manga') : options.genStyle;

  return JSON.stringify({
    styleMode: options.genStyle,
    style: styleValue,
    customStyle: normalizedCustomStyle || undefined,
    language: options.genLanguage,
    minPages: options.minPages,
    maxPages: options.maxPages,
    usePortraits: options.usePortraits,
    autoGeneratePortraits: options.autoGeneratePortraits,
    autoGeneratePageImages: options.autoGeneratePageImages,
    pagePromptConcurrency: options.pagePromptConcurrency,
    startFromStage: options.startFromStage,
    forceRestart: options.forceRestart,
  });
};

export const usePersistedMangaGenOptions = (projectId: string | undefined) => {
  const storageKey = useMemo(() => (projectId ? `afn:manga_gen_opts:${projectId}` : null), [projectId]);
  const initialOptions = useMemo(() => createDefaultOptions(), []);

  const [options, setOptions] = usePersistedState<MangaGenOptions>(storageKey, initialOptions, {
    parse: parsePersistedOptions,
    serialize: serializePersistedOptions,
  });

  const setGenStyle = useCallback((genStyle: MangaGenStyle) => setOptions((prev) => ({ ...prev, genStyle })), []);
  const setCustomStyle = useCallback((customStyle: string) => setOptions((prev) => ({ ...prev, customStyle })), []);
  const setGenLanguage = useCallback((genLanguage: MangaGenLanguage) => setOptions((prev) => ({ ...prev, genLanguage })), []);
  const setMinPages = useCallback((minPages: number) => setOptions((prev) => ({ ...prev, minPages })), []);
  const setMaxPages = useCallback((maxPages: number) => setOptions((prev) => ({ ...prev, maxPages })), []);
  const setUsePortraits = useCallback((usePortraits: boolean) => setOptions((prev) => ({ ...prev, usePortraits })), []);
  const setAutoGeneratePortraits = useCallback(
    (autoGeneratePortraits: boolean) => setOptions((prev) => ({ ...prev, autoGeneratePortraits })),
    [],
  );
  const setAutoGeneratePageImages = useCallback(
    (autoGeneratePageImages: boolean) => setOptions((prev) => ({ ...prev, autoGeneratePageImages })),
    [],
  );
  const setPagePromptConcurrency = useCallback(
    (pagePromptConcurrency: number) => setOptions((prev) => ({ ...prev, pagePromptConcurrency })),
    [],
  );
  const setStartFromStage = useCallback(
    (startFromStage: MangaStartFromStage) => setOptions((prev) => ({ ...prev, startFromStage })),
    [],
  );
  const setForceRestart = useCallback((forceRestart: boolean) => setOptions((prev) => ({ ...prev, forceRestart })), []);

  return {
    ...options,
    setGenStyle,
    setCustomStyle,
    setGenLanguage,
    setMinPages,
    setMaxPages,
    setUsePortraits,
    setAutoGeneratePortraits,
    setAutoGeneratePageImages,
    setPagePromptConcurrency,
    setStartFromStage,
    setForceRestart,
  };
};
