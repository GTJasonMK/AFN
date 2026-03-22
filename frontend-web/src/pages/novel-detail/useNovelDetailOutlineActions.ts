import { useCallback } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { useNovelDetailChapterOutlineRegenerate } from './useNovelDetailChapterOutlineRegenerate';
import { useNovelDetailLatestChapterOutlineActions } from './useNovelDetailLatestChapterOutlineActions';
import { useNovelDetailLatestPartOutlineActions } from './useNovelDetailLatestPartOutlineActions';
import { useNovelDetailPartOutlineRegenerate } from './useNovelDetailPartOutlineRegenerate';
import { useNovelDetailPartOutlineChapterGenerate } from './useNovelDetailPartOutlineChapterGenerate';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';
import { writerApi } from '../../api/writer';
import { buildWorkflowRollbackConfirmMessage, inferWorkflowRollbackDialogType } from '../../utils/workflowRollback';

type OptionalPromptOptions = {
  title?: string;
  hint?: string;
  initialValue?: string;
  onConfirm: (promptText?: string) => void | Promise<void>;
};

type UseNovelDetailOutlineActionsParams = {
  projectId: string;
  projectStatus: string | undefined;
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
  projectStatus,
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
    projectStatus,
    partOutlines,
    maxDeletablePartCount,
    fetchProject,
    fetchPartProgress,
    setIsDeleteLatestPartsModalOpen,
    setIsRegenerateLatestPartsModalOpen,
    addToast,
  });

  const openPartOutlinesModal = useCallback(async (mode: 'generate' | 'continue') => {
    if (!partTotalChapters) {
      addToast('无法获取总章节数，请先生成蓝图', 'error');
      return;
    }

    const statusRaw = String(projectStatus || '').trim();
    const needsRollback =
      statusRaw === 'writing' ||
      statusRaw === 'completed' ||
      statusRaw === 'chapter_outlines_ready';

    if (needsRollback) {
      const isWritingLike = statusRaw === 'writing' || statusRaw === 'completed';
      let rollbackPreviewMessage: string | null = null;
      let rollbackDialogType: 'warning' | 'danger' = isWritingLike ? 'danger' : 'warning';

      try {
        const preview = await writerApi.previewRollbackProjectWorkflow(projectId, 'part_outlines_ready', {
          timeout: 15_000,
        });
        rollbackPreviewMessage = buildWorkflowRollbackConfirmMessage(preview) || null;
        rollbackDialogType = inferWorkflowRollbackDialogType(preview);
      } catch (e) {
        console.warn('[workflow] rollback preview failed', e);
      }

      const ok = await confirmDialog({
        title: '需要回退到部分大纲阶段',
        message: rollbackPreviewMessage || (isWritingLike
          ? (
              '当前项目已进入「写作阶段」。\n\n' +
              '为了生成/重生成部分大纲，必须回退到「部分大纲就绪」并清理依赖数据：\n' +
              '- 删除已生成的章节正文（包含向量库/RAG索引相关数据）\n' +
              '- 删除章节大纲\n\n' +
              '此操作不可恢复。是否继续？'
            )
          : (
              '当前项目已生成「章节大纲」。\n\n' +
              '为了生成/重生成部分大纲，必须回退到「部分大纲就绪」并删除章节大纲。\n\n' +
              '此操作不可恢复。是否继续？'
            )),
        confirmText: '继续回退',
        dialogType: rollbackDialogType,
      });
      if (!ok) return;

      try {
        await writerApi.rollbackProjectWorkflow(projectId, 'part_outlines_ready', { timeout: 0 });
        await Promise.allSettled([fetchProject(), fetchPartProgress()]);
        addToast('已回退到部分大纲阶段', 'success');
      } catch (e) {
        console.error(e);
        addToast('回退失败，请查看后端日志', 'error');
        return;
      }
    }

    setPartGenerateMode(mode);
    setIsPartGenerateModalOpen(true);
  }, [
    addToast,
    fetchPartProgress,
    fetchProject,
    partTotalChapters,
    projectId,
    projectStatus,
    setIsPartGenerateModalOpen,
    setPartGenerateMode,
  ]);

  const {
    regeneratingPartKey,
    handleRegenerateAllPartOutlines,
    handleRegenerateLastPartOutline,
    handleRegeneratePartOutline,
  } = useNovelDetailPartOutlineRegenerate({
    id: projectId,
    projectStatus,
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
