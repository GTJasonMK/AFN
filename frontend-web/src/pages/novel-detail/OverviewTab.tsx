import React from 'react';
import { BookCard } from '../../components/ui/BookCard';
import { BookInput, BookTextarea } from '../../components/ui/BookInput';

export type OverviewTabProps = {
  blueprintData: any;
  setBlueprintData: (next: any) => void;
  project: any | null;
  importStatus: any | null;
  importStatusLoading: boolean;
  importStarting: boolean;
  startImportAnalysis: () => void | Promise<void>;
  refreshImportStatus: () => void | Promise<void>;
  cancelImportAnalysis: () => void | Promise<void>;
};

export const OverviewTab: React.FC<OverviewTabProps> = ({
  blueprintData,
  setBlueprintData,
  project,
  importStatus,
  importStatusLoading,
  importStarting,
  startImportAnalysis,
  refreshImportStatus,
  cancelImportAnalysis,
}) => {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          <BookCard className="p-6 space-y-4">
            <h3 className="font-serif font-bold text-lg text-book-text-main border-b border-book-border/40 pb-2">
              一句话梗概
            </h3>
            <BookTextarea
              value={blueprintData.one_sentence_summary || ''}
              onChange={(e) => setBlueprintData({ ...blueprintData, one_sentence_summary: e.target.value })}
              className="min-h-[80px] text-base font-serif leading-relaxed"
            />
          </BookCard>

          <BookCard className="p-6 space-y-4">
            <h3 className="font-serif font-bold text-lg text-book-text-main border-b border-book-border/40 pb-2">
              故事全貌
            </h3>
            <BookTextarea
              value={blueprintData.full_synopsis || ''}
              onChange={(e) => setBlueprintData({ ...blueprintData, full_synopsis: e.target.value })}
              className="min-h-[300px] text-base font-serif leading-relaxed"
            />
          </BookCard>
        </div>

        <div className="space-y-6">
          {project?.is_imported && (
            <BookCard className="p-5 space-y-4">
              <div className="flex items-center justify-between gap-2">
                <h3 className="font-bold text-sm text-book-text-main">导入分析</h3>
                <div className="flex items-center gap-2">
                  {(() => {
                    const status = String(importStatus?.status || project.import_analysis_status || 'pending');
                    const canStart = status !== 'completed' && status !== 'analyzing';
                    if (!canStart) return null;
                    const isResume = status === 'failed' || status === 'cancelled';
                    return (
                      <button
                        onClick={startImportAnalysis}
                        className="text-xs text-book-primary font-bold hover:underline disabled:opacity-50"
                        disabled={importStatusLoading || importStarting}
                        title={isResume ? '继续导入分析（从断点尝试恢复）' : '开始导入分析'}
                      >
                        {importStarting ? '启动中…' : (isResume ? '继续分析' : '开始分析')}
                      </button>
                    );
                  })()}
                  <button
                    onClick={refreshImportStatus}
                    className="text-xs text-book-primary font-bold hover:underline"
                    disabled={importStatusLoading}
                  >
                    {importStatusLoading ? '刷新中…' : '刷新'}
                  </button>
                  {importStatus?.status === 'analyzing' && (
                    <button
                      onClick={cancelImportAnalysis}
                      className="text-xs text-red-600 font-bold hover:underline"
                      disabled={importStatusLoading}
                    >
                      取消
                    </button>
                  )}
                </div>
              </div>

              <div className="text-xs text-book-text-muted">
                状态：{importStatusLoading ? '加载中…' : (importStatus?.status || project.import_analysis_status || 'pending')}
              </div>

              <div className="space-y-2">
                <div className="h-2 rounded bg-book-bg border border-book-border/40 overflow-hidden">
                  <div
                    className="h-full bg-book-primary"
                    style={{ width: `${Math.max(0, Math.min(100, Number(importStatus?.progress?.overall_progress || 0)))}%` }}
                  />
                </div>
                <div className="flex items-center justify-between text-[11px] text-book-text-muted">
                  <span>{String(importStatus?.progress?.message || '等待开始分析')}</span>
                  <span>{Number(importStatus?.progress?.overall_progress || 0)}%</span>
                </div>
              </div>

              {importStatus?.progress?.stages && (
                <div className="space-y-2">
                  <div className="text-xs font-bold text-book-text-sub">阶段</div>
                  <div className="space-y-2">
                    {Object.entries(importStatus.progress.stages as Record<string, any>).slice(0, 6).map(([k, v]) => (
                      <div key={k} className="text-[11px] text-book-text-muted flex items-center justify-between gap-2">
                        <span className="truncate">
                          {String(v.name || k)}{v.status === 'in_progress' ? '（进行中）' : ''}
                        </span>
                        <span className="font-mono">
                          {Number(v.completed || 0)}/{Number(v.total || 0)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </BookCard>
          )}

          <BookCard className="p-5 space-y-4 sticky top-4">
            <h3 className="font-bold text-sm text-book-text-main">基础设定</h3>
            <div className="space-y-3">
              <BookInput
                label="作品类型"
                value={blueprintData.genre || ''}
                onChange={(e) => setBlueprintData({ ...blueprintData, genre: e.target.value })}
              />
              <BookInput
                label="目标读者"
                value={blueprintData.target_audience || ''}
                onChange={(e) => setBlueprintData({ ...blueprintData, target_audience: e.target.value })}
              />
              <BookInput
                label="叙事风格"
                value={blueprintData.style || ''}
                onChange={(e) => setBlueprintData({ ...blueprintData, style: e.target.value })}
              />
              <BookInput
                label="情感基调"
                value={blueprintData.tone || ''}
                onChange={(e) => setBlueprintData({ ...blueprintData, tone: e.target.value })}
              />
            </div>
          </BookCard>
        </div>
      </div>
    </div>
  );
};
