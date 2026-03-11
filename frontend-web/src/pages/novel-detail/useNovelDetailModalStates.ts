import { useState } from 'react';

type PartGenerateMode = 'generate' | 'continue';

export const useNovelDetailModalStates = () => {
  const [isOutlineModalOpen, setIsOutlineModalOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [isDeleteLatestModalOpen, setIsDeleteLatestModalOpen] = useState(false);
  const [isRegenerateLatestModalOpen, setIsRegenerateLatestModalOpen] = useState(false);
  const [isPartGenerateModalOpen, setIsPartGenerateModalOpen] = useState(false);
  const [partGenerateMode, setPartGenerateMode] = useState<PartGenerateMode>('generate');
  const [isDeleteLatestPartsModalOpen, setIsDeleteLatestPartsModalOpen] = useState(false);
  const [isRegenerateLatestPartsModalOpen, setIsRegenerateLatestPartsModalOpen] = useState(false);

  return {
    isOutlineModalOpen,
    setIsOutlineModalOpen,
    isBatchModalOpen,
    setIsBatchModalOpen,
    isDeleteLatestModalOpen,
    setIsDeleteLatestModalOpen,
    isRegenerateLatestModalOpen,
    setIsRegenerateLatestModalOpen,
    isPartGenerateModalOpen,
    setIsPartGenerateModalOpen,
    partGenerateMode,
    setPartGenerateMode,
    isDeleteLatestPartsModalOpen,
    setIsDeleteLatestPartsModalOpen,
    isRegenerateLatestPartsModalOpen,
    setIsRegenerateLatestPartsModalOpen,
  };
};
