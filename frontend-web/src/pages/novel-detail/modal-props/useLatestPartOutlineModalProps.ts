import { useMemo } from 'react';
import type { LatestPartModalInput, LatestPartOutlineModalProps } from './types';

export const useLatestPartOutlineModalProps = ({
  partOutlines,
  isDeleteLatestPartsModalOpen,
  setIsDeleteLatestPartsModalOpen,
  deletingLatestParts,
  maxDeletablePartCount,
  deleteLatestPartsCount,
  setDeleteLatestPartsCount,
  handleDeleteLatestPartOutlines,
  isRegenerateLatestPartsModalOpen,
  setIsRegenerateLatestPartsModalOpen,
  regeneratingLatestParts,
  regenerateLatestPartsCount,
  setRegenerateLatestPartsCount,
  regenerateLatestPartsPrompt,
  setRegenerateLatestPartsPrompt,
  handleRegenerateLatestPartOutlines,
}: LatestPartModalInput): LatestPartOutlineModalProps => {
  const partOutlineCount = partOutlines.length;

  return useMemo<LatestPartOutlineModalProps>(() => ({
    deleteModal: {
      isOpen: isDeleteLatestPartsModalOpen,
      setOpen: setIsDeleteLatestPartsModalOpen,
      deleting: deletingLatestParts,
      maxDeletableCount: maxDeletablePartCount,
      count: deleteLatestPartsCount,
      setCount: setDeleteLatestPartsCount,
      onConfirm: handleDeleteLatestPartOutlines,
    },
    regenerateModal: {
      isOpen: isRegenerateLatestPartsModalOpen,
      setOpen: setIsRegenerateLatestPartsModalOpen,
      regenerating: regeneratingLatestParts,
      partOutlineCount,
      count: regenerateLatestPartsCount,
      setCount: setRegenerateLatestPartsCount,
      prompt: regenerateLatestPartsPrompt,
      setPrompt: setRegenerateLatestPartsPrompt,
      onConfirm: handleRegenerateLatestPartOutlines,
    },
  }), [
    deleteLatestPartsCount,
    deletingLatestParts,
    handleDeleteLatestPartOutlines,
    handleRegenerateLatestPartOutlines,
    isDeleteLatestPartsModalOpen,
    isRegenerateLatestPartsModalOpen,
    maxDeletablePartCount,
    partOutlineCount,
    regenerateLatestPartsCount,
    regenerateLatestPartsPrompt,
    regeneratingLatestParts,
    setDeleteLatestPartsCount,
    setIsDeleteLatestPartsModalOpen,
    setIsRegenerateLatestPartsModalOpen,
    setRegenerateLatestPartsCount,
    setRegenerateLatestPartsPrompt,
  ]);
};
