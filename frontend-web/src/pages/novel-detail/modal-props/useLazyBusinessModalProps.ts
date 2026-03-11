import { useMemo } from 'react';
import type { BusinessModalInput, LazyBusinessModalProps } from './types';

export const useLazyBusinessModalProps = ({
  blueprintData,
  partOutlines,
  partTotalChapters,
  latestChapterNumber,
  partCoveredChapters,
  partGenerateMode,
  isOutlineModalOpen,
  setIsOutlineModalOpen,
  editingChapter,
  isBatchModalOpen,
  setIsBatchModalOpen,
  isProtagonistModalOpen,
  setIsProtagonistModalOpen,
  isPartGenerateModalOpen,
  setIsPartGenerateModalOpen,
  detailPart,
  setDetailPart,
  refreshProjectAndPartProgress,
}: BusinessModalInput): LazyBusinessModalProps => {
  const chaptersPerPart = Number(blueprintData?.chapters_per_part || 25) || 25;
  const partOutlineCount = partOutlines.length;
  const partGenerateTotalChapters = Math.max(10, partTotalChapters || 10);

  return useMemo<LazyBusinessModalProps>(() => ({
    outlineModal: {
      isOpen: isOutlineModalOpen,
      setOpen: setIsOutlineModalOpen,
      editingChapter,
    },
    batchModal: {
      isOpen: isBatchModalOpen,
      setOpen: setIsBatchModalOpen,
    },
    protagonistModal: {
      isOpen: isProtagonistModalOpen,
      setOpen: setIsProtagonistModalOpen,
      currentChapterNumber: latestChapterNumber,
    },
    partGenerateModal: {
      isOpen: isPartGenerateModalOpen,
      setOpen: setIsPartGenerateModalOpen,
      mode: partGenerateMode,
      totalChapters: partGenerateTotalChapters,
      chaptersPerPart,
      currentCoveredChapters: partCoveredChapters || undefined,
      currentPartsCount: partOutlineCount || undefined,
      onSuccess: refreshProjectAndPartProgress,
    },
    partDetailModal: {
      detailPart,
      setDetailPart,
    },
  }), [
    chaptersPerPart,
    detailPart,
    editingChapter,
    isBatchModalOpen,
    isOutlineModalOpen,
    isPartGenerateModalOpen,
    isProtagonistModalOpen,
    latestChapterNumber,
    partCoveredChapters,
    partGenerateMode,
    partGenerateTotalChapters,
    partOutlineCount,
    refreshProjectAndPartProgress,
    setDetailPart,
    setIsBatchModalOpen,
    setIsOutlineModalOpen,
    setIsPartGenerateModalOpen,
    setIsProtagonistModalOpen,
  ]);
};
