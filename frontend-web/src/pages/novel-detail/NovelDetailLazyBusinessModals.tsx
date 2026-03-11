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
  onProjectRefresh: () => void | Promise<void>;
  outlineModal: {
    isOpen: boolean;
    setOpen: (open: boolean) => void;
    editingChapter: any | null;
  };
  batchModal: {
    isOpen: boolean;
    setOpen: (open: boolean) => void;
  };
  protagonistModal: {
    isOpen: boolean;
    setOpen: (open: boolean) => void;
    currentChapterNumber: number;
  };
  partGenerateModal: {
    isOpen: boolean;
    setOpen: (open: boolean) => void;
    mode: 'generate' | 'continue';
    totalChapters: number;
    chaptersPerPart: number;
    currentCoveredChapters?: number;
    currentPartsCount?: number;
    onSuccess: () => Promise<void>;
  };
  partDetailModal: {
    detailPart: any | null;
    setDetailPart: (part: any | null) => void;
  };
};

export const NovelDetailLazyBusinessModals: React.FC<NovelDetailLazyBusinessModalsProps> = ({
  projectId,
  onProjectRefresh,
  outlineModal,
  batchModal,
  protagonistModal,
  partGenerateModal,
  partDetailModal,
}) => {
  const {
    isOpen: isOutlineModalOpen,
    setOpen: setOutlineModalOpen,
    editingChapter,
  } = outlineModal;
  const {
    isOpen: isBatchModalOpen,
    setOpen: setBatchModalOpen,
  } = batchModal;
  const {
    isOpen: isProtagonistModalOpen,
    setOpen: setProtagonistModalOpen,
    currentChapterNumber,
  } = protagonistModal;
  const {
    isOpen: isPartGenerateModalOpen,
    setOpen: setPartGenerateModalOpen,
    mode: partGenerateMode,
    totalChapters,
    chaptersPerPart,
    currentCoveredChapters,
    currentPartsCount,
    onSuccess: onPartGenerateSuccess,
  } = partGenerateModal;
  const { detailPart, setDetailPart } = partDetailModal;

  return (
    <>
      {isOutlineModalOpen ? (
        <Suspense fallback={null}>
          <OutlineEditModalLazy
            isOpen={isOutlineModalOpen}
            onClose={() => setOutlineModalOpen(false)}
            chapter={editingChapter}
            projectId={projectId}
            onSuccess={() => {
              onProjectRefresh();
            }}
          />
        </Suspense>
      ) : null}

      {isBatchModalOpen ? (
        <Suspense fallback={null}>
          <BatchGenerateModalLazy
            isOpen={isBatchModalOpen}
            onClose={() => setBatchModalOpen(false)}
            projectId={projectId}
            onSuccess={() => {
              onProjectRefresh();
            }}
          />
        </Suspense>
      ) : null}

      {isProtagonistModalOpen ? (
        <Suspense fallback={null}>
          <ProtagonistProfilesModalLazy
            isOpen={isProtagonistModalOpen}
            onClose={() => setProtagonistModalOpen(false)}
            projectId={projectId}
            currentChapterNumber={currentChapterNumber}
          />
        </Suspense>
      ) : null}

      {isPartGenerateModalOpen ? (
        <Suspense fallback={null}>
          <PartOutlineGenerateModalLazy
            isOpen={isPartGenerateModalOpen}
            onClose={() => setPartGenerateModalOpen(false)}
            projectId={projectId}
            mode={partGenerateMode}
            totalChapters={totalChapters}
            defaultChaptersPerPart={chaptersPerPart}
            currentCoveredChapters={currentCoveredChapters}
            currentPartsCount={currentPartsCount}
            onSuccess={async () => {
              await onPartGenerateSuccess();
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
