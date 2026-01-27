import React, { useCallback, useMemo, useState } from 'react';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';
import { BookTextarea } from '../ui/BookInput';
import { useToast } from '../feedback/Toast';
import { writerApi, PromptPreviewResponse } from '../../api/writer';
import { Eye, Copy, RefreshCw, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

interface ChapterPromptPreviewViewProps {
  projectId: string;
  chapterNumber: number;
  writingNotes?: string;
  onChangeWritingNotes?: (value: string) => void;
}

export const ChapterPromptPreviewView: React.FC<ChapterPromptPreviewViewProps> = ({
  projectId,
  chapterNumber,
  writingNotes,
  onChangeWritingNotes,
}) => {
  const { addToast } = useToast();

  const [localNotes, setLocalNotes] = useState('');
  const notes = writingNotes ?? localNotes;
  const setNotes = (value: string) => {
    if (onChangeWritingNotes) onChangeWritingNotes(value);
    else setLocalNotes(value);
  };

  const [useRag, setUseRag] = useState(true);
  const [isRetry, setIsRetry] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<PromptPreviewResponse | null>(null);

  const [showSystem, setShowSystem] = useState(false);
  const [showUser, setShowUser] = useState(false);

  const sections = useMemo(() => {
    const map = data?.prompt_sections || {};
    return Object.entries(map).filter(([, v]) => Boolean((v || '').trim()));
  }, [data]);

  const handlePreview = useCallback(async () => {
    if (!chapterNumber) return;
    setLoading(true);
    try {
      const res = await writerApi.previewChapterPrompt(projectId, chapterNumber, {
        writingNotes: notes?.trim() || undefined,
        isRetry,
        useRag,
      });
      setData(res);
      addToast('提示词预览已生成', 'success');
    } catch (e) {
      console.error(e);
      setData(null);
      addToast('提示词预览失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast, chapterNumber, isRetry, notes, projectId, useRag]);

  const copyText = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      addToast(`已复制：${label}`, 'success');
    } catch (e) {
      console.error(e);
      addToast('复制失败（可能缺少剪贴板权限）', 'error');
    }
  };

  const rag = data?.rag_statistics;

  return (
    <div className="space-y-4">
      <BookCard className="p-4 space-y-4">
        <div className="flex items-center justify-between gap-2">
          <div className="font-bold text-book-text-main flex items-center gap-2">
            <Sparkles size={16} className="text-book-primary" />
            提示词预览
          </div>
          <BookButton variant="primary" size="sm" onClick={handlePreview} disabled={loading}>
            <Eye size={14} className="mr-1" />
            {loading ? '生成中…' : '预览'}
          </BookButton>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm text-book-text-main">
            <input
              type="checkbox"
              className="rounded border-book-border text-book-primary focus:ring-book-primary"
              checked={useRag}
              onChange={(e) => setUseRag(e.target.checked)}
              disabled={loading}
            />
            <span className="font-bold">启用 RAG</span>
          </label>

          <label className="flex items-center gap-2 text-sm text-book-text-main">
            <input
              type="checkbox"
              className="rounded border-book-border text-book-primary focus:ring-book-primary"
              checked={isRetry}
              onChange={(e) => setIsRetry(e.target.checked)}
              disabled={loading}
            />
            <span className="font-bold">重生成模式</span>
          </label>
        </div>

        <BookTextarea
          label="写作指令（可选）"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={5}
          placeholder="例如：本章重点描写主角内心变化，减少对话，多用动作推动剧情…"
        />
      </BookCard>

      {data && (
        <BookCard className="p-4 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div className="font-bold text-book-text-main">统计</div>
            <BookButton variant="ghost" size="sm" onClick={handlePreview} disabled={loading}>
              <RefreshCw size={14} className={`mr-1 ${loading ? 'animate-spin' : ''}`} />
              刷新
            </BookButton>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs text-book-text-muted">
            <div className="bg-book-bg p-3 rounded-lg border border-book-border/40">
              <div className="font-bold text-book-text-main mb-1">长度 / tokens</div>
              <div>字符：{data.total_length}</div>
              <div>估算 tokens：{data.estimated_tokens}</div>
            </div>
            <div className="bg-book-bg p-3 rounded-lg border border-book-border/40">
              <div className="font-bold text-book-text-main mb-1">RAG</div>
              <div>chunks：{rag?.chunk_count ?? 0}</div>
              <div>summaries：{rag?.summary_count ?? 0}</div>
              <div>压缩后长度：{rag?.context_length ?? 0}</div>
            </div>
          </div>

          {(rag?.query_main || (rag?.query_characters || []).length || (rag?.query_foreshadowing || []).length) ? (
            <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/40 space-y-1">
              {rag?.query_main ? <div>主查询：{rag?.query_main}</div> : null}
              {(rag?.query_characters || []).length ? (
                <div>角色查询：{(rag?.query_characters || []).join(' / ')}</div>
              ) : null}
              {(rag?.query_foreshadowing || []).length ? (
                <div>伏笔查询：{(rag?.query_foreshadowing || []).join(' / ')}</div>
              ) : null}
            </div>
          ) : null}
        </BookCard>
      )}

      {data && (
        <div className="space-y-3">
          <BookCard className="p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="font-bold text-book-text-main">系统提示词</div>
              <div className="flex items-center gap-2">
                <BookButton variant="ghost" size="sm" onClick={() => setShowSystem((v) => !v)}>
                  {showSystem ? <ChevronUp size={14} className="mr-1" /> : <ChevronDown size={14} className="mr-1" />}
                  {showSystem ? '收起' : '展开'}
                </BookButton>
                <BookButton variant="secondary" size="sm" onClick={() => copyText(data.system_prompt, '系统提示词')}>
                  <Copy size={14} className="mr-1" />
                  复制
                </BookButton>
              </div>
            </div>
            {showSystem && (
              <pre className="mt-3 text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed bg-book-bg-paper p-3 rounded-lg border border-book-border/40 overflow-auto">
                {data.system_prompt}
              </pre>
            )}
          </BookCard>

          <BookCard className="p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="font-bold text-book-text-main">用户提示词（写作上下文）</div>
              <div className="flex items-center gap-2">
                <BookButton variant="ghost" size="sm" onClick={() => setShowUser((v) => !v)}>
                  {showUser ? <ChevronUp size={14} className="mr-1" /> : <ChevronDown size={14} className="mr-1" />}
                  {showUser ? '收起' : '展开'}
                </BookButton>
                <BookButton variant="secondary" size="sm" onClick={() => copyText(data.user_prompt, '用户提示词')}>
                  <Copy size={14} className="mr-1" />
                  复制
                </BookButton>
              </div>
            </div>
            {showUser && (
              <pre className="mt-3 text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed bg-book-bg-paper p-3 rounded-lg border border-book-border/40 overflow-auto">
                {data.user_prompt}
              </pre>
            )}
          </BookCard>

          {sections.length > 0 && (
            <BookCard className="p-4">
              <div className="font-bold text-book-text-main mb-3">分段预览</div>
              <div className="space-y-3">
                {sections.map(([key, value]) => (
                  <div key={key} className="rounded-lg border border-book-border/40 bg-book-bg p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="font-bold text-book-primary text-sm truncate">{key}</div>
                      <BookButton variant="ghost" size="sm" onClick={() => copyText(value, key)}>
                        <Copy size={14} className="mr-1" />
                        复制
                      </BookButton>
                    </div>
                    <pre className="mt-2 text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed">
                      {value}
                    </pre>
                  </div>
                ))}
              </div>
            </BookCard>
          )}
        </div>
      )}
    </div>
  );
};
