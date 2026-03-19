import React, { useRef } from 'react';
import { Clock, Trash2, ChevronRight, Book, Code } from 'lucide-react';
import { getStatusText } from '../../utils/constants';
import {
  getProjectHomeEntryLabel,
  getProjectSecondaryEntryLabel,
} from '../../utils/projectRouting';

export interface ProjectListItemModel {
  id: string;
  title: string;
  description?: string;
  status: string;
  updated_at: string;
  kind?: 'novel' | 'coding';
}

interface ProjectListItemProps {
  project: ProjectListItemModel;
  onClick: (project: ProjectListItemModel) => void;
  onOpenWorkspace?: (project: ProjectListItemModel) => void;
  onDelete?: (project: ProjectListItemModel) => void;
  onPrefetch?: (project: ProjectListItemModel, trigger: 'hover' | 'commit') => (() => void) | void;
  variant?: 'default' | 'compact' | 'dense';
}

const statusToneMap: Record<string, string> = {
  inspiration: 'border-sky-500/25 bg-sky-500/8 text-sky-700 dark:text-sky-300',
  draft: 'border-amber-500/25 bg-amber-500/8 text-amber-700 dark:text-amber-300',
  completed: 'border-emerald-500/25 bg-emerald-500/8 text-emerald-700 dark:text-emerald-300',
};

const formatUpdatedAt = (value: string): string => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '时间未知';
  return parsed.toLocaleString([], {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const ProjectListItemInner: React.FC<ProjectListItemProps> = ({ 
  project, 
  onClick, 
  onOpenWorkspace,
  onDelete,
  onPrefetch,
  variant = 'default',
}) => {
  const cancelPrefetchRef = useRef<(() => void) | null>(null);
  const isDense = variant === 'dense';
  const isCompact = variant === 'compact' || isDense;
  const normalizedStatus = String(project.status || '').toLowerCase();
  const statusTone = statusToneMap[normalizedStatus] || 'border-book-border/50 bg-book-bg/65 text-book-text-sub';
  const kindLabel = isDense
    ? (project.kind === 'coding' ? 'Prompt' : '小说')
    : (project.kind === 'coding' ? 'Prompt 工程' : '小说项目');
  const primaryLabel = getProjectHomeEntryLabel(project);
  const secondaryLabel = getProjectSecondaryEntryLabel(project);
  const showWorkspaceEntry = Boolean(secondaryLabel && onOpenWorkspace);
  const denseTitleClampStyle: React.CSSProperties | undefined = isDense
    ? {
        display: '-webkit-box',
        WebkitBoxOrient: 'vertical',
        WebkitLineClamp: 2,
        overflow: 'hidden',
      }
    : undefined;
  const articleClassName = isDense
    ? 'perf-card group relative h-full cursor-pointer overflow-hidden rounded-[22px] border border-book-border/55 bg-book-bg-paper/88 p-3 shadow-[0_16px_34px_-30px_rgba(36,18,6,0.4)] transition-[transform,border-color,box-shadow,background-color,color] duration-200 hover:-translate-y-0.5 hover:border-book-primary/22 hover:bg-book-bg-paper/92 hover:shadow-[0_22px_40px_-32px_rgba(36,18,6,0.44)]'
    : isCompact
    ? 'perf-card group relative h-full cursor-pointer overflow-hidden rounded-[24px] border border-book-border/55 bg-book-bg-paper/86 p-3.5 shadow-[0_16px_34px_-30px_rgba(36,18,6,0.44)] transition-[transform,border-color,box-shadow,background-color,color] duration-200 hover:-translate-y-0.5 hover:border-book-primary/22 hover:bg-book-bg-paper/92 hover:shadow-[0_22px_40px_-32px_rgba(36,18,6,0.46)]'
    : 'perf-card group relative cursor-pointer overflow-hidden rounded-[30px] border border-book-border/55 bg-book-bg-paper/84 p-5 shadow-[0_18px_38px_-30px_rgba(36,18,6,0.44)] transition-[transform,border-color,box-shadow,background-color,color] duration-200 hover:-translate-y-0.5 hover:border-book-primary/22 hover:bg-book-bg-paper/92 hover:shadow-[0_22px_46px_-32px_rgba(36,18,6,0.46)] sm:p-6';
  const titleClassName = isDense
    ? 'mt-1 font-serif text-[1.05rem] font-bold tracking-[0.01em] leading-tight text-book-text-main transition-colors duration-300 group-hover:text-book-primary'
    : isCompact
    ? 'mt-1.5 font-serif text-[1.18rem] font-bold tracking-[0.01em] leading-tight text-book-text-main transition-colors duration-300 group-hover:text-book-primary'
    : 'mt-3 font-serif text-2xl font-bold tracking-[0.02em] text-book-text-main transition-colors duration-300 group-hover:text-book-primary sm:text-[1.75rem]';
  const descriptionClassName = isDense
    ? 'hidden'
    : isCompact
    ? 'mt-1 text-[0.8rem] leading-relaxed text-book-text-sub'
    : 'mt-2 max-w-3xl text-sm leading-relaxed text-book-text-sub sm:text-[0.95rem]';
  const iconClassName = isDense
    ? 'flex h-9 w-9 shrink-0 items-center justify-center rounded-[14px] border border-book-border/50 bg-book-bg/78 text-book-primary shadow-[inset_0_1px_0_rgba(255,255,255,0.3)] transition-[transform,border-color,color] duration-200 group-hover:scale-[1.02] group-hover:border-book-primary/30 group-hover:text-book-primary-light'
    : isCompact
    ? 'flex h-10 w-10 shrink-0 items-center justify-center rounded-[15px] border border-book-border/50 bg-book-bg/78 text-book-primary shadow-[inset_0_1px_0_rgba(255,255,255,0.3)] transition-[transform,border-color,color] duration-200 group-hover:scale-[1.02] group-hover:border-book-primary/30 group-hover:text-book-primary-light'
    : 'flex h-14 w-14 shrink-0 items-center justify-center rounded-[20px] border border-book-border/50 bg-book-bg/78 text-book-primary shadow-[inset_0_1px_0_rgba(255,255,255,0.3)] transition-[transform,border-color,color] duration-200 group-hover:scale-[1.02] group-hover:border-book-primary/30 group-hover:text-book-primary-light';
  const actionButtonClassName = isDense
    ? 'inline-flex min-h-8 items-center justify-center whitespace-nowrap rounded-full border border-book-primary/28 bg-book-primary px-3 text-[0.72rem] font-semibold text-white transition-[transform,border-color,background-color,color] duration-200 hover:-translate-y-0.5 hover:bg-book-primary-light'
    : isCompact
    ? 'inline-flex min-h-9 items-center justify-center whitespace-nowrap rounded-full border border-book-primary/28 bg-book-primary px-3.5 text-xs font-semibold text-white transition-[transform,border-color,background-color,color] duration-200 hover:-translate-y-0.5 hover:bg-book-primary-light'
    : 'inline-flex min-h-11 items-center justify-center whitespace-nowrap rounded-full border border-book-primary/28 bg-book-primary px-4 text-sm font-semibold text-white transition-[transform,border-color,background-color,color] duration-200 hover:-translate-y-0.5 hover:bg-book-primary-light';
  const secondaryActionClassName = isDense
    ? 'inline-flex min-h-8 items-center justify-center whitespace-nowrap rounded-full border border-book-border/55 bg-book-bg px-3 text-[0.72rem] font-semibold text-book-text-main transition-[transform,border-color,background-color,color] duration-200 hover:-translate-y-0.5 hover:border-book-primary/30 hover:text-book-primary'
    : isCompact
    ? 'inline-flex min-h-9 items-center justify-center whitespace-nowrap rounded-full border border-book-border/55 bg-book-bg px-3.5 text-xs font-semibold text-book-text-main transition-[transform,border-color,background-color,color] duration-200 hover:-translate-y-0.5 hover:border-book-primary/30 hover:text-book-primary'
    : 'inline-flex min-h-11 items-center justify-center whitespace-nowrap rounded-full border border-book-border/55 bg-book-bg px-4 text-sm font-semibold text-book-text-main transition-[transform,border-color,background-color,color] duration-200 hover:-translate-y-0.5 hover:border-book-primary/30 hover:text-book-primary';
  const sideMetaClassName = isDense
    ? 'flex flex-wrap items-end justify-between gap-2'
    : isCompact
    ? 'flex flex-wrap items-center justify-between gap-3'
    : 'flex items-center justify-between gap-4 sm:justify-end';

  return (
    <article
      onClick={() => onClick(project)}
      onMouseEnter={() => {
        cancelPrefetchRef.current?.();
        const cancel = onPrefetch?.(project, 'hover');
        cancelPrefetchRef.current = typeof cancel === 'function' ? cancel : null;
      }}
      onMouseLeave={() => {
        cancelPrefetchRef.current?.();
        cancelPrefetchRef.current = null;
      }}
      onPointerDown={() => {
        cancelPrefetchRef.current?.();
        cancelPrefetchRef.current = null;
        onPrefetch?.(project, 'commit');
      }}
      className={articleClassName}
    >
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/24 via-transparent to-book-primary/6 opacity-70" />
      <div className="pointer-events-none absolute inset-y-6 left-0 w-px origin-top scale-y-0 bg-gradient-to-b from-transparent via-book-primary to-transparent transition-transform duration-300 group-hover:scale-y-100" />

      <div className={`relative z-[1] flex h-full min-h-0 flex-col ${isDense ? 'gap-2.5' : isCompact ? 'gap-3' : 'gap-5'}`}>
        <div className={`flex min-w-0 ${isCompact ? 'gap-3' : 'gap-4'}`}>
          <div className={iconClassName}>
            {project.kind === 'coding' ? <Code size={isDense ? 16 : isCompact ? 18 : 22} /> : <Book size={isDense ? 16 : isCompact ? 18 : 22} />}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`${isDense ? 'px-2 py-0.5 text-[0.62rem]' : isCompact ? 'px-2.5 py-1 text-[0.68rem]' : ''} story-pill`}>{kindLabel}</span>
              <span className={`inline-flex items-center rounded-full border ${isDense ? 'px-2 py-0.5 text-[0.68rem]' : 'px-2.5 py-1 text-[0.72rem]'} font-semibold ${statusTone}`}>
                {getStatusText(project.status)}
              </span>
            </div>

            <h3 className={titleClassName} style={denseTitleClampStyle}>
              {project.title || '未命名项目'}
            </h3>
            <p
              className={descriptionClassName}
              style={isCompact && !isDense ? {
                display: '-webkit-box',
                WebkitBoxOrient: 'vertical',
                WebkitLineClamp: 1,
                overflow: 'hidden',
              } : undefined}
            >
              {project.description || '暂无描述，进入项目后继续补全世界观、角色和任务结构。'}
            </p>
          </div>
        </div>

        <div className={`${isCompact ? 'mt-auto' : ''} ${sideMetaClassName}`}>
          <div className={isCompact ? 'inline-flex items-center gap-2 text-xs font-semibold text-book-text-main' : 'text-left sm:text-right'}>
            <div className={`${isCompact ? 'hidden' : 'text-[0.68rem] font-bold uppercase tracking-[0.22em] text-book-text-muted'}`}>
              Last Touch
            </div>
            <div className={`${isCompact ? '' : 'mt-1 '}inline-flex items-center gap-2 ${isDense ? 'text-[0.72rem]' : isCompact ? 'text-xs' : 'text-sm'} font-semibold text-book-text-main`}>
              <Clock size={isDense ? 11 : isCompact ? 12 : 14} className="text-book-text-muted" />
              {formatUpdatedAt(project.updated_at)}
            </div>
          </div>

          <div className={`flex flex-wrap items-center ${isCompact ? 'justify-end gap-1.5' : 'gap-2'}`}>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onClick(project);
              }}
              onPointerDown={(e) => {
                e.stopPropagation();
                cancelPrefetchRef.current?.();
                cancelPrefetchRef.current = null;
                onPrefetch?.(project, 'commit');
              }}
              className={actionButtonClassName}
              aria-label={primaryLabel}
            >
              {primaryLabel}
            </button>
            {showWorkspaceEntry ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenWorkspace?.(project);
                }}
                className={secondaryActionClassName}
                aria-label={secondaryLabel || undefined}
              >
                {secondaryLabel}
              </button>
            ) : null}
            {onDelete ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(project);
                }}
                className={`${isDense ? 'h-8 w-8' : isCompact ? 'h-9 w-9' : 'h-11 w-11'} inline-flex items-center justify-center rounded-full border border-book-border/50 bg-book-bg/70 text-book-text-muted transition-all duration-200 hover:border-red-400/35 hover:bg-red-50/80 hover:text-red-500 dark:hover:bg-red-900/20`}
                title="删除项目"
                aria-label="删除项目"
              >
                <Trash2 size={isDense ? 13 : isCompact ? 14 : 16} />
              </button>
            ) : null}

            {!isDense ? (
              <div className={`${isCompact ? 'h-9 w-9' : 'h-11 w-11'} inline-flex items-center justify-center rounded-full border border-book-border/45 bg-book-bg/70 text-book-primary transition-all duration-300 group-hover:translate-x-1 group-hover:border-book-primary/35 group-hover:bg-book-primary group-hover:text-white`}>
                <ChevronRight size={isCompact ? 16 : 18} />
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </article>
  );
};

export const ProjectListItem = React.memo(ProjectListItemInner);
