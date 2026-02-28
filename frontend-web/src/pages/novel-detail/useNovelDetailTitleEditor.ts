import { useCallback, useState } from 'react';
import { novelsApi } from '../../api/novels';

type UseNovelDetailTitleEditorParams = {
  id: string | undefined;
  projectTitle: string | undefined;
  fetchProject: () => Promise<void>;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailTitleEditor = ({
  id,
  projectTitle,
  fetchProject,
  addToast,
}: UseNovelDetailTitleEditorParams) => {
  const [isEditTitleModalOpen, setIsEditTitleModalOpen] = useState(false);
  const [editTitleValue, setEditTitleValue] = useState('');
  const [editTitleSaving, setEditTitleSaving] = useState(false);

  const openEditTitleModal = useCallback(() => {
    setEditTitleValue(String(projectTitle || '').trim());
    setIsEditTitleModalOpen(true);
  }, [projectTitle]);

  const closeEditTitleModal = useCallback(() => {
    if (editTitleSaving) return;
    setIsEditTitleModalOpen(false);
  }, [editTitleSaving]);

  const saveProjectTitle = useCallback(async () => {
    if (!id) return;
    const next = (editTitleValue || '').trim();
    if (!next) {
      addToast('标题不能为空', 'error');
      return;
    }

    setEditTitleSaving(true);
    try {
      await novelsApi.update(id, { title: next });
      addToast('标题已更新', 'success');
      setIsEditTitleModalOpen(false);
      await fetchProject();
    } catch (e) {
      console.error(e);
      addToast('标题更新失败', 'error');
    } finally {
      setEditTitleSaving(false);
    }
  }, [addToast, editTitleValue, fetchProject, id]);

  return {
    isEditTitleModalOpen,
    editTitleValue,
    editTitleSaving,
    setEditTitleValue,
    openEditTitleModal,
    closeEditTitleModal,
    saveProjectTitle,
  };
};
