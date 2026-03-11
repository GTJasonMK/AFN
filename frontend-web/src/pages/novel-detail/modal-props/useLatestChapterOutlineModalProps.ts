import { useMemo } from 'react';
import type { LatestChapterModalInput, LatestChapterOutlineModalProps } from './types';

export const useLatestChapterOutlineModalProps = ({
  chapterOutlines,
  isRegenerateLatestModalOpen,
  setIsRegenerateLatestModalOpen,
  regeneratingLatest,
  regenerateLatestCount,
  setRegenerateLatestCount,
  regenerateLatestPrompt,
  setRegenerateLatestPrompt,
  handleRegenerateLatestOutlines,
  isDeleteLatestModalOpen,
  setIsDeleteLatestModalOpen,
  deletingLatest,
  deleteLatestCount,
  setDeleteLatestCount,
  handleDeleteLatestOutlines,
}: LatestChapterModalInput): LatestChapterOutlineModalProps => {
  const chapterOutlineCount = chapterOutlines.length;

  return useMemo<LatestChapterOutlineModalProps>(() => ({
    regenerateModal: {
      isOpen: isRegenerateLatestModalOpen,
      setOpen: setIsRegenerateLatestModalOpen,
      regenerating: regeneratingLatest,
      chapterOutlineCount,
      count: regenerateLatestCount,
      setCount: setRegenerateLatestCount,
      prompt: regenerateLatestPrompt,
      setPrompt: setRegenerateLatestPrompt,
      onConfirm: handleRegenerateLatestOutlines,
    },
    deleteModal: {
      isOpen: isDeleteLatestModalOpen,
      setOpen: setIsDeleteLatestModalOpen,
      deleting: deletingLatest,
      chapterOutlineCount,
      count: deleteLatestCount,
      setCount: setDeleteLatestCount,
      onConfirm: handleDeleteLatestOutlines,
    },
  }), [
    chapterOutlineCount,
    deleteLatestCount,
    deletingLatest,
    handleDeleteLatestOutlines,
    handleRegenerateLatestOutlines,
    isDeleteLatestModalOpen,
    isRegenerateLatestModalOpen,
    regenerateLatestCount,
    regenerateLatestPrompt,
    regeneratingLatest,
    setDeleteLatestCount,
    setIsDeleteLatestModalOpen,
    setIsRegenerateLatestModalOpen,
    setRegenerateLatestCount,
    setRegenerateLatestPrompt,
  ]);
};
