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
  const needsPartOutlines = Boolean(blueprintData?.needs_part_outlines);
  const latestOutlineChapterNumber = (() => {
    const list = Array.isArray(blueprintData?.chapter_outline) ? blueprintData.chapter_outline : [];
    if (list.length === 0) return 0;
    return list.reduce((acc: number, item: any) => Math.max(acc, Number(item?.chapter_number) || 0), 0);
  })();
  const partOutlineMaxCoveredChapter = (() => {
    if (!Array.isArray(partOutlines) || partOutlines.length === 0) return null;
    const raw = partOutlines.reduce((acc, po) => Math.max(acc, Number(po?.end_chapter) || 0), 0);
    return Number.isFinite(raw) && raw > 0 ? raw : null;
  })();

  return useMemo<LazyBusinessModalProps>(() => ({
    outlineModal: {
      isOpen: isOutlineModalOpen,
      setOpen: setIsOutlineModalOpen,
      editingChapter,
    },
    batchModal: {
      isOpen: isBatchModalOpen,
      setOpen: setIsBatchModalOpen,
      latestOutlineChapterNumber,
      needsPartOutlines,
      partOutlineCount,
      partOutlineMaxCoveredChapter,
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
    latestOutlineChapterNumber,
    needsPartOutlines,
    partCoveredChapters,
    partGenerateMode,
    partGenerateTotalChapters,
    partOutlineCount,
    partOutlineMaxCoveredChapter,
    refreshProjectAndPartProgress,
    setDetailPart,
    setIsBatchModalOpen,
    setIsOutlineModalOpen,
    setIsPartGenerateModalOpen,
    setIsProtagonistModalOpen,
  ]);
};
