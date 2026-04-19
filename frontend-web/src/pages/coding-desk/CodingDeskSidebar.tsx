import React, { lazy, Suspense } from 'react';
import { LayoutPanelLeft } from 'lucide-react';
import { BookCard } from '../../components/ui/BookCard';

const DirectoryTreeLazy = lazy(() =>
  import('../../components/coding/DirectoryTree').then((m) => ({ default: m.DirectoryTree }))
);

type CodingDeskSidebarProps = {
  project: any;
  treeLoading: boolean;
  showAgentTree: boolean;
  agentTreeData: any;
  treeData: any;
  onSelectFile: (fileId: number) => void | Promise<void>;
};

export const CodingDeskSidebar: React.FC<CodingDeskSidebarProps> = ({
  project,
  treeLoading,
  showAgentTree,
  agentTreeData,
  treeData,
  onSelectFile,
}) => {
  const displayTree = showAgentTree && agentTreeData ? agentTreeData : treeData;

  return (
    <div className="flex w-[300px] flex-col border-r border-book-border/60 bg-book-bg-paper">
      <div className="border-b border-book-border/30 p-3">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-book-text-sub">
          <LayoutPanelLeft size={14} />
          项目结构
          {showAgentTree ? (
            <span className="ml-1 rounded border border-book-primary/20 bg-book-primary/10 px-1.5 py-0.5 text-[10px] font-bold text-book-primary">
              规划预览
            </span>
          ) : null}
        </div>
      </div>

      <div className="border-b border-book-border/30 p-3">
        <BookCard className="border-book-border/40 bg-book-bg/40 p-3">
          <div className="text-xs text-book-text-muted">状态：{String(project?.status || 'unknown')}</div>
          <div className="mt-1 truncate text-sm font-bold text-book-text-main">
            {String(project?.title || '未命名项目')}
          </div>
        </BookCard>
      </div>

      <div className="custom-scrollbar flex-1 overflow-y-auto">
        {treeLoading && !displayTree ? (
          <div className="p-4 text-xs text-book-text-muted">目录加载中…</div>
        ) : (
          <Suspense fallback={<div className="p-4 text-xs text-book-text-muted">目录组件加载中…</div>}>
            <DirectoryTreeLazy data={displayTree} onSelectFile={onSelectFile} />
          </Suspense>
        )}
      </div>
    </div>
  );
};
