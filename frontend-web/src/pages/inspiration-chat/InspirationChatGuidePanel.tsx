import React from 'react';
import { BookCard } from '../../components/ui/BookCard';

type InspirationChatGuidePanelProps = {
  isElectronRuntime: boolean;
  isTyping: boolean;
  mode: 'novel' | 'coding';
  showBlueprintBtn: boolean;
  progressSummaryLines: string[];
  progressSummaryMaxLines: number;
  progressSummaryPlaceholder: string;
  onFocusConversation: () => void;
};

export const InspirationChatGuidePanel: React.FC<InspirationChatGuidePanelProps> = ({
  isElectronRuntime,
  isTyping,
  mode,
  showBlueprintBtn,
  progressSummaryLines,
  progressSummaryMaxLines,
  progressSummaryPlaceholder,
  onFocusConversation,
}) => {
  return (
    <aside className="h-full space-y-4">
      <BookCard
        className="flex h-full min-h-0 flex-col p-6"
        variant={isElectronRuntime ? 'default' : 'flat'}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
            引导区
          </div>
          {!isTyping ? (
            <button
              type="button"
              onClick={onFocusConversation}
              className="rounded-full border border-book-border/55 bg-book-bg-paper/78 px-3 py-1.5 text-xs font-semibold text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/35 hover:text-book-primary"
            >
              去回答
            </button>
          ) : null}
        </div>

        <div className="mt-4 text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
          当前进度
        </div>
        <div className="mt-3 flex min-h-0 flex-1 flex-col">
          {progressSummaryLines.length > 0 ? (
            isElectronRuntime ? (
              <>
                <ul className="space-y-2">
                  {progressSummaryLines.slice(0, progressSummaryMaxLines).map((line, idx) => (
                    <li key={`${idx}-${line}`} className="flex gap-2 text-sm text-book-text-main">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-book-primary/70" />
                      <span className="line-clamp-2 flex-1 leading-relaxed">{line}</span>
                    </li>
                  ))}
                </ul>
                <div className="mt-auto pt-4 text-xs leading-relaxed text-book-text-sub">
                  {showBlueprintBtn
                    ? (mode === 'coding' ? '信息已足够清晰，可以开始生成架构设计。' : '信息已足够清晰，可以开始生成蓝图。')
                    : '继续在右侧对话区补充信息，这里会自动汇总你已经确认的关键点。'}
                </div>
              </>
            ) : (
              <ul className="space-y-2">
                {progressSummaryLines.slice(0, progressSummaryMaxLines).map((line, idx) => (
                  <li
                    key={`${idx}-${line}`}
                    className="flex gap-3 rounded-xl border border-book-border/45 bg-book-bg-paper/70 px-4 py-3 text-sm text-book-text-main"
                  >
                    <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-book-primary/70" />
                    <span className="flex-1 leading-relaxed">
                      {line}
                    </span>
                  </li>
                ))}
              </ul>
            )
          ) : (
            <div className="flex flex-1 items-center rounded-xl border border-dashed border-book-border/50 bg-book-bg-paper/60 px-4 py-4 text-sm leading-relaxed text-book-text-sub">
              <div className="w-full">
                <div className="text-sm font-semibold text-book-text-main">
                  {isTyping ? 'AI 正在整理当前进度…' : '进度会在每轮对话后自动生成'}
                </div>
                <div className="mt-2 text-sm leading-relaxed text-book-text-sub">
                  {isTyping ? '请稍等片刻。' : progressSummaryPlaceholder}
                </div>
              </div>
            </div>
          )}
        </div>
      </BookCard>
    </aside>
  );
};
