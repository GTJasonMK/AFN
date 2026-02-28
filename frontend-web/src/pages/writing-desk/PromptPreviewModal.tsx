import React, { lazy, Suspense } from 'react';
import { Modal } from '../../components/ui/Modal';
import { BookButton } from '../../components/ui/BookButton';

const ChapterPromptPreviewViewLazy = lazy(() =>
  import('../../components/business/ChapterPromptPreviewView').then((m) => ({ default: m.ChapterPromptPreviewView }))
);

export const PromptPreviewModal: React.FC<{
  projectId: string;
  chapterNumber: number | null;
  isOpen: boolean;
  writingNotes: string;
  onChangeWritingNotes: (text: string) => void;
  onClose: () => void;
}> = ({ projectId, chapterNumber, isOpen, writingNotes, onChangeWritingNotes, onClose }) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`第 ${chapterNumber ?? ''} 章 - 提示词预览`}
      maxWidthClassName="max-w-6xl"
      className="max-h-[90vh]"
      footer={
        <div className="flex justify-end gap-2">
          <BookButton variant="ghost" onClick={onClose}>
            关闭
          </BookButton>
        </div>
      }
    >
      <div className="max-h-[75vh] overflow-auto custom-scrollbar pr-1">
        {chapterNumber ? (
          <Suspense fallback={<div className="text-sm text-book-text-muted">提示词预览加载中…</div>}>
            <ChapterPromptPreviewViewLazy
              projectId={projectId}
              chapterNumber={chapterNumber}
              writingNotes={writingNotes}
              onChangeWritingNotes={onChangeWritingNotes}
            />
          </Suspense>
        ) : (
          <div className="text-sm text-book-text-muted">请先选择章节</div>
        )}
      </div>
    </Modal>
  );
};

