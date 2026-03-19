/**
 * 写作台主工作区标签页 - 照抄桌面端 writing_desk/workspace/chapter_display.py
 *
 * 标签页：正文、版本、评审、摘要、分析、漫画
 */

import React, { lazy, Suspense, useState, useRef, useImperativeHandle, useEffect } from 'react';
import { BookButton } from '../ui/BookButton';
import { Dropdown } from '../ui/Dropdown';
import { ChapterVersion } from '../../api/writer';
import { Maximize2, Minimize2, FileText, Files, BadgeCheck, ScrollText, BarChart3, Layers, Save, Sparkles, Square, Loader2, Type, Check } from 'lucide-react';
import type { Chapter } from '../../api/writer';
import { usePersistedTab } from '../../hooks/usePersistedTab';

export type WorkspaceTabId = 'content' | 'versions' | 'review' | 'summary' | 'analysis' | 'manga';
type GenProgress = { stage?: string; message?: string; current?: number; total?: number } | null;

export type WorkspaceHandle = {
  focus: () => void;
  focusAndSelect: (start: number, end: number) => void;
};

interface WorkspaceTabsProps {
  projectId: string;
  chapter?: Chapter | null;
  content: string;
  versions?: ChapterVersion[];
  selectedVersionIndex?: number | null;
  isSaving?: boolean;
  isGenerating?: boolean;
  genProgress?: GenProgress;
  canGenerate?: boolean;
  generateDisabledReason?: string | null;
  onChange: (value: string) => void;
  onSave: () => void;
  onGenerate: () => void;
  onStopGenerating: () => void;
  onSelectVersion: (index: number) => void;
}

const WORKSPACE_TAB_STORAGE_KEY = (projectId: string) => `afn:workspace_tab:${projectId}`;
const WORKSPACE_ALLOWED_TABS: readonly WorkspaceTabId[] = ['content', 'versions', 'review', 'summary', 'analysis', 'manga'];

// 照抄桌面端的标签页定义
const tabs: { id: WorkspaceTabId; label: string; description: string; icon: React.ElementType }[] = [
  { id: 'content', label: '正文', description: '当前章节的主写作舞台与专注模式。', icon: FileText },
  { id: 'versions', label: '版本', description: '查看当前章节的版本候选与切换历史。', icon: Files },
  { id: 'review', label: '评审', description: '聚焦问题反馈、修订建议与质量回看。', icon: BadgeCheck },
  { id: 'summary', label: '摘要', description: '章节摘要与 RAG 收束信息，用于上下文续写。', icon: ScrollText },
  { id: 'analysis', label: '分析', description: '结构化分析角色、关键事件与伏笔状态。', icon: BarChart3 },
  { id: 'manga', label: '漫画', description: '提取当前章节的漫画化镜头与分镜提示。', icon: Layers },
];

const loadChapterVersionsView = () =>
  import('./ChapterVersionsView').then((m) => ({ default: m.ChapterVersionsView }));
const loadChapterReviewView = () =>
  import('./ChapterReviewView').then((m) => ({ default: m.ChapterReviewView }));
const loadChapterSummaryView = () =>
  import('./ChapterSummaryView').then((m) => ({ default: m.ChapterSummaryView }));
const loadChapterAnalysisView = () =>
  import('./ChapterAnalysisView').then((m) => ({ default: m.ChapterAnalysisView }));
const loadMangaPromptViewer = () =>
  import('./MangaPromptViewer').then((m) => ({ default: m.MangaPromptViewer }));

const ChapterVersionsViewLazy = lazy(loadChapterVersionsView);
const ChapterReviewViewLazy = lazy(loadChapterReviewView);
const ChapterSummaryViewLazy = lazy(loadChapterSummaryView);
const ChapterAnalysisViewLazy = lazy(loadChapterAnalysisView);
const MangaPromptViewerLazy = lazy(loadMangaPromptViewer);

export const WorkspaceTabs = React.forwardRef<WorkspaceHandle, WorkspaceTabsProps>(({
  projectId,
  chapter,
  content,
  versions = [],
  selectedVersionIndex,
  isSaving,
  isGenerating,
  genProgress,
  canGenerate = true,
  generateDisabledReason,
  onChange,
  onSave,
  onGenerate,
  onStopGenerating,
  onSelectVersion,
}, ref) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isFocusMode, setIsFocusMode] = useState(false);

  // 当前标签页
  const [activeTab, setActiveTab] = usePersistedTab(
    WORKSPACE_TAB_STORAGE_KEY(projectId),
    'content',
    WORKSPACE_ALLOWED_TABS,
  );

  useImperativeHandle(ref, () => ({
    focus: () => {
      textareaRef.current?.focus();
    },
    focusAndSelect: (start: number, end: number) => {
      const el = textareaRef.current;
      if (!el) return;
      setActiveTab('content'); // 切换到正文标签页
      const valueLen = (el.value || '').length;
      const safeStart = Math.max(0, Math.min(valueLen, Math.floor(start)));
      const safeEnd = Math.max(safeStart, Math.min(valueLen, Math.floor(end)));
      el.focus();
      try {
        el.setSelectionRange(safeStart, safeEnd);
      } catch {
        // ignore
      }
    },
  }), [setActiveTab]);

  // 键盘快捷键
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFocusMode) {
        e.preventDefault();
        setIsFocusMode(false);
        return;
      }

      const isMac = navigator.platform.toUpperCase().includes('MAC');
      const modKey = isMac ? e.metaKey : e.ctrlKey;

      if (modKey && e.key.toLowerCase() === 's') {
        e.preventDefault();
        if (!isSaving) onSave();
        return;
      }

      if (modKey && e.key === 'Enter') {
        e.preventDefault();
        if (!isGenerating) onGenerate();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isFocusMode, isGenerating, isSaving, onGenerate, onSave]);

  const chapterNumber = chapter?.chapter_number;
  const contentChars = React.useMemo(() => (content || '').replace(/\s/g, '').length, [content]);
  const progressPercent =
    typeof genProgress?.current === 'number' &&
    typeof genProgress?.total === 'number' &&
    genProgress.total > 0
      ? Math.min(100, Math.max(0, (genProgress.current / genProgress.total) * 100))
      : null;
  const progressLabel = String(genProgress?.message || genProgress?.stage || '生成中…').trim();
  const canGenerateNow = Boolean(canGenerate);
  const generateHint = !canGenerateNow
    ? (String(generateDisabledReason || '').trim() || '当前不满足生成条件，请先完成上一步。')
    : '生成当前章节（Ctrl/Cmd + Enter）';

  const resolvedSelectedVersionIndex = React.useMemo(() => {
    if (typeof selectedVersionIndex === 'number') return selectedVersionIndex;
    if (selectedVersionIndex === null) return null;
    const idx = versions.findIndex((item) => item.content === content);
    return idx >= 0 ? idx : null;
  }, [content, selectedVersionIndex, versions]);

  const selectedVersionLabel = React.useMemo(() => {
    if (resolvedSelectedVersionIndex !== null && versions[resolvedSelectedVersionIndex]) {
      return versions[resolvedSelectedVersionIndex].version_label || `版本 ${resolvedSelectedVersionIndex + 1}`;
    }
    return '草稿';
  }, [resolvedSelectedVersionIndex, versions]);

  const versionDropdownItems = React.useMemo(() => {
    return versions.map((item, idx) => ({
      label: String(item.version_label || `版本 ${idx + 1}`),
      onClick: () => {
        if (isGenerating || isSaving) return;
        onSelectVersion(idx);
      },
      icon: idx === resolvedSelectedVersionIndex ? <Check size={14} /> : <Files size={14} />,
    }));
  }, [isGenerating, isSaving, onSelectVersion, resolvedSelectedVersionIndex, versions]);

  return (
    <div className={`relative flex h-full flex-1 flex-col bg-book-bg transition-all duration-500 ease-in-out ${isFocusMode ? 'fixed inset-0 z-50' : ''}`}>
      {isFocusMode ? (
        <div className="fixed top-4 right-4 z-[60] flex items-center gap-2">
          <BookButton
            variant="secondary"
            size="sm"
            onClick={() => setIsFocusMode(false)}
            title="退出专注 (Esc)"
          >
            <Minimize2 size={16} className="mr-1" />
            退出专注
          </BookButton>
        </div>
      ) : null}
      {/* 标签页切换栏 - 照抄桌面端 */}
      <div className={`
        sticky top-0 z-20 border-b border-book-border/45 bg-book-bg-paper/92 px-3 py-2 shadow-sm backdrop-blur-md transition-all duration-300 relative
        ${isFocusMode ? 'opacity-0 hover:opacity-100' : ''}
      `}>
        {isGenerating ? (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-0.5 bg-book-border/25">
            {progressPercent !== null ? (
              <div className="h-full bg-book-primary transition-all duration-300" style={{ width: `${progressPercent}%` }} />
            ) : (
              <div className="h-full w-1/3 bg-book-primary animate-pulse" />
            )}
          </div>
        ) : null}

        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <div className="flex items-center gap-1 rounded-[18px] border border-book-border/50 bg-book-bg p-1 shadow-inner">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                title={`${tab.label}：${tab.description}`}
                className={`
                      flex items-center gap-1.5 rounded-[14px] px-2.5 py-1.5 text-xs font-medium transition-all duration-300
                  ${isActive
                    ? 'border border-book-border/50 bg-book-bg-paper text-book-primary shadow-sm'
                    : 'text-book-text-muted hover:text-book-text-main hover:bg-book-bg-paper/50'}
                `}
              >
                <Icon size={14} />
                {tab.label}
              </button>
            );
          })}
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2">
            {activeTab === 'content' && versions.length > 0 ? (
              <Dropdown
                label={`版本：${selectedVersionLabel}`}
                items={versionDropdownItems}
              />
            ) : null}

            {chapterNumber ? (
              <span className="story-pill-compact hidden sm:inline-flex">
                第 {chapterNumber} 章
              </span>
            ) : null}

            <span className="story-pill-compact hidden lg:inline-flex" title="当前编辑区字数（去空白）">
              <Type size={14} />
              {contentChars}
            </span>

            {isGenerating ? (
              <span
                className="hidden xl:inline-flex items-center gap-2 text-xs text-book-text-muted"
                title={progressLabel}
              >
                <Loader2 size={14} className="animate-spin text-book-primary" />
                <span className="max-w-[18rem] truncate">{progressLabel}</span>
                {progressPercent !== null ? (
                  <span className="font-mono">{Math.round(progressPercent)}%</span>
                ) : null}
              </span>
            ) : null}

            <BookButton
              variant="secondary"
              size="sm"
              onClick={onSave}
              disabled={Boolean(isSaving) || Boolean(isGenerating)}
              title="保存当前章节（Ctrl/Cmd + S）"
            >
              {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              {isSaving ? '保存中…' : '保存'}
            </BookButton>

            {isGenerating ? (
              <BookButton variant="danger" size="sm" onClick={onStopGenerating} title={progressLabel || '停止生成'}>
                <Square size={16} />
                停止
              </BookButton>
            ) : (
              <BookButton
                variant="primary"
                size="sm"
                onClick={onGenerate}
                disabled={Boolean(isSaving) || !canGenerateNow}
                title={generateHint}
              >
                <Sparkles size={16} />
                生成
              </BookButton>
            )}

            {activeTab === 'content' ? (
              <BookButton
                variant="ghost"
                size="sm"
                onClick={() => setIsFocusMode(!isFocusMode)}
                title={isFocusMode ? "退出专注 (Esc)" : "专注模式"}
              >
                {isFocusMode ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
              </BookButton>
            ) : null}
          </div>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-hidden">
        {/* 正文标签页 */}
        {activeTab === 'content' && (
          <div className="h-full overflow-hidden">
            <div className={`mx-auto flex h-full w-full flex-col p-4 sm:p-5 ${isFocusMode ? 'max-w-5xl' : 'max-w-[1280px]'}`}>
              <div className="flex-1 min-h-0 rounded-2xl border border-book-border/55 bg-book-bg-paper p-4 shadow-surface-strong sm:p-6">
                <textarea
                  ref={textareaRef}
                  value={content}
                  onChange={(e) => onChange(e.target.value)}
                  placeholder="开始书写你的故事..."
                  className={`
                    h-full w-full resize-none bg-transparent outline-none
                    font-serif text-[1.03rem] leading-8 text-book-text-main
                    placeholder:text-book-text-muted placeholder:italic
                    transition-all duration-300
                    overflow-y-auto custom-scrollbar
                  `}
                />
              </div>
            </div>
          </div>
        )}

        {/* 版本标签页 */}
        {activeTab === 'versions' && chapterNumber && (
          <div className="h-full overflow-y-auto custom-scrollbar p-4 sm:p-5">
            <div className="mx-auto w-full max-w-[1280px]">
              <Suspense fallback={<div className="text-xs text-book-text-muted">加载中…</div>}>
                <ChapterVersionsViewLazy
                  projectId={projectId}
                  chapterNumber={chapterNumber}
                  onSelectVersion={onSelectVersion}
                />
              </Suspense>
            </div>
          </div>
        )}

        {/* 评审标签页 */}
        {activeTab === 'review' && chapterNumber && (
          <div className="h-full overflow-y-auto custom-scrollbar p-4 sm:p-5">
            <div className="mx-auto w-full max-w-[1280px]">
              <Suspense fallback={<div className="text-xs text-book-text-muted">加载中…</div>}>
                <ChapterReviewViewLazy
                  projectId={projectId}
                  chapterNumber={chapterNumber}
                />
              </Suspense>
            </div>
          </div>
        )}

        {/* 摘要标签页 */}
        {activeTab === 'summary' && chapterNumber && (
          <div className="h-full overflow-y-auto custom-scrollbar p-4 sm:p-5">
            <div className="mx-auto w-full max-w-[1280px]">
              <Suspense fallback={<div className="text-xs text-book-text-muted">加载中…</div>}>
                <ChapterSummaryViewLazy
                  projectId={projectId}
                  chapterNumber={chapterNumber}
                />
              </Suspense>
            </div>
          </div>
        )}

        {/* 分析标签页 */}
        {activeTab === 'analysis' && chapterNumber && (
          <div className="h-full overflow-y-auto custom-scrollbar p-4 sm:p-5">
            <div className="mx-auto w-full max-w-[1280px]">
              <Suspense fallback={<div className="text-xs text-book-text-muted">加载中…</div>}>
                <ChapterAnalysisViewLazy
                  projectId={projectId}
                  chapterNumber={chapterNumber}
                />
              </Suspense>
            </div>
          </div>
        )}

        {/* 漫画标签页 */}
        {activeTab === 'manga' && chapterNumber && (
          <div className="h-full overflow-y-auto custom-scrollbar p-4 sm:p-5">
            <div className="mx-auto w-full max-w-[1280px]">
              <Suspense fallback={<div className="text-xs text-book-text-muted">加载中…</div>}>
                <MangaPromptViewerLazy
                  projectId={projectId}
                  chapterNumber={chapterNumber}
                />
              </Suspense>
            </div>
          </div>
        )}

        {/* 未选择章节时的提示 */}
        {activeTab !== 'content' && !chapterNumber && (
          <div className="flex h-full items-center justify-center p-6 text-book-text-muted">
            <div className="rounded-xl border border-book-border/50 bg-book-bg-paper/78 px-6 py-5 text-center shadow-surface">
              <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">No Chapter</div>
              <p className="mt-3 text-sm leading-relaxed text-book-text-sub">请先选择一个章节，再打开辅助视图。</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

WorkspaceTabs.displayName = 'WorkspaceTabs';
