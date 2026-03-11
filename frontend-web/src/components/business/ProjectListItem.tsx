import React from 'react';
import { Clock, Trash2, ChevronRight, Book, Code } from 'lucide-react';
import { getStatusText } from '../../utils/constants';

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
  onDelete?: (project: ProjectListItemModel) => void;
  onHover?: (project: ProjectListItemModel) => void;
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
  onDelete,
  onHover 
}) => {
  const normalizedStatus = String(project.status || '').toLowerCase();
  const statusTone = statusToneMap[normalizedStatus] || 'border-book-border/50 bg-book-bg/65 text-book-text-sub';
  const kindLabel = project.kind === 'coding' ? 'Prompt 工程' : '小说项目';

  return (
    <article
      onClick={() => onClick(project)}
      onMouseEnter={() => onHover?.(project)}
      onFocus={() => onHover?.(project)}
      className="group relative cursor-pointer overflow-hidden rounded-[30px] border border-book-border/55 bg-book-bg-paper/80 p-5 shadow-[0_26px_58px_-44px_rgba(36,18,6,0.96)] transition-all duration-300 hover:-translate-y-1 hover:border-book-primary/25 hover:bg-book-bg-paper/92 hover:shadow-[0_32px_72px_-44px_rgba(36,18,6,0.96)] sm:p-6"
    >
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/35 via-transparent to-book-primary/8 opacity-80" />
      <div className="pointer-events-none absolute inset-y-6 left-0 w-px origin-top scale-y-0 bg-gradient-to-b from-transparent via-book-primary to-transparent transition-transform duration-300 group-hover:scale-y-100" />

      <div className="relative z-[1] flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 gap-4">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[20px] border border-book-border/50 bg-book-bg/78 text-book-primary shadow-[inset_0_1px_0_rgba(255,255,255,0.42)] transition-all duration-300 group-hover:scale-105 group-hover:border-book-primary/30 group-hover:text-book-primary-light">
            {project.kind === 'coding' ? <Code size={22} /> : <Book size={22} />}
          </div>

          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="story-pill">{kindLabel}</span>
              <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[0.72rem] font-semibold ${statusTone}`}>
                {getStatusText(project.status)}
              </span>
            </div>

            <h3 className="mt-3 font-serif text-2xl font-bold tracking-[0.02em] text-book-text-main transition-colors duration-300 group-hover:text-book-primary sm:text-[1.75rem]">
              {project.title || '未命名项目'}
            </h3>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-book-text-sub sm:text-[0.95rem]">
              {project.description || '暂无描述，进入项目后继续补全世界观、角色和任务结构。'}
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between gap-4 sm:justify-end">
          <div className="text-left sm:text-right">
            <div className="text-[0.68rem] font-bold uppercase tracking-[0.22em] text-book-text-muted">
              Last Touch
            </div>
            <div className="mt-1 inline-flex items-center gap-2 text-sm font-semibold text-book-text-main">
              <Clock size={14} className="text-book-text-muted" />
              {formatUpdatedAt(project.updated_at)}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {onDelete ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(project);
                }}
                className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-book-border/50 bg-book-bg/70 text-book-text-muted transition-all duration-200 hover:border-red-400/35 hover:bg-red-50/80 hover:text-red-500 dark:hover:bg-red-900/20"
                title="删除项目"
                aria-label="删除项目"
              >
                <Trash2 size={16} />
              </button>
            ) : null}

            <div className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-book-border/45 bg-book-bg/70 text-book-primary transition-all duration-300 group-hover:translate-x-1 group-hover:border-book-primary/35 group-hover:bg-book-primary group-hover:text-white">
              <ChevronRight size={18} />
            </div>
          </div>
        </div>
      </div>
    </article>
  );
};

export const ProjectListItem = React.memo(ProjectListItemInner);
