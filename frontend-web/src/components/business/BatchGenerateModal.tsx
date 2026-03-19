import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Modal } from '../ui/Modal';
import { BookInput } from '../ui/BookInput';
import { BookButton } from '../ui/BookButton';
import { useToast } from '../feedback/Toast';
import { useSSE } from '../../hooks/useSSE';
import {
  NovelDialogIntro,
  NovelDialogMetric,
  NovelDialogMetricGrid,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from './novel/NovelDialogPrimitives';

interface BatchGenerateModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  onSuccess: () => void;
  initialCount?: number;
  initialStartFrom?: number | '';
  latestOutlineChapterNumber?: number;
  needsPartOutlines?: boolean;
  partOutlineCount?: number;
  partOutlineMaxCoveredChapter?: number | null;
}

export const BatchGenerateModal: React.FC<BatchGenerateModalProps> = ({
  isOpen,
  onClose,
  projectId,
  onSuccess,
  initialCount,
  initialStartFrom,
  latestOutlineChapterNumber,
  needsPartOutlines,
  partOutlineCount,
  partOutlineMaxCoveredChapter,
}) => {
  const [count, setCount] = useState(10);
  const [startFrom, setStartFrom] = useState<number | ''>('');
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState('');
  const { addToast } = useToast();
  const prevOpenRef = useRef(false);

  useEffect(() => {
    if (!isOpen) {
      prevOpenRef.current = false;
      return;
    }
    if (prevOpenRef.current) return;
    prevOpenRef.current = true;

    const nextCountRaw = typeof initialCount === 'number' ? initialCount : 10;
    const nextCount = Math.max(1, Math.min(100, Math.floor(nextCountRaw || 10)));
    setCount(nextCount);
    setStartFrom(initialStartFrom === undefined ? '' : initialStartFrom);
    setProgress('');
    setGenerating(false);
  }, [initialCount, initialStartFrom, isOpen]);

  const { connect, disconnect } = useSSE((event, data) => {
    if (event === 'progress') {
      setProgress(`正在生成... (${data.generated_count}/${data.total_count})`);
    } else if (event === 'complete') {
      setGenerating(false);
      addToast(`成功生成 ${data.total_chapters} 章大纲`, 'success');
      onSuccess();
      onClose();
    } else if (event === 'error') {
      setGenerating(false);
      addToast(data.message, 'error');
    }
  });

  const resolvedStartChapter = useMemo(() => {
    const v = startFrom === '' ? null : Number(startFrom);
    if (v && Number.isFinite(v) && v > 0) return Math.floor(v);
    const latest = typeof latestOutlineChapterNumber === 'number' ? latestOutlineChapterNumber : Number.NaN;
    if (Number.isFinite(latest) && latest > 0) return Math.floor(latest) + 1;
    return 1;
  }, [latestOutlineChapterNumber, startFrom]);

  const resolvedEndChapter = useMemo(() => {
    const safeCount = Math.max(1, Math.min(100, Math.floor(Number(count) || 1)));
    return resolvedStartChapter + safeCount - 1;
  }, [count, resolvedStartChapter]);

  const safeCount = useMemo(() => Math.max(1, Math.min(100, Math.floor(Number(count) || 1))), [count]);
  const autoStartUnknown = useMemo(() => {
    if (startFrom !== '') return false;
    const latest = typeof latestOutlineChapterNumber === 'number' ? latestOutlineChapterNumber : Number.NaN;
    return !(Number.isFinite(latest) && latest >= 0);
  }, [latestOutlineChapterNumber, startFrom]);

  const startDisabledReason = useMemo(() => {
    if (!needsPartOutlines) return null;
    const c = Number(partOutlineCount || 0);
    if (!Number.isFinite(c) || c <= 0) {
      return '该项目需要先生成分部大纲，才能生成章节大纲。请先在项目详情页生成分部大纲。';
    }
    const coverMax = partOutlineMaxCoveredChapter;
    if (!autoStartUnknown && coverMax && Number.isFinite(coverMax) && coverMax > 0 && resolvedEndChapter > coverMax) {
      return `目标范围（第${resolvedStartChapter}-${resolvedEndChapter}章）超出分部大纲覆盖范围（当前覆盖到第${coverMax}章）。请先生成下一部分分部大纲，或缩小生成范围。`;
    }
    return null;
  }, [autoStartUnknown, needsPartOutlines, partOutlineCount, partOutlineMaxCoveredChapter, resolvedEndChapter, resolvedStartChapter]);

  const handleGenerate = async () => {
    if (startDisabledReason) {
      addToast(startDisabledReason, 'info');
      return;
    }
    setGenerating(true);
    setProgress('初始化...');
    // Connect to SSE stream
    await connect(`/writer/novels/${projectId}/chapter-outlines/generate-by-count`, {
      count: count,
      start_from: startFrom === '' ? undefined : Number(startFrom) // 留空则自动从当前最大章节号+1继续
    });
  };

  const handleCancel = () => {
    if (generating) {
        disconnect();
    }
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleCancel}
      title="批量生成章节大纲"
      footer={
        <div className="flex justify-end gap-2">
          <BookButton variant="ghost" onClick={handleCancel}>
            {generating ? '停止' : '取消'}
          </BookButton>
          <BookButton
            variant="primary"
            onClick={handleGenerate}
            disabled={generating || Boolean(startDisabledReason)}
            title={startDisabledReason || '开始生成章节大纲'}
          >
            {generating ? '生成中...' : '开始生成'}
          </BookButton>
        </div>
      }
    >
      <NovelDialogStack>
        <NovelDialogIntro
          eyebrow="Batch Outline"
          title="批量续写章节大纲"
          description="基于当前蓝图和已有章节状态，自动续写后续章节大纲。适合在主线结构稳定后批量补齐后续章节。"
        >
          <div className="flex flex-wrap gap-2">
            <span className="story-pill">蓝图稳定后执行</span>
            <span className="story-pill">支持指定起始章节</span>
          </div>
        </NovelDialogIntro>

        <NovelDialogMetricGrid>
          <NovelDialogMetric label="默认数量" value={count} note="可一次性生成 1-100 章大纲。" />
          <NovelDialogMetric
            label="起始方式"
            value={startFrom === '' ? '自动续写' : `从第 ${startFrom} 章开始`}
            note="留空时会自动从当前最大章节号的下一章开始。"
          />
        </NovelDialogMetricGrid>

        <NovelDialogSection
          eyebrow="Generation Setup"
          title="生成参数"
          description="建议先确认生成数量，再决定是否从指定章节号开始续写。"
        >
          <div className="grid gap-4 md:grid-cols-2">
            <BookInput 
              label="生成数量"
              type="number"
              min={1}
              max={100}
              value={count}
              onChange={e => setCount(parseInt(e.target.value) || 1)}
              disabled={generating}
            />
            <BookInput
              label="起始章节（可选）"
              type="number"
              min={1}
              value={startFrom}
              onChange={(e) => {
                const v = e.target.value.trim();
                setStartFrom(v === '' ? '' : (parseInt(v, 10) || 1));
              }}
              disabled={generating}
              placeholder="留空则自动续写到下一章"
            />
          </div>
        </NovelDialogSection>

        <NovelDialogSurface>
          <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
            Target
          </div>
          <div className="mt-3 text-sm font-semibold text-book-text-main">
            {autoStartUnknown
              ? `将自动续写后续 ${safeCount} 章大纲（起始章节由后端根据现有大纲决定）`
              : `将生成第 ${resolvedStartChapter}-${resolvedEndChapter} 章大纲`}
          </div>
          {startDisabledReason ? (
            <div className="mt-2 text-xs leading-relaxed text-red-500/90">
              {startDisabledReason}
            </div>
          ) : (
            <div className="mt-2 text-xs leading-relaxed text-book-text-sub">
              {needsPartOutlines
                ? (autoStartUnknown
                    ? '已检测到分部大纲约束；如需精确控制范围，建议填写「起始章节」。'
                    : '已检测到分部大纲约束：生成范围必须落在分部大纲覆盖内。')
                : '生成范围会在后端进行连贯性校验。'}
            </div>
          )}
        </NovelDialogSurface>

        {progress ? (
          <NovelDialogSurface>
            <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">Progress</div>
            <div className="mt-3 text-sm font-semibold text-book-primary animate-pulse">{progress}</div>
          </NovelDialogSurface>
        ) : null}
      </NovelDialogStack>
    </Modal>
  );
};
