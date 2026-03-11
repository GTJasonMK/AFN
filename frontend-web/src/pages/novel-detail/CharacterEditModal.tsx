import React from 'react';
import { Modal } from '../../components/ui/Modal';
import { BookButton } from '../../components/ui/BookButton';
import { BookInput, BookTextarea } from '../../components/ui/BookInput';

type CharacterEditModalProps = {
  isOpen: boolean;
  setOpen: (open: boolean) => void;
  editingIndex: number | null;
  onSave: () => void | Promise<void>;
  charForm: any;
  setCharForm: React.Dispatch<React.SetStateAction<any>>;
};

export const CharacterEditModal: React.FC<CharacterEditModalProps> = ({
  isOpen,
  setOpen,
  editingIndex,
  onSave,
  charForm,
  setCharForm,
}) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={() => setOpen(false)}
      title={editingIndex !== null ? '编辑角色' : '添加新角色'}
      footer={
        <div className="flex justify-end gap-2">
          <BookButton variant="ghost" onClick={() => setOpen(false)}>取消</BookButton>
          <BookButton variant="primary" onClick={onSave}>保存</BookButton>
        </div>
      }
    >
      <div className="space-y-4">
        <BookInput
          label="姓名"
          value={charForm.name || ''}
          onChange={(e) => setCharForm((prev: any) => ({ ...prev, name: e.target.value }))}
        />
        <BookInput
          label="身份"
          value={charForm.identity || ''}
          onChange={(e) => setCharForm((prev: any) => ({ ...prev, identity: e.target.value }))}
        />
        <BookTextarea
          label="性格特征"
          value={charForm.personality || ''}
          onChange={(e) => setCharForm((prev: any) => ({ ...prev, personality: e.target.value }))}
        />
        <BookTextarea
          label="目标与动机"
          value={charForm.goal || ''}
          onChange={(e) => setCharForm((prev: any) => ({ ...prev, goal: e.target.value }))}
        />
        <BookTextarea
          label="能力（可选）"
          value={charForm.ability || ''}
          onChange={(e) => setCharForm((prev: any) => ({ ...prev, ability: e.target.value }))}
          rows={3}
          placeholder="例如：剑术、推理、黑客技能、魔法天赋…"
        />
        <BookTextarea
          label="背景（可选）"
          value={charForm.background || ''}
          onChange={(e) => setCharForm((prev: any) => ({ ...prev, background: e.target.value }))}
          rows={4}
          placeholder="例如：出身、经历、创伤、转折点…"
        />
        <BookTextarea
          label="与主角关系（可选）"
          value={charForm.relationship_with_protagonist || ''}
          onChange={(e) => setCharForm((prev: any) => ({ ...prev, relationship_with_protagonist: e.target.value }))}
          rows={3}
          placeholder="例如：盟友/对手/师徒/亲属/互相利用…"
        />
      </div>
    </Modal>
  );
};
