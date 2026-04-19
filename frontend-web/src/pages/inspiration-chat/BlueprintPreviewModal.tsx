import React from 'react';
import { Modal } from '../../components/ui/Modal';
import { BookButton } from '../../components/ui/BookButton';
import {
  NovelDialogIntro,
  NovelDialogMetric,
  NovelDialogMetricGrid,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from '../../components/business/novel/NovelDialogPrimitives';

type BlueprintPreviewModalProps = {
  isOpen: boolean;
  mode: 'novel' | 'coding';
  showBlueprintBtn: boolean;
  blueprintPreview: any | null;
  blueprintTip: string | null;
  isGeneratingBlueprint: boolean;
  onClose: () => void;
  onRegenerate: () => void | Promise<void>;
  onConfirm: () => void | Promise<void>;
};

export const BlueprintPreviewModal: React.FC<BlueprintPreviewModalProps> = ({
  isOpen,
  mode,
  showBlueprintBtn,
  blueprintPreview,
  blueprintTip,
  isGeneratingBlueprint,
  onClose,
  onRegenerate,
  onConfirm,
}) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="蓝图预览与确认"
      maxWidthClassName="max-w-3xl"
      footer={
        <>
          <BookButton variant="ghost" onClick={onClose} disabled={isGeneratingBlueprint}>
            返回对话
          </BookButton>
          <BookButton variant="secondary" onClick={onRegenerate} disabled={isGeneratingBlueprint}>
            {isGeneratingBlueprint ? '重新生成中…' : '重新生成'}
          </BookButton>
          {blueprintPreview && typeof blueprintPreview === 'object' ? (
            <BookButton variant="primary" onClick={onConfirm}>
              确认并继续
            </BookButton>
          ) : null}
        </>
      }
    >
      <NovelDialogStack>
        <NovelDialogIntro
          eyebrow={mode === 'novel' ? 'Story Blueprint' : 'System Blueprint'}
          title={mode === 'novel' ? '确认故事蓝图' : '确认架构蓝图'}
          description={
            mode === 'novel'
              ? '先快速判断作品名和一句话摘要是否对得上你的设想，再决定是否回到对话继续压实。'
              : '先确认系统类型和一句话摘要是否准确，再决定是否回到对话继续澄清。'
          }
        >
          <div className="flex flex-wrap gap-2">
            <span className="story-pill">{mode === 'novel' ? '对话已压缩成故事蓝图' : '对话已压缩成系统方案'}</span>
            {showBlueprintBtn ? <span className="story-pill">可继续下一阶段</span> : null}
          </div>
        </NovelDialogIntro>

        {blueprintTip ? (
          <NovelDialogSurface className="text-sm leading-relaxed text-book-text-sub">
            {blueprintTip}
          </NovelDialogSurface>
        ) : null}

        <NovelDialogMetricGrid>
          <NovelDialogMetric
            label={mode === 'novel' ? '标题 / 类型' : '系统类型'}
            value={
              mode === 'novel'
                ? String(blueprintPreview?.title || '（未命名）')
                : String(blueprintPreview?.project_type_desc || '（未设置项目类型）')
            }
            note={mode === 'novel' ? '先确认作品名是否贴合这轮灵感收敛结果。' : '先确认系统定位是否准确。'}
          />
          <NovelDialogMetric
            label="一句话摘要"
            value={String(
              blueprintPreview?.one_sentence_summary || blueprintPreview?.summary || '（暂无一句话概要）',
            )}
            note="这是判断是否进入下一阶段的最快速参考。"
          />
        </NovelDialogMetricGrid>

        <NovelDialogSection
          eyebrow="Summary"
          title="蓝图摘要"
          description="这里展示当前蓝图的压缩摘要，适合快速决定是确认还是重生。"
        >
          <NovelDialogSurface>
            {mode === 'novel' ? (
              <div className="space-y-2 text-sm text-book-text-main">
                <div className="font-serif text-lg font-bold">
                  {String(blueprintPreview?.title || '（未命名）')}
                </div>
                <div className="italic text-book-text-sub">
                  {String(blueprintPreview?.one_sentence_summary || '（暂无一句话概要）')}
                </div>
              </div>
            ) : (
              <div className="space-y-2 text-sm text-book-text-main">
                <div className="font-serif text-lg font-bold">
                  {String(blueprintPreview?.project_type_desc || '（未设置项目类型）')}
                </div>
                <div className="italic text-book-text-sub">
                  {String(
                    blueprintPreview?.one_sentence_summary ||
                      blueprintPreview?.summary ||
                      '（暂无一句话概要）',
                  )}
                </div>
              </div>
            )}
          </NovelDialogSurface>
        </NovelDialogSection>

        <details className="rounded-xl border border-book-border/45 bg-book-bg-paper/80">
          <summary className="cursor-pointer select-none px-5 py-4 text-sm font-semibold text-book-text-main">
            查看完整蓝图（JSON）
          </summary>
          <div className="px-5 pb-5">
            <NovelDialogSurface className="max-h-[22rem] overflow-auto custom-scrollbar">
              <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-book-text-main">
                {(() => {
                  try {
                    return JSON.stringify(blueprintPreview || {}, null, 2);
                  } catch {
                    return String(blueprintPreview ?? '');
                  }
                })()}
              </pre>
            </NovelDialogSurface>
          </div>
        </details>
      </NovelDialogStack>
    </Modal>
  );
};
