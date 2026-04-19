import React from 'react';
import { Eye, Search } from 'lucide-react';
import { BookButton } from '../../ui/BookButton';
import { Modal } from '../../ui/Modal';
import {
  NovelDialogIntro,
  NovelDialogMetric,
  NovelDialogMetricGrid,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from '../novel/NovelDialogPrimitives';
import { buildSimpleInlineDiff, type Suggestion } from './shared';

interface OptimizationSuggestionPreviewModalProps {
  previewSuggestion: Suggestion | null;
  previewApplied: boolean;
  canEdit: boolean;
  onClose: () => void;
  onPreviewToEditor: () => void;
  onApplyToEditor: () => void;
  onLocateText?: (text: string) => void;
}

export const OptimizationSuggestionPreviewModal: React.FC<
  OptimizationSuggestionPreviewModalProps
> = ({
  previewSuggestion,
  previewApplied,
  canEdit,
  onClose,
  onPreviewToEditor,
  onApplyToEditor,
  onLocateText,
}) => {
  return (
    <Modal
      isOpen={Boolean(previewSuggestion)}
      onClose={onClose}
      title={
        previewSuggestion
          ? `预览建议：段落 ${previewSuggestion.paragraph_index + 1} · ${previewSuggestion.category}`
          : '预览建议'
      }
      maxWidthClassName="max-w-4xl"
      footer={
        <div className="flex justify-end gap-2">
          {previewSuggestion &&
          onLocateText &&
          (previewSuggestion.original_text || '').trim() ? (
            <BookButton
              variant="secondary"
              onClick={() => onLocateText(previewSuggestion.original_text)}
              title="在编辑器中定位原文片段"
            >
              <Search size={14} className="mr-1" />
              定位原文
            </BookButton>
          ) : null}
          {previewSuggestion && canEdit ? (
            <BookButton
              variant="secondary"
              onClick={onPreviewToEditor}
              title="在编辑器中预览（确认/撤销）"
            >
              <Eye size={14} className="mr-1" />
              预览到编辑器
            </BookButton>
          ) : null}
          <BookButton variant="ghost" onClick={onClose}>
            关闭
          </BookButton>
          <BookButton
            variant="primary"
            onClick={onApplyToEditor}
            disabled={!previewSuggestion || !canEdit || previewApplied}
          >
            {previewApplied ? '已应用' : '应用到编辑器'}
          </BookButton>
        </div>
      }
    >
      {previewSuggestion ? (
        <NovelDialogStack>
          <NovelDialogIntro
            eyebrow="Optimization Preview"
            title={`段落 ${previewSuggestion.paragraph_index + 1} 的建议预览`}
            description="先看差异高亮，再决定是直接应用，还是先把建议投射到编辑器里做一次临时预览。"
          >
            <div className="flex flex-wrap gap-2">
              <span className="story-pill">{previewSuggestion.category}</span>
              <span className="story-pill">
                {previewApplied ? '该建议已应用' : '尚未应用'}
              </span>
            </div>
          </NovelDialogIntro>

          <NovelDialogMetricGrid>
            <NovelDialogMetric
              label="原文长度"
              value={previewSuggestion.original_text.length}
              note="按字符数统计，用于快速判断本次修改片段规模。"
            />
            <NovelDialogMetric
              label="建议长度"
              value={previewSuggestion.suggested_text.length}
              note="如果建议明显更短或更长，建议先预览到编辑器再决定。"
            />
          </NovelDialogMetricGrid>

          {previewSuggestion.reason ? (
            <NovelDialogSurface className="whitespace-pre-wrap text-xs leading-relaxed text-book-text-muted">
              理由：{previewSuggestion.reason}
            </NovelDialogSurface>
          ) : null}

          <NovelDialogSection
            eyebrow="Diff"
            title="差异高亮"
            description="红色表示删除，绿色表示新增，用来快速判断本次建议的改动密度。"
          >
            <NovelDialogSurface className="max-h-[30vh] overflow-auto">
              <div className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-book-text-main">
                {buildSimpleInlineDiff(
                  previewSuggestion.original_text,
                  previewSuggestion.suggested_text
                ).map((segment, index) => (
                  <span
                    key={`preview-dialog-diff-${index}`}
                    className={
                      segment.type === 'remove'
                        ? 'bg-red-500/10 text-red-700 line-through'
                        : segment.type === 'add'
                          ? 'bg-green-500/10 text-green-700'
                          : ''
                    }
                  >
                    {segment.text}
                  </span>
                ))}
              </div>
            </NovelDialogSurface>
          </NovelDialogSection>

          <NovelDialogSection
            eyebrow="Compare"
            title="原文与建议对照"
            description="左右对照查看语言密度、信息遗漏和节奏变化。"
          >
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <NovelDialogSurface>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                  Original
                </div>
                <pre className="mt-3 max-h-[60vh] overflow-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-book-text-main">
                  {previewSuggestion.original_text}
                </pre>
              </NovelDialogSurface>
              <NovelDialogSurface>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                  Suggested
                </div>
                <pre className="mt-3 max-h-[60vh] overflow-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-book-text-main">
                  {previewSuggestion.suggested_text}
                </pre>
              </NovelDialogSurface>
            </div>
          </NovelDialogSection>

          <NovelDialogSurface className="text-xs leading-relaxed text-book-text-muted">
            提示：应用后可在面板顶部点击“撤销”恢复到上一次应用前的正文。
          </NovelDialogSurface>
        </NovelDialogStack>
      ) : null}
    </Modal>
  );
};
