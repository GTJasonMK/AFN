import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';
import { Modal } from '../ui/Modal';
import { BookTextarea } from '../ui/BookInput';
import { useToast } from '../feedback/Toast';
import { writerApi } from '../../api/writer';
import { Files, RefreshCw, Check, Copy, Loader2 } from 'lucide-react';

const countChars = (text: string) => text.replace(/\s/g, '').length;

interface ChapterVersionsViewProps {
  projectId: string;
  chapterNumber: number;
  onSelectVersion?: (index: number) => void;
  onRetryVersion?: (index: number, customPrompt?: string) => void | Promise<void>;
}

export const ChapterVersionsView: React.FC<ChapterVersionsViewProps> = ({
  projectId,
  chapterNumber,
  onSelectVersion,
  onRetryVersion,
}) => {
  const { addToast } = useToast();
  const [versions, setVersions] = useState<string[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const chapter = await writerApi.getChapter(projectId, chapterNumber);
      const vs = Array.isArray(chapter.versions) ? chapter.versions : [];
      setVersions(vs);
      setSelectedIndex(typeof chapter.selected_version === 'number' ? chapter.selected_version : null);
    } catch (e) {
      console.error(e);
      addToast('获取版本数据失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast, chapterNumber, projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const items = useMemo(() => {
    return versions.map((content, idx) => ({
      idx,
      wordCount: countChars(content || ''),
      preview: (content || '').trim().slice(0, 120),
    }));
  }, [versions]);

  const [activeIndex, setActiveIndex] = useState<number>(0);

  useEffect(() => {
    if (typeof selectedIndex === 'number' && selectedIndex >= 0 && selectedIndex < versions.length) {
      setActiveIndex(selectedIndex);
    } else if (versions.length > 0 && activeIndex >= versions.length) {
      setActiveIndex(0);
    }
  }, [activeIndex, selectedIndex, versions.length]);

  const [retryIndex, setRetryIndex] = useState<number | null>(null);
  const [customPrompt, setCustomPrompt] = useState('');
  const retryContent = retryIndex === null ? '' : (versions[retryIndex] || '');

  const handleCopy = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      addToast(`已复制：${label}`, 'success');
    } catch (e) {
      console.error(e);
      addToast('复制失败（可能缺少剪贴板权限）', 'error');
    }
  };

  const handleSelectVersion = async (index: number) => {
    if (onSelectVersion) {
      onSelectVersion(index);
    } else {
      try {
        await writerApi.selectVersion(projectId, chapterNumber, index);
        setSelectedIndex(index);
        addToast('版本已选择', 'success');
      } catch (e) {
        console.error(e);
        addToast('选择版本失败', 'error');
      }
    }
  };

  const handleRetryVersion = async (index: number, prompt?: string) => {
    if (onRetryVersion) {
      await onRetryVersion(index, prompt);
      await fetchData();
    } else {
      try {
        await writerApi.retryVersion(projectId, chapterNumber, index, prompt);
        addToast('已提交重新生成任务', 'success');
        await fetchData();
      } catch (e) {
        console.error(e);
        addToast('重新生成失败', 'error');
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 size={24} className="animate-spin text-book-primary" />
      </div>
    );
  }

  if (!versions || versions.length === 0) {
    return (
      <div className="space-y-4">
        <BookCard className="p-4">
          <div className="font-bold text-book-text-main flex items-center gap-2">
            <Files size={16} className="text-book-primary" />
            暂无候选版本
          </div>
          <div className="text-xs text-book-text-muted mt-2 leading-relaxed">
            生成章节后，这里会显示多个候选版本供你选择与重试。
          </div>
        </BookCard>
      </div>
    );
  }

	  const currentContent = versions[activeIndex] || '';
	  const currentWordCount = countChars(currentContent || '');
	  const isSelected = typeof selectedIndex === 'number' && selectedIndex === activeIndex;

  return (
    <div className="space-y-4">
      <BookCard className="p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="font-bold text-book-text-main flex items-center gap-2">
            <Files size={16} className="text-book-primary" />
            版本管理
            <span className="text-xs text-book-text-muted font-normal">共 {versions.length} 个</span>
            {typeof selectedIndex === 'number' ? (
              <span className="text-xs text-book-text-muted font-normal"> 已选：版本 {selectedIndex + 1}</span>
            ) : null}
          </div>
          <BookButton variant="ghost" size="sm" onClick={fetchData}>
            <RefreshCw size={14} />
          </BookButton>
        </div>
	        <div className="text-[11px] text-book-text-muted mt-2 leading-relaxed">
	          提示：选择版本会更新后端"已选版本"，并同步刷新写作台编辑器内容（如有未保存修改会提示确认）。
	        </div>
	      </BookCard>

      <BookCard className="p-4">
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar">
          {items.map((it) => {
            const selected = typeof selectedIndex === 'number' && selectedIndex === it.idx;
            const active = activeIndex === it.idx;
            return (
              <button
                key={`tab-${it.idx}`}
                onClick={() => setActiveIndex(it.idx)}
                className={`
                  flex-none px-3 py-1.5 text-xs font-bold rounded-md border transition-all
                  ${active ? 'bg-book-bg border-book-primary/40 text-book-primary shadow-inner' : 'bg-book-bg-paper border-book-border/50 text-book-text-muted hover:text-book-text-main'}
                `}
                title={selected ? '已选版本' : '点击查看'}
              >
                版本 {it.idx + 1}
                {selected ? ' *' : ''}
              </button>
            );
          })}
        </div>
      </BookCard>

      <BookCard className="p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="font-bold text-book-text-main flex items-center gap-2">
            <span className="text-book-primary">版本 {activeIndex + 1}</span>
            {isSelected ? (
              <span className="inline-flex items-center gap-1 text-xs text-green-600">
                <Check size={14} /> 已选择
              </span>
            ) : null}
            <span className="text-xs text-book-text-muted font-mono">{currentWordCount}</span>
          </div>
          <BookButton
            variant="secondary"
            size="sm"
            onClick={() => handleCopy(currentContent || '', `版本 ${activeIndex + 1}`)}
            disabled={!currentContent}
            title="复制该版本全文"
          >
            <Copy size={14} className="mr-1" />
            复制
          </BookButton>
        </div>

        <div className="mt-3 max-h-[52vh] overflow-auto rounded-lg border border-book-border/40 bg-book-bg-paper p-3 custom-scrollbar">
          {currentContent && currentContent.trim() ? (
            <pre className="text-sm text-book-text-main whitespace-pre-wrap font-serif leading-relaxed">
              {currentContent}
            </pre>
          ) : (
            <div className="text-xs text-book-text-muted italic">（空内容）</div>
          )}
        </div>

	        <div className="mt-4 flex items-center justify-end gap-2">
	          <BookButton
	            variant={isSelected ? 'ghost' : 'primary'}
	            size="sm"
	            onClick={() => handleSelectVersion(activeIndex)}
	            disabled={isSelected}
          >
            {isSelected ? '已选择' : '选择该版本'}
          </BookButton>
          <BookButton
            variant="secondary"
            size="sm"
            onClick={() => {
              setRetryIndex(activeIndex);
              setCustomPrompt('');
            }}
            title="基于该版本重新生成（可输入优化提示词）"
          >
            <RefreshCw size={14} className="mr-1" />
            重新生成
          </BookButton>
        </div>
      </BookCard>

      <Modal
        isOpen={retryIndex !== null}
        onClose={() => setRetryIndex(null)}
        title={retryIndex === null ? '重新生成版本' : `重新生成：版本 ${retryIndex + 1}`}
        maxWidthClassName="max-w-2xl"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={() => setRetryIndex(null)}>
              取消
            </BookButton>
            <BookButton
              variant="primary"
              onClick={async () => {
                if (retryIndex === null) return;
                const promptText = customPrompt.trim();
                await handleRetryVersion(retryIndex, promptText ? promptText : undefined);
                setRetryIndex(null);
              }}
            >
              开始生成
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <BookTextarea
            label="优化提示词（可选）"
            rows={6}
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
            placeholder="例如：加强冲突、补足动机、提升画面感、减少口水对白…"
          />
          <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 leading-relaxed">
            说明：留空则按系统默认策略重生成该版本；填写则会把你的提示作为优化方向。本操作会更新版本列表，但不会自动覆盖你当前未保存的编辑内容。
          </div>

          {retryContent && retryContent.trim() ? (
            <div className="text-xs">
              <div className="font-bold text-book-text-main mb-2">该版本内容预览</div>
              <div className="max-h-40 overflow-auto rounded-lg border border-book-border/40 bg-book-bg-paper p-3 custom-scrollbar">
                <pre className="whitespace-pre-wrap text-book-text-main font-serif leading-relaxed">
                  {retryContent.trim().slice(0, 600)}
                  {retryContent.trim().length > 600 ? '\n...' : ''}
                </pre>
              </div>
            </div>
          ) : null}
        </div>
      </Modal>
    </div>
  );
};
