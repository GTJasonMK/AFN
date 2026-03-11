import { useCallback, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';

type RelForm = {
  character_from: string;
  character_to: string;
  description: string;
};

const EMPTY_REL_FORM: RelForm = {
  character_from: '',
  character_to: '',
  description: '',
};

type UseNovelDetailRelationshipEditorParams = {
  blueprintData: any;
  setBlueprintData: Dispatch<SetStateAction<any>>;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailRelationshipEditor = ({
  blueprintData,
  setBlueprintData,
  addToast,
}: UseNovelDetailRelationshipEditorParams) => {
  const [editingRelIndex, setEditingRelIndex] = useState<number | null>(null);
  const [relForm, setRelForm] = useState<RelForm>({ ...EMPTY_REL_FORM });
  const [isRelModalOpen, setIsRelModalOpen] = useState(false);

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

    const item = { character_from: from, character_to: to, description };
    setBlueprintData((prev: any) => {
      const list = [...(Array.isArray(prev?.relationships) ? prev.relationships : [])];
      if (editingRelIndex !== null) {
        list[editingRelIndex] = item;
      } else {
        list.push(item);
      }
      return { ...(prev || {}), relationships: list };
    });
    setIsRelModalOpen(false);
  }, [addToast, editingRelIndex, relForm, setBlueprintData]);

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

    setBlueprintData((prev: any) => {
      const relationships = Array.isArray(prev?.relationships) ? prev.relationships : [];
      const next = relationships.filter((_: any, i: number) => i !== index);
      return { ...(prev || {}), relationships: next };
    });
  }, [blueprintData, setBlueprintData]);

  return {
    editingRelIndex,
    relForm,
    isRelModalOpen,
    setRelForm,
    setIsRelModalOpen,
    handleAddRel,
    handleEditRel,
    handleSaveRel,
    handleDeleteRel,
  };
};
