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
        maxWidthClassName="max-w-2xl"
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
        <NovelDialogStack>
          <NovelDialogIntro
            eyebrow="Regenerate Latest"
            title="回退并重建最新章节大纲"
            tone="warning"
            description="系统会定位最近 N 个章节大纲中最早的一章，从那里重新生成，并按串行生成原则移除其后的章节大纲。"
          >
            <div className="flex flex-wrap gap-2">
              <span className="story-pill">可用章节大纲 {chapterOutlineCount}</span>
              <span className="story-pill">支持附加优化提示词</span>
            </div>
          </NovelDialogIntro>

          <NovelDialogMetricGrid>
            <NovelDialogMetric
              label="现有大纲"
              value={chapterOutlineCount}
              note="只能在已有章节大纲的范围内回退和重生。"
            />
            <NovelDialogMetric
              label="本次重生成"
              value={regenerateLatestCount}
              note="系统会从最近 N 章中最早的一章重新起算。"
            />
          </NovelDialogMetricGrid>

          <NovelDialogSection
            eyebrow="Scope"
            title="重生成范围"
            description="先确认需要回退几章，再决定是否补充额外优化指令。"
          >
            <div className="space-y-4">
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
          </NovelDialogSection>

          <NovelDialogSurface className="text-xs leading-relaxed text-book-text-muted">
            提示：删除后若需要补齐后续章节，可回到章节大纲面板使用“批量生成章节大纲”继续向后生成。
          </NovelDialogSurface>
        </NovelDialogStack>
      </Modal>

      <Modal
        isOpen={isDeleteLatestModalOpen}
        onClose={() => setIsDeleteLatestModalOpen(false)}
        title="删除最新章节大纲"
        maxWidthClassName="max-w-xl"
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
        <NovelDialogStack>
          <NovelDialogIntro
            eyebrow="Delete Latest"
            title="回退最新章节大纲"
            tone="danger"
            description="删除会从最后一章开始回退，并联动清理依附其上的正文、评审、摘要与向量数据，避免后续链路引用失效上下文。"
          />

          <NovelDialogMetricGrid>
            <NovelDialogMetric
              label="可删除大纲"
              value={deleteModalChapterOutlineCount}
              note="删除会从最新一章开始，按顺序向前回退。"
            />
            <NovelDialogMetric
              label="本次删除"
              value={deleteLatestCount}
              note="建议小步回退，逐次确认结构变更是否符合预期。"
            />
          </NovelDialogMetricGrid>

          <NovelDialogSection
            eyebrow="Rollback"
            title="删除范围"
            description="删除后不可在前端直接恢复，建议先确认最近生成链路是否需要保留。"
          >
            <BookInput
              label={`删除数量（1-${Math.max(1, deleteModalChapterOutlineCount)})`}
              type="number"
              min={1}
              max={Math.max(1, deleteModalChapterOutlineCount)}
              value={deleteLatestCount}
              onChange={(e) => setDeleteLatestCount(parseInt(e.target.value, 10) || 1)}
              disabled={deletingLatest}
            />
          </NovelDialogSection>
        </NovelDialogStack>
      </Modal>
    </>
  );
};
