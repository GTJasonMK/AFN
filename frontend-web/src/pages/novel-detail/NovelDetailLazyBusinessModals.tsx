import React, { lazy, Suspense } from 'react';

const OutlineEditModalLazy = lazy(() =>
  import('../../components/business/OutlineEditModal').then((m) => ({ default: m.OutlineEditModal }))
);
const BatchGenerateModalLazy = lazy(() =>
  import('../../components/business/BatchGenerateModal').then((m) => ({ default: m.BatchGenerateModal }))
);
const ProtagonistProfilesModalLazy = lazy(() =>
  import('../../components/business/ProtagonistProfilesModal').then((m) => ({ default: m.ProtagonistProfilesModal }))
);
const PartOutlineGenerateModalLazy = lazy(() =>
  import('../../components/business/PartOutlineGenerateModal').then((m) => ({ default: m.PartOutlineGenerateModal }))
);
const PartOutlineDetailModalLazy = lazy(() =>
  import('../../components/business/PartOutlineDetailModal').then((m) => ({ default: m.PartOutlineDetailModal }))
);

type NovelDetailLazyBusinessModalsProps = {
  projectId: string;
  isOutlineModalOpen: boolean;
  setIsOutlineModalOpen: (open: boolean) => void;
  editingChapter: any | null;
  fetchProject: () => void | Promise<void>;
  isBatchModalOpen: boolean;
  setIsBatchModalOpen: (open: boolean) => void;
  isProtagonistModalOpen: boolean;
  setIsProtagonistModalOpen: (open: boolean) => void;
  currentChapterNumber: number;
  isPartGenerateModalOpen: boolean;
  setIsPartGenerateModalOpen: (open: boolean) => void;
  partGenerateMode: 'generate' | 'continue';
  totalChapters: number;
  chaptersPerPart: number;
  currentCoveredChapters?: number;
  currentPartsCount?: number;
  fetchPartProgress: () => Promise<void>;
  detailPart: any | null;
  setDetailPart: (part: any | null) => void;
};

export const NovelDetailLazyBusinessModals: React.FC<NovelDetailLazyBusinessModalsProps> = ({
  projectId,
  isOutlineModalOpen,
  setIsOutlineModalOpen,
  editingChapter,
  fetchProject,
  isBatchModalOpen,
  setIsBatchModalOpen,
  isProtagonistModalOpen,
  setIsProtagonistModalOpen,
  currentChapterNumber,
  isPartGenerateModalOpen,
  setIsPartGenerateModalOpen,
  partGenerateMode,
  totalChapters,
  chaptersPerPart,
  currentCoveredChapters,
  currentPartsCount,
  fetchPartProgress,
  detailPart,
  setDetailPart,
}) => {
  return (
    <>
      {isOutlineModalOpen ? (
        <Suspense fallback={null}>
          <OutlineEditModalLazy
            isOpen={isOutlineModalOpen}
            onClose={() => setIsOutlineModalOpen(false)}
            chapter={editingChapter}
            projectId={projectId}
            onSuccess={() => {
              fetchProject();
            }}
          />
        </Suspense>
      ) : null}

      {isBatchModalOpen ? (
        <Suspense fallback={null}>
          <BatchGenerateModalLazy
            isOpen={isBatchModalOpen}
            onClose={() => setIsBatchModalOpen(false)}
            projectId={projectId}
            onSuccess={() => {
              fetchProject();
            }}
          />
        </Suspense>
      ) : null}

      {isProtagonistModalOpen ? (
        <Suspense fallback={null}>
          <ProtagonistProfilesModalLazy
            isOpen={isProtagonistModalOpen}
            onClose={() => setIsProtagonistModalOpen(false)}
            projectId={projectId}
            currentChapterNumber={currentChapterNumber}
          />
        </Suspense>
      ) : null}

      {isPartGenerateModalOpen ? (
        <Suspense fallback={null}>
          <PartOutlineGenerateModalLazy
            isOpen={isPartGenerateModalOpen}
            onClose={() => setIsPartGenerateModalOpen(false)}
            projectId={projectId}
            mode={partGenerateMode}
            totalChapters={totalChapters}
            defaultChaptersPerPart={chaptersPerPart}
            currentCoveredChapters={currentCoveredChapters}
            currentPartsCount={currentPartsCount}
            onSuccess={async () => {
              await fetchProject();
              await fetchPartProgress();
            }}
          />
        </Suspense>
      ) : null}

      {detailPart ? (
        <Suspense fallback={null}>
          <PartOutlineDetailModalLazy
            isOpen={Boolean(detailPart)}
            onClose={() => setDetailPart(null)}
            part={detailPart}
          />
        </Suspense>
      ) : null}
    </>
  );
};
