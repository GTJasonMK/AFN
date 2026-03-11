import React from 'react';
import { Play, RefreshCw, Share, Sparkles, Trash2 } from 'lucide-react';
import { BookButton } from '../../components/ui/BookButton';
import { OutlinesPartCard } from './OutlinesPartCard';

export type OutlinesPartSectionProps = {
  projectId: string;
  safeNavigate: (to: string) => void | Promise<void>;
  partLoading: boolean;
  partOutlines: any[];
  visiblePartOutlines: any[];
  remainingPartOutlines: number;
  partProgress: any | null;
  canContinuePartOutlines: boolean;
  partCoveredChapters: number;
  maxDeletablePartCount: number;
  deletingLatestParts: boolean;
  regeneratingLatestParts: boolean;
  regeneratingPartKey: string | null;
  generatingPartChapters: number | null;
  setIsDeleteLatestPartsModalOpen: (open: boolean) => void;
  setIsRegenerateLatestPartsModalOpen: (open: boolean) => void;
  openPartOutlinesModal: (mode: 'generate' | 'continue') => void | Promise<void>;
  handleRegenerateLastPartOutline: () => void | Promise<void>;
  handleRegenerateAllPartOutlines: () => void | Promise<void>;
  handleRegeneratePartOutline: (partNumber: number) => void | Promise<void>;
  handleGeneratePartChapters: (part: any) => void | Promise<void>;
  setDetailPart: (part: any) => void;
  countOutlinesInRange: (startChapter: number, endChapter: number) => number;
  setPartOutlinesRenderLimit: React.Dispatch<React.SetStateAction<number>>;
  partOutlinesRenderBatchSize: number;
};

export const OutlinesPartSection: React.FC<OutlinesPartSectionProps> = ({
  projectId,
  safeNavigate,
  partLoading,
  partOutlines,
  visiblePartOutlines,
  remainingPartOutlines,
  partProgress,
  canContinuePartOutlines,
  partCoveredChapters,
  maxDeletablePartCount,
  deletingLatestParts,
  regeneratingLatestParts,
  regeneratingPartKey,
  generatingPartChapters,
  setIsDeleteLatestPartsModalOpen,
  setIsRegenerateLatestPartsModalOpen,
  openPartOutlinesModal,
  handleRegenerateLastPartOutline,
  handleRegenerateAllPartOutlines,
  handleRegeneratePartOutline,
  handleGeneratePartChapters,
  setDetailPart,
  countOutlinesInRange,
  setPartOutlinesRenderLimit,
  partOutlinesRenderBatchSize,
}) => {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-serif font-bold text-lg text-book-text-main">部分大纲</h3>
        <div className="flex items-center gap-2">
          {partOutlines.length ? (
            <>
              {canContinuePartOutlines ? (
                <BookButton
                  size="sm"
                  variant="ghost"
                  onClick={() => openPartOutlinesModal('continue')}
                  disabled={regeneratingPartKey !== null}
                  title={partCoveredChapters ? `继续生成（当前已覆盖到第${partCoveredChapters}章）` : '继续生成部分大纲'}
                >
                  <Play size={16} className="mr-1" />
                  继续生成
                </BookButton>
              ) : null}
              <BookButton
                size="sm"
                variant="ghost"
                onClick={() => setIsDeleteLatestPartsModalOpen(true)}
                disabled={deletingLatestParts || regeneratingPartKey !== null || maxDeletablePartCount === 0}
                title={
                  maxDeletablePartCount === 0
                    ? '至少需要保留 1 个部分大纲，当前无法删除'
                    : '删除最后 N 个部分大纲（会级联删除对应章节大纲）'
                }
              >
                <Trash2 size={16} className={`mr-1 ${deletingLatestParts ? 'animate-spin' : ''}`} />
                {deletingLatestParts ? '删除中…' : '删除最新'}
              </BookButton>
              <BookButton
                size="sm"
                variant="ghost"
                onClick={() => setIsRegenerateLatestPartsModalOpen(true)}
                disabled={regeneratingPartKey !== null || regeneratingLatestParts || !partOutlines.length}
                title="重生成最新 N 个部分大纲（会级联删除对应章节大纲/内容/向量数据）"
              >
                <RefreshCw size={16} className={`mr-1 ${regeneratingLatestParts ? 'animate-spin' : ''}`} />
                {regeneratingLatestParts ? '重生成中…' : '重生成最新'}
              </BookButton>
              <BookButton
                size="sm"
                variant="ghost"
                onClick={handleRegenerateLastPartOutline}
                disabled={regeneratingPartKey !== null}
                title="重生成最后一个部分大纲（会删除该部分对应章节大纲/内容/向量数据）"
              >
                <Sparkles size={16} className={`mr-1 ${regeneratingPartKey === 'last' ? 'animate-spin' : ''}`} />
                {regeneratingPartKey === 'last' ? '重生成中…' : '重生成最后'}
              </BookButton>
              <BookButton
                size="sm"
                variant="ghost"
                onClick={handleRegenerateAllPartOutlines}
                disabled={regeneratingPartKey !== null}
                title="重生成所有部分大纲（会删除所有章节大纲/内容/向量数据）"
              >
                <Sparkles size={16} className={`mr-1 ${regeneratingPartKey === 'all' ? 'animate-spin' : ''}`} />
                {regeneratingPartKey === 'all' ? '重生成中…' : '重生成全部'}
              </BookButton>
            </>
          ) : (
            <BookButton
              size="sm"
              onClick={() => openPartOutlinesModal('generate')}
              disabled={regeneratingPartKey !== null}
            >
              <Sparkles size={16} className="mr-1" /> 生成部分大纲
            </BookButton>
          )}
        </div>
      </div>

      {partLoading ? (
        <div className="text-center py-20 text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30">
          加载中...
        </div>
      ) : partOutlines.length ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-sm text-book-text-muted">
            <span>进度：{partProgress?.completed_parts ?? 0}/{partProgress?.total_parts ?? partOutlines.length}</span>
            <button
              onClick={() => safeNavigate(`/write/${projectId}`)}
              className="text-book-primary hover:text-book-primary-light transition-colors font-bold"
            >
              前往写作台 →
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {visiblePartOutlines.map((part: any) => (
              <OutlinesPartCard
                key={part.part_number}
                part={part}
                regeneratingPartKey={regeneratingPartKey}
                generatingPartChapters={generatingPartChapters}
                setDetailPart={setDetailPart}
                handleRegeneratePartOutline={handleRegeneratePartOutline}
                handleGeneratePartChapters={handleGeneratePartChapters}
                countOutlinesInRange={countOutlinesInRange}
              />
            ))}
          </div>

          {remainingPartOutlines > 0 ? (
            <div className="flex justify-center">
              <BookButton
                size="sm"
                variant="ghost"
                onClick={() => setPartOutlinesRenderLimit((prev) => prev + partOutlinesRenderBatchSize)}
              >
                加载更多部分大纲（剩余 {remainingPartOutlines}）
              </BookButton>
            </div>
          ) : null}
        </div>
      ) : (
        <div className="text-center py-20 text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30">
          <Share size={48} className="mx-auto mb-4 opacity-50" />
          <p>尚未生成部分大纲。生成后可在此查看进度与内容。</p>
        </div>
      )}
    </div>
  );
};
