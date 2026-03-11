import React from 'react';
import { X } from 'lucide-react';
import { ChapterList } from '../../components/business/ChapterList';
import type { Chapter } from '../../api/writer';

export const WritingDeskSidebar: React.FC<{
  projectId: string;
  chapters: Chapter[];
  draftRevision: number;
  currentChapterNumber?: number;
  projectInfo: any;
  width: number;
  compact?: boolean;
  onClose?: () => void;
  onResizeMouseDown: (e: React.MouseEvent) => void;
  onSelectChapter: (chapterNumber: number) => void | Promise<void>;
  onCreateChapter: () => void | Promise<void>;
  onEditOutline: (chapter: Chapter) => void;
  onRegenerateOutline?: (chapter: Chapter) => void;
  onResetChapter: (chapter: Chapter) => void;
  onDeleteChapter: (chapter: Chapter) => void;
  onBatchGenerate: () => void;
  onOpenProtagonistProfiles: () => void;
}> = ({
  projectId,
  chapters,
  draftRevision,
  currentChapterNumber,
  projectInfo,
  width,
  compact = false,
  onClose,
  onResizeMouseDown,
  onSelectChapter,
  onCreateChapter,
  onEditOutline,
  onRegenerateOutline,
  onResetChapter,
  onDeleteChapter,
  onBatchGenerate,
  onOpenProtagonistProfiles,
}) => {
  if (compact) {
    return (
      <>
        <button
          type="button"
          aria-label="关闭章节导航遮罩"
          className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm xl:hidden"
          onClick={onClose}
        />

        <div className="fixed inset-y-0 left-0 z-50 w-[min(100vw,26rem)] xl:hidden">
          <div className="flex h-full flex-col border-r border-book-border/50 bg-book-bg-paper shadow-[0_30px_90px_-40px_rgba(0,0,0,0.55)]">
            <div className="flex items-center justify-between border-b border-book-border/40 px-4 py-4">
              <div>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                  Chapter Rail
                </div>
                <div className="mt-1 font-semibold text-book-text-main">章节导航</div>
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
              <ChapterList
                chapters={chapters}
                projectId={projectId}
                draftRevision={draftRevision}
                currentChapterNumber={currentChapterNumber}
                projectInfo={projectInfo}
                onSelectChapter={onSelectChapter}
                onCreateChapter={onCreateChapter}
                onEditOutline={onEditOutline}
                onRegenerateOutline={onRegenerateOutline}
                onResetChapter={onResetChapter}
                onDeleteChapter={onDeleteChapter}
                onBatchGenerate={onBatchGenerate}
                onOpenProtagonistProfiles={onOpenProtagonistProfiles}
              />
            </div>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="shrink-0 h-full" style={{ width }}>
        <ChapterList
          chapters={chapters}
          projectId={projectId}
          draftRevision={draftRevision}
          currentChapterNumber={currentChapterNumber}
          projectInfo={projectInfo}
          onSelectChapter={onSelectChapter}
          onCreateChapter={onCreateChapter}
          onEditOutline={onEditOutline}
          onRegenerateOutline={onRegenerateOutline}
          onResetChapter={onResetChapter}
          onDeleteChapter={onDeleteChapter}
          onBatchGenerate={onBatchGenerate}
          onOpenProtagonistProfiles={onOpenProtagonistProfiles}
        />
      </div>

      <div
        className="w-1.5 shrink-0 cursor-col-resize bg-transparent hover:bg-book-primary/20 transition-colors"
        onMouseDown={onResizeMouseDown}
        title="拖拽调整章节栏宽度"
      />
    </>
  );
};
