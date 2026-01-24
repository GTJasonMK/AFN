import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { BookButton } from '../ui/BookButton';
import { useToast } from '../feedback/Toast';
import { apiClient } from '../../api/client';
import { Upload } from 'lucide-react';

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
      footer={
        <div className="flex justify-end gap-2">
          <BookButton variant="ghost" onClick={onClose}>取消</BookButton>
          <BookButton variant="primary" onClick={handleImport} disabled={loading || !file}>
            {loading ? '导入中...' : '开始导入'}
          </BookButton>
        </div>
      }
    >
      <div className="space-y-6 text-center">
        <div className="border-2 border-dashed border-book-border rounded-lg p-8 flex flex-col items-center justify-center hover:bg-book-bg transition-colors cursor-pointer relative">
            <input 
                type="file" 
                accept=".txt" 
                onChange={handleFileChange}
                className="absolute inset-0 opacity-0 cursor-pointer"
            />
            <Upload size={32} className="text-book-text-muted mb-2" />
            <p className="text-sm text-book-text-main font-bold">
                {file ? file.name : "点击选择 TXT 文件"}
            </p>
            <p className="text-xs text-book-text-muted mt-1">支持自动识别章节</p>
        </div>
      </div>
    </Modal>
  );
};
