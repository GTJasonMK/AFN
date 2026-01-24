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
}

export const ProjectListItem: React.FC<ProjectListItemProps> = ({ 
  project, 
  onClick, 
  onDelete 
}) => {
  return (
    <div 
      onClick={() => onClick(project)}
      className="group relative flex items-center justify-between p-5 rounded-xl border border-book-border/40 bg-book-bg-paper/40 hover:bg-book-bg-paper hover:shadow-lg hover:shadow-book-card/5 hover:border-book-primary/20 transition-all duration-300 cursor-pointer overflow-hidden"
    >
      {/* Decorative accent on hover */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-book-primary scale-y-0 group-hover:scale-y-100 transition-transform duration-300 origin-center" />

      <div className="flex items-center gap-4 flex-1 min-w-0">
        {/* Icon Placeholder */}
        <div className="w-10 h-10 rounded-lg bg-book-bg flex items-center justify-center text-book-primary/60 group-hover:text-book-primary group-hover:scale-110 transition-all duration-300 shadow-inner">
          {project.kind === 'coding' ? <Code size={20} /> : <Book size={20} />}
        </div>

        <div className="min-w-0">
          <h3 className="font-serif text-lg font-bold text-book-text-main group-hover:text-book-primary transition-colors truncate tracking-wide">
            {project.title || "未命名项目"}
          </h3>
          <p className="text-xs text-book-text-muted mt-1 truncate max-w-md group-hover:text-book-text-sub transition-colors">
            {project.description || "暂无描述..."}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-6 text-sm">
        <span className={`
          px-2.5 py-1 rounded-full text-xs font-medium border
          ${project.status === 'inspiration' ? 'text-blue-600 bg-blue-50/50 border-blue-100 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800/30' : 
            project.status === 'completed' ? 'text-green-600 bg-green-50/50 border-green-100 dark:bg-green-900/20 dark:text-green-300 dark:border-green-800/30' :
            'text-book-text-sub bg-book-bg border-book-border/50'}
        `}>
          {getStatusText(project.status)}
        </span>

        <div className="flex items-center text-book-text-muted text-xs w-28 justify-end tabular-nums">
          <Clock size={12} className="mr-1.5 opacity-70" />
          <span>{new Date(project.updated_at).toLocaleDateString()}</span>
        </div>

        <div className="flex items-center gap-2 w-16 justify-end">
          {onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(project);
              }}
              className="p-2 rounded-full text-book-text-muted hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all duration-200 opacity-0 group-hover:opacity-100 hover:scale-110"
              title="删除项目"
            >
              <Trash2 size={16} />
            </button>
          )}
          
          <ChevronRight size={18} className="text-book-text-muted/50 group-hover:text-book-primary group-hover:translate-x-1 transition-all duration-300" />
        </div>
      </div>
    </div>
  );
};
