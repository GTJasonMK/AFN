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

type LatestPartOutlineModalsProps = {
  deleteModal: {
    isOpen: boolean;
    setOpen: (open: boolean) => void;
    deleting: boolean;
    maxDeletableCount: number;
    count: number;
    setCount: (value: number) => void;
    onConfirm: () => void | Promise<void>;
  };
  regenerateModal: {
    isOpen: boolean;
    setOpen: (open: boolean) => void;
    regenerating: boolean;
    partOutlineCount: number;
    count: number;
    setCount: (value: number) => void;
    prompt: string;
    setPrompt: (value: string) => void;
    onConfirm: () => void | Promise<void>;
  };
};

export const LatestPartOutlineModals: React.FC<LatestPartOutlineModalsProps> = ({
  deleteModal,
  regenerateModal,
}) => {
  const {
    isOpen: isDeleteLatestPartsModalOpen,
    setOpen: setIsDeleteLatestPartsModalOpen,
    deleting: deletingLatestParts,
    maxDeletableCount: maxDeletablePartCount,
    count: deleteLatestPartsCount,
    setCount: setDeleteLatestPartsCount,
    onConfirm: handleDeleteLatestPartOutlines,
  } = deleteModal;
  const {
    isOpen: isRegenerateLatestPartsModalOpen,
    setOpen: setIsRegenerateLatestPartsModalOpen,
    regenerating: regeneratingLatestParts,
    partOutlineCount,
    count: regenerateLatestPartsCount,
    setCount: setRegenerateLatestPartsCount,
    prompt: regenerateLatestPartsPrompt,
    setPrompt: setRegenerateLatestPartsPrompt,
    onConfirm: handleRegenerateLatestPartOutlines,
  } = regenerateModal;

  return (
    <>
      <Modal
        isOpen={isDeleteLatestPartsModalOpen}
        onClose={() => setIsDeleteLatestPartsModalOpen(false)}
        title="删除最新部分大纲"
        maxWidthClassName="max-w-xl"
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
        <NovelDialogStack>
          <NovelDialogIntro
            eyebrow="Delete Latest Parts"
            title="回退最近的部分结构"
            tone="danger"
            description="删除会从最后一个部分开始回退，并按串行生成原则级联移除对应范围内的章节大纲。后端会保留至少一个部分，避免结构被清空。"
          />

          <NovelDialogMetricGrid>
            <NovelDialogMetric
              label="最大可删"
              value={maxDeletablePartCount}
              note="系统至少保留 1 个部分大纲，防止整体结构失效。"
            />
            <NovelDialogMetric
              label="本次回退"
              value={deleteLatestPartsCount}
              note="建议逐次回退并检查对应章节大纲是否仍符合节奏规划。"
            />
          </NovelDialogMetricGrid>

          <NovelDialogSection
            eyebrow="Rollback"
            title="删除数量"
            description="删除后如需补齐，可重新生成部分大纲并继续向下扩写章节结构。"
          >
            <BookInput
              label={`删除数量（1-${Math.max(1, maxDeletablePartCount)})`}
              type="number"
              min={1}
              max={Math.max(1, maxDeletablePartCount)}
              value={deleteLatestPartsCount}
              onChange={(e) => setDeleteLatestPartsCount(parseInt(e.target.value, 10) || 1)}
              disabled={deletingLatestParts || maxDeletablePartCount <= 0}
            />
          </NovelDialogSection>
        </NovelDialogStack>
      </Modal>

      <Modal
        isOpen={isRegenerateLatestPartsModalOpen}
        onClose={() => setIsRegenerateLatestPartsModalOpen(false)}
        title="重生成最新部分大纲"
        maxWidthClassName="max-w-2xl"
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
              disabled={regeneratingLatestParts || partOutlineCount <= 0}
            >
              {regeneratingLatestParts ? '重生成中…' : '重生成'}
            </BookButton>
          </div>
        }
      >
        <NovelDialogStack>
          <NovelDialogIntro
            eyebrow="Regenerate Latest Parts"
            title="回退并重建最近部分"
            tone="warning"
            description="系统会从最近 N 个部分中最早的一部分重新起算，并联动清理其后的部分、章节大纲、正文与向量数据。"
          >
            <div className="flex flex-wrap gap-2">
              <span className="story-pill">现有部分 {partOutlineCount}</span>
              <span className="story-pill">支持追加优化提示词</span>
            </div>
          </NovelDialogIntro>

          <NovelDialogMetricGrid>
            <NovelDialogMetric
              label="现有部分"
              value={partOutlineCount}
              note="重生成范围只能落在已存在的部分大纲之内。"
            />
            <NovelDialogMetric
              label="本次重生成"
              value={regenerateLatestPartsCount}
              note="会从最近 N 个部分里最早的一部分重新向后生成。"
            />
          </NovelDialogMetricGrid>

          <NovelDialogSection
            eyebrow="Scope"
            title="重生成范围"
            description="先确认需要回退的部分数量，再决定是否提供补充提示词。"
          >
            <div className="space-y-4">
              <BookInput
                label={`重生成数量（1-${Math.max(1, partOutlineCount)})`}
                type="number"
                min={1}
                max={Math.max(1, partOutlineCount)}
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
          </NovelDialogSection>

          <NovelDialogSurface className="text-xs leading-relaxed text-book-text-muted">
            提示：如果只是补充后续部分，优先使用“继续生成部分大纲”；只有当前结构整体失真时再考虑回退重生。
          </NovelDialogSurface>
        </NovelDialogStack>
      </Modal>
    </>
  );
};
