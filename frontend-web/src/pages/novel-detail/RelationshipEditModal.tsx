import React from 'react';
import { Modal } from '../../components/ui/Modal';
import { BookButton } from '../../components/ui/BookButton';
import { BookInput, BookTextarea } from '../../components/ui/BookInput';
import {
  NovelDialogIntro,
  NovelDialogMetric,
  NovelDialogMetricGrid,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from '../../components/business/novel/NovelDialogPrimitives';

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
  const isEditing = editingIndex !== null;
  const isCompleteLink = Boolean(relForm.character_from.trim() && relForm.character_to.trim());

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => setOpen(false)}
      title={isEditing ? '编辑关系' : '添加关系'}
      maxWidthClassName="max-w-xl"
      footer={
        <div className="flex justify-end gap-2">
          <BookButton variant="ghost" onClick={() => setOpen(false)}>取消</BookButton>
          <BookButton variant="primary" onClick={onSave}>保存</BookButton>
        </div>
      }
    >
      <NovelDialogStack>
        <datalist id={CHARACTER_NAMES_DATA_LIST_ID}>
          {characterNames.map((name) => (
            <option key={`c-${name}`} value={name} />
          ))}
        </datalist>

        <NovelDialogIntro
          eyebrow="Relationship Graph"
          title={isEditing ? '修订人物关系' : '补充人物关系'}
          description="人物关系会影响蓝图关系网、章节冲突调度和角色互动提示。建议先固定两端角色，再补充关系阶段和张力说明。"
        >
          <div className="flex flex-wrap gap-2">
            <span className="story-pill">{isEditing ? '编辑关系边' : '创建关系边'}</span>
            <span className="story-pill">{isCompleteLink ? '两端角色已指定' : '待指定角色端点'}</span>
          </div>
        </NovelDialogIntro>

        <NovelDialogMetricGrid>
          <NovelDialogMetric
            label="角色池"
            value={characterNames.length}
            note="输入时支持从现有角色名单中自动补全。"
          />
          <NovelDialogMetric
            label="当前状态"
            value={isCompleteLink ? '关系已成型' : '待补全'}
            note="关系描述建议写清楚立场、历史原因和当前张力。"
          />
        </NovelDialogMetricGrid>

        <NovelDialogSection
          eyebrow="Endpoints"
          title="关系两端"
          description="关系默认以角色 A 指向角色 B 记录，填写时可按叙事视角或关系发起方理解。"
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
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
          </div>
        </NovelDialogSection>

        <NovelDialogSection
          eyebrow="Description"
          title="关系描述"
          description="写清楚双方是什么关系、为何形成、现阶段是否稳定，以及未来可能如何变化。"
        >
          <BookTextarea
            label="关系描述"
            value={relForm.description}
            onChange={(e) => setRelForm((prev) => ({ ...prev, description: e.target.value }))}
            rows={4}
            placeholder="例如：青梅竹马，因一次误会渐行渐远，如今在利益合作中重新试探彼此…"
          />
        </NovelDialogSection>

        <NovelDialogSurface className="text-xs leading-relaxed text-book-text-muted">
          提示：如果两人关系会在不同阶段变化，先描述当前阶段；关键转折可在章节推进后继续回到这里修订。
        </NovelDialogSurface>
      </NovelDialogStack>
    </Modal>
  );
};
