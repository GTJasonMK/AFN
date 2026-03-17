import React, { useState } from 'react';
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
}

export const BatchGenerateModal: React.FC<BatchGenerateModalProps> = ({
  isOpen,
  onClose,
  projectId,
  onSuccess
}) => {
  const [count, setCount] = useState(10);
  const [startFrom, setStartFrom] = useState<number | ''>('');
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState('');
  const { addToast } = useToast();

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

  const handleGenerate = async () => {
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
          <BookButton variant="primary" onClick={handleGenerate} disabled={generating}>
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
