import { useCallback, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { writerApi } from '../../api/writer';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';

type UseNovelDetailLatestPartOutlineActionsParams = {
  id: string | undefined;
  partOutlines: any[];
  maxDeletablePartCount: number;
  fetchProject: () => Promise<void>;
  fetchPartProgress: () => Promise<void>;
  setIsDeleteLatestPartsModalOpen: Dispatch<SetStateAction<boolean>>;
  setIsRegenerateLatestPartsModalOpen: Dispatch<SetStateAction<boolean>>;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailLatestPartOutlineActions = ({
  id,
  partOutlines,
  maxDeletablePartCount,
  fetchProject,
  fetchPartProgress,
  setIsDeleteLatestPartsModalOpen,
  setIsRegenerateLatestPartsModalOpen,
  addToast,
}: UseNovelDetailLatestPartOutlineActionsParams) => {
  const [deleteLatestPartsCount, setDeleteLatestPartsCount] = useState(1);
  const [deletingLatestParts, setDeletingLatestParts] = useState(false);
  const [regenerateLatestPartsCount, setRegenerateLatestPartsCount] = useState(1);
  const [regenerateLatestPartsPrompt, setRegenerateLatestPartsPrompt] = useState('');
  const [regeneratingLatestParts, setRegeneratingLatestParts] = useState(false);

  const handleDeleteLatestPartOutlines = useCallback(async () => {
    if (!id) return;
    if (maxDeletablePartCount <= 0) {
      addToast('至少需要保留 1 个部分大纲，当前无法删除', 'error');
      return;
    }

    const count = Math.max(1, Math.min(Number(deleteLatestPartsCount) || 1, maxDeletablePartCount));
    const ok = await confirmDialog({
      title: '删除最新部分大纲',
      message:
        `确定要删除最后 ${count} 个部分大纲吗？\n\n` +
        `这些部分对应的章节大纲也会被一起删除。\n` +
        `此操作不可恢复。`,
      confirmText: '删除',
      dialogType: 'danger',
    });
    if (!ok) return;

    setDeletingLatestParts(true);
    try {
      const result = await writerApi.deleteLatestPartOutlines(id, count);
      addToast(result?.message || `已删除最后 ${count} 个部分大纲`, 'success');
      setIsDeleteLatestPartsModalOpen(false);
      await fetchProject();
      await fetchPartProgress();
    } catch (e) {
      console.error(e);
      addToast('删除失败', 'error');
    } finally {
      setDeletingLatestParts(false);
    }
  }, [
    addToast,
    deleteLatestPartsCount,
    fetchPartProgress,
    fetchProject,
    id,
    maxDeletablePartCount,
    setIsDeleteLatestPartsModalOpen,
  ]);

  const handleRegenerateLatestPartOutlines = useCallback(async () => {
    if (!id) return;
    if (!partOutlines.length) return;

    const sorted = [...partOutlines].sort(
      (a: any, b: any) => Number(a?.part_number || 0) - Number(b?.part_number || 0)
    );
    const maxCount = sorted.length;
    const count = Math.max(1, Math.min(Number(regenerateLatestPartsCount) || 1, maxCount));
    const lastN = sorted.slice(-count);
    const start = Number(lastN[0]?.part_number || 0);
    const end = Number(lastN[lastN.length - 1]?.part_number || 0);
    if (!start || !end || end < start) {
      addToast('部分大纲数据异常，无法重生成', 'error');
      return;
    }

    const ok = await confirmDialog({
      title: '重生成最新部分大纲',
      message:
        `将重生成最后 ${count} 个部分大纲（第${start}-${end}部分）。\n\n` +
        `串行生成原则：会级联删除第${start + 1}-${end}部分的大纲，以及对应章节大纲/内容/向量数据。\n\n` +
        `确定继续？`,
      confirmText: '继续',
      dialogType: 'danger',
    });
    if (!ok) return;

    setRegeneratingLatestParts(true);
    try {
      const promptText = regenerateLatestPartsPrompt.trim() || undefined;
      const result = await writerApi.regeneratePartOutline(
        id,
        start,
        { prompt: promptText, cascadeDelete: true },
        { timeout: 0 }
      );
      addToast(result?.message || `第${start}部分大纲已重生成`, 'success');
      if (result?.cascade_deleted?.message) addToast(String(result.cascade_deleted.message), 'info');
      setIsRegenerateLatestPartsModalOpen(false);
      setRegenerateLatestPartsPrompt('');
      await Promise.allSettled([fetchProject(), fetchPartProgress()]);
    } catch (e) {
      console.error(e);
      addToast('重生成失败', 'error');
    } finally {
      setRegeneratingLatestParts(false);
    }
  }, [
    addToast,
    fetchPartProgress,
    fetchProject,
    id,
    partOutlines,
    regenerateLatestPartsCount,
    regenerateLatestPartsPrompt,
    setIsRegenerateLatestPartsModalOpen,
  ]);

  return {
    deleteLatestPartsCount,
    setDeleteLatestPartsCount,
    deletingLatestParts,
    regenerateLatestPartsCount,
    setRegenerateLatestPartsCount,
    regenerateLatestPartsPrompt,
    setRegenerateLatestPartsPrompt,
    regeneratingLatestParts,
    handleDeleteLatestPartOutlines,
    handleRegenerateLatestPartOutlines,
  };
};
