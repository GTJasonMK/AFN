import React, { useEffect, useMemo, useState } from 'react';
import { Modal } from '../ui/Modal';
import { BookInput } from '../ui/BookInput';
import { BookButton } from '../ui/BookButton';
import { useSSE } from '../../hooks/useSSE';
import { useToast } from '../feedback/Toast';

type PartOutlineGenerateMode = 'generate' | 'continue';

interface PartOutlineGenerateModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  mode: PartOutlineGenerateMode;
  totalChapters: number;
  defaultChaptersPerPart?: number;
  currentCoveredChapters?: number;
  currentPartsCount?: number;
  onSuccess: () => void | Promise<void>;
}

const clampInt = (value: any, min: number, max: number, fallback: number) => {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(min, Math.min(max, Math.floor(n)));
};

export const PartOutlineGenerateModal: React.FC<PartOutlineGenerateModalProps> = ({
  isOpen,
  onClose,
  projectId,
  mode,
  totalChapters,
  defaultChaptersPerPart,
  currentCoveredChapters,
  currentPartsCount,
  onSuccess,
}) => {
  const { addToast } = useToast();
  const [targetChapters, setTargetChapters] = useState<number>(Math.max(10, totalChapters || 10));
  const [chaptersPerPart, setChaptersPerPart] = useState<number>(defaultChaptersPerPart || 25);
  const [limitParts, setLimitParts] = useState<number | ''>('');
  const [running, setRunning] = useState(false);
  const [progressText, setProgressText] = useState('');
  const [progress, setProgress] = useState<{ current: number; total: number } | null>(null);

  const endpoint = useMemo(() => {
    const safeProjectId = String(projectId || '').trim();
    if (!safeProjectId) return null;
    return mode === 'continue'
      ? `/writer/novels/${safeProjectId}/parts/continue-stream`
      : `/writer/novels/${safeProjectId}/parts/generate-stream`;
  }, [mode, projectId]);

  const { connect, disconnect, isConnected } = useSSE((event, data) => {
    if (event === 'progress') {
      const msg = typeof data?.message === 'string' ? data.message : '';
      const current = Number(data?.current_part || 0);
      const total = Number(data?.total_parts || 0);
      const status = String(data?.status || '');

      if (msg) setProgressText(msg);
      else if (status === 'starting') setProgressText('正在初始化…');
      else if (current && total) setProgressText(`正在生成第 ${current}/${total} 部分…`);
      else setProgressText('生成中…');

      if (total > 0) {
        setProgress({ current: Math.max(0, current), total: Math.max(1, total) });
      } else {
        setProgress(null);
      }
      return;
    }

    if (event === 'complete') {
      setRunning(false);
      setProgressText(typeof data?.message === 'string' ? data.message : '生成完成');
      setProgress(null);
      addToast(typeof data?.message === 'string' ? data.message : '生成完成', 'success');
      Promise.resolve(onSuccess())
        .catch((e) => console.error(e))
        .finally(() => onClose());
      return;
    }

    if (event === 'error') {
      setRunning(false);
      const saved = Number((data as any)?.saved_count || 0);
      const msg =
        typeof (data as any)?.message === 'string'
          ? String((data as any).message)
          : (data instanceof Error ? data.message : '生成失败');
      addToast(saved > 0 ? `${msg}（已保存 ${saved} 个部分）` : msg, 'error');
      setProgressText(saved > 0 ? `${msg}（已保存 ${saved} 个部分）` : msg);
      setProgress(null);
      if (saved > 0) {
        Promise.resolve(onSuccess()).catch((e) => console.error(e));
      }
    }
  });

  useEffect(() => {
    if (!isOpen) {
      disconnect();
      setRunning(false);
      return;
    }
    // 打开弹窗时重置参数与进度（保持行为可预期）
    setRunning(false);
    setProgressText('');
    setProgress(null);

    const safeTotal = Math.max(10, Number(totalChapters || 10));
    const safePerPart = clampInt(defaultChaptersPerPart ?? 25, 10, 100, 25);

    if (mode === 'continue' && currentCoveredChapters && currentCoveredChapters > 0) {
      setTargetChapters(Math.min(safeTotal, Math.max(currentCoveredChapters + 1, safeTotal)));
    } else {
      setTargetChapters(safeTotal);
    }
    setChaptersPerPart(safePerPart);
    setLimitParts('');
  }, [currentCoveredChapters, defaultChaptersPerPart, disconnect, isOpen, mode, totalChapters]);

  const description = useMemo(() => {
    if (mode === 'continue') {
      const covered = currentCoveredChapters ? `当前已覆盖到第${currentCoveredChapters}章` : '将从最后一个部分继续生成';
      const parts = currentPartsCount ? `（已有${currentPartsCount}个部分）` : '';
      return `${covered}${parts}；不会删除已生成的部分大纲。`;
    }
    return '从第1部分开始生成，会覆盖并重建全部部分大纲（不会自动删除你的章节正文，但后续生成会以新结构为准）。';
  }, [currentCoveredChapters, currentPartsCount, mode]);

  const progressPercent = useMemo(() => {
    if (!progress) return null;
    if (progress.total <= 0) return null;
    const pct = (progress.current / progress.total) * 100;
    return Math.max(0, Math.min(100, Number.isFinite(pct) ? pct : 0));
  }, [progress]);

  const handleStart = async () => {
    if (!endpoint) return;
    if (running || isConnected) return;

    const safeTarget = clampInt(targetChapters, 10, Math.max(10, totalChapters || 10), Math.max(10, totalChapters || 10));
    const safePerPart = clampInt(chaptersPerPart, 10, 100, defaultChaptersPerPart || 25);

    // continue 模式下：目标章节不能小于“已覆盖到的章节+1”（否则没意义）
    if (mode === 'continue' && currentCoveredChapters && safeTarget <= currentCoveredChapters) {
      addToast(`目标章节需大于当前覆盖章节（当前已覆盖到第${currentCoveredChapters}章）`, 'error');
      return;
    }

    const body: any = {
      total_chapters: safeTarget,
      chapters_per_part: safePerPart,
    };
    if (mode === 'continue' && limitParts !== '') {
      body.count = clampInt(limitParts, 1, 100, 1);
    }

    setRunning(true);
    setProgressText('正在初始化…');
    setProgress(null);

    try {
      await connect(endpoint, body);
    } catch (e) {
      console.error(e);
      setRunning(false);
      addToast('启动失败（请检查后端与网络）', 'error');
    }
  };

  const handleClose = () => {
    if (running || isConnected) {
      disconnect();
    }
    setRunning(false);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={mode === 'continue' ? '继续生成部分大纲' : '生成部分大纲'}
      maxWidthClassName="max-w-2xl"
      footer={
        <div className="flex justify-end gap-2">
          <BookButton variant="ghost" onClick={handleClose}>
            {running || isConnected ? '停止' : '取消'}
          </BookButton>
          <BookButton variant="primary" onClick={handleStart} disabled={running || isConnected || !endpoint}>
            {running || isConnected ? '生成中…' : (mode === 'continue' ? '开始继续生成' : '开始生成')}
          </BookButton>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
          {description}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <BookInput
            label={`目标章节（覆盖到第 N 章，≤ ${Math.max(10, totalChapters || 10)}）`}
            type="number"
            min={10}
            max={Math.max(10, totalChapters || 10)}
            value={targetChapters}
            onChange={(e) => setTargetChapters(parseInt(e.target.value, 10) || 10)}
            disabled={running || isConnected}
          />
          <BookInput
            label="每部分章节数（10-100）"
            type="number"
            min={10}
            max={100}
            value={chaptersPerPart}
            onChange={(e) => setChaptersPerPart(parseInt(e.target.value, 10) || 25)}
            disabled={running || isConnected}
          />
        </div>

        {mode === 'continue' ? (
          <BookInput
            label="限制新增部分数量（可选）"
            type="number"
            min={1}
            max={100}
            value={limitParts}
            onChange={(e) => {
              const v = e.target.value.trim();
              setLimitParts(v === '' ? '' : (parseInt(v, 10) || 1));
            }}
            disabled={running || isConnected}
            placeholder="留空则生成全部剩余部分"
          />
        ) : null}

        {running || isConnected ? (
          <div className="space-y-2">
            <div className="text-xs text-book-primary animate-pulse font-medium">
              {progressText || '生成中…'}
            </div>
            {typeof progressPercent === 'number' ? (
              <div className="w-full h-2 rounded bg-book-bg border border-book-border/40 overflow-hidden">
                <div
                  className="h-2 bg-book-primary transition-all duration-500"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </Modal>
  );
};

