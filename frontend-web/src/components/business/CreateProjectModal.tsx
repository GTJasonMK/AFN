import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { BookInput, BookTextarea } from '../ui/BookInput';
import { BookButton } from '../ui/BookButton';
import { novelsApi } from '../../api/novels';
import { codingApi } from '../../api/coding';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Code } from 'lucide-react';
import {
  NovelDialogIntro,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from './novel/NovelDialogPrimitives';

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  defaultType?: 'novel' | 'coding';
  codingEnabled?: boolean;
}

export const CreateProjectModal: React.FC<CreateProjectModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  defaultType = 'novel',
  codingEnabled = true,
}) => {
  const [type, setType] = useState<'novel' | 'coding'>(defaultType);
  const [novelCreateMode, setNovelCreateMode] = useState<'ai' | 'free'>('ai');
  const [codingCreateMode, setCodingCreateMode] = useState<'ai' | 'empty'>('ai');
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const isNovel = type === 'novel';
  const activeCreateMode = isNovel ? novelCreateMode : codingCreateMode;

  // 每次打开时，根据入口重置类型，避免"上次选择"带来误操作
  // 其它字段也清空，确保新建流程可预期
  React.useEffect(() => {
    if (isOpen) {
      // 如果编程项目功能关闭，强制使用 novel 类型
      setType(codingEnabled ? defaultType : 'novel');
      setNovelCreateMode('ai');
      setCodingCreateMode('ai');
      setTitle('');
      setPrompt('');
      setLoading(false);
    }
  }, [isOpen, defaultType, codingEnabled]);

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
      maxWidthClassName="max-w-2xl"
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
      <NovelDialogStack>
        <NovelDialogIntro
          eyebrow={isNovel ? 'Story Project' : 'Prompt Project'}
          title={isNovel ? '开始一部新小说' : '开始一个新 Prompt 项目'}
          description={
            isNovel
              ? '先决定标题和启动方式。你可以走灵感对话生成蓝图，也可以直接进入小说详情页开始自由创作。'
              : '先决定标题和启动方式。你可以走需求分析对话，也可以直接创建空项目。'
          }
        >
          <div className="flex flex-wrap gap-2">
            <span className="story-pill">{isNovel ? '小说创作入口' : 'Prompt 工程入口'}</span>
            <span className="story-pill">
              {activeCreateMode === 'ai' ? 'AI 引导模式' : activeCreateMode === 'free' ? '自由创作模式' : '空项目模式'}
            </span>
          </div>
        </NovelDialogIntro>

        {codingEnabled ? (
          <NovelDialogSection
            eyebrow="Project Type"
            title="项目类型"
            description="这里只决定启动流向，不影响项目创建后的核心数据结构。"
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <button
                onClick={() => setType('novel')}
                className={`rounded-[24px] border px-4 py-4 text-left transition-all ${
                  type === 'novel'
                    ? 'border-book-primary/40 bg-book-primary/8 text-book-primary'
                    : 'border-book-border/50 bg-book-bg-paper/80 text-book-text-muted hover:border-book-primary/30'
                }`}
              >
                <div className="flex items-center gap-3">
                  <BookOpen size={22} />
                  <div>
                    <div className="text-sm font-semibold">长篇小说</div>
                    <div className="mt-1 text-xs leading-relaxed">用于故事蓝图、卷章结构和写作台链路。</div>
                  </div>
                </div>
              </button>

              <button
                onClick={() => setType('coding')}
                className={`rounded-[24px] border px-4 py-4 text-left transition-all ${
                  type === 'coding'
                    ? 'border-book-primary/40 bg-book-primary/8 text-book-primary'
                    : 'border-book-border/50 bg-book-bg-paper/80 text-book-text-muted hover:border-book-primary/30'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Code size={22} />
                  <div>
                    <div className="text-sm font-semibold">Prompt工程</div>
                    <div className="mt-1 text-xs leading-relaxed">用于需求澄清、架构蓝图和工程工作台。</div>
                  </div>
                </div>
              </button>
            </div>
          </NovelDialogSection>
        ) : null}

        <NovelDialogSection
          eyebrow="Project Setup"
          title="基础信息"
          description={isNovel ? '给作品命名，并决定是否从灵感对话进入蓝图阶段。' : '给项目命名，并决定是否通过 AI 对话先整理需求。'}
        >
          <div className="space-y-4">
            <BookInput
              label="项目名称"
              placeholder={isNovel ? '给你的故事起个名字…' : '项目名称…'}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              autoFocus
            />

            <div className="space-y-3">
              <div className="ml-1 text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                创建模式
              </div>

              {isNovel ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  <button
                    type="button"
                    onClick={() => setNovelCreateMode('ai')}
                    className={`rounded-[22px] border px-4 py-4 text-left transition-all ${
                      novelCreateMode === 'ai'
                        ? 'border-book-primary/40 bg-book-primary/8 text-book-text-main'
                        : 'border-book-border/50 bg-book-bg-paper/80 text-book-text-muted hover:border-book-primary/30'
                    }`}
                  >
                    <div className="text-sm font-semibold">AI 灵感对话（推荐）</div>
                    <div className="mt-2 text-xs leading-relaxed">先对话打磨设定，再生成蓝图与大纲。</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setNovelCreateMode('free')}
                    className={`rounded-[22px] border px-4 py-4 text-left transition-all ${
                      novelCreateMode === 'free'
                        ? 'border-book-primary/40 bg-book-primary/8 text-book-text-main'
                        : 'border-book-border/50 bg-book-bg-paper/80 text-book-text-muted hover:border-book-primary/30'
                    }`}
                  >
                    <div className="text-sm font-semibold">自由创作</div>
                    <div className="mt-2 text-xs leading-relaxed">跳过灵感对话，直接进入项目详情页后再手动补蓝图。</div>
                  </button>
                </div>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  <button
                    type="button"
                    onClick={() => setCodingCreateMode('ai')}
                    className={`rounded-[22px] border px-4 py-4 text-left transition-all ${
                      codingCreateMode === 'ai'
                        ? 'border-book-primary/40 bg-book-primary/8 text-book-text-main'
                        : 'border-book-border/50 bg-book-bg-paper/80 text-book-text-muted hover:border-book-primary/30'
                    }`}
                  >
                    <div className="text-sm font-semibold">AI 需求分析（推荐）</div>
                    <div className="mt-2 text-xs leading-relaxed">先对话澄清需求，再生成架构蓝图。</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setCodingCreateMode('empty')}
                    className={`rounded-[22px] border px-4 py-4 text-left transition-all ${
                      codingCreateMode === 'empty'
                        ? 'border-book-primary/40 bg-book-primary/8 text-book-text-main'
                        : 'border-book-border/50 bg-book-bg-paper/80 text-book-text-muted hover:border-book-primary/30'
                    }`}
                  >
                    <div className="text-sm font-semibold">空项目</div>
                    <div className="mt-2 text-xs leading-relaxed">跳过需求对话，直接进入项目详情页。</div>
                  </button>
                </div>
              )}
            </div>

            <BookTextarea
              label={isNovel ? '灵感种子 / 备注（可选）' : '需求描述 / 备注（可选）'}
              placeholder={isNovel ? '简单描述你的想法，AI 将协助你完善…' : '描述你想开发的软件系统…'}
              rows={4}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </div>
        </NovelDialogSection>

        <NovelDialogSurface className="text-xs leading-relaxed text-book-text-muted">
          提示：项目创建后仍然可以在详情页继续补全蓝图、设定或需求描述。这里更像启动入口，不必一次性把所有信息填满。
        </NovelDialogSurface>
      </NovelDialogStack>
    </Modal>
  );
};
