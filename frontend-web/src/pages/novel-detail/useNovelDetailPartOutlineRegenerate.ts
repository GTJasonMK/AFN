import { useCallback, useState } from 'react';
import { writerApi } from '../../api/writer';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';

type OptionalPromptOptions = {
  title?: string;
  hint?: string;
  initialValue?: string;
  onConfirm: (promptText?: string) => void | Promise<void>;
};

type UseNovelDetailPartOutlineRegenerateParams = {
  id: string | undefined;
  partProgress: any | null;
  setPartProgress: (next: any) => void;
  fetchProject: () => Promise<void>;
  fetchPartProgress: () => Promise<void>;
  openOptionalPromptModal: (opts: OptionalPromptOptions) => void;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailPartOutlineRegenerate = ({
  id,
  partProgress,
  setPartProgress,
  fetchProject,
  fetchPartProgress,
  openOptionalPromptModal,
  addToast,
}: UseNovelDetailPartOutlineRegenerateParams) => {
  const [regeneratingPartKey, setRegeneratingPartKey] = useState<string | null>(null);

  const handleRegenerateAllPartOutlines = useCallback(async () => {
    if (!id) return;
    const ok = await confirmDialog({
      title: '重生成所有部分大纲',
      message: '重生成所有部分大纲将删除所有已生成的章节大纲（以及可能存在的章节内容/向量数据）。\n\n是否继续？',
      confirmText: '继续',
      dialogType: 'danger',
    });
    if (!ok) return;

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
  }, [addToast, fetchPartProgress, fetchProject, id, openOptionalPromptModal, setPartProgress]);

  const handleRegenerateLastPartOutline = useCallback(async () => {
    if (!id) return;
    const ok = await confirmDialog({
      title: '重生成最后一个部分',
      message: '重生成最后一个部分大纲将删除该部分对应的章节大纲（以及可能存在的章节内容/向量数据）。\n\n是否继续？',
      confirmText: '继续',
      dialogType: 'danger',
    });
    if (!ok) return;

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
  }, [addToast, fetchPartProgress, fetchProject, id, openOptionalPromptModal, setPartProgress]);

  const handleRegeneratePartOutline = useCallback(async (partNumber: number) => {
    if (!id) return;
    const parts = Array.isArray(partProgress?.parts) ? partProgress.parts : [];
    const maxPart = parts.length ? Math.max(...parts.map((p: any) => Number(p.part_number || 0))) : partNumber;
    const isLast = partNumber === maxPart;

    let cascadeDelete = false;
    if (!isLast && maxPart > 0) {
      const ok = await confirmDialog({
        title: '串行生成原则',
        message:
          `串行生成原则：只能直接重生成最后一个部分（当前最后一个为第${maxPart}部分）。\n\n` +
          `若要重生成第${partNumber}部分，必须级联删除第${partNumber + 1}-${maxPart}部分的大纲，以及对应章节大纲/内容/向量数据。\n\n是否继续？`,
        confirmText: '继续',
        dialogType: 'danger',
      });
      if (!ok) return;
      cascadeDelete = true;
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
    fetchPartProgress,
    fetchProject,
    id,
    openOptionalPromptModal,
    partProgress,
    setPartProgress,
  ]);

  return {
    regeneratingPartKey,
    handleRegenerateAllPartOutlines,
    handleRegenerateLastPartOutline,
    handleRegeneratePartOutline,
  };
};
