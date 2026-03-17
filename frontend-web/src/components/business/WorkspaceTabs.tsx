/**
 * 写作台主工作区标签页 - 照抄桌面端 writing_desk/workspace/chapter_display.py
 *
 * 标签页：正文、版本、评审、摘要、分析、漫画
 */

import React, { lazy, Suspense, useState, useRef, useImperativeHandle, useEffect } from 'react';
import { BookButton } from '../ui/BookButton';
import { ChapterVersion } from '../../api/writer';
import { Maximize2, Minimize2, FileText, Files, BadgeCheck, ScrollText, BarChart3, Layers } from 'lucide-react';
import type { Chapter } from '../../api/writer';
import { usePersistedTab } from '../../hooks/usePersistedTab';

export type WorkspaceTabId = 'content' | 'versions' | 'review' | 'summary' | 'analysis' | 'manga';

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
  onChange: (value: string) => void;
  onSave: () => void;
  onGenerate: () => void;
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
  onChange,
  onSave,
  onGenerate,
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
  const activeTabMeta = tabs.find((tab) => tab.id === activeTab) ?? tabs[0];

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
        sticky top-0 z-20 border-b border-book-border/45 bg-book-bg-paper/92 px-3 py-3 shadow-sm backdrop-blur-md transition-all duration-300
        ${isFocusMode ? 'opacity-0 hover:opacity-100' : ''}
      `}>
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex min-w-0 flex-col gap-3 xl:flex-row xl:items-center">
            <div className="flex items-center gap-1 rounded-[20px] border border-book-border/50 bg-book-bg p-1 shadow-inner">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                      flex items-center gap-1.5 rounded-[16px] px-3 py-2 text-xs font-medium transition-all duration-300
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

            <div className="min-w-0 xl:max-w-md">
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-book-text-muted">
                {activeTabMeta.label}
              </div>
              <div className="mt-1 text-sm leading-relaxed text-book-text-sub">
                {activeTabMeta.description}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 xl:border-l xl:border-book-border/30 xl:pl-4">
            <div className="hidden text-[11px] font-semibold uppercase tracking-[0.18em] text-book-text-muted lg:block">
              {activeTab === 'content' ? '正文工作区' : '辅助视图'}
            </div>

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

      {/* 版本选择栏（仅在正文标签页显示） */}
      {activeTab === 'content' && versions.length > 0 && (
        <div className="border-b border-book-border/30 bg-book-bg-paper/55 px-4 py-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-book-text-muted">版本切换</span>
            <div className="flex flex-wrap items-center gap-1">
            {versions.map((v, idx) => {
              const isSelected = typeof selectedVersionIndex === 'number'
                ? selectedVersionIndex === idx
                : (selectedVersionIndex === null ? false : content === v.content);
              const key = `version-${v.id ? String(v.id) : 'none'}-${idx}-${v.version_label || 'unknown'}`;
              return (
                <button
                  key={key}
                  onClick={() => onSelectVersion(idx)}
                  disabled={Boolean(isGenerating) || Boolean(isSaving)}
                  className={`
                      rounded-full px-3 py-1 text-xs transition-all
                    ${isSelected
                      ? 'bg-book-primary text-white'
                      : 'border border-book-border/40 text-book-text-muted hover:text-book-text-main hover:bg-book-bg'}
                    ${(isGenerating || isSaving) ? 'opacity-60 cursor-not-allowed' : ''}
                  `}
                >
                  {v.version_label}
                </button>
              );
            })}
            </div>
          </div>
        </div>
      )}

      {/* 内容区域 */}
      <div className="flex-1 overflow-hidden">
        {/* 正文标签页 */}
        {activeTab === 'content' && (
          <div className="h-full overflow-y-auto custom-scrollbar">
            <div className={`mx-auto flex min-h-full w-full flex-col gap-4 p-4 sm:p-5 ${isFocusMode ? 'max-w-5xl' : 'max-w-[1280px]'}`}>
              <section className="rounded-xl border border-book-border/55 bg-book-bg-paper/78 px-5 py-5 shadow-surface">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                      Draft Stage
                    </div>
                    <h3 className="mt-2 font-serif text-2xl font-bold text-book-text-main sm:text-[2rem]">
                      当前章节正文舞台
                    </h3>
                    <p className="mt-2 max-w-2xl text-sm leading-relaxed text-book-text-sub">
                      这里是当前章节的主写作区。保存与生成已经上收至页面头部，这里只保留正文编辑和专注写作能力。
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {chapterNumber ? <span className="story-pill">第 {chapterNumber} 章</span> : null}
                    <span className="story-pill">{isFocusMode ? '专注模式已启用' : '普通编辑模式'}</span>
                  </div>
                </div>
              </section>

              <div className="min-h-[28rem] flex-1 rounded-2xl border border-book-border/55 bg-book-bg-paper p-5 shadow-surface-strong sm:p-7">
                <textarea
                  ref={textareaRef}
                  value={content}
                  onChange={(e) => onChange(e.target.value)}
                  placeholder="开始书写你的故事..."
                  className={`
                    h-full min-h-[22rem] w-full resize-none bg-transparent outline-none
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
            <div className="space-y-4">
              <section className="rounded-xl border border-book-border/55 bg-book-bg-paper/78 px-5 py-5 shadow-surface">
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">Version Archive</div>
                <h3 className="mt-2 font-serif text-2xl font-bold text-book-text-main">版本候选与取舍</h3>
                <p className="mt-2 text-sm leading-relaxed text-book-text-sub">
                  对照当前章节的候选版本，判断保留、切换或回退的路径。
                </p>
              </section>
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
            <div className="space-y-4">
              <section className="rounded-xl border border-book-border/55 bg-book-bg-paper/78 px-5 py-5 shadow-surface">
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">Review Board</div>
                <h3 className="mt-2 font-serif text-2xl font-bold text-book-text-main">评审与问题回看</h3>
                <p className="mt-2 text-sm leading-relaxed text-book-text-sub">
                  把章节问题、修订建议和质量判断集中到一个审阅视角里。
                </p>
              </section>
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
            <div className="space-y-4">
              <section className="rounded-xl border border-book-border/55 bg-book-bg-paper/78 px-5 py-5 shadow-surface">
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">Summary Stage</div>
                <h3 className="mt-2 font-serif text-2xl font-bold text-book-text-main">章节摘要与上下文压缩</h3>
                <p className="mt-2 text-sm leading-relaxed text-book-text-sub">
                  检查摘要是否足够概括章节信息，并作为后续生成的稳定上下文。
                </p>
              </section>
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
            <div className="space-y-4">
              <section className="rounded-xl border border-book-border/55 bg-book-bg-paper/78 px-5 py-5 shadow-surface">
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">Analysis Deck</div>
                <h3 className="mt-2 font-serif text-2xl font-bold text-book-text-main">结构化分析与伏笔追踪</h3>
                <p className="mt-2 text-sm leading-relaxed text-book-text-sub">
                  聚焦角色状态、关键事件和未解悬念，判断章节是否还能继续推进。
                </p>
              </section>
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
            <div className="space-y-4">
              <section className="rounded-xl border border-book-border/55 bg-book-bg-paper/78 px-5 py-5 shadow-surface">
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">Storyboard Deck</div>
                <h3 className="mt-2 font-serif text-2xl font-bold text-book-text-main">漫画化提示与镜头拆解</h3>
                <p className="mt-2 text-sm leading-relaxed text-book-text-sub">
                  从章节正文中提取可视化镜头与场景提示，为漫画化表达提供结构参考。
                </p>
              </section>
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
