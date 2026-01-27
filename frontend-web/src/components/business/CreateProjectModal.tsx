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
  const [novelCreateMode, setNovelCreateMode] = useState<'ai' | 'free'>('ai');
  const [codingCreateMode, setCodingCreateMode] = useState<'ai' | 'empty'>('ai');
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // 每次打开时，根据入口重置类型，避免“上次选择”带来误操作
  // 其它字段也清空，确保新建流程可预期
  React.useEffect(() => {
    if (isOpen) {
      setType(defaultType);
      setNovelCreateMode('ai');
      setCodingCreateMode('ai');
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
        const skipInspiration = novelCreateMode === 'free';
        const newProject = await novelsApi.create({
          title,
          initial_prompt: prompt,
          skip_inspiration: skipInspiration,
        });
        navigate(skipInspiration ? `/novel/${newProject.id}` : `/inspiration/${newProject.id}`);
      } else {
        const skipConversation = codingCreateMode === 'empty';
        const newProject = await codingApi.create({
          title,
          initial_prompt: prompt,
          skip_conversation: skipConversation,
        });
        navigate(skipConversation ? `/coding/detail/${newProject.id}` : `/coding/inspiration/${newProject.id}`);
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

          {/* Create Mode */}
          <div className="space-y-1.5">
            <label className="block text-sm font-bold text-book-text-sub ml-1">
              创建模式
            </label>
            {type === 'novel' ? (
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setNovelCreateMode('ai')}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    novelCreateMode === 'ai'
                      ? 'border-book-primary bg-book-primary/5 text-book-text-main'
                      : 'border-book-border bg-book-bg-paper text-book-text-muted hover:border-book-primary/40'
                  }`}
                >
                  <div className="text-sm font-bold">AI 灵感对话（推荐）</div>
                  <div className="text-[11px] mt-1 leading-relaxed">
                    先对话打磨设定，再生成蓝图与大纲。
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setNovelCreateMode('free')}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    novelCreateMode === 'free'
                      ? 'border-book-primary bg-book-primary/5 text-book-text-main'
                      : 'border-book-border bg-book-bg-paper text-book-text-muted hover:border-book-primary/40'
                  }`}
                >
                  <div className="text-sm font-bold">自由创作</div>
                  <div className="text-[11px] mt-1 leading-relaxed">
                    跳过灵感对话，直接进入项目详情（可手动生成蓝图）。
                  </div>
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setCodingCreateMode('ai')}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    codingCreateMode === 'ai'
                      ? 'border-book-primary bg-book-primary/5 text-book-text-main'
                      : 'border-book-border bg-book-bg-paper text-book-text-muted hover:border-book-primary/40'
                  }`}
                >
                  <div className="text-sm font-bold">AI 需求分析（推荐）</div>
                  <div className="text-[11px] mt-1 leading-relaxed">
                    先对话澄清需求，再生成架构蓝图。
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setCodingCreateMode('empty')}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    codingCreateMode === 'empty'
                      ? 'border-book-primary bg-book-primary/5 text-book-text-main'
                      : 'border-book-border bg-book-bg-paper text-book-text-muted hover:border-book-primary/40'
                  }`}
                >
                  <div className="text-sm font-bold">空项目</div>
                  <div className="text-[11px] mt-1 leading-relaxed">
                    跳过需求对话，直接进入项目详情（可手动生成蓝图）。
                  </div>
                </button>
              </div>
            )}
          </div>
          
          <div className="space-y-1.5">
            <label className="block text-sm font-bold text-book-text-sub ml-1">
              {type === 'novel' ? '灵感种子 / 备注（可选）' : '需求描述 / 备注（可选）'}
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
