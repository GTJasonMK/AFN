import React from 'react';
import { BookCard } from '../ui/BookCard';
import { ChevronDown, ChevronUp, User } from 'lucide-react';

interface BlueprintCardProps {
  title?: string;
  summary?: string;
  style?: string;
  progress?: { current: number; total: number };
  portraitUrl?: string | null;
  portraitName?: string | null;
  onClick?: () => void;
  ariaLabel?: string;
  peekOpen?: boolean;
  onTogglePeek?: () => void;
}

export const BlueprintCard: React.FC<BlueprintCardProps> = ({
  title = '小说项目',
  summary = '点击打开角色档案，查看角色设定与章节快照。',
  style = '未设定',
  progress,
  portraitUrl,
  portraitName,
  onClick,
  ariaLabel = '打开角色档案',
  peekOpen = false,
  onTogglePeek,
}) => {
  const progressPercent =
    progress && typeof progress.current === 'number' && typeof progress.total === 'number' && progress.total > 0
      ? Math.min(100, Math.max(0, (progress.current / progress.total) * 100))
      : null;

  return (
    <BookCard
      hover
      variant="flat"
      className="h-40 w-full p-4"
      title={ariaLabel}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={ariaLabel}
      onKeyDown={(e) => {
        if (!onClick) return;
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <div className="flex h-full flex-col gap-2.5">
        <div className="grid grid-cols-[1fr_auto] items-start gap-3">
          <div className="min-w-0">
            <div className="flex min-w-0 items-center justify-between gap-2">
              <div className="min-w-0 truncate text-[0.72rem] font-bold tracking-[0.18em] text-book-text-muted" title="角色档案">
                角色档案
              </div>
              {onTogglePeek ? (
                <button
                  type="button"
                  className={`story-pill-compact inline-flex shrink-0 items-center gap-1.5 border-book-border/55 bg-book-bg/70 text-book-text-sub transition-colors hover:border-book-primary/35 hover:text-book-primary ${
                    peekOpen ? 'border-book-primary/35 bg-book-primary/10 text-book-primary' : ''
                  }`}
                  title={peekOpen ? '收起概览' : '展开概览'}
                  aria-label={peekOpen ? '收起项目概览' : '展开项目概览'}
                  aria-expanded={peekOpen}
                  onClick={(e) => {
                    e.stopPropagation();
                    onTogglePeek();
                  }}
                  onMouseDown={(e) => e.stopPropagation()}
                >
                  <span className="text-[11px] font-semibold">概览</span>
                  {peekOpen ? <ChevronUp size={14} className="opacity-80" /> : <ChevronDown size={14} className="opacity-80" />}
                </button>
              ) : null}
            </div>
            <div className="mt-1 line-clamp-1 font-serif text-sm font-bold text-book-text-main" title={title}>
              {title}
            </div>
          </div>

          <div className="shrink-0">
            {portraitUrl ? (
              <img
                src={portraitUrl}
                alt={portraitName || '角色立绘'}
                className="h-11 w-11 rounded-2xl border border-book-border/50 object-cover shadow-sm"
                loading="lazy"
              />
            ) : (
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-book-border/50 bg-book-bg/60 text-book-text-sub">
                <User size={18} />
              </div>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span
            className="inline-flex max-w-full items-center truncate rounded-full border border-book-primary/20 bg-book-primary/10 px-2 py-0.5 text-xs font-bold text-book-primary"
            title={style}
          >
            {style}
          </span>
        </div>

        <p className="line-clamp-2 text-xs leading-relaxed text-book-text-sub" title={summary}>
          {summary}
        </p>

        {progress ? (
          <div className="mt-auto space-y-1">
            <div className="flex items-center justify-between text-[10px] text-book-text-muted">
              <span>创作进度</span>
              <span className="font-mono">
                {progress.current}/{progress.total}
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-book-border/30">
              <div
                className="h-full bg-book-primary transition-all duration-300"
                style={{ width: `${progressPercent ?? 0}%` }}
              />
            </div>
          </div>
        ) : (
          <div className="mt-auto text-[10px] text-book-text-muted">点击打开角色档案</div>
        )}
      </div>
    </BookCard>
  );
};
