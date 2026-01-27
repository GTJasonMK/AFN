import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { BookInput } from '../ui/BookInput';
import { BookButton } from '../ui/BookButton';
import { useToast } from '../feedback/Toast';
import { useSSE } from '../../hooks/useSSE';

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
      <div className="space-y-4">
        <p className="text-sm text-book-text-secondary">
          基于当前的蓝图和已有的章节内容，自动续写后续章节大纲。
        </p>
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
        {progress && (
          <div className="text-xs text-book-primary animate-pulse font-medium">
            {progress}
          </div>
        )}
      </div>
    </Modal>
  );
};
