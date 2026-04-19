import React from 'react';
import {
  ListChecks,
  PauseCircle,
  PlayCircle,
  XCircle,
} from 'lucide-react';
import { BookButton } from '../../ui/BookButton';
import { BookCard } from '../../ui/BookCard';
import {
  DIMENSIONS,
  type AnalysisScope,
  type OptimizationMode,
  type ParagraphPreviewResponse,
} from './shared';

interface ContentOptimizationControlsCardProps {
  mode: OptimizationMode;
  scope: AnalysisScope;
  dimensions: string[];
  preview: ParagraphPreviewResponse | null;
  selectedParagraphs: number[];
  rangeInput: string;
  previewLoading: boolean;
  running: boolean;
  paused: boolean;
  sessionId: string | null;
  onModeChange: (value: OptimizationMode) => void;
  onScopeChange: (value: AnalysisScope) => void;
  onToggleDimension: (id: string) => void;
  onFetchPreview: () => void;
  onStartOptimization: () => void;
  onContinueSession: () => void;
  onStopStream: () => void;
  onCancelSession: () => void;
  onRangeInputChange: (value: string) => void;
  onApplyRangeSelection: () => void;
  onSelectAllPreview: () => void;
  onClearPreviewSelection: () => void;
  onToggleParagraphSelection: (index: number) => void;
}

export const ContentOptimizationControlsCard: React.FC<
  ContentOptimizationControlsCardProps
> = ({
  mode,
  scope,
  dimensions,
  preview,
  selectedParagraphs,
  rangeInput,
  previewLoading,
  running,
  paused,
  sessionId,
  onModeChange,
  onScopeChange,
  onToggleDimension,
  onFetchPreview,
  onStartOptimization,
  onContinueSession,
  onStopStream,
  onCancelSession,
  onRangeInputChange,
  onApplyRangeSelection,
  onSelectAllPreview,
  onClearPreviewSelection,
  onToggleParagraphSelection,
}) => {
  return (
    <BookCard className="space-y-4 p-4">
      <div className="grid grid-cols-2 gap-3">
        <label className="text-xs font-bold text-book-text-sub">
          模式
          <select
            className="book-control book-select mt-1 w-full rounded-lg border px-3 py-2 text-sm text-book-text-main"
            value={mode}
            onChange={(event) =>
              onModeChange(event.target.value as OptimizationMode)
            }
            disabled={running}
          >
            <option value="plan">计划（先分析后选择）</option>
            <option value="review">审核（逐条暂停确认）</option>
            <option value="auto">自动（不中断）</option>
          </select>
        </label>

        <label className="text-xs font-bold text-book-text-sub">
          范围
          <select
            className="book-control book-select mt-1 w-full rounded-lg border px-3 py-2 text-sm text-book-text-main"
            value={scope}
            onChange={(event) =>
              onScopeChange(event.target.value as AnalysisScope)
            }
            disabled={running}
          >
            <option value="full">全章</option>
            <option value="selected">选中段落</option>
          </select>
        </label>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2 text-xs font-bold text-book-text-sub">
          <span>检查维度</span>
          <span className="text-[11px] text-book-text-muted">
            {dimensions.length}/{DIMENSIONS.length}
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {DIMENSIONS.map((dimension) => (
            <label
              key={dimension.id}
              className="flex items-center gap-2 rounded border border-book-border/50 bg-book-bg px-2 py-1 text-xs text-book-text-main"
            >
              <input
                type="checkbox"
                checked={dimensions.includes(dimension.id)}
                onChange={() => onToggleDimension(dimension.id)}
                disabled={running}
                className="book-check h-4 w-4 rounded border-book-border/60 bg-book-bg-paper/80"
              />
              {dimension.label}
            </label>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <BookButton
          variant="ghost"
          size="sm"
          onClick={onFetchPreview}
          disabled={previewLoading || running}
          title="调用后端段落切分预览（用于选择段落）"
        >
          <ListChecks
            size={14}
            className={`mr-1 ${previewLoading ? 'animate-spin' : ''}`}
          />
          {previewLoading ? '预览中…' : '段落预览'}
        </BookButton>

        <div className="flex-1" />

        {!running ? (
          <BookButton variant="primary" size="sm" onClick={onStartOptimization}>
            <PlayCircle size={14} className="mr-1" />
            开始
          </BookButton>
        ) : paused ? (
          <BookButton
            variant="primary"
            size="sm"
            onClick={onContinueSession}
            disabled={!sessionId}
          >
            <PlayCircle size={14} className="mr-1" />
            继续
          </BookButton>
        ) : (
          <BookButton variant="secondary" size="sm" onClick={onStopStream}>
            <PauseCircle size={14} className="mr-1" />
            停止流
          </BookButton>
        )}

        <BookButton
          variant="secondary"
          size="sm"
          onClick={onCancelSession}
          disabled={!running && !sessionId}
        >
          <XCircle size={14} className="mr-1" />
          取消
        </BookButton>
      </div>

      {scope === 'selected' && preview ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-xs text-book-text-muted">
              已识别 {preview.total_paragraphs} 段，已选择{' '}
              {selectedParagraphs.length} 段
            </div>
            <div className="flex items-center gap-2">
              <button
                className="text-xs font-bold text-book-primary hover:underline"
                onClick={onSelectAllPreview}
                type="button"
              >
                全选
              </button>
              <button
                className="text-xs text-book-text-muted hover:underline"
                onClick={onClearPreviewSelection}
                type="button"
              >
                清空
              </button>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              className="book-control flex-1 rounded-lg border px-3 py-2 text-sm text-book-text-main"
              placeholder="范围：1-5, 9-18, 20（回车应用）"
              value={rangeInput}
              onChange={(event) => onRangeInputChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  onApplyRangeSelection();
                }
              }}
              disabled={running}
            />
            <BookButton
              variant="ghost"
              size="sm"
              onClick={onApplyRangeSelection}
              disabled={running}
            >
              应用
            </BookButton>
          </div>
          <div className="custom-scrollbar max-h-64 space-y-2 overflow-y-auto pr-1">
            {preview.paragraphs.map((paragraph) => (
              <label
                key={paragraph.index}
                className="flex items-start gap-2 rounded border border-book-border/40 bg-book-bg p-2"
              >
                <input
                  type="checkbox"
                  checked={selectedParagraphs.includes(paragraph.index)}
                  onChange={() =>
                    onToggleParagraphSelection(paragraph.index)
                  }
                  disabled={running}
                  className="book-check mt-0.5 h-4 w-4 rounded border-book-border/60 bg-book-bg-paper/80"
                />
                <div className="min-w-0">
                  <div className="text-[11px] text-book-text-muted">
                    段落 {paragraph.index + 1} · {paragraph.length}
                  </div>
                  <div className="text-xs leading-relaxed text-book-text-main">
                    {paragraph.preview}
                  </div>
                </div>
              </label>
            ))}
          </div>
        </div>
      ) : null}

      {sessionId ? (
        <div className="text-[11px] text-book-text-muted">
          session_id：<span className="font-mono">{sessionId}</span>
        </div>
      ) : null}
    </BookCard>
  );
};
