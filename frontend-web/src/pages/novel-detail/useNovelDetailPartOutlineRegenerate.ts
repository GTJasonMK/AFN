import { useCallback, useState } from 'react';
import { writerApi } from '../../api/writer';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';
import { buildWorkflowRollbackConfirmMessage, inferWorkflowRollbackDialogType } from '../../utils/workflowRollback';

type OptionalPromptOptions = {
  title?: string;
  hint?: string;
  initialValue?: string;
  onConfirm: (promptText?: string) => void | Promise<void>;
};

type UseNovelDetailPartOutlineRegenerateParams = {
  id: string | undefined;
  projectStatus: string | undefined;
  partProgress: any | null;
  setPartProgress: (next: any) => void;
  fetchProject: () => Promise<void>;
  fetchPartProgress: () => Promise<void>;
  openOptionalPromptModal: (opts: OptionalPromptOptions) => void;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailPartOutlineRegenerate = ({
  id,
  projectStatus,
  partProgress,
  setPartProgress,
  fetchProject,
  fetchPartProgress,
  openOptionalPromptModal,
  addToast,
}: UseNovelDetailPartOutlineRegenerateParams) => {
  const [regeneratingPartKey, setRegeneratingPartKey] = useState<string | null>(null);

  const getRollbackPreviewIfNeeded = useCallback(async () => {
    const statusRaw = String(projectStatus || '').trim();
    const needsRollback =
      statusRaw === 'writing' ||
      statusRaw === 'completed' ||
      statusRaw === 'chapter_outlines_ready';
    if (!needsRollback || !id) {
      return { needsRollback: false as const, message: '', dialogType: 'warning' as const };
    }

    try {
      const preview = await writerApi.previewRollbackProjectWorkflow(id, 'part_outlines_ready', { timeout: 15_000 });
      return {
        needsRollback: true as const,
        message: buildWorkflowRollbackConfirmMessage(preview),
        dialogType: inferWorkflowRollbackDialogType(preview),
      };
    } catch (e) {
      console.warn('[workflow] rollback preview failed', e);
      return {
        needsRollback: true as const,
        message: '',
        dialogType: statusRaw === 'writing' || statusRaw === 'completed' ? ('danger' as const) : ('warning' as const),
      };
    }
  }, [id, projectStatus]);

  const rollbackToPartOutlinesReady = useCallback(async () => {
    if (!id) return false;
    try {
      await writerApi.rollbackProjectWorkflow(id, 'part_outlines_ready', { timeout: 0 });
      await Promise.allSettled([fetchProject(), fetchPartProgress()]);
      return true;
    } catch (e) {
      console.error(e);
      addToast('回退失败（无法重生成部分大纲）', 'error');
      return false;
    }
  }, [addToast, fetchPartProgress, fetchProject, id]);

  const handleRegenerateAllPartOutlines = useCallback(async () => {
    if (!id) return;
    const rollbackInfo = await getRollbackPreviewIfNeeded();
    const ok = await confirmDialog({
      title: '重生成所有部分大纲',
      message: rollbackInfo.needsRollback
        ? (
            '该操作需要先回退到「部分大纲就绪」阶段。\n\n' +
            (rollbackInfo.message ? `${rollbackInfo.message}\n\n` : '') +
            '回退完成后将继续执行：重生成所有部分大纲。\n' +
            '注意：这会删除所有已生成的章节大纲（以及可能存在的章节内容/向量数据）。'
          )
        : '重生成所有部分大纲将删除所有已生成的章节大纲（以及可能存在的章节内容/向量数据）。\n\n是否继续？',
      confirmText: '继续',
      dialogType: rollbackInfo.needsRollback ? rollbackInfo.dialogType : 'danger',
    });
    if (!ok) return;

    if (rollbackInfo.needsRollback) {
      const rolledBack = await rollbackToPartOutlinesReady();
      if (!rolledBack) return;
    }

    openOptionalPromptModal({
      title: '输入优化提示词（可选）',
      hint: '留空则按默认策略重生成；填写则会作为优化方向参与生成。',
      onConfirm: async (promptText?: string) => {
        setRegeneratingPartKey('all');
        try {
          const res = await writerApi.regenerateAllPartOutlines(id, promptText, { timeout: 0 });
          setPartProgress(res);
          addToast('部分大纲已重生成', 'success');
          await fetchProject();
          await fetchPartProgress();
        } catch (e) {
          console.error(e);
          addToast('重生成失败', 'error');
        } finally {
          setRegeneratingPartKey(null);
        }
      },
    });
  }, [
    addToast,
    getRollbackPreviewIfNeeded,
    fetchPartProgress,
    fetchProject,
    id,
    openOptionalPromptModal,
    rollbackToPartOutlinesReady,
    setPartProgress,
  ]);

  const handleRegenerateLastPartOutline = useCallback(async () => {
    if (!id) return;
    const rollbackInfo = await getRollbackPreviewIfNeeded();
    const ok = await confirmDialog({
      title: '重生成最后一个部分',
      message: rollbackInfo.needsRollback
        ? (
            '该操作需要先回退到「部分大纲就绪」阶段。\n\n' +
            (rollbackInfo.message ? `${rollbackInfo.message}\n\n` : '') +
            '回退完成后将继续执行：重生成最后一个部分大纲。\n' +
            '注意：这会删除该部分对应的章节大纲（以及可能存在的章节内容/向量数据）。'
          )
        : '重生成最后一个部分大纲将删除该部分对应的章节大纲（以及可能存在的章节内容/向量数据）。\n\n是否继续？',
      confirmText: '继续',
      dialogType: rollbackInfo.needsRollback ? rollbackInfo.dialogType : 'danger',
    });
    if (!ok) return;

    if (rollbackInfo.needsRollback) {
      const rolledBack = await rollbackToPartOutlinesReady();
      if (!rolledBack) return;
    }

    openOptionalPromptModal({
      title: '输入优化提示词（可选）',
      hint: '留空则按默认策略重生成；填写则会作为优化方向参与生成。',
      onConfirm: async (promptText?: string) => {
        setRegeneratingPartKey('last');
        try {
          const res = await writerApi.regenerateLastPartOutline(id, promptText, { timeout: 0 });
          setPartProgress(res);
          addToast('最后一个部分大纲已重生成', 'success');
          await fetchProject();
          await fetchPartProgress();
        } catch (e) {
          console.error(e);
          addToast('重生成失败', 'error');
        } finally {
          setRegeneratingPartKey(null);
        }
      },
    });
  }, [
    addToast,
    getRollbackPreviewIfNeeded,
    fetchPartProgress,
    fetchProject,
    id,
    openOptionalPromptModal,
    rollbackToPartOutlinesReady,
    setPartProgress,
  ]);

  const handleRegeneratePartOutline = useCallback(async (partNumber: number) => {
    if (!id) return;
    const parts = Array.isArray(partProgress?.parts) ? partProgress.parts : [];
    const maxPart = parts.length ? Math.max(...parts.map((p: any) => Number(p.part_number || 0))) : partNumber;
    const isLast = partNumber === maxPart;

    const rollbackInfo = await getRollbackPreviewIfNeeded();
    let cascadeDelete = false;
    let rollbackConfirmed = false;
    if (!isLast && maxPart > 0) {
      const ok = await confirmDialog({
        title: '串行生成原则',
        message:
          `串行生成原则：只能直接重生成最后一个部分（当前最后一个为第${maxPart}部分）。\n\n` +
          `若要重生成第${partNumber}部分，必须级联删除第${partNumber + 1}-${maxPart}部分的大纲，以及对应章节大纲/内容/向量数据。\n\n` +
          (rollbackInfo.needsRollback
            ? (
                '此外，该操作需要先回退到「部分大纲就绪」阶段。\n\n' +
                (rollbackInfo.message ? `${rollbackInfo.message}\n\n` : '')
              )
            : '') +
          '是否继续？',
        confirmText: '继续',
        dialogType: rollbackInfo.needsRollback ? rollbackInfo.dialogType : 'danger',
      });
      if (!ok) return;
      cascadeDelete = true;
      rollbackConfirmed = rollbackInfo.needsRollback;
    }

    if (rollbackInfo.needsRollback) {
      if (!rollbackConfirmed) {
        const ok = await confirmDialog({
          title: '需要回退到部分大纲阶段',
          message: rollbackInfo.message || (
            '当前项目不处于可操作部分大纲的阶段。\n\n' +
            '为了重生成部分大纲，需要先回退并清理依赖数据（如章节大纲/章节正文）。\n\n' +
            '此操作不可恢复。是否继续？'
          ),
          confirmText: '继续回退',
          dialogType: rollbackInfo.dialogType,
        });
        if (!ok) return;
      }
      const rolledBack = await rollbackToPartOutlinesReady();
      if (!rolledBack) return;
    }

    openOptionalPromptModal({
      title: '输入优化提示词（可选）',
      hint: '留空则按默认策略重生成；填写则会作为优化方向参与生成。',
      onConfirm: async (promptText?: string) => {
        setRegeneratingPartKey(String(partNumber));
        try {
          const res = await writerApi.regeneratePartOutline(
            id,
            partNumber,
            { prompt: promptText, cascadeDelete },
            { timeout: 0 }
          );
          setPartProgress(res);
          addToast(`第${partNumber}部分大纲已重生成`, 'success');
          await fetchProject();
          await fetchPartProgress();
        } catch (e) {
          console.error(e);
          addToast('重生成失败', 'error');
        } finally {
          setRegeneratingPartKey(null);
        }
      },
    });
  }, [
    addToast,
    getRollbackPreviewIfNeeded,
    fetchPartProgress,
    fetchProject,
    id,
    openOptionalPromptModal,
    partProgress,
    rollbackToPartOutlinesReady,
    setPartProgress,
  ]);

  return {
    regeneratingPartKey,
    handleRegenerateAllPartOutlines,
    handleRegenerateLastPartOutline,
    handleRegeneratePartOutline,
  };
};
