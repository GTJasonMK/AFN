import { useCallback, useState } from 'react';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';

type RelForm = {
  character_from: string;
  character_to: string;
  description: string;
};

type UseNovelDetailCharacterRelationshipEditorParams = {
  blueprintData: any;
  setBlueprintData: (next: any) => void;
  addToast: (message: string, type?: string) => void;
};

const EMPTY_CHAR_FORM = {
  name: '',
  identity: '',
  personality: '',
  goal: '',
  ability: '',
  background: '',
  relationship_with_protagonist: '',
};

const EMPTY_REL_FORM: RelForm = {
  character_from: '',
  character_to: '',
  description: '',
};

export const useNovelDetailCharacterRelationshipEditor = ({
  blueprintData,
  setBlueprintData,
  addToast,
}: UseNovelDetailCharacterRelationshipEditorParams) => {
  const [editingCharIndex, setEditingCharIndex] = useState<number | null>(null);
  const [charForm, setCharForm] = useState<any>({});
  const [isCharModalOpen, setIsCharModalOpen] = useState(false);
  const [charactersView, setCharactersView] = useState<'info' | 'portraits'>('info');
  const [isProtagonistModalOpen, setIsProtagonistModalOpen] = useState(false);

  const [editingRelIndex, setEditingRelIndex] = useState<number | null>(null);
  const [relForm, setRelForm] = useState<RelForm>({ ...EMPTY_REL_FORM });
  const [isRelModalOpen, setIsRelModalOpen] = useState(false);

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
    const list = [...(Array.isArray(blueprintData?.characters) ? blueprintData.characters : [])];
    if (editingCharIndex !== null) {
      list[editingCharIndex] = charForm;
    } else {
      list.push(charForm);
    }
    setBlueprintData({ ...blueprintData, characters: list });
    setIsCharModalOpen(false);
  }, [blueprintData, charForm, editingCharIndex, setBlueprintData]);

  const handleDeleteChar = useCallback(async (index: number) => {
    const ok = await confirmDialog({
      title: '删除角色',
      message: '确定要删除这个角色吗？',
      confirmText: '删除',
      dialogType: 'danger',
    });
    if (!ok) return;

    const list = [...(Array.isArray(blueprintData?.characters) ? blueprintData.characters : [])];
    if (index < 0 || index >= list.length) return;
    list.splice(index, 1);
    setBlueprintData({ ...blueprintData, characters: list });
  }, [blueprintData, setBlueprintData]);

  const handleAddRel = useCallback(() => {
    setEditingRelIndex(null);
    setRelForm({ ...EMPTY_REL_FORM });
    setIsRelModalOpen(true);
  }, []);

  const handleEditRel = useCallback((index: number) => {
    const list = Array.isArray(blueprintData?.relationships) ? blueprintData.relationships : [];
    const rel = list[index];
    if (!rel) return;

    setEditingRelIndex(index);
    setRelForm({
      character_from: String(rel.character_from || ''),
      character_to: String(rel.character_to || ''),
      description: String(rel.description || ''),
    });
    setIsRelModalOpen(true);
  }, [blueprintData]);

  const handleSaveRel = useCallback(() => {
    const from = relForm.character_from.trim();
    const to = relForm.character_to.trim();
    const description = relForm.description.trim();
    if (!from || !to) {
      addToast('请输入关系双方角色名', 'error');
      return;
    }

    const list = [...(Array.isArray(blueprintData?.relationships) ? blueprintData.relationships : [])];
    const item = { character_from: from, character_to: to, description };
    if (editingRelIndex !== null) {
      list[editingRelIndex] = item;
    } else {
      list.push(item);
    }

    setBlueprintData({ ...blueprintData, relationships: list });
    setIsRelModalOpen(false);
  }, [addToast, blueprintData, editingRelIndex, relForm, setBlueprintData]);

  const handleDeleteRel = useCallback(async (index: number) => {
    const list = Array.isArray(blueprintData?.relationships) ? blueprintData.relationships : [];
    const rel = list[index];
    if (!rel) return;

    const label = `${rel.character_from || ''} → ${rel.character_to || ''}`;
    const ok = await confirmDialog({
      title: '删除关系',
      message: `确定要删除该关系吗？\n${label}`,
      confirmText: '删除',
      dialogType: 'danger',
    });
    if (!ok) return;

    const next = list.filter((_: any, i: number) => i !== index);
    setBlueprintData({ ...blueprintData, relationships: next });
  }, [blueprintData, setBlueprintData]);

  return {
    editingCharIndex,
    charForm,
    isCharModalOpen,
    charactersView,
    isProtagonistModalOpen,
    editingRelIndex,
    relForm,
    isRelModalOpen,
    setCharForm,
    setIsCharModalOpen,
    setCharactersView,
    setIsProtagonistModalOpen,
    setRelForm,
    setIsRelModalOpen,
    handleEditChar,
    handleAddChar,
    handleSaveChar,
    handleDeleteChar,
    handleAddRel,
    handleEditRel,
    handleSaveRel,
    handleDeleteRel,
  };
};
