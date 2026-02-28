import React from 'react';
import { ChapterList } from '../../components/business/ChapterList';
import type { Chapter } from '../../api/writer';

export const WritingDeskSidebar: React.FC<{
  projectId: string;
  chapters: Chapter[];
  draftRevision: number;
  currentChapterNumber?: number;
  projectInfo: any;
  width: number;
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

