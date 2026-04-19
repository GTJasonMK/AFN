import React, { lazy, Suspense } from 'react';
import type { Chapter } from '../../api/writer';
import { ImportChapterModal } from '../../components/business/ImportChapterModal';
import { PromptPreviewModal } from './PromptPreviewModal';
import { WritingNotesModal } from './WritingNotesModal';
import type { WritingDeskBatchModalPreset } from './shared';

const OutlineEditModalLazy = lazy(() =>
  import('../../components/business/OutlineEditModal').then((m) => ({ default: m.OutlineEditModal }))
);
const BatchGenerateModalLazy = lazy(() =>
  import('../../components/business/BatchGenerateModal').then((m) => ({ default: m.BatchGenerateModal }))
);
const ProtagonistProfilesModalLazy = lazy(() =>
  import('../../components/business/ProtagonistProfilesModal').then((m) => ({ default: m.ProtagonistProfilesModal }))
);

type WritingDeskModalsProps = {
  projectId: string;
  currentChapterNumber: number | null;
  isPromptPreviewModalOpen: boolean;
  promptPreviewNotes: string;
  onChangePromptPreviewNotes: (value: string) => void;
  onClosePromptPreview: () => void;
  isOutlineModalOpen: boolean;
  editingChapter: Chapter | null;
  onCloseOutlineModal: () => void;
  onOutlineSuccess: () => void | Promise<void>;
  isBatchModalOpen: boolean;
  batchModalPreset: WritingDeskBatchModalPreset;
  latestOutlineChapterNumber: number;
  needsPartOutlines: boolean;
  partOutlineCount: number;
  partOutlineCoverMax: number | null;
  onCloseBatchModal: () => void;
  onBatchSuccess: () => void | Promise<void>;
  isProtagonistModalOpen: boolean;
  onCloseProtagonistModal: () => void;
  isImportChapterModalOpen: boolean;
  suggestedImportChapterNumber: number;
  onCloseImportChapterModal: () => void;
  onImportedChapter: (chapterNo: number) => void | Promise<void>;
  optionalPromptModal: React.ReactNode;
  isWritingNotesModalOpen: boolean;
  writingNotesDraft: string;
  onChangeWritingNotesDraft: (value: string) => void;
  onCloseWritingNotesModal: () => void;
  onCommitWritingNotes: (next: string) => void;
};

export const WritingDeskModals: React.FC<WritingDeskModalsProps> = ({
  projectId,
  currentChapterNumber,
  isPromptPreviewModalOpen,
  promptPreviewNotes,
  onChangePromptPreviewNotes,
  onClosePromptPreview,
  isOutlineModalOpen,
  editingChapter,
  onCloseOutlineModal,
  onOutlineSuccess,
  isBatchModalOpen,
  batchModalPreset,
  latestOutlineChapterNumber,
  needsPartOutlines,
  partOutlineCount,
  partOutlineCoverMax,
  onCloseBatchModal,
  onBatchSuccess,
  isProtagonistModalOpen,
  onCloseProtagonistModal,
  isImportChapterModalOpen,
  suggestedImportChapterNumber,
  onCloseImportChapterModal,
  onImportedChapter,
  optionalPromptModal,
  isWritingNotesModalOpen,
  writingNotesDraft,
  onChangeWritingNotesDraft,
  onCloseWritingNotesModal,
  onCommitWritingNotes,
}) => {
  return (
    <>
      <PromptPreviewModal
        projectId={projectId}
        chapterNumber={currentChapterNumber}
        isOpen={isPromptPreviewModalOpen}
        writingNotes={promptPreviewNotes}
        onChangeWritingNotes={onChangePromptPreviewNotes}
        onClose={onClosePromptPreview}
      />

      {isOutlineModalOpen ? (
        <Suspense fallback={null}>
          <OutlineEditModalLazy
            isOpen={isOutlineModalOpen}
            onClose={onCloseOutlineModal}
            chapter={editingChapter}
            projectId={projectId}
            onSuccess={onOutlineSuccess}
          />
        </Suspense>
      ) : null}

      {isBatchModalOpen ? (
        <Suspense fallback={null}>
          <BatchGenerateModalLazy
            isOpen={isBatchModalOpen}
            onClose={onCloseBatchModal}
            projectId={projectId}
            initialCount={batchModalPreset.count}
            initialStartFrom={batchModalPreset.startFrom}
            latestOutlineChapterNumber={latestOutlineChapterNumber}
            needsPartOutlines={needsPartOutlines}
            partOutlineCount={partOutlineCount}
            partOutlineMaxCoveredChapter={partOutlineCoverMax}
            onSuccess={onBatchSuccess}
          />
        </Suspense>
      ) : null}

      {isProtagonistModalOpen ? (
        <Suspense fallback={null}>
          <ProtagonistProfilesModalLazy
            isOpen={isProtagonistModalOpen}
            onClose={onCloseProtagonistModal}
            projectId={projectId}
            currentChapterNumber={currentChapterNumber ?? undefined}
          />
        </Suspense>
      ) : null}

      <ImportChapterModal
        projectId={projectId}
        isOpen={isImportChapterModalOpen}
        onClose={onCloseImportChapterModal}
        suggestedChapterNumber={suggestedImportChapterNumber}
        onImported={onImportedChapter}
      />

      {optionalPromptModal}

      <WritingNotesModal
        isOpen={isWritingNotesModalOpen}
        draft={writingNotesDraft}
        onChangeDraft={onChangeWritingNotesDraft}
        onClose={onCloseWritingNotesModal}
        onCommit={onCommitWritingNotes}
      />
    </>
  );
};
