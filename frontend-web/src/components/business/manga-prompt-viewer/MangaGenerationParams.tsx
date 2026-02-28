import React from 'react';
import type { MangaGenLanguage, MangaGenStyle, MangaStartFromStage } from '../../../hooks/usePersistedMangaGenOptions';

type MangaGenerationParamsProps = {
  genStyle: MangaGenStyle;
  setGenStyle: (value: MangaGenStyle) => void;
  customStyle: string;
  setCustomStyle: (value: string) => void;
  genLanguage: MangaGenLanguage;
  setGenLanguage: (value: MangaGenLanguage) => void;
  minPages: number;
  setMinPages: (value: number) => void;
  maxPages: number;
  setMaxPages: (value: number) => void;
  startFromStage: MangaStartFromStage;
  setStartFromStage: (value: MangaStartFromStage) => void;
  pagePromptConcurrency: number;
  setPagePromptConcurrency: (value: number) => void;
  usePortraits: boolean;
  setUsePortraits: (value: boolean) => void;
  autoGeneratePortraits: boolean;
  setAutoGeneratePortraits: (value: boolean) => void;
  autoGeneratePageImages: boolean;
  setAutoGeneratePageImages: (value: boolean) => void;
  forceRestart: boolean;
  setForceRestart: (value: boolean) => void;
  disabled?: boolean;
};

export const MangaGenerationParams: React.FC<MangaGenerationParamsProps> = ({
  genStyle,
  setGenStyle,
  customStyle,
  setCustomStyle,
  genLanguage,
  setGenLanguage,
  minPages,
  setMinPages,
  maxPages,
  setMaxPages,
  startFromStage,
  setStartFromStage,
  pagePromptConcurrency,
  setPagePromptConcurrency,
  usePortraits,
  setUsePortraits,
  autoGeneratePortraits,
  setAutoGeneratePortraits,
  autoGeneratePageImages,
  setAutoGeneratePageImages,
  forceRestart,
  setForceRestart,
  disabled,
}) => {
  return (
    <details className="group rounded-lg border border-book-border/40 bg-book-bg-paper">
      <summary className="cursor-pointer select-none px-4 py-3 font-bold text-book-text-main">
        生成参数
        <span className="ml-2 text-[11px] font-normal text-book-text-muted">
          {(genStyle === 'custom' ? 'custom' : genStyle)} · {genLanguage} · {minPages}-{maxPages}页{forceRestart ? ' · 强制重来' : ''}
        </span>
      </summary>
      <div className="px-4 pb-4 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs font-bold text-book-text-sub">
            风格
            <select
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
              value={genStyle}
              onChange={(e) => setGenStyle(e.target.value as MangaGenStyle)}
              disabled={disabled}
            >
              <option value="manga">manga（日漫）</option>
              <option value="anime">anime（动画）</option>
              <option value="comic">comic（美漫）</option>
              <option value="webtoon">webtoon（条漫）</option>
              <option value="custom">custom（自定义）</option>
            </select>
          </label>

          <label className="text-xs font-bold text-book-text-sub">
            语言
            <select
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
              value={genLanguage}
              onChange={(e) => setGenLanguage(e.target.value as MangaGenLanguage)}
              disabled={disabled}
            >
              <option value="chinese">中文</option>
              <option value="japanese">日文</option>
              <option value="english">英文</option>
              <option value="korean">韩文</option>
            </select>
          </label>
        </div>

        {genStyle === 'custom' && (
          <label className="text-xs font-bold text-book-text-sub">
            自定义风格描述
            <input
              type="text"
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
              value={customStyle}
              onChange={(e) => setCustomStyle(e.target.value)}
              disabled={disabled}
              placeholder="例如：漫画风格, 黑白漫画, 网点纸, 日式漫画, 精细线条, 高对比度"
            />
          </label>
        )}

        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs font-bold text-book-text-sub">
            最少页数
            <input
              type="number"
              min={3}
              max={30}
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
              value={minPages}
              onChange={(e) => {
                const v = Math.max(3, Math.min(30, Number(e.target.value) || 3));
                setMinPages(v);
                if (v > maxPages) setMaxPages(v);
              }}
              disabled={disabled}
            />
          </label>
          <label className="text-xs font-bold text-book-text-sub">
            最多页数
            <input
              type="number"
              min={3}
              max={30}
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
              value={maxPages}
              onChange={(e) => {
                const v = Math.max(3, Math.min(30, Number(e.target.value) || 3));
                setMaxPages(v);
                if (v < minPages) setMinPages(v);
              }}
              disabled={disabled}
            />
          </label>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs font-bold text-book-text-sub">
            从阶段开始
            <select
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
              value={startFromStage}
              onChange={(e) => setStartFromStage(e.target.value as MangaStartFromStage)}
              disabled={disabled}
            >
              <option value="auto">自动（断点续传/从头）</option>
              <option value="extraction">extraction（信息提取）</option>
              <option value="planning">planning（页面规划）</option>
              <option value="storyboard">storyboard（分镜设计）</option>
              <option value="prompt_building">prompt_building（画格提示词）</option>
              <option value="page_prompt_building">page_prompt_building（整页提示词）</option>
            </select>
          </label>

          <label className="text-xs font-bold text-book-text-sub">
            整页提示词并发数
            <input
              type="number"
              min={1}
              max={20}
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
              value={pagePromptConcurrency}
              onChange={(e) => {
                const v = Math.max(1, Math.min(20, Math.floor(Number(e.target.value) || 1)));
                setPagePromptConcurrency(v);
              }}
              disabled={disabled}
            />
          </label>
        </div>

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm text-book-text-main">
            <input
              type="checkbox"
              className="rounded border-book-border text-book-primary focus:ring-book-primary"
              checked={usePortraits}
              onChange={(e) => setUsePortraits(e.target.checked)}
              disabled={disabled}
            />
            <span className="font-bold">使用角色立绘作为参考图</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-book-text-main">
            <input
              type="checkbox"
              className="rounded border-book-border text-book-primary focus:ring-book-primary"
              checked={autoGeneratePortraits}
              onChange={(e) => setAutoGeneratePortraits(e.target.checked)}
              disabled={disabled}
            />
            <span className="font-bold">缺失立绘自动生成</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-book-text-main">
            <input
              type="checkbox"
              className="rounded border-book-border text-book-primary focus:ring-book-primary"
              checked={autoGeneratePageImages}
              onChange={(e) => setAutoGeneratePageImages(e.target.checked)}
              disabled={disabled}
            />
            <span className="font-bold">分镜完成后自动生成整页图片（耗时）</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-book-text-main">
            <input
              type="checkbox"
              className="rounded border-book-border text-book-primary focus:ring-book-primary"
              checked={forceRestart}
              onChange={(e) => setForceRestart(e.target.checked)}
              disabled={disabled}
            />
            <span className="font-bold">强制从头开始（忽略断点）</span>
          </label>
        </div>

        <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 leading-relaxed">
          提示：页数越多生成越慢；“自动生成整页图片”会显著增加耗时；“强制从头开始”会忽略断点与已有结果（适合你想完全重做分镜的场景）。
        </div>
      </div>
    </details>
  );
};

