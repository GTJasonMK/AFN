import React, { useCallback } from 'react';
import { Modal } from '../../components/ui/Modal';
import { BookButton } from '../../components/ui/BookButton';
import { BookTextarea } from '../../components/ui/BookInput';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';
import { useToast } from '../../components/feedback/Toast';

export const WritingNotesModal: React.FC<{
  isOpen: boolean;
  draft: string;
  onChangeDraft: (text: string) => void;
  onClose: () => void;
  onCommit: (text: string) => void;
}> = ({ isOpen, draft, onChangeDraft, onClose, onCommit }) => {
  const { addToast } = useToast();

  const handleClear = useCallback(async () => {
    const ok = await confirmDialog({
      title: '清空写作指导',
      message: '确定清空写作指导？',
      confirmText: '清空',
      dialogType: 'warning',
    });
    if (!ok) return;
    onChangeDraft('');
  }, [onChangeDraft]);

  const handleSave = useCallback(() => {
    const next = String(draft || '');
    onCommit(next);
    onClose();
    addToast(next.trim() ? '已更新写作指导' : '已清空写作指导', 'success');
  }, [addToast, draft, onClose, onCommit]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="写作指导（可选）"
      maxWidthClassName="max-w-2xl"
      footer={
        <div className="flex justify-end gap-2">
          <BookButton variant="ghost" onClick={onClose}>
            取消
          </BookButton>
          <BookButton variant="secondary" onClick={handleClear}>
            清空
          </BookButton>
          <BookButton variant="primary" onClick={handleSave}>
            保存
          </BookButton>
        </div>
      }
    >
      <div className="space-y-4">
        <BookTextarea
          label="写作指导"
          rows={10}
          value={draft}
          onChange={(e) => onChangeDraft(e.target.value)}
          placeholder="例如：本章重点描写主角内心变化，减少对话，多用动作推动剧情…"
        />
        <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 leading-relaxed">
          提示：写作指导会参与“提示词预览 / AI 续写 / RAG 检索”，用于控制本章写作方向。留空则按大纲与上下文自动生成。
        </div>
      </div>
    </Modal>
  );
};

