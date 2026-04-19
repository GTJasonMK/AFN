import React from 'react';
import { Database, RefreshCw, Search, Sparkles } from 'lucide-react';
import { CodingDependency } from '../../api/coding';
import { BookCard } from '../../components/ui/BookCard';
import { BookButton } from '../../components/ui/BookButton';

type CodingDetailGenerationTabProps = {
  dependencies: CodingDependency[];
  tabLoading: boolean;
  onSyncDependencies: () => void | Promise<void>;
  onDeleteDependency: (dependency: CodingDependency) => void | Promise<void>;
  ragCompleteness: any;
  ragLoading: boolean;
  ragIngesting: boolean;
  onIngestRag: (force: boolean) => void | Promise<void>;
  generatedSourceFiles: any[];
  generatedTotalVersions: number;
  loading: boolean;
  onRefreshGeneratedContent: () => void | Promise<void>;
  onOpenGeneratedFile: (fileId: number) => void;
  onOpenCodingDesk: (fileId?: number) => void;
  ragQuery: string;
  onRagQueryChange: (value: string) => void;
  onRunRagQuery: () => void | Promise<void>;
  ragQueryLoading: boolean;
  ragResult: any;
};

export const CodingDetailGenerationTab: React.FC<CodingDetailGenerationTabProps> = ({
  dependencies,
  tabLoading,
  onSyncDependencies,
  onDeleteDependency,
  ragCompleteness,
  ragLoading,
  ragIngesting,
  onIngestRag,
  generatedSourceFiles,
  generatedTotalVersions,
  loading,
  onRefreshGeneratedContent,
  onOpenGeneratedFile,
  onOpenCodingDesk,
  ragQuery,
  onRagQueryChange,
  onRunRagQuery,
  ragQueryLoading,
  ragResult,
}) => {
  return (
    <div className="space-y-6">
      <BookCard className="p-5">
        <div className="mb-4 flex items-center justify-between">
          <div className="text-sm font-bold text-book-text-main">RAG状态</div>
          <div className="flex items-center gap-2">
            <BookButton
              size="sm"
              variant="ghost"
              onClick={() => onIngestRag(false)}
              disabled={ragLoading || ragIngesting}
            >
              <Database size={16} className={`mr-1 ${ragIngesting ? 'animate-pulse' : ''}`} />
              {ragIngesting ? '入库中...' : '同步RAG'}
            </BookButton>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-6">
          <div>
            <div className="mb-1 text-xs text-book-text-muted">数据完整性</div>
            <div className="mb-1 h-2 rounded-full bg-book-border">
              <div
                className={`h-full rounded-full ${ragCompleteness?.complete ? 'bg-green-500' : 'bg-yellow-500'}`}
                style={{ width: ragCompleteness?.complete ? '100%' : '50%' }}
              />
            </div>
            <div className="text-xs text-book-text-sub">
              {ragCompleteness?.total_vector_count ?? '--'} / {ragCompleteness?.total_db_count ?? '--'}
            </div>
          </div>
          <div>
            <div className="mb-1 text-xs text-book-text-muted">已入库</div>
            <div className="text-xl font-bold text-green-600">{ragCompleteness?.total_vector_count ?? 0}</div>
          </div>
          <div>
            <div className="mb-1 text-xs text-book-text-muted">待入库</div>
            <div className="text-xl font-bold text-yellow-600">
              {Math.max(0, (ragCompleteness?.total_db_count ?? 0) - (ragCompleteness?.total_vector_count ?? 0))}
            </div>
          </div>
        </div>
      </BookCard>

      <BookCard className="p-5">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="text-sm font-bold text-book-text-main">依赖关系</div>
            <span className="text-xs text-book-text-muted">({dependencies.length})</span>
          </div>
          <BookButton size="sm" variant="ghost" onClick={onSyncDependencies} disabled={tabLoading}>
            <RefreshCw size={16} className="mr-1" />
            同步依赖
          </BookButton>
        </div>
        {dependencies.length === 0 ? (
          <div className="py-4 text-center text-sm text-book-text-muted">暂无依赖关系</div>
        ) : (
          <div className="custom-scrollbar max-h-48 space-y-2 overflow-y-auto">
            {dependencies.slice(0, 10).map((dependency, idx) => (
              <div key={idx} className="flex items-center justify-between rounded bg-book-bg/50 p-2">
                <span className="text-sm text-book-text-main">
                  {dependency.from_module} → {dependency.to_module}
                </span>
                <button
                  type="button"
                  className="text-xs font-bold text-red-600 hover:underline"
                  onClick={() => onDeleteDependency(dependency)}
                >
                  删除
                </button>
              </div>
            ))}
            {dependencies.length > 10 && (
              <div className="text-center text-xs text-book-text-muted">
                ... 还有 {dependencies.length - 10} 条
              </div>
            )}
          </div>
        )}
      </BookCard>

      <BookCard className="p-5">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="text-sm font-bold text-book-text-main">已生成内容</div>
            <span className="text-xs text-book-text-muted">({generatedSourceFiles.length})</span>
            {generatedTotalVersions > 0 && (
              <span className="text-xs text-book-text-muted">{generatedTotalVersions} 版本</span>
            )}
          </div>
          <BookButton size="sm" variant="ghost" onClick={onRefreshGeneratedContent} disabled={loading}>
            <RefreshCw size={16} className={`mr-1 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </BookButton>
        </div>
        {generatedSourceFiles.length === 0 ? (
          <div className="py-4 text-center text-sm text-book-text-muted">暂无已生成内容</div>
        ) : (
          <div className="custom-scrollbar max-h-64 space-y-2 overflow-y-auto">
            {generatedSourceFiles.slice(0, 20).map((file: any) => (
              <div
                key={file.id}
                className="flex items-center justify-between rounded border border-book-border/40 bg-book-bg/50 p-2"
              >
                <div className="min-w-0">
                  <div className="truncate text-sm font-bold text-book-text-main">
                    {file.filename || file.file_path}
                  </div>
                  <div className="truncate text-xs text-book-text-muted">{file.file_path || ''}</div>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="text-xs text-book-text-muted">{Number(file.version_count || 0)} 版本</span>
                  <button
                    type="button"
                    className="text-xs font-bold text-book-primary hover:underline"
                    onClick={() => onOpenGeneratedFile(file.id)}
                  >
                    打开
                  </button>
                  <button
                    type="button"
                    className="text-xs font-bold text-book-primary hover:underline"
                    onClick={() => onOpenCodingDesk(file.id)}
                  >
                    工作台
                  </button>
                </div>
              </div>
            ))}
            {generatedSourceFiles.length > 20 && (
              <div className="text-center text-xs text-book-text-muted">
                ... 还有 {generatedSourceFiles.length - 20} 个
              </div>
            )}
          </div>
        )}
      </BookCard>

      <BookCard className="p-5">
        <div className="mb-4 flex items-center justify-between">
          <div className="text-sm font-bold text-book-text-main">检索查询</div>
          <BookButton
            size="sm"
            variant="ghost"
            onClick={onRunRagQuery}
            disabled={ragQueryLoading || !ragQuery.trim()}
          >
            <Search size={16} className={`mr-1 ${ragQueryLoading ? 'animate-spin' : ''}`} />
            查询
          </BookButton>
        </div>
        <input
          className="book-control mb-4 w-full rounded-lg border px-3 py-2 text-sm text-book-text-main"
          value={ragQuery}
          onChange={(event) => onRagQueryChange(event.target.value)}
          placeholder="输入问题，例如：模块职责/依赖关系/异常处理..."
          onKeyDown={(event) => {
            if (event.key === 'Enter') onRunRagQuery();
          }}
        />
        {ragResult ? (
          <div className="custom-scrollbar max-h-64 space-y-3 overflow-y-auto">
            {Array.isArray((ragResult as any).chunks) &&
              (ragResult as any).chunks.map((chunk: any, idx: number) => (
                <div key={idx} className="rounded border border-book-border/40 bg-book-bg/50 p-3">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-xs font-bold text-book-text-main">{chunk?.source || 'unknown'}</span>
                    <span className="font-mono text-[10px] text-book-text-muted">
                      {chunk?.score?.toFixed(3) || ''}
                    </span>
                  </div>
                  <div className="whitespace-pre-wrap text-xs text-book-text-sub">
                    {chunk?.content || ''}
                  </div>
                </div>
              ))}
            {!(ragResult as any).chunks?.length && (
              <div className="py-4 text-center text-sm text-book-text-muted">未命中结果</div>
            )}
          </div>
        ) : (
          <div className="py-8 text-center text-sm text-book-text-muted">
            <Sparkles size={24} className="mx-auto mb-2 opacity-50" />
            输入问题以检索已入库的项目知识
          </div>
        )}
      </BookCard>
    </div>
  );
};
