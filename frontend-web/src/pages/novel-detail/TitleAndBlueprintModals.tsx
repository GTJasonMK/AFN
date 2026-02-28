import React from 'react';
import { Modal } from '../../components/ui/Modal';
import { BookButton } from '../../components/ui/BookButton';
import { BookCard } from '../../components/ui/BookCard';
import { BookInput, BookTextarea } from '../../components/ui/BookInput';

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
        <div className="space-y-4">
          <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
            说明：优化蓝图会重置已生成的章节大纲、章节内容以及向量库等后续数据。建议先导出/备份再执行。
          </div>

          <BookTextarea
            label="优化指令"
            value={refineInstruction}
            onChange={(e) => setRefineInstruction(e.target.value)}
            rows={6}
            placeholder="例如：把世界观从现代都市改为架空蒸汽朋克，并强化主角动机与成长线…"
          />

          <label className="flex items-center gap-2 text-sm text-book-text-main">
            <input
              type="checkbox"
              className="rounded border-book-border text-book-primary focus:ring-book-primary"
              checked={refineForce}
              onChange={(e) => setRefineForce(e.target.checked)}
            />
            <span className="font-bold">强制优化（存在后续数据时也继续）</span>
          </label>

          {refineResult && (
            <BookCard className="p-4">
              <div className="text-xs text-book-text-muted mb-2">AI 说明</div>
              <div className="text-sm text-book-text-main whitespace-pre-wrap leading-relaxed">
                {refineResult}
              </div>
            </BookCard>
          )}
        </div>
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
        <div className="space-y-4">
          <BookInput
            label="标题"
            value={editTitleValue}
            onChange={(e) => setEditTitleValue(e.target.value)}
            placeholder="请输入新标题"
            autoFocus
          />
          <div className="text-xs text-book-text-muted">
            提示：标题为项目基本信息（与蓝图字段独立）。桌面端同款入口位于标题旁“编辑”按钮。
          </div>
        </div>
      </Modal>
    </>
  );
};
