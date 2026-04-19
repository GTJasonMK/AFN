import React from 'react';
import { Copy, Search, XCircle } from 'lucide-react';
import { BookButton } from '../../ui/BookButton';
import { BookCard } from '../../ui/BookCard';
import {
  THINKING_LABELS,
  formatThinkingTimestamp,
  type ThinkingEvent,
} from './shared';

interface ContentOptimizationThinkingPanelProps {
  thinkingEvents: ThinkingEvent[];
  thinkingExpanded: boolean;
  thinkingScrollRef: React.RefObject<HTMLDivElement>;
  running: boolean;
  onCopy: () => void;
  onClear: () => void;
  onToggleExpanded: () => void;
}

export const ContentOptimizationThinkingPanel: React.FC<
  ContentOptimizationThinkingPanelProps
> = ({
  thinkingEvents,
  thinkingExpanded,
  thinkingScrollRef,
  running,
  onCopy,
  onClear,
  onToggleExpanded,
}) => {
  const lastEvent =
    thinkingEvents.length > 0
      ? thinkingEvents[thinkingEvents.length - 1]
      : null;

  return (
    <BookCard className="p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-bold text-book-text-main">
          <Search size={16} className="text-book-primary" />
          思考流
        </div>
        <div className="flex items-center gap-2">
          {thinkingEvents.length > 0 ? (
            <BookButton
              variant="ghost"
              size="sm"
              onClick={onCopy}
              title="复制完整思考流"
            >
              <Copy size={14} className="mr-1" />
              复制
            </BookButton>
          ) : null}
          {thinkingEvents.length > 0 ? (
            <BookButton
              variant="ghost"
              size="sm"
              onClick={onClear}
              title="清空思考流"
            >
              <XCircle size={14} className="mr-1" />
              清空
            </BookButton>
          ) : null}
          <BookButton variant="ghost" size="sm" onClick={onToggleExpanded}>
            {thinkingExpanded ? '收起' : '展开'}
          </BookButton>
        </div>
      </div>

      {thinkingEvents.length === 0 ? (
        <div className="text-xs leading-relaxed text-book-text-muted">
          {running
            ? '思考流等待输出…'
            : '开始优化后，这里会显示 Agent 的 Thinking / Action / Observation 过程。'}
        </div>
      ) : thinkingExpanded ? (
        <div
          ref={thinkingScrollRef}
          className="custom-scrollbar max-h-56 space-y-2 overflow-y-auto pr-1"
        >
          {thinkingEvents.map((event) => {
            const meta =
              THINKING_LABELS[event.type] || {
                label: event.type,
                cls: 'text-book-text-muted',
              };

            return (
              <div
                key={event.id}
                className="rounded border border-book-border/40 bg-book-bg p-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className={`text-[11px] font-bold ${meta.cls}`}>
                    {meta.label}
                    {event.title ? (
                      <span className="ml-2 font-normal text-book-text-muted">
                        {event.title}
                      </span>
                    ) : null}
                  </div>
                  <div className="text-[10px] text-book-text-muted">
                    {formatThinkingTimestamp(event.ts)}
                  </div>
                </div>
                {event.content ? (
                  <pre className="mt-1 whitespace-pre-wrap font-mono text-xs leading-relaxed text-book-text-main">
                    {event.content}
                  </pre>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-xs leading-relaxed text-book-text-muted">
          最近：
          {lastEvent
            ? (() => {
                const meta =
                  THINKING_LABELS[lastEvent.type] || {
                    label: lastEvent.type,
                    cls: '',
                  };
                const title = lastEvent.title ? ` · ${lastEvent.title}` : '';
                return `${meta.label}${title}`;
              })()
            : ''}
        </div>
      )}
    </BookCard>
  );
};
