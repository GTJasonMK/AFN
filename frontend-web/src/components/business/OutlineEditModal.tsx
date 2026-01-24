import React, { useState, useEffect } from 'react';
import { Modal } from '../ui/Modal';
import { BookInput, BookTextarea } from '../ui/BookInput';
import { BookButton } from '../ui/BookButton';
import { writerApi, Chapter } from '../../api/writer';
import { useToast } from '../feedback/Toast';

interface OutlineEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  chapter: Chapter | null;
  projectId: string;
  onSuccess: () => void;
}

export const OutlineEditModal: React.FC<OutlineEditModalProps> = ({
  isOpen,
  onClose,
  chapter,
  projectId,
  onSuccess
}) => {
  const [title, setTitle] = useState('');
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();

  useEffect(() => {
    if (chapter) {
      setTitle(chapter.title);
      setSummary(chapter.summary || '');
    }
  }, [chapter]);

  const handleSave = async () => {
    if (!chapter) return;
    setLoading(true);
    try {
      await writerApi.updateOutline(projectId, chapter.chapter_number, title, summary);
      addToast('大纲更新成功', 'success');
      onSuccess();
      onClose();
    } catch (e) {
      console.error(e);
      addToast('更新失败', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`编辑大纲 - 第${chapter?.chapter_number}章`}
      footer={
        <div className="flex justify-end gap-2">
          <BookButton variant="ghost" onClick={onClose}>取消</BookButton>
          <BookButton variant="primary" onClick={handleSave} disabled={loading}>
            {loading ? '保存中...' : '保存'}
          </BookButton>
        </div>
      }
    >
      <div className="space-y-4">
        <BookInput 
          label="章节标题"
          value={title}
          onChange={e => setTitle(e.target.value)}
        />
        <BookTextarea 
          label="章节摘要"
          rows={6}
          value={summary}
          onChange={e => setSummary(e.target.value)}
        />
      </div>
    </Modal>
  );
};