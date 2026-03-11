import { useCallback, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';

const EMPTY_CHAR_FORM = {
  name: '',
  identity: '',
  personality: '',
  goal: '',
  ability: '',
  background: '',
  relationship_with_protagonist: '',
};

type UseNovelDetailCharacterEditorParams = {
  blueprintData: any;
  setBlueprintData: Dispatch<SetStateAction<any>>;
};

export const useNovelDetailCharacterEditor = ({
  blueprintData,
  setBlueprintData,
}: UseNovelDetailCharacterEditorParams) => {
  const [editingCharIndex, setEditingCharIndex] = useState<number | null>(null);
  const [charForm, setCharForm] = useState<any>({});
  const [isCharModalOpen, setIsCharModalOpen] = useState(false);
  const [charactersView, setCharactersView] = useState<'info' | 'portraits'>('info');

  const handleEditChar = useCallback((index: number) => {
    const list = Array.isArray(blueprintData?.characters) ? blueprintData.characters : [];
    const target = list[index];
    if (!target) return;

    setEditingCharIndex(index);
    setCharForm({ ...target });
    setIsCharModalOpen(true);
  }, [blueprintData]);

  const handleAddChar = useCallback(() => {
    setEditingCharIndex(null);
    setCharForm({ ...EMPTY_CHAR_FORM });
    setIsCharModalOpen(true);
  }, []);

  const handleSaveChar = useCallback(() => {
    setBlueprintData((prev: any) => {
      const list = [...(Array.isArray(prev?.characters) ? prev.characters : [])];
      if (editingCharIndex !== null) {
        list[editingCharIndex] = charForm;
      } else {
        list.push(charForm);
      }
      return { ...(prev || {}), characters: list };
    });
    setIsCharModalOpen(false);
  }, [charForm, editingCharIndex, setBlueprintData]);

  const handleDeleteChar = useCallback(async (index: number) => {
    const ok = await confirmDialog({
      title: '删除角色',
      message: '确定要删除这个角色吗？',
      confirmText: '删除',
      dialogType: 'danger',
    });
    if (!ok) return;

    setBlueprintData((prev: any) => {
      const list = [...(Array.isArray(prev?.characters) ? prev.characters : [])];
      if (index < 0 || index >= list.length) return prev;
      list.splice(index, 1);
      return { ...(prev || {}), characters: list };
    });
  }, [setBlueprintData]);

  return {
    editingCharIndex,
    charForm,
    isCharModalOpen,
    charactersView,
    setCharForm,
    setIsCharModalOpen,
    setCharactersView,
    handleEditChar,
    handleAddChar,
    handleSaveChar,
    handleDeleteChar,
  };
};
