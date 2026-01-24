import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { BookInput, BookTextarea } from '../ui/BookInput';
import { BookButton } from '../ui/BookButton';
import { novelsApi } from '../../api/novels';
import { codingApi } from '../../api/coding';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Code } from 'lucide-react';

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  defaultType?: 'novel' | 'coding';
}

export const CreateProjectModal: React.FC<CreateProjectModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  defaultType = 'novel',
}) => {
  const [type, setType] = useState<'novel' | 'coding'>(defaultType);
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // 每次打开时，根据入口重置类型，避免“上次选择”带来误操作
  // 其它字段也清空，确保新建流程可预期
  React.useEffect(() => {
    if (isOpen) {
      setType(defaultType);
      setTitle('');
      setPrompt('');
      setLoading(false);
    }
  }, [isOpen, defaultType]);

  const handleSubmit = async () => {
    if (!title.trim()) return;
    
    setLoading(true);
    try {
      if (type === 'novel') {
        const newProject = await novelsApi.create({
          title,
          initial_prompt: prompt,
          skip_inspiration: false 
        });
        navigate(`/inspiration/${newProject.id}`);
      } else {
        const newProject = await codingApi.create({
          title,
          initial_prompt: prompt,
          skip_conversation: false
        });
        // Navigate to coding inspiration (reusing existing chat page but with different mode handling ideally)
        // For now, we route to a specific coding inspiration path to differentiate
        navigate(`/coding/inspiration/${newProject.id}`);
      }
      
      onClose();
      if (onSuccess) onSuccess();
    } catch (error) {
      console.error('Failed to create project:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="开启新项目"
      footer={
        <>
          <BookButton variant="ghost" onClick={onClose}>
            取消
          </BookButton>
          <BookButton 
            variant="primary" 
            onClick={handleSubmit} 
            disabled={loading || !title.trim()}
          >
            {loading ? '创建中...' : '开始创作'}
          </BookButton>
        </>
      }
    >
      <div className="space-y-6">
        {/* Type Selection */}
        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={() => setType('novel')}
            className={`p-4 rounded-lg border-2 flex flex-col items-center gap-2 transition-all ${
              type === 'novel' 
                ? 'border-book-primary bg-book-primary/5 text-book-primary' 
                : 'border-book-border bg-book-bg-paper text-book-text-muted hover:border-book-primary/50'
            }`}
          >
            <BookOpen size={24} />
            <span className="font-bold text-sm">长篇小说</span>
          </button>
          
          <button
            onClick={() => setType('coding')}
            className={`p-4 rounded-lg border-2 flex flex-col items-center gap-2 transition-all ${
              type === 'coding' 
                ? 'border-book-primary bg-book-primary/5 text-book-primary' 
                : 'border-book-border bg-book-bg-paper text-book-text-muted hover:border-book-primary/50'
            }`}
          >
            <Code size={24} />
            <span className="font-bold text-sm">Prompt 工程</span>
          </button>
        </div>

        <div className="space-y-4">
          <BookInput
            label="项目名称"
            placeholder={type === 'novel' ? "给你的故事起个名字..." : "项目名称..."}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
          />
          
          <div className="space-y-1.5">
            <label className="block text-sm font-bold text-book-text-sub ml-1">
              {type === 'novel' ? '灵感种子 (可选)' : '需求描述 (可选)'}
            </label>
            <BookTextarea
              placeholder={type === 'novel' 
                ? "简单描述你的想法，AI将协助你完善..." 
                : "描述你想开发的软件系统..."}
              rows={4}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </div>
        </div>
      </div>
    </Modal>
  );
};
