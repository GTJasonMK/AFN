import React from 'react';
import { CheckCircle2, Search, Undo2 } from 'lucide-react';
import { BookButton } from '../../ui/BookButton';
import { BookCard } from '../../ui/BookCard';
import {
  buildSimpleInlineDiff,
  type InlinePreviewState,
} from './shared';

interface ContentOptimizationInlinePreviewCardProps {
  inlinePreview: InlinePreviewState;
  onSelectRange?: (start: number, end: number) => void;
  onRevert: () => void;
  onConfirm: () => void;
}

export const ContentOptimizationInlinePreviewCard: React.FC<
  ContentOptimizationInlinePreviewCardProps
> = ({ inlinePreview, onSelectRange, onRevert, onConfirm }) => {
  return (
    <BookCard className="border border-book-accent/30 bg-book-bg-paper p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-bold text-book-text-main">
            正在预览：{inlinePreview.label}
          </div>
          <div className="mt-1 text-xs leading-relaxed text-book-text-muted">
            预览会直接修改编辑器内容；请尽快“确认/撤销”。如需手动编辑，
            建议先确认后再改，避免撤销覆盖。
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {onSelectRange && inlinePreview.range ? (
            <BookButton
              variant="ghost"
              size="sm"
              onClick={() =>
                onSelectRange(
                  inlinePreview.range!.start,
                  inlinePreview.range!.end
                )
              }
              title="重新定位到修改位置"
            >
              <Search size={14} className="mr-1" />
              定位
            </BookButton>
          ) : null}
          <BookButton variant="ghost" size="sm" onClick={onRevert}>
            <Undo2 size={14} className="mr-1" />
            撤销预览
          </BookButton>
          <BookButton variant="primary" size="sm" onClick={onConfirm}>
            <CheckCircle2 size={14} className="mr-1" />
            确认应用
          </BookButton>
        </div>
      </div>

      <div className="mt-3 text-xs">
        <div className="mb-1 text-[11px] text-book-text-muted">差异高亮</div>
        <div className="whitespace-pre-wrap rounded-lg border border-book-border/40 bg-book-bg p-3 font-mono leading-relaxed text-book-text-main">
          {buildSimpleInlineDiff(
            inlinePreview.suggestion.original_text,
            inlinePreview.suggestion.suggested_text
          ).map((segment, index) => (
            <span
              key={`inline-preview-diff-${index}`}
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
      </div>
    </BookCard>
  );
};
