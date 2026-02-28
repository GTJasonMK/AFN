import React from 'react';
import { Modal } from '../../components/ui/Modal';
import { BookButton } from '../../components/ui/BookButton';
import { BookInput, BookTextarea } from '../../components/ui/BookInput';

type CharacterAndRelationshipModalsProps = {
  isCharModalOpen: boolean;
  setIsCharModalOpen: (open: boolean) => void;
  editingCharIndex: number | null;
  handleSaveChar: () => void | Promise<void>;
  charForm: any;
  setCharForm: React.Dispatch<React.SetStateAction<any>>;
  isRelModalOpen: boolean;
  setIsRelModalOpen: (open: boolean) => void;
  editingRelIndex: number | null;
  handleSaveRel: () => void | Promise<void>;
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

export const CharacterAndRelationshipModals: React.FC<CharacterAndRelationshipModalsProps> = ({
  isCharModalOpen,
  setIsCharModalOpen,
  editingCharIndex,
  handleSaveChar,
  charForm,
  setCharForm,
  isRelModalOpen,
  setIsRelModalOpen,
  editingRelIndex,
  handleSaveRel,
  characterNames,
  relForm,
  setRelForm,
}) => {
  return (
    <>
      <Modal
        isOpen={isCharModalOpen}
        onClose={() => setIsCharModalOpen(false)}
        title={editingCharIndex !== null ? '编辑角色' : '添加新角色'}
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={() => setIsCharModalOpen(false)}>取消</BookButton>
            <BookButton variant="primary" onClick={handleSaveChar}>保存</BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <BookInput
            label="姓名"
            value={charForm.name || ''}
            onChange={(e) => setCharForm({ ...charForm, name: e.target.value })}
          />
          <BookInput
            label="身份"
            value={charForm.identity || ''}
            onChange={(e) => setCharForm({ ...charForm, identity: e.target.value })}
          />
          <BookTextarea
            label="性格特征"
            value={charForm.personality || ''}
            onChange={(e) => setCharForm({ ...charForm, personality: e.target.value })}
          />
          <BookTextarea
            label="目标与动机"
            value={charForm.goal || ''}
            onChange={(e) => setCharForm({ ...charForm, goal: e.target.value })}
          />
          <BookTextarea
            label="能力（可选）"
            value={charForm.ability || ''}
            onChange={(e) => setCharForm({ ...charForm, ability: e.target.value })}
            rows={3}
            placeholder="例如：剑术、推理、黑客技能、魔法天赋…"
          />
          <BookTextarea
            label="背景（可选）"
            value={charForm.background || ''}
            onChange={(e) => setCharForm({ ...charForm, background: e.target.value })}
            rows={4}
            placeholder="例如：出身、经历、创伤、转折点…"
          />
          <BookTextarea
            label="与主角关系（可选）"
            value={charForm.relationship_with_protagonist || ''}
            onChange={(e) => setCharForm({ ...charForm, relationship_with_protagonist: e.target.value })}
            rows={3}
            placeholder="例如：盟友/对手/师徒/亲属/互相利用…"
          />
        </div>
      </Modal>

      <Modal
        isOpen={isRelModalOpen}
        onClose={() => setIsRelModalOpen(false)}
        title={editingRelIndex !== null ? '编辑关系' : '添加关系'}
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={() => setIsRelModalOpen(false)}>取消</BookButton>
            <BookButton variant="primary" onClick={handleSaveRel}>保存</BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <datalist id="novel-character-names">
            {characterNames.map((name) => (
              <option key={`c-${name}`} value={name} />
            ))}
          </datalist>

          <BookInput
            label="角色A"
            value={relForm.character_from}
            onChange={(e) => setRelForm({ ...relForm, character_from: e.target.value })}
            placeholder="例如：林远"
            list="novel-character-names"
          />
          <BookInput
            label="角色B"
            value={relForm.character_to}
            onChange={(e) => setRelForm({ ...relForm, character_to: e.target.value })}
            placeholder="例如：苏鸢"
            list="novel-character-names"
          />
          <BookTextarea
            label="关系描述"
            value={relForm.description}
            onChange={(e) => setRelForm({ ...relForm, description: e.target.value })}
            rows={4}
            placeholder="例如：青梅竹马，因一次误会渐行渐远…"
          />
        </div>
      </Modal>
    </>
  );
};
