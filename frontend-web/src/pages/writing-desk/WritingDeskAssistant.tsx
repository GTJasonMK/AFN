import React, { lazy, Suspense } from 'react';

const AssistantPanelLazy = lazy(() =>
  import('../../components/business/AssistantPanel').then((m) => ({ default: m.AssistantPanel }))
);

export const WritingDeskAssistant: React.FC<{
  projectId: string;
  chapterNumber?: number;
  content: string;
  onChangeContent: (content: string) => void;
  onLocateText: (text: string) => void;
  onSelectRange: (start: number, end: number) => void;
  onJumpToChapter: (chapterNumber: number) => void | Promise<void>;
  isOpen: boolean;
  width: number;
  mountReady: boolean;
  onResizeMouseDown: (e: React.MouseEvent) => void;
}> = ({
  projectId,
  chapterNumber,
  content,
  onChangeContent,
  onLocateText,
  onSelectRange,
  onJumpToChapter,
  isOpen,
  width,
  mountReady,
  onResizeMouseDown,
}) => {
  if (!isOpen) return null;

  return (
    <>
      <div
        className="w-1.5 shrink-0 cursor-col-resize bg-transparent hover:bg-book-primary/20 transition-colors"
        onMouseDown={onResizeMouseDown}
        title="拖拽调整助手面板宽度"
      />
      <div className="shrink-0 h-full" style={{ width }}>
        {mountReady ? (
          <Suspense fallback={<div className="h-full p-4 text-xs text-book-text-muted">助手面板加载中…</div>}>
            <AssistantPanelLazy
              projectId={projectId}
              chapterNumber={chapterNumber}
              content={content}
              onChangeContent={onChangeContent}
              onLocateText={onLocateText}
              onSelectRange={onSelectRange}
              onJumpToChapter={onJumpToChapter}
            />
          </Suspense>
        ) : (
          <div className="h-full p-4 text-xs text-book-text-muted">助手面板准备中…</div>
        )}
      </div>
    </>
  );
};

