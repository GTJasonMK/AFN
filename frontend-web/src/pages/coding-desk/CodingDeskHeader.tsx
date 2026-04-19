import React from 'react';

type CodingDeskHeaderProps = {
  projectTitle: string;
  currentFilePath: string | null;
  isAssistantOpen: boolean;
  onBack: () => void;
  onOpenProjectDetail: () => void;
  onToggleAssistant: () => void;
};

export const CodingDeskHeader: React.FC<CodingDeskHeaderProps> = ({
  projectTitle,
  currentFilePath,
  isAssistantOpen,
  onBack,
  onOpenProjectDetail,
  onToggleAssistant,
}) => {
  return (
    <div className="h-14 shrink-0 z-30 flex items-center gap-3 border-b border-book-border bg-book-bg-paper px-4">
      <button
        onClick={onBack}
        className="rounded px-3 py-1.5 text-sm text-book-primary hover:bg-book-primary/10"
        type="button"
      >
        &lt; 返回
      </button>

      <div className="h-6 w-px bg-book-border" />

      <div className="text-[15px] font-semibold text-book-text-main">
        {projectTitle || '加载中...'}
      </div>

      <div className="h-6 w-px bg-book-border" />

      {currentFilePath ? (
        <div className="text-xs font-mono text-book-text-sub">
          {currentFilePath}
        </div>
      ) : null}

      <div className="flex-1" />

      <button
        onClick={onOpenProjectDetail}
        className="rounded border border-book-border px-3 py-1.5 text-xs text-book-text-sub transition-colors hover:border-book-primary hover:bg-book-primary/10 hover:text-book-primary"
        type="button"
      >
        项目详情
      </button>

      <button
        onClick={onToggleAssistant}
        className={`rounded border px-3 py-1.5 text-xs transition-colors ${
          isAssistantOpen
            ? 'border-book-primary bg-book-primary text-white'
            : 'border-book-primary text-book-primary hover:bg-book-primary/10'
        }`}
        type="button"
      >
        RAG助手
      </button>
    </div>
  );
};
