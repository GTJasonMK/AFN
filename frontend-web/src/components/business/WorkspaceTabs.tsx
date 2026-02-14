/**
 * 写作台主工作区标签页 - 照抄桌面端 writing_desk/workspace/chapter_display.py
 *
 * 标签页：正文、版本、评审、摘要、分析、漫画
 */

import React, { lazy, Suspense, useState, useRef, useImperativeHandle, useEffect } from 'react';
import { BookButton } from '../ui/BookButton';
import { ChapterVersion } from '../../api/writer';
import { Save, RefreshCw, Maximize2, Minimize2, Database, Eye, FileText, Files, BadgeCheck, ScrollText, BarChart3, Layers } from 'lucide-react';
import type { Chapter } from '../../api/writer';

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
  isIngestingRag?: boolean;
  onChange: (value: string) => void;
  onSave: () => void;
  onGenerate: () => void;
  onPreviewPrompt?: () => void;
  onIngestRag?: () => void;
  onSelectVersion: (index: number) => void;
}

const WORKSPACE_TAB_STORAGE_KEY = (projectId: string) => `afn:workspace_tab:${projectId}`;

// 照抄桌面端的标签页定义
const tabs: { id: WorkspaceTabId; label: string; icon: React.ElementType }[] = [
  { id: 'content', label: '正文', icon: FileText },
  { id: 'versions', label: '版本', icon: Files },
  { id: 'review', label: '评审', icon: BadgeCheck },
  { id: 'summary', label: '摘要', icon: ScrollText },
  { id: 'analysis', label: '分析', icon: BarChart3 },
  { id: 'manga', label: '漫画', icon: Layers },
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
  isIngestingRag,
  onChange,
  onSave,
  onGenerate,
  onPreviewPrompt,
  onIngestRag,
  onSelectVersion,
}, ref) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isFocusMode, setIsFocusMode] = useState(false);

  // 当前标签页
  const [activeTab, setActiveTab] = useState<WorkspaceTabId>(() => {
    try {
      const raw = localStorage.getItem(WORKSPACE_TAB_STORAGE_KEY(projectId));
      if (raw && tabs.some(t => t.id === raw)) return raw as WorkspaceTabId;
    } catch {
      // ignore
    }
    return 'content';
  });

  // 持久化标签页选择
  useEffect(() => {
    try {
      localStorage.setItem(WORKSPACE_TAB_STORAGE_KEY(projectId), activeTab);
    } catch {
      // ignore
    }
  }, [activeTab, projectId]);

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
  }), []);

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
    <div className={`flex-1 flex flex-col h-full bg-book-bg relative transition-all duration-500 ease-in-out ${isFocusMode ? 'z-50 fixed inset-0' : ''}`}>
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
        h-12 border-b border-book-border/40 flex items-center px-4 gap-1
        bg-book-bg-paper/90 backdrop-blur-md sticky top-0 z-20 shadow-sm transition-all duration-300
        ${isFocusMode ? 'opacity-0 hover:opacity-100' : ''}
      `}>
        {/* 左侧：标签页按钮 */}
        <div className="flex items-center gap-1 bg-book-bg p-1 rounded-lg border border-book-border/50 shadow-inner">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-300 flex items-center gap-1.5
                  ${isActive
                    ? 'bg-book-bg-paper text-book-primary shadow-sm border border-book-border/50'
                    : 'text-book-text-muted hover:text-book-text-main hover:bg-book-bg-paper/50'}
                `}
              >
                <Icon size={14} />
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="flex-1" />

        {/* 右侧：操作按钮（对齐桌面端：预览提示词/生成章节在任何 Tab 都可见） */}
        <div className="flex items-center gap-3 pl-4 border-l border-book-border/30">
          {/* 专注模式：仅正文 Tab 可用 */}
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

          {/* RAG 入库：仅正文 Tab（并依赖调用方提供） */}
          {activeTab === 'content' && onIngestRag ? (
            <BookButton
              variant="ghost"
              size="sm"
              onClick={onIngestRag}
              disabled={isSaving || isGenerating || isIngestingRag}
              title="保存并处理RAG（摘要、分析、向量入库）"
            >
              <Database size={16} className={isIngestingRag ? 'animate-pulse' : ''} />
            </BookButton>
          ) : null}

          {/* 预览提示词：桌面端在顶部 header 常驻 */}
          {onPreviewPrompt ? (
            <BookButton
              variant="ghost"
              size="sm"
              onClick={onPreviewPrompt}
              disabled={isSaving || isGenerating}
              title="预览提示词（用于测试RAG检索效果）"
            >
              <Eye size={16} />
              <span className="ml-1.5">预览提示词</span>
            </BookButton>
          ) : null}

          {/* 保存：仅正文 Tab */}
          {activeTab === 'content' ? (
            <BookButton
              variant="ghost"
              size="sm"
              onClick={onSave}
              disabled={isSaving || isGenerating}
              title="保存 (Ctrl+S)"
            >
              <Save size={16} className={isSaving ? 'animate-spin' : ''} />
            </BookButton>
          ) : null}

          {/* 生成章节：桌面端在顶部 header 常驻 */}
          <BookButton
            variant="primary"
            size="sm"
            onClick={onGenerate}
            disabled={isGenerating || isSaving}
            title="生成章节 (Ctrl+Enter)"
          >
            <RefreshCw size={16} className={isGenerating ? 'animate-spin' : ''} />
            <span className="ml-1.5">{isGenerating ? '生成中...' : '生成章节'}</span>
          </BookButton>
        </div>
      </div>

      {/* 版本选择栏（仅在正文标签页显示） */}
      {activeTab === 'content' && versions.length > 0 && (
        <div className="h-10 border-b border-book-border/30 flex items-center px-4 bg-book-bg-paper/50">
          <span className="text-xs text-book-text-muted mr-3">版本:</span>
          <div className="flex items-center gap-1">
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
                    px-2 py-0.5 text-xs rounded transition-all
                    ${isSelected
                      ? 'bg-book-primary text-white'
                      : 'text-book-text-muted hover:text-book-text-main hover:bg-book-bg'}
                    ${(isGenerating || isSaving) ? 'opacity-60 cursor-not-allowed' : ''}
                  `}
                >
                  {v.version_label}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* 内容区域 */}
      <div className="flex-1 overflow-hidden">
        {/* 正文标签页 */}
        {activeTab === 'content' && (
          <div className="h-full overflow-hidden">
            <div className={`h-full p-8 transition-all duration-500 ${isFocusMode ? 'max-w-3xl mx-auto' : ''}`}>
              <textarea
                ref={textareaRef}
                value={content}
                onChange={(e) => onChange(e.target.value)}
                placeholder="开始书写你的故事..."
                className={`
                  w-full h-full min-h-0 bg-transparent resize-none outline-none
                  font-serif text-lg leading-relaxed text-book-text-main
                  placeholder:text-book-text-muted placeholder:italic
                  transition-all duration-300
                  overflow-y-auto custom-scrollbar
                `}
              />
            </div>
          </div>
        )}

        {/* 版本标签页 */}
        {activeTab === 'versions' && chapterNumber && (
          <div className="h-full overflow-y-auto custom-scrollbar p-4">
            <Suspense fallback={<div className="text-xs text-book-text-muted">加载中…</div>}>
              <ChapterVersionsViewLazy
                projectId={projectId}
                chapterNumber={chapterNumber}
                onSelectVersion={onSelectVersion}
              />
            </Suspense>
          </div>
        )}

        {/* 评审标签页 */}
        {activeTab === 'review' && chapterNumber && (
          <div className="h-full overflow-y-auto custom-scrollbar p-4">
            <Suspense fallback={<div className="text-xs text-book-text-muted">加载中…</div>}>
              <ChapterReviewViewLazy
                projectId={projectId}
                chapterNumber={chapterNumber}
              />
            </Suspense>
          </div>
        )}

        {/* 摘要标签页 */}
        {activeTab === 'summary' && chapterNumber && (
          <div className="h-full overflow-y-auto custom-scrollbar p-4">
            <Suspense fallback={<div className="text-xs text-book-text-muted">加载中…</div>}>
              <ChapterSummaryViewLazy
                projectId={projectId}
                chapterNumber={chapterNumber}
              />
            </Suspense>
          </div>
        )}

        {/* 分析标签页 */}
        {activeTab === 'analysis' && chapterNumber && (
          <div className="h-full overflow-y-auto custom-scrollbar p-4">
            <Suspense fallback={<div className="text-xs text-book-text-muted">加载中…</div>}>
              <ChapterAnalysisViewLazy
                projectId={projectId}
                chapterNumber={chapterNumber}
              />
            </Suspense>
          </div>
        )}

        {/* 漫画标签页 */}
        {activeTab === 'manga' && chapterNumber && (
          <div className="h-full overflow-y-auto custom-scrollbar p-4">
            <Suspense fallback={<div className="text-xs text-book-text-muted">加载中…</div>}>
              <MangaPromptViewerLazy
                projectId={projectId}
                chapterNumber={chapterNumber}
              />
            </Suspense>
          </div>
        )}

        {/* 未选择章节时的提示 */}
        {activeTab !== 'content' && !chapterNumber && (
          <div className="h-full flex items-center justify-center text-book-text-muted">
            <p>请先选择一个章节</p>
          </div>
        )}
      </div>
    </div>
  );
});

WorkspaceTabs.displayName = 'WorkspaceTabs';
