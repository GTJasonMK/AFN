import React, { useRef } from 'react';
import { Book, ChevronRight, Clock, Code, Trash2 } from 'lucide-react';
import { getStatusText } from '../../utils/constants';
import { getProjectKindLabel } from '../../utils/projectRouting';
import type { ProjectListItemModel } from './ProjectListItem';

interface ProjectLauncherRowProps {
  project: ProjectListItemModel;
  onLaunch: (project: ProjectListItemModel) => void;
  onDelete?: (project: ProjectListItemModel) => void;
  onPrefetch?: (project: ProjectListItemModel, trigger: 'hover' | 'commit') => (() => void) | void;
  showDelete?: boolean;
  compact?: boolean;
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

const ProjectLauncherRowInner: React.FC<ProjectLauncherRowProps> = ({
  project,
  onLaunch,
  onDelete,
  onPrefetch,
  showDelete = false,
  compact = false,
}) => {
  const cancelPrefetchRef = useRef<(() => void) | null>(null);
  const normalizedStatus = String(project.status || '').toLowerCase();
  const statusTone = statusToneMap[normalizedStatus] || 'border-book-border/50 bg-book-bg/65 text-book-text-sub';
  const kindLabel = getProjectKindLabel(project);

  return (
    <article
      onClick={() => onLaunch(project)}
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
      className={`perf-card group relative overflow-hidden rounded-[22px] border border-book-border/50 bg-book-bg-paper/80 transition-[border-color,background-color,transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:border-book-primary/28 hover:bg-book-bg-paper/92 hover:shadow-[0_26px_56px_-44px_rgba(36,18,6,0.96)] ${
        compact ? 'min-h-[72px] px-3.5 py-3' : 'min-h-[80px] px-4 py-3.5'
      }`}
    >
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-white/20 via-transparent to-book-primary/6 opacity-70" />
      <div className={`relative z-[1] flex min-h-0 items-center gap-3 ${compact ? 'gap-3' : 'gap-4'}`}>
        <div className={`flex shrink-0 items-center justify-center rounded-[16px] border border-book-border/45 bg-book-bg/76 text-book-primary ${
          compact ? 'h-10 w-10' : 'h-11 w-11'
        }`}>
          {project.kind === 'coding' ? <Code size={compact ? 18 : 19} /> : <Book size={compact ? 18 : 19} />}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 flex-wrap items-start gap-2">
            <h3
              className={`min-w-0 flex-1 font-serif font-bold leading-tight text-book-text-main transition-colors duration-200 group-hover:text-book-primary ${
                compact ? 'text-[0.98rem]' : 'text-[1.05rem]'
              }`}
              style={{
                display: '-webkit-box',
                WebkitBoxOrient: 'vertical',
                WebkitLineClamp: 2,
                overflow: 'hidden',
              }}
            >
              {project.title || '未命名项目'}
            </h3>
            <span className={`story-pill shrink-0 ${compact ? 'px-2.5 py-1 text-[0.66rem]' : 'px-3 py-1 text-[0.68rem]'}`}>
              {kindLabel}
            </span>
          </div>

          <div className={`mt-1 flex flex-wrap items-center gap-2 ${compact ? 'gap-y-1.5' : 'gap-y-2'}`}>
            <span className={`inline-flex items-center rounded-full border font-semibold ${statusTone} ${
              compact ? 'px-2 py-0.5 text-[0.66rem]' : 'px-2.5 py-1 text-[0.7rem]'
            }`}>
              {getStatusText(project.status)}
            </span>
            <span className={`inline-flex items-center gap-1.5 text-book-text-muted ${compact ? 'text-[0.72rem]' : 'text-xs'}`}>
              <Clock size={compact ? 12 : 13} />
              {formatUpdatedAt(project.updated_at)}
            </span>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {showDelete && onDelete ? (
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onDelete(project);
              }}
              className={`inline-flex items-center justify-center rounded-full border border-book-border/50 bg-book-bg/70 text-book-text-muted opacity-0 transition-all duration-200 group-hover:opacity-100 hover:border-red-400/35 hover:bg-red-50/80 hover:text-red-500 dark:hover:bg-red-900/20 ${
                compact ? 'h-8 w-8' : 'h-9 w-9'
              }`}
              title="删除项目"
              aria-label="删除项目"
            >
              <Trash2 size={compact ? 13 : 14} />
            </button>
          ) : null}

          <div className={`inline-flex items-center justify-center rounded-full border border-book-border/45 bg-book-bg/70 text-book-primary transition-all duration-300 group-hover:translate-x-1 group-hover:border-book-primary/35 group-hover:bg-book-primary group-hover:text-white ${
            compact ? 'h-9 w-9' : 'h-10 w-10'
          }`}>
            <ChevronRight size={compact ? 16 : 18} />
          </div>
        </div>
      </div>
    </article>
  );
};

export const ProjectLauncherRow = React.memo(ProjectLauncherRowInner);
