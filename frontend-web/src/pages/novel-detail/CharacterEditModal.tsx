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
} from '../../components/business/novel/NovelDialogPrimitives';

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
  const isEditing = editingIndex !== null;
  const relationshipWithProtagonist = String(charForm.relationship_with_protagonist || '').trim();

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => setOpen(false)}
      title={isEditing ? '编辑角色' : '添加新角色'}
      maxWidthClassName="max-w-2xl"
      footer={
        <div className="flex justify-end gap-2">
          <BookButton variant="ghost" onClick={() => setOpen(false)}>取消</BookButton>
          <BookButton variant="primary" onClick={onSave}>保存</BookButton>
        </div>
      }
    >
      <NovelDialogStack>
        <NovelDialogIntro
          eyebrow="Character Sheet"
          title={isEditing ? '修订角色卡' : '建立新角色'}
          description="角色资料会参与蓝图设定、章节生成和关系网推导。先补全基础身份，再补充性格、目标和与主角的互动位置。"
        >
          <div className="flex flex-wrap gap-2">
            <span className="story-pill">{isEditing ? '编辑现有角色' : '创建角色条目'}</span>
            {relationshipWithProtagonist ? <span className="story-pill">{relationshipWithProtagonist}</span> : null}
          </div>
        </NovelDialogIntro>

        <NovelDialogMetricGrid>
          <NovelDialogMetric
            label="当前模式"
            value={isEditing ? '编辑中' : '新建'}
            note={isEditing ? '建议重点修订身份定位与成长目标。' : '先录入最小可用信息，后续可继续补充。'}
          />
          <NovelDialogMetric
            label="主角关系"
            value={relationshipWithProtagonist || '待补充'}
            note="这项信息会直接影响人物关系图和提示词中的互动约束。"
          />
        </NovelDialogMetricGrid>

        <NovelDialogSection
          eyebrow="Core"
          title="基础角色信息"
          description="先明确名字、身份、性格和核心目标，保证角色在后续生成中有稳定锚点。"
        >
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
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
            </div>

            <BookTextarea
              label="性格特征"
              value={charForm.personality || ''}
              onChange={(e) => setCharForm((prev: any) => ({ ...prev, personality: e.target.value }))}
              rows={4}
              placeholder="例如：克制寡言、极端护短、对规则高度敏感…"
            />

            <BookTextarea
              label="目标与动机"
              value={charForm.goal || ''}
              onChange={(e) => setCharForm((prev: any) => ({ ...prev, goal: e.target.value }))}
              rows={4}
              placeholder="例如：寻找失踪亲人、洗刷冤案、守住家族秘密…"
            />
          </div>
        </NovelDialogSection>

        <NovelDialogSection
          eyebrow="Depth"
          title="延展设定"
          description="这些信息用于丰富人物张力和长期行为逻辑，不确定时可先留空，后续迭代补足。"
        >
          <div className="space-y-4">
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
              placeholder="例如：盟友 / 对手 / 师徒 / 亲属 / 互相利用…"
            />
          </div>
        </NovelDialogSection>
      </NovelDialogStack>
    </Modal>
  );
};
