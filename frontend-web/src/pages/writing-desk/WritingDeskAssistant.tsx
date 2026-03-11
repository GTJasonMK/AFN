import React, { lazy, Suspense } from 'react';
import { X } from 'lucide-react';

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
  compact?: boolean;
  onClose?: () => void;
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
  compact = false,
  onClose,
  mountReady,
  onResizeMouseDown,
}) => {
  if (!isOpen) return null;

  if (compact) {
    return (
      <>
        <button
          type="button"
          aria-label="关闭助手遮罩"
          className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm xl:hidden"
          onClick={onClose}
        />

        <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[min(100vw,30rem)] xl:hidden">
          <div className="flex h-full flex-col border-l border-book-border/50 bg-book-bg-paper shadow-[0_30px_90px_-40px_rgba(0,0,0,0.55)]">
            <div className="flex items-center justify-between border-b border-book-border/40 px-4 py-4">
              <div>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                  Assistant Rail
                </div>
                <div className="mt-1 font-semibold text-book-text-main">写作助手</div>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-book-border/50 bg-book-bg/70 text-book-text-muted transition-colors hover:text-book-primary"
              >
                <X size={16} />
              </button>
            </div>

            <div className="min-h-0 flex-1">
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
          </div>
        </div>
      </>
    );
  }

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
