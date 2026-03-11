import React from 'react';
import { Modal } from '../../components/ui/Modal';
import { BookButton } from '../../components/ui/BookButton';
import { BookInput, BookTextarea } from '../../components/ui/BookInput';

type RelationshipEditModalProps = {
  isOpen: boolean;
  setOpen: (open: boolean) => void;
  editingIndex: number | null;
  onSave: () => void | Promise<void>;
  characterNames: string[];
  relForm: {
    character_from: string;
    character_to: string;
    description: string;
  };
  setRelForm: React.Dispatch<
    React.SetStateAction<{
      character_from: string;
      character_to: string;
      description: string;
    }>
  >;
};

const CHARACTER_NAMES_DATA_LIST_ID = 'novel-character-names';

export const RelationshipEditModal: React.FC<RelationshipEditModalProps> = ({
  isOpen,
  setOpen,
  editingIndex,
  onSave,
  characterNames,
  relForm,
  setRelForm,
}) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={() => setOpen(false)}
      title={editingIndex !== null ? '编辑关系' : '添加关系'}
      footer={
        <div className="flex justify-end gap-2">
          <BookButton variant="ghost" onClick={() => setOpen(false)}>取消</BookButton>
          <BookButton variant="primary" onClick={onSave}>保存</BookButton>
        </div>
      }
    >
      <div className="space-y-4">
        <datalist id={CHARACTER_NAMES_DATA_LIST_ID}>
          {characterNames.map((name) => (
            <option key={`c-${name}`} value={name} />
          ))}
        </datalist>

        <BookInput
          label="角色A"
          value={relForm.character_from}
          onChange={(e) => setRelForm((prev) => ({ ...prev, character_from: e.target.value }))}
          placeholder="例如：林远"
          list={CHARACTER_NAMES_DATA_LIST_ID}
        />
        <BookInput
          label="角色B"
          value={relForm.character_to}
          onChange={(e) => setRelForm((prev) => ({ ...prev, character_to: e.target.value }))}
          placeholder="例如：苏鸢"
          list={CHARACTER_NAMES_DATA_LIST_ID}
        />
        <BookTextarea
          label="关系描述"
          value={relForm.description}
          onChange={(e) => setRelForm((prev) => ({ ...prev, description: e.target.value }))}
          rows={4}
          placeholder="例如：青梅竹马，因一次误会渐行渐远…"
        />
      </div>
    </Modal>
  );
};
