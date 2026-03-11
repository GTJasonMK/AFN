import { useCallback } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { useNovelDetailChapterOutlineRegenerate } from './useNovelDetailChapterOutlineRegenerate';
import { useNovelDetailLatestChapterOutlineActions } from './useNovelDetailLatestChapterOutlineActions';
import { useNovelDetailLatestPartOutlineActions } from './useNovelDetailLatestPartOutlineActions';
import { useNovelDetailPartOutlineRegenerate } from './useNovelDetailPartOutlineRegenerate';
import { useNovelDetailPartOutlineChapterGenerate } from './useNovelDetailPartOutlineChapterGenerate';

type OptionalPromptOptions = {
  title?: string;
  hint?: string;
  initialValue?: string;
  onConfirm: (promptText?: string) => void | Promise<void>;
};

type UseNovelDetailOutlineActionsParams = {
  projectId: string;
  chapterOutlines: any[];
  partOutlines: any[];
  partProgress: any | null;
  partTotalChapters: number;
  maxDeletablePartCount: number;
  setPartProgress: (next: any) => void;
  fetchProject: () => Promise<void>;
  fetchPartProgress: () => Promise<void>;
  setIsDeleteLatestModalOpen: Dispatch<SetStateAction<boolean>>;
  setIsRegenerateLatestModalOpen: Dispatch<SetStateAction<boolean>>;
  setIsDeleteLatestPartsModalOpen: Dispatch<SetStateAction<boolean>>;
  setIsRegenerateLatestPartsModalOpen: Dispatch<SetStateAction<boolean>>;
  setPartGenerateMode: (mode: 'generate' | 'continue') => void;
  setIsPartGenerateModalOpen: Dispatch<SetStateAction<boolean>>;
  openOptionalPromptModal: (options: OptionalPromptOptions) => void;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailOutlineActions = ({
  projectId,
  chapterOutlines,
  partOutlines,
  partProgress,
  partTotalChapters,
  maxDeletablePartCount,
  setPartProgress,
  fetchProject,
  fetchPartProgress,
  setIsDeleteLatestModalOpen,
  setIsRegenerateLatestModalOpen,
  setIsDeleteLatestPartsModalOpen,
  setIsRegenerateLatestPartsModalOpen,
  setPartGenerateMode,
  setIsPartGenerateModalOpen,
  openOptionalPromptModal,
  addToast,
}: UseNovelDetailOutlineActionsParams) => {
  const { handleRegenerateOutline } = useNovelDetailChapterOutlineRegenerate({
    id: projectId,
    chapterOutlines,
    fetchProject,
    openOptionalPromptModal,
    addToast,
  });

  const latestChapterOutlineActions = useNovelDetailLatestChapterOutlineActions({
    id: projectId,
    chapterOutlines,
    fetchProject,
    setIsDeleteLatestModalOpen,
    setIsRegenerateLatestModalOpen,
    addToast,
  });

  const latestPartOutlineActions = useNovelDetailLatestPartOutlineActions({
    id: projectId,
    partOutlines,
    maxDeletablePartCount,
    fetchProject,
    fetchPartProgress,
    setIsDeleteLatestPartsModalOpen,
    setIsRegenerateLatestPartsModalOpen,
    addToast,
  });

  const openPartOutlinesModal = useCallback((mode: 'generate' | 'continue') => {
    if (!partTotalChapters) {
      addToast('无法获取总章节数，请先生成蓝图', 'error');
      return;
    }
    setPartGenerateMode(mode);
    setIsPartGenerateModalOpen(true);
  }, [addToast, partTotalChapters, setIsPartGenerateModalOpen, setPartGenerateMode]);

  const {
    regeneratingPartKey,
    handleRegenerateAllPartOutlines,
    handleRegenerateLastPartOutline,
    handleRegeneratePartOutline,
  } = useNovelDetailPartOutlineRegenerate({
    id: projectId,
    partProgress,
    setPartProgress,
    fetchProject,
    fetchPartProgress,
    openOptionalPromptModal,
    addToast,
  });

  const {
    generatingPartChapters,
    handleGeneratePartChapters,
  } = useNovelDetailPartOutlineChapterGenerate({
    id: projectId,
    chapterOutlines,
    fetchProject,
    fetchPartProgress,
    addToast,
  });

  return {
    handleRegenerateOutline,
    latestChapterOutlineActions,
    latestPartOutlineActions,
    latestOutlineInputParams: {
      latestPartOutlineInput: latestPartOutlineActions,
      latestChapterOutlineInput: latestChapterOutlineActions,
    },
    openPartOutlinesModal,
    regeneratingPartKey,
    handleRegenerateAllPartOutlines,
    handleRegenerateLastPartOutline,
    handleRegeneratePartOutline,
    generatingPartChapters,
    handleGeneratePartChapters,
  };
};
