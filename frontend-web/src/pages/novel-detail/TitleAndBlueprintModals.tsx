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

type TitleAndBlueprintModalsProps = {
  isRefineModalOpen: boolean;
  closeRefineModal: () => void;
  handleRefineBlueprint: () => void | Promise<void>;
  refining: boolean;
  refineInstruction: string;
  setRefineInstruction: (value: string) => void;
  refineForce: boolean;
  setRefineForce: (value: boolean) => void;
  refineResult: string | null;
  isEditTitleModalOpen: boolean;
  closeEditTitleModal: () => void;
  editTitleSaving: boolean;
  saveProjectTitle: () => void | Promise<void>;
  editTitleValue: string;
  setEditTitleValue: (value: string) => void;
};

export const TitleAndBlueprintModals: React.FC<TitleAndBlueprintModalsProps> = ({
  isRefineModalOpen,
  closeRefineModal,
  handleRefineBlueprint,
  refining,
  refineInstruction,
  setRefineInstruction,
  refineForce,
  setRefineForce,
  refineResult,
  isEditTitleModalOpen,
  closeEditTitleModal,
  editTitleSaving,
  saveProjectTitle,
  editTitleValue,
  setEditTitleValue,
}) => {
  return (
    <>
      <Modal
        isOpen={isRefineModalOpen}
        onClose={closeRefineModal}
        title="优化蓝图"
        maxWidthClassName="max-w-2xl"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={closeRefineModal}>关闭</BookButton>
            <BookButton
              variant="primary"
              onClick={handleRefineBlueprint}
              disabled={refining || !refineInstruction.trim()}
            >
              {refining ? '优化中...' : '开始优化'}
            </BookButton>
          </div>
        }
      >
        <NovelDialogStack>
          <NovelDialogIntro
            eyebrow="Blueprint Refine"
            title="重写故事蓝图方向"
            tone="warning"
            description="蓝图优化会重新定义故事设定，并清空依赖旧蓝图生成的后续内容。建议先导出或备份，再执行高影响改写。"
          >
            <div className="flex flex-wrap gap-2">
              <span className="story-pill">高影响操作</span>
              <span className="story-pill">{refineForce ? '已启用强制优化' : '默认安全模式'}</span>
            </div>
          </NovelDialogIntro>

          <NovelDialogMetricGrid>
            <NovelDialogMetric
              label="影响范围"
              value="蓝图后续链路"
              note="已生成的章节大纲、章节正文与向量库数据会被重置。"
            />
            <NovelDialogMetric
              label="执行模式"
              value={refineForce ? '强制' : '常规'}
              note={refineForce ? '即使存在后续数据也继续执行。' : '建议确认备份后再提交。'}
            />
          </NovelDialogMetricGrid>

          <NovelDialogSection
            eyebrow="Instruction"
            title="优化指令"
            description="用自然语言描述这次蓝图改写的目标，例如世界观迁移、人物动机强化或主线冲突重构。"
          >
            <BookTextarea
              label="优化指令"
              value={refineInstruction}
              onChange={(e) => setRefineInstruction(e.target.value)}
              rows={6}
              placeholder="例如：把世界观从现代都市改为架空蒸汽朋克，并强化主角动机与成长线…"
            />
          </NovelDialogSection>

          <NovelDialogSurface className="space-y-3">
            <label className="flex items-start gap-3 text-sm text-book-text-main">
              <input
                type="checkbox"
                className="mt-0.5 rounded border-book-border text-book-primary focus:ring-book-primary"
                checked={refineForce}
                onChange={(e) => setRefineForce(e.target.checked)}
              />
              <span className="leading-relaxed">
                <span className="font-bold">强制优化</span>
                <span className="ml-2 text-book-text-sub">存在后续数据时也继续执行，适合已确认要整体推翻旧结构的场景。</span>
              </span>
            </label>
          </NovelDialogSurface>

          {refineResult ? (
            <NovelDialogSection
              eyebrow="AI Note"
              title="AI 说明"
              description="以下内容用于帮助你判断这次蓝图修订是否符合预期。"
            >
              <NovelDialogSurface className="whitespace-pre-wrap text-sm leading-relaxed text-book-text-main">
                {refineResult}
              </NovelDialogSurface>
            </NovelDialogSection>
          ) : null}
        </NovelDialogStack>
      </Modal>

      <Modal
        isOpen={isEditTitleModalOpen}
        onClose={closeEditTitleModal}
        title="编辑项目标题"
        maxWidthClassName="max-w-lg"
        footer={
          <>
            <BookButton
              variant="ghost"
              onClick={closeEditTitleModal}
              disabled={editTitleSaving}
            >
              取消
            </BookButton>
            <BookButton
              variant="primary"
              onClick={saveProjectTitle}
              disabled={editTitleSaving || !editTitleValue.trim()}
            >
              {editTitleSaving ? '保存中…' : '保存'}
            </BookButton>
          </>
        }
      >
        <NovelDialogStack>
          <NovelDialogIntro
            eyebrow="Project Title"
            title="更新项目标题"
            description="项目标题是作品对外展示的基础信息，与蓝图内的书名字段相互独立。这里修改的是项目壳层名称。"
          />

          <NovelDialogSection
            eyebrow="Identity"
            title="标题信息"
            description="标题会出现在项目列表、详情页头部和路由入口中，建议保持简洁、明确且易于识别。"
          >
            <BookInput
              label="标题"
              value={editTitleValue}
              onChange={(e) => setEditTitleValue(e.target.value)}
              placeholder="请输入新标题"
              autoFocus
            />
          </NovelDialogSection>

          <NovelDialogSurface className="text-xs leading-relaxed text-book-text-muted">
            提示：标题仅影响项目基本信息，不会自动改写蓝图中的作品名、卷名或章节内容。
          </NovelDialogSurface>
        </NovelDialogStack>
      </Modal>
    </>
  );
};
