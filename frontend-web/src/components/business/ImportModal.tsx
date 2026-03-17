import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { BookButton } from '../ui/BookButton';
import { useToast } from '../feedback/Toast';
import { apiClient } from '../../api/client';
import { Upload } from 'lucide-react';
import {
  NovelDialogIntro,
  NovelDialogMetric,
  NovelDialogMetricGrid,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from './novel/NovelDialogPrimitives';

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const ImportModal: React.FC<ImportModalProps> = ({
  isOpen,
  onClose,
  onSuccess
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleImport = async () => {
    if (!file) return;
    setLoading(true);
    
    // 1. Create empty project
    try {
        const title = file.name.replace('.txt', '');
        const createRes = await apiClient.post('/novels', {
            title,
            initial_prompt: "",
            skip_inspiration: true
        });
        const projectId = createRes.data.id;

        // 2. Import TXT
        const formData = new FormData();
        formData.append('file', file);
        
        await apiClient.post(`/novels/${projectId}/import-txt`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });

        // 3. Start Analysis
        await apiClient.post(`/novels/${projectId}/analyze`);

        addToast('导入成功，正在后台分析...', 'success');
        onSuccess();
        onClose();
    } catch (e) {
        console.error(e);
        addToast('导入失败', 'error');
    } finally {
        setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="导入小说 (TXT)"
      maxWidthClassName="max-w-2xl"
      footer={
        <div className="flex justify-end gap-2">
          <BookButton variant="ghost" onClick={onClose}>取消</BookButton>
          <BookButton variant="primary" onClick={handleImport} disabled={loading || !file}>
            {loading ? '导入中...' : '开始导入'}
          </BookButton>
        </div>
      }
    >
      <NovelDialogStack>
        <NovelDialogIntro
          eyebrow="TXT Import"
          title="从 TXT 快速建立小说项目"
          description="导入流程会先创建一个空项目，再上传 TXT 并立即启动后台分析。适合把已有长篇文本快速迁移进小说工作台。"
        >
          <div className="flex flex-wrap gap-2">
            <span className="story-pill">自动创建项目</span>
            <span className="story-pill">自动启动分析</span>
          </div>
        </NovelDialogIntro>

        <NovelDialogMetricGrid>
          <NovelDialogMetric
            label="当前文件"
            value={file ? '已选择' : '未选择'}
            note={file ? file.name : '请选择一个 TXT 文件作为导入源。'}
          />
          <NovelDialogMetric
            label="导入链路"
            value="创建 -> 导入 -> 分析"
            note="导入完成后会在后台继续做章节识别和结构分析。"
          />
        </NovelDialogMetricGrid>

        <NovelDialogSection
          eyebrow="Source File"
          title="选择 TXT 文件"
          description="支持自动识别章节。文件名会被用作默认项目标题，你也可以导入后再到详情页修改。"
        >
          <label className="relative block cursor-pointer">
            <input
              type="file"
              accept=".txt"
              onChange={handleFileChange}
              className="absolute inset-0 opacity-0"
            />
            <div className="flex min-h-[220px] flex-col items-center justify-center rounded-[28px] border-2 border-dashed border-book-border/55 bg-book-bg/65 px-6 py-8 text-center transition-all hover:border-book-primary/35 hover:bg-book-bg-paper/72">
              <Upload size={34} className="text-book-text-muted" />
              <div className="mt-4 text-base font-semibold text-book-text-main">
                {file ? file.name : '点击选择 TXT 文件'}
              </div>
              <div className="mt-2 text-sm leading-relaxed text-book-text-sub">
                支持自动识别章节标题与正文结构。
              </div>
            </div>
          </label>
        </NovelDialogSection>

        <NovelDialogSurface className="text-xs leading-relaxed text-book-text-muted">
          提示：导入后系统会立刻触发分析任务。如果文本体量较大，章节拆分和蓝图归纳会在后台继续执行一段时间。
        </NovelDialogSurface>
      </NovelDialogStack>
    </Modal>
  );
};
