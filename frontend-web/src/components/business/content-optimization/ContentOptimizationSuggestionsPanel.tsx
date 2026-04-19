import React from 'react';
import {
  CheckCircle2,
  Copy,
  Eye,
  ListChecks,
  Search,
  Undo2,
} from 'lucide-react';
import { BookButton } from '../../ui/BookButton';
import { BookCard } from '../../ui/BookCard';
import {
  getSuggestionKey,
  priorityColor,
  type Suggestion,
  type UndoSnapshot,
} from './shared';

interface ContentOptimizationSuggestionsPanelProps {
  suggestions: Suggestion[];
  appliedSet: ReadonlySet<string>;
  inlinePreviewKey: string | null;
  lastUndo: UndoSnapshot | null;
  undoStackLength: number;
  canEdit: boolean;
  onUndoLastApply: () => void;
  onStartInlinePreview: (suggestion: Suggestion) => void;
  onOpenPreview: (suggestion: Suggestion) => void;
  onApplySuggestion: (suggestion: Suggestion) => void;
  onConfirmInlinePreview: () => void;
  onCopySuggestion: (suggestion: Suggestion) => void;
  onLocateText?: (text: string) => void;
}

export const ContentOptimizationSuggestionsPanel: React.FC<
  ContentOptimizationSuggestionsPanelProps
> = ({
  suggestions,
  appliedSet,
  inlinePreviewKey,
  lastUndo,
  undoStackLength,
  canEdit,
  onUndoLastApply,
  onStartInlinePreview,
  onOpenPreview,
  onApplySuggestion,
  onConfirmInlinePreview,
  onCopySuggestion,
  onLocateText,
}) => {
  return (
    <BookCard className="p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="font-bold text-book-text-main">建议列表</div>
        <div className="flex items-center gap-2">
          {lastUndo && canEdit ? (
            <BookButton
              variant="ghost"
              size="sm"
              onClick={onUndoLastApply}
              title={`撤销上次应用：${lastUndo.label}`}
            >
              <Undo2 size={14} className="mr-1" />
              撤销{undoStackLength > 1 ? `（${undoStackLength}）` : ''}
            </BookButton>
          ) : null}
          <div className="text-xs text-book-text-muted">
            共 {suggestions.length} 条
          </div>
        </div>
      </div>

      {suggestions.length === 0 ? (
        <div className="text-xs leading-relaxed text-book-text-muted">
          开始优化后，这里会显示修改建议。
        </div>
      ) : (
        <div className="space-y-3">
          {suggestions.map((suggestion, index) => {
            const key = getSuggestionKey(suggestion);
            const applied = appliedSet.has(key);
            const previewing = inlinePreviewKey === key;

            return (
              <div
                key={`content-optimization-suggestion-${key}-${index}`}
                className="rounded-lg border border-book-border/40 bg-book-bg p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="text-xs font-bold text-book-text-main">
                    段落 {suggestion.paragraph_index + 1} · {suggestion.category}
                    <span
                      className={`ml-2 ${
                        priorityColor[suggestion.priority] ||
                        'text-book-text-muted'
                      }`}
                    >
                      {suggestion.priority}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <BookButton
                      variant="ghost"
                      size="sm"
                      onClick={() => onStartInlinePreview(suggestion)}
                      disabled={previewing}
                      title="在编辑器中预览（确认/撤销）"
                    >
                      <Eye size={14} className="mr-1" />
                      {previewing ? '预览中' : '预览'}
                    </BookButton>
                    <BookButton
                      variant="ghost"
                      size="sm"
                      onClick={() => onOpenPreview(suggestion)}
                      title="打开对比预览"
                    >
                      <ListChecks size={14} className="mr-1" />
                      对比
                    </BookButton>
                    {onLocateText && (suggestion.original_text || '').trim() ? (
                      <BookButton
                        variant="ghost"
                        size="sm"
                        onClick={() => onLocateText(suggestion.original_text)}
                        title="在编辑器中定位原文片段"
                      >
                        <Search size={14} className="mr-1" />
                        定位
                      </BookButton>
                    ) : null}
                    <BookButton
                      variant="secondary"
                      size="sm"
                      onClick={() =>
                        previewing
                          ? onConfirmInlinePreview()
                          : onApplySuggestion(suggestion)
                      }
                      disabled={(!previewing && applied) || !canEdit}
                    >
                      <CheckCircle2 size={14} className="mr-1" />
                      {previewing ? '确认' : applied ? '已应用' : '应用'}
                    </BookButton>
                    <BookButton
                      variant="ghost"
                      size="sm"
                      onClick={() => onCopySuggestion(suggestion)}
                      title="复制建议文本"
                    >
                      <Copy size={14} className="mr-1" />
                      复制
                    </BookButton>
                  </div>
                </div>

                {suggestion.reason ? (
                  <div className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-book-text-muted">
                    理由：{suggestion.reason}
                  </div>
                ) : null}

                <div className="mt-3 grid grid-cols-1 gap-2">
                  <div className="text-xs">
                    <div className="mb-1 text-[11px] text-book-text-muted">
                      原文
                    </div>
                    <div className="whitespace-pre-wrap rounded border border-book-border/40 bg-book-bg-paper p-2 leading-relaxed text-book-text-main">
                      {suggestion.original_text}
                    </div>
                  </div>
                  <div className="text-xs">
                    <div className="mb-1 text-[11px] text-book-text-muted">
                      建议
                    </div>
                    <div className="whitespace-pre-wrap rounded border border-book-border/40 bg-book-bg-paper p-2 leading-relaxed text-book-text-main">
                      {suggestion.suggested_text}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </BookCard>
  );
};
