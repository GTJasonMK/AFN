import React from 'react';
import { Play, RefreshCw, XCircle } from 'lucide-react';
import { MangaPromptProgress } from '../../../api/writer';
import { BookCard } from '../../ui/BookCard';
import { BookButton } from '../../ui/BookButton';

type MangaProgressCardProps = {
  showProgress: boolean;
  progress: MangaPromptProgress | null;
  progressStatus: string;
  generatingPrompts: boolean;
  isProgressRunning: boolean;
  cancelingPrompts: boolean;
  canResumeGeneration: boolean;
  progressPercent: number | null;
  onCancel: () => void | Promise<void>;
  onResume: () => void;
  onForceRestart: () => void;
};

export const MangaProgressCard: React.FC<MangaProgressCardProps> = ({
  showProgress,
  progress,
  progressStatus,
  generatingPrompts,
  isProgressRunning,
  cancelingPrompts,
  canResumeGeneration,
  progressPercent,
  onCancel,
  onResume,
  onForceRestart,
}) => {
  if (!showProgress) return null;

  return (
    <BookCard className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-bold text-book-text-main">
            生成进度：{progress?.stage_label || (generatingPrompts ? '处理中' : '未开始')}
            {progressStatus === 'completed' ? '（已完成）' : null}
            {progressStatus === 'cancelled' ? '（已取消）' : null}
          </div>
          <div className="mt-1 whitespace-pre-wrap text-xs leading-relaxed text-book-text-muted">
            {progress?.message || (generatingPrompts ? '生成中…（可在此查看进度）' : '')}
          </div>
        </div>
        <div className="flex flex-none items-center gap-2">
          {(generatingPrompts || isProgressRunning) && (
            <BookButton
              variant="ghost"
              size="sm"
              onClick={onCancel}
              disabled={cancelingPrompts}
            >
              <XCircle size={14} className="mr-1" />
              {cancelingPrompts ? '停止中…' : '停止生成'}
            </BookButton>
          )}
          {canResumeGeneration && !generatingPrompts && (
            <>
              <BookButton variant="primary" size="sm" onClick={onResume} disabled={cancelingPrompts}>
                <Play size={14} className="mr-1" />
                继续生成
              </BookButton>
              <BookButton variant="ghost" size="sm" onClick={onForceRestart} disabled={cancelingPrompts}>
                <RefreshCw size={14} className="mr-1" />
                强制重来
              </BookButton>
            </>
          )}
        </div>
      </div>

      {progressPercent !== null && (
        <div className="mt-3">
          <div className="overflow-hidden rounded-full bg-book-border/30">
            <div className="h-2 bg-book-primary" style={{ width: `${progressPercent}%` }} />
          </div>
          <div className="mt-1 text-[11px] text-book-text-muted">
            {progress?.current ?? 0}/{progress?.total ?? 0}（{progressPercent}%）
          </div>
        </div>
      )}
    </BookCard>
  );
};
