import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { Dropdown } from '../../components/ui/Dropdown';
import { BookButton } from '../../components/ui/BookButton';

type GenProgress = { stage?: string; message?: string; current?: number; total?: number } | null;

export const WritingDeskHeader: React.FC<{
  projectTitle: string;
  projectStyle: string;
  completedChaptersCount: number;
  totalChaptersCount: number;
  contentChars: number;
  onBack: () => void;
  onOpenImportChapter: () => void;
  onExportTxt: () => void;
  onExportMarkdown: () => void;
  onOpenWritingNotes: () => void;
  onOpenPromptPreview: () => void;
  onOpenProjectDetail: () => void;
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
  onBack,
  onOpenImportChapter,
  onExportTxt,
  onExportMarkdown,
  onOpenWritingNotes,
  onOpenPromptPreview,
  onOpenProjectDetail,
  isAssistantOpen,
  onToggleAssistant,
  isGenerating,
  genProgress,
  onStopGenerating,
}) => {
  return (
    <div className="h-14 border-b border-book-border bg-book-bg-paper flex items-center px-4 justify-between shrink-0 z-30 shadow-sm">
      {/* 左侧：返回按钮 */}
      <button
        onClick={onBack}
        className="flex items-center justify-center w-9 h-9 rounded-full bg-book-primary text-white hover:opacity-90 transition-opacity"
        title="返回项目列表"
      >
        <ArrowLeft size={18} />
      </button>

      {/* 中间：项目信息 */}
      <div className="flex-1 min-w-0 mx-4 px-4 py-2 bg-book-bg rounded-lg border border-book-border/50">
        <div className="font-serif font-bold text-book-text-main text-sm truncate">
          {projectTitle || '写作台'}
        </div>
        <div className="text-[11px] text-book-text-muted truncate">
          {projectStyle || '自由创作'}
          {' · '}
          {completedChaptersCount}/{totalChaptersCount}章
          {contentChars > 0 && ` · ${contentChars}字`}
        </div>
      </div>

      {/* 右侧：操作按钮 */}
      <div className="flex items-center gap-2">
        <Dropdown
          label="导入/导出"
          items={[
            { label: '导入章节', onClick: onOpenImportChapter },
            { label: '导出为 TXT', onClick: onExportTxt },
            { label: '导出为 Markdown', onClick: onExportMarkdown },
          ]}
        />

        <Dropdown
          label="工具"
          items={[
            { label: '写作指导', onClick: onOpenWritingNotes },
            { label: '提示词预览', onClick: onOpenPromptPreview },
          ]}
        />

        <BookButton variant="primary" size="sm" onClick={onOpenProjectDetail} title="打开项目详情">
          项目详情
        </BookButton>

        <BookButton
          variant={isAssistantOpen ? 'primary' : 'ghost'}
          size="sm"
          onClick={onToggleAssistant}
          title={isAssistantOpen ? '隐藏助手面板' : '显示助手面板'}
        >
          {isAssistantOpen ? '隐藏助手' : '显示助手'}
        </BookButton>
      </div>

      {/* 生成进度（仅在生成时显示） */}
      {isGenerating && (
        <div className="flex items-center gap-3 ml-4">
          <div className="min-w-0 text-right">
            <div className="text-[11px] text-book-text-muted truncate">
              {genProgress?.message || genProgress?.stage || '生成中...'}
            </div>
            {typeof genProgress?.current === 'number' && typeof genProgress?.total === 'number' && genProgress.total > 0 ? (
              <div className="mt-1 h-1.5 w-32 bg-book-border/30 rounded-full overflow-hidden">
                <div
                  className="h-full bg-book-primary transition-all duration-300"
                  style={{ width: `${Math.min(100, Math.max(0, (genProgress.current / genProgress.total) * 100))}%` }}
                />
              </div>
            ) : (
              <div className="mt-1 h-1.5 w-32 bg-book-border/30 rounded-full overflow-hidden">
                <div className="h-full w-1/3 bg-book-primary animate-pulse" />
              </div>
            )}
          </div>
          <button
            onClick={onStopGenerating}
            className="text-xs text-book-accent hover:text-book-accent/80 transition-colors font-bold"
            title="停止生成"
          >
            停止
          </button>
        </div>
      )}
    </div>
  );
};

