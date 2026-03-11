import React from 'react';
import {
  ArrowLeft,
  Database,
  Download,
  Eye,
  FolderOpen,
  PanelLeft,
  PanelRight,
  Save,
  ScrollText,
  Sparkles,
  Upload,
} from 'lucide-react';
import { Dropdown } from '../../components/ui/Dropdown';
import { BookButton } from '../../components/ui/BookButton';

type GenProgress = { stage?: string; message?: string; current?: number; total?: number } | null;

export const WritingDeskHeader: React.FC<{
  projectTitle: string;
  projectStyle: string;
  completedChaptersCount: number;
  totalChaptersCount: number;
  contentChars: number;
  currentChapterNumber?: number | null;
  onBack: () => void;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  onOpenImportChapter: () => void;
  onExportTxt: () => void;
  onExportMarkdown: () => void;
  onOpenWritingNotes: () => void;
  onOpenPromptPreview: () => void;
  onOpenProjectDetail: () => void;
  onSave: () => void;
  isSaving: boolean;
  onGenerate: () => void;
  onIngestRag: () => void;
  isRagIngesting: boolean;
  isAssistantOpen: boolean;
  onToggleAssistant: () => void;
  isGenerating: boolean;
  genProgress: GenProgress;
  onStopGenerating: () => void;
}> = ({
  projectTitle,
  projectStyle,
  completedChaptersCount,
  totalChaptersCount,
  contentChars,
  currentChapterNumber,
  onBack,
  isSidebarOpen,
  onToggleSidebar,
  onOpenImportChapter,
  onExportTxt,
  onExportMarkdown,
  onOpenWritingNotes,
  onOpenPromptPreview,
  onOpenProjectDetail,
  onSave,
  isSaving,
  onGenerate,
  onIngestRag,
  isRagIngesting,
  isAssistantOpen,
  onToggleAssistant,
  isGenerating,
  genProgress,
  onStopGenerating,
}) => {
  const progressPercent =
    typeof genProgress?.current === 'number' &&
    typeof genProgress?.total === 'number' &&
    genProgress.total > 0
      ? Math.min(100, Math.max(0, (genProgress.current / genProgress.total) * 100))
      : null;

  return (
    <section className="dramatic-surface rounded-[30px] px-4 py-4 sm:px-5 sm:py-5">
      <div className="relative z-[1] space-y-4">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={onBack}
                className="inline-flex h-11 items-center gap-2 rounded-full border border-book-border/55 bg-book-bg-paper/78 px-4 text-sm font-semibold text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/30 hover:text-book-primary"
                title="返回项目列表"
              >
                <ArrowLeft size={16} />
                返回
              </button>
              <div className="eyebrow">Writing Desk</div>
              <span className="story-pill">{projectStyle || '自由创作'}</span>
              {currentChapterNumber ? <span className="story-pill">当前第 {currentChapterNumber} 章</span> : null}
            </div>

            <div>
              <h1 className="font-serif text-[clamp(2rem,4vw,3.6rem)] font-bold leading-[0.96] tracking-[-0.04em] text-book-text-main">
                {projectTitle || '写作台'}
              </h1>
              <p className="mt-2 text-sm leading-relaxed text-book-text-sub sm:text-base">
                把章节推进、版本切换、RAG 诊断和正文生成收束到一个控制台里，减少在多个面板之间反复跳转。
              </p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 xl:w-[24rem]">
            <div className="metric-tile">
              <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                已完成章节
              </div>
              <div className="mt-3 font-serif text-3xl font-bold text-book-text-main">
                {completedChaptersCount}
              </div>
              <div className="mt-2 text-sm text-book-text-sub">共 {totalChaptersCount} 章</div>
            </div>
            <div className="metric-tile">
              <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                正文长度
              </div>
              <div className="mt-3 font-serif text-3xl font-bold text-book-text-main">
                {contentChars}
              </div>
              <div className="mt-2 text-sm text-book-text-sub">当前编辑区字数</div>
            </div>
            <div className="metric-tile">
              <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                当前阶段
              </div>
              <div className="mt-3 text-lg font-semibold text-book-text-main">
                {isGenerating ? '正在生成' : isSaving ? '正在保存' : '可继续推进'}
              </div>
              <div className="mt-2 text-sm text-book-text-sub">高频动作统一放在顶部</div>
            </div>
          </div>
        </div>

        <div className="story-divider" />

        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <BookButton
              variant={isSidebarOpen ? 'secondary' : 'ghost'}
              size="sm"
              onClick={onToggleSidebar}
            >
              <PanelLeft size={16} />
              {isSidebarOpen ? '隐藏章节栏' : '章节导航'}
            </BookButton>

            <BookButton
              variant={isAssistantOpen ? 'secondary' : 'ghost'}
              size="sm"
              onClick={onToggleAssistant}
            >
              <PanelRight size={16} />
              {isAssistantOpen ? '隐藏助手' : '显示助手'}
            </BookButton>

            <Dropdown
              label="导入导出"
              items={[
                { label: '导入章节', icon: <Upload size={14} />, onClick: onOpenImportChapter },
                { label: '导出 TXT', icon: <Download size={14} />, onClick: onExportTxt },
                { label: '导出 Markdown', icon: <Download size={14} />, onClick: onExportMarkdown },
                { label: '打开项目详情', icon: <FolderOpen size={14} />, onClick: onOpenProjectDetail },
              ]}
            />

            <Dropdown
              label="工作台工具"
              items={[
                { label: '写作指导', icon: <ScrollText size={14} />, onClick: onOpenWritingNotes },
                { label: '提示词预览', icon: <Eye size={14} />, onClick: onOpenPromptPreview },
                {
                  label: isRagIngesting ? 'RAG 处理中…' : 'RAG 入库',
                  icon: <Database size={14} />,
                  onClick: onIngestRag,
                },
              ]}
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <BookButton
              variant="secondary"
              size="md"
              onClick={onSave}
              disabled={isSaving || isGenerating}
            >
              <Save size={16} />
              {isSaving ? '保存中…' : '保存'}
            </BookButton>

            <BookButton
              variant="primary"
              size="md"
              onClick={onGenerate}
              disabled={isGenerating || isSaving}
            >
              <Sparkles size={16} />
              {isGenerating ? '生成中…' : '生成章节'}
            </BookButton>
          </div>
        </div>

        {isGenerating ? (
          <div className="rounded-[24px] border border-book-border/55 bg-book-bg-paper/78 px-4 py-4 shadow-[0_20px_44px_-34px_rgba(36,18,6,0.92)]">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                  Generation Status
                </div>
                <div className="mt-2 text-sm font-semibold text-book-text-main">
                  {genProgress?.message || genProgress?.stage || '生成中…'}
                </div>
              </div>
              <BookButton variant="ghost" size="sm" onClick={onStopGenerating}>
                停止
              </BookButton>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-book-border/30">
              {progressPercent !== null ? (
                <div className="h-full rounded-full bg-book-primary transition-all duration-300" style={{ width: `${progressPercent}%` }} />
              ) : (
                <div className="h-full w-1/3 rounded-full bg-book-primary animate-pulse" />
              )}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
};
