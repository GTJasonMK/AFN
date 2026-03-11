import React from 'react';
import { Modal } from '../../components/ui/Modal';
import { BookButton } from '../../components/ui/BookButton';
import { BookInput, BookTextarea } from '../../components/ui/BookInput';

type LatestChapterOutlineModalsProps = {
  regenerateModal: {
    isOpen: boolean;
    setOpen: (open: boolean) => void;
    regenerating: boolean;
    chapterOutlineCount: number;
    count: number;
    setCount: (value: number) => void;
    prompt: string;
    setPrompt: (value: string) => void;
    onConfirm: () => void | Promise<void>;
  };
  deleteModal: {
    isOpen: boolean;
    setOpen: (open: boolean) => void;
    deleting: boolean;
    chapterOutlineCount: number;
    count: number;
    setCount: (value: number) => void;
    onConfirm: () => void | Promise<void>;
  };
};

export const LatestChapterOutlineModals: React.FC<LatestChapterOutlineModalsProps> = ({
  regenerateModal,
  deleteModal,
}) => {
  const {
    isOpen: isRegenerateLatestModalOpen,
    setOpen: setIsRegenerateLatestModalOpen,
    regenerating: regeneratingLatest,
    chapterOutlineCount,
    count: regenerateLatestCount,
    setCount: setRegenerateLatestCount,
    prompt: regenerateLatestPrompt,
    setPrompt: setRegenerateLatestPrompt,
    onConfirm: handleRegenerateLatestOutlines,
  } = regenerateModal;
  const {
    isOpen: isDeleteLatestModalOpen,
    setOpen: setIsDeleteLatestModalOpen,
    deleting: deletingLatest,
    chapterOutlineCount: deleteModalChapterOutlineCount,
    count: deleteLatestCount,
    setCount: setDeleteLatestCount,
    onConfirm: handleDeleteLatestOutlines,
  } = deleteModal;

  return (
    <>
      <Modal
        isOpen={isRegenerateLatestModalOpen}
        onClose={() => setIsRegenerateLatestModalOpen(false)}
        title="重生成最新章节大纲"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton
              variant="ghost"
              onClick={() => setIsRegenerateLatestModalOpen(false)}
              disabled={regeneratingLatest}
            >
              取消
            </BookButton>
            <BookButton
              variant="primary"
              onClick={handleRegenerateLatestOutlines}
              disabled={regeneratingLatest || chapterOutlineCount <= 0}
            >
              {regeneratingLatest ? '重生成中…' : '重生成'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
            说明：该操作等价于桌面端“重新生成最新 N 个章节大纲”。实现方式为：从“最后 N 个大纲”中找到最早的那一章，重生成该章大纲，并按串行原则级联删除后续大纲。删除后如需补齐，可使用“批量生成章节大纲”继续生成。
          </div>

          <BookInput
            label={`重生成数量（1-${Math.max(1, chapterOutlineCount)})`}
            type="number"
            min={1}
            max={Math.max(1, chapterOutlineCount)}
            value={regenerateLatestCount}
            onChange={(e) => setRegenerateLatestCount(parseInt(e.target.value, 10) || 1)}
            disabled={regeneratingLatest}
          />

          <BookTextarea
            label="优化提示词（可选）"
            value={regenerateLatestPrompt}
            onChange={(e) => setRegenerateLatestPrompt(e.target.value)}
            rows={5}
            placeholder="留空则使用默认生成策略，例如：加强冲突、优化节奏、强化伏笔回收…"
            disabled={regeneratingLatest}
          />
        </div>
      </Modal>

      <Modal
        isOpen={isDeleteLatestModalOpen}
        onClose={() => setIsDeleteLatestModalOpen(false)}
        title="删除最新章节大纲"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={() => setIsDeleteLatestModalOpen(false)} disabled={deletingLatest}>
              取消
            </BookButton>
            <BookButton
              variant="primary"
              onClick={handleDeleteLatestOutlines}
              disabled={deletingLatest || deleteModalChapterOutlineCount <= 0}
            >
              {deletingLatest ? '删除中…' : '删除'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
            删除会从“最后一章”开始回退。若被删除章节已生成正文/评审/摘要/向量数据，将同时级联删除，避免后续生成引用到失效上下文。
          </div>
          <BookInput
            label={`删除数量（1-${Math.max(1, deleteModalChapterOutlineCount)})`}
            type="number"
            min={1}
            max={Math.max(1, deleteModalChapterOutlineCount)}
            value={deleteLatestCount}
            onChange={(e) => setDeleteLatestCount(parseInt(e.target.value, 10) || 1)}
            disabled={deletingLatest}
          />
        </div>
      </Modal>
    </>
  );
};
