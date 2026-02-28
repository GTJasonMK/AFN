import { useCallback, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { writerApi } from '../../api/writer';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';

type UseNovelDetailLatestChapterOutlineActionsParams = {
  id: string | undefined;
  chapterOutlines: any[];
  fetchProject: () => Promise<void>;
  setIsDeleteLatestModalOpen: Dispatch<SetStateAction<boolean>>;
  setIsRegenerateLatestModalOpen: Dispatch<SetStateAction<boolean>>;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailLatestChapterOutlineActions = ({
  id,
  chapterOutlines,
  fetchProject,
  setIsDeleteLatestModalOpen,
  setIsRegenerateLatestModalOpen,
  addToast,
}: UseNovelDetailLatestChapterOutlineActionsParams) => {
  const [deleteLatestCount, setDeleteLatestCount] = useState(5);
  const [deletingLatest, setDeletingLatest] = useState(false);
  const [regenerateLatestCount, setRegenerateLatestCount] = useState(1);
  const [regenerateLatestPrompt, setRegenerateLatestPrompt] = useState('');
  const [regeneratingLatest, setRegeneratingLatest] = useState(false);

  const handleDeleteLatestOutlines = useCallback(async () => {
    if (!id) return;
    const count = Math.max(1, Math.min(Number(deleteLatestCount) || 1, chapterOutlines.length || 1));
    const ok = await confirmDialog({
      title: '删除最新章节大纲',
      message:
        `确定要删除最新 ${count} 章章节大纲吗？\n\n` +
        `提示：如果这些章节已有生成内容，将级联删除章节内容与向量库数据。此操作不可恢复。`,
      confirmText: '删除',
      dialogType: 'danger',
    });
    if (!ok) return;

    setDeletingLatest(true);
    try {
      const result = await writerApi.deleteLatestChapterOutlines(id, count);
      addToast(result?.message || `已删除最新 ${count} 章大纲`, 'success');
      if (result?.warning) addToast(String(result.warning), 'info');
      setIsDeleteLatestModalOpen(false);
      await fetchProject();
    } catch (e) {
      console.error(e);
      addToast('删除失败', 'error');
    } finally {
      setDeletingLatest(false);
    }
  }, [
    addToast,
    chapterOutlines.length,
    deleteLatestCount,
    fetchProject,
    id,
    setIsDeleteLatestModalOpen,
  ]);

  const handleRegenerateLatestOutlines = useCallback(async () => {
    if (!id) return;
    if (!chapterOutlines.length) return;

    const sorted = [...chapterOutlines].sort(
      (a: any, b: any) => Number(a?.chapter_number || 0) - Number(b?.chapter_number || 0)
    );
    const maxCount = sorted.length;
    const count = Math.max(1, Math.min(Number(regenerateLatestCount) || 1, maxCount));
    const lastN = sorted.slice(-count);
    const start = Number(lastN[0]?.chapter_number || 0);
    const end = Number(sorted[sorted.length - 1]?.chapter_number || 0);
    if (!start || !end || end < start) {
      addToast('章节大纲数据异常，无法重生成', 'error');
      return;
    }

    const ok = await confirmDialog({
      title: '重生成最新章节大纲',
      message:
        `将重生成最后 ${count} 个章节大纲（第${start}-${end}章）。\n\n` +
        `串行生成原则：会级联删除第${start + 1}-${end}章的大纲（以及可能存在的章节内容/向量数据）。\n\n` +
        `确定继续？`,
      confirmText: '继续',
      dialogType: 'danger',
    });
    if (!ok) return;

    setRegeneratingLatest(true);
    try {
      const promptText = regenerateLatestPrompt.trim() || undefined;
      const result = await writerApi.regenerateChapterOutline(
        id,
        start,
        { prompt: promptText, cascadeDelete: true },
        { timeout: 0 }
      );
      addToast(result?.message || `第${start}章大纲已重生成`, 'success');
      if (result?.cascade_deleted?.message) addToast(String(result.cascade_deleted.message), 'info');
      setIsRegenerateLatestModalOpen(false);
      setRegenerateLatestPrompt('');
      await fetchProject();
    } catch (e) {
      console.error(e);
      addToast('重生成失败', 'error');
    } finally {
      setRegeneratingLatest(false);
    }
  }, [
    addToast,
    chapterOutlines,
    fetchProject,
    id,
    regenerateLatestCount,
    regenerateLatestPrompt,
    setIsRegenerateLatestModalOpen,
  ]);

  return {
    deleteLatestCount,
    setDeleteLatestCount,
    deletingLatest,
    regenerateLatestCount,
    setRegenerateLatestCount,
    regenerateLatestPrompt,
    setRegenerateLatestPrompt,
    regeneratingLatest,
    handleDeleteLatestOutlines,
    handleRegenerateLatestOutlines,
  };
};
