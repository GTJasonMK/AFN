import React from 'react';
import { Modal } from '../../components/ui/Modal';
import { BookButton } from '../../components/ui/BookButton';
import { BookInput, BookTextarea } from '../../components/ui/BookInput';

type LatestPartOutlineModalsProps = {
  isDeleteLatestPartsModalOpen: boolean;
  setIsDeleteLatestPartsModalOpen: (open: boolean) => void;
  deletingLatestParts: boolean;
  maxDeletablePartCount: number;
  handleDeleteLatestPartOutlines: () => void | Promise<void>;
  deleteLatestPartsCount: number;
  setDeleteLatestPartsCount: (value: number) => void;
  isRegenerateLatestPartsModalOpen: boolean;
  setIsRegenerateLatestPartsModalOpen: (open: boolean) => void;
  regeneratingLatestParts: boolean;
  partOutlines: any[];
  handleRegenerateLatestPartOutlines: () => void | Promise<void>;
  regenerateLatestPartsCount: number;
  setRegenerateLatestPartsCount: (value: number) => void;
  regenerateLatestPartsPrompt: string;
  setRegenerateLatestPartsPrompt: (value: string) => void;
};

export const LatestPartOutlineModals: React.FC<LatestPartOutlineModalsProps> = ({
  isDeleteLatestPartsModalOpen,
  setIsDeleteLatestPartsModalOpen,
  deletingLatestParts,
  maxDeletablePartCount,
  handleDeleteLatestPartOutlines,
  deleteLatestPartsCount,
  setDeleteLatestPartsCount,
  isRegenerateLatestPartsModalOpen,
  setIsRegenerateLatestPartsModalOpen,
  regeneratingLatestParts,
  partOutlines,
  handleRegenerateLatestPartOutlines,
  regenerateLatestPartsCount,
  setRegenerateLatestPartsCount,
  regenerateLatestPartsPrompt,
  setRegenerateLatestPartsPrompt,
}) => {
  return (
    <>
      <Modal
        isOpen={isDeleteLatestPartsModalOpen}
        onClose={() => setIsDeleteLatestPartsModalOpen(false)}
        title="删除最新部分大纲"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton
              variant="ghost"
              onClick={() => setIsDeleteLatestPartsModalOpen(false)}
              disabled={deletingLatestParts}
            >
              取消
            </BookButton>
            <BookButton
              variant="primary"
              onClick={handleDeleteLatestPartOutlines}
              disabled={deletingLatestParts || maxDeletablePartCount <= 0}
            >
              {deletingLatestParts ? '删除中…' : '删除'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
            删除会从“最后一个部分”开始回退，并按“串行生成原则”级联删除对应范围的章节大纲。后端禁止删除全部部分大纲（至少保留 1 个部分）。
          </div>
          <BookInput
            label={`删除数量（1-${Math.max(1, maxDeletablePartCount)})`}
            type="number"
            min={1}
            max={Math.max(1, maxDeletablePartCount)}
            value={deleteLatestPartsCount}
            onChange={(e) => setDeleteLatestPartsCount(parseInt(e.target.value, 10) || 1)}
            disabled={deletingLatestParts || maxDeletablePartCount <= 0}
          />
        </div>
      </Modal>

      <Modal
        isOpen={isRegenerateLatestPartsModalOpen}
        onClose={() => setIsRegenerateLatestPartsModalOpen(false)}
        title="重生成最新部分大纲"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton
              variant="ghost"
              onClick={() => setIsRegenerateLatestPartsModalOpen(false)}
              disabled={regeneratingLatestParts}
            >
              取消
            </BookButton>
            <BookButton
              variant="primary"
              onClick={handleRegenerateLatestPartOutlines}
              disabled={regeneratingLatestParts || !partOutlines.length}
            >
              {regeneratingLatestParts ? '重生成中…' : '重生成'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
            说明：该操作等价于桌面端“重新生成最新 N 个部分大纲”。实现方式为：从“最后 N 个部分”中找到最早的那一部分，重生成该部分大纲，并按串行原则级联删除后续部分与对应章节大纲/内容/向量数据。
          </div>

          <BookInput
            label={`重生成数量（1-${Math.max(1, partOutlines.length)})`}
            type="number"
            min={1}
            max={Math.max(1, partOutlines.length)}
            value={regenerateLatestPartsCount}
            onChange={(e) => setRegenerateLatestPartsCount(parseInt(e.target.value, 10) || 1)}
            disabled={regeneratingLatestParts}
          />

          <BookTextarea
            label="优化提示词（可选）"
            value={regenerateLatestPartsPrompt}
            onChange={(e) => setRegenerateLatestPartsPrompt(e.target.value)}
            rows={5}
            placeholder="留空则使用默认生成策略，例如：优化节奏、强化冲突、提升转折密度…"
            disabled={regeneratingLatestParts}
          />
        </div>
      </Modal>
    </>
  );
};
