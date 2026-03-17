import React, { useCallback, useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, Copy, Eye, RefreshCw } from 'lucide-react';
import { BookButton } from '../ui/BookButton';
import { BookTextarea } from '../ui/BookInput';
import { useToast } from '../feedback/Toast';
import { writerApi, type PromptPreviewResponse } from '../../api/writer';
import {
  NovelDialogIntro,
  NovelDialogMetric,
  NovelDialogMetricGrid,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from './novel/NovelDialogPrimitives';

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
    return Object.entries(map).filter(([, value]) => Boolean((value || '').trim()));
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
    <NovelDialogStack>
      <NovelDialogSection
        eyebrow="Prompt Console"
        title="构建本章提示词"
        description="调整写作指令、RAG 开关与重生成模式，确认这次生成会使用什么上下文。"
        actions={(
          <BookButton variant="primary" size="sm" onClick={handlePreview} disabled={loading}>
            <Eye size={14} />
            {loading ? '生成中…' : '预览'}
          </BookButton>
        )}
      >
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <span className="story-pill">第 {chapterNumber} 章</span>
            <span className="story-pill">{useRag ? '启用 RAG' : '关闭 RAG'}</span>
            <span className="story-pill">{isRetry ? '重生成模式' : '首次生成模式'}</span>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex items-center gap-2 rounded-[20px] border border-book-border/45 bg-book-bg/72 px-4 py-3 text-sm text-book-text-main">
              <input
                type="checkbox"
                className="rounded border-book-border text-book-primary focus:ring-book-primary"
                checked={useRag}
                onChange={(e) => setUseRag(e.target.checked)}
                disabled={loading}
              />
              <span className="font-semibold">启用 RAG 上下文</span>
            </label>

            <label className="flex items-center gap-2 rounded-[20px] border border-book-border/45 bg-book-bg/72 px-4 py-3 text-sm text-book-text-main">
              <input
                type="checkbox"
                className="rounded border-book-border text-book-primary focus:ring-book-primary"
                checked={isRetry}
                onChange={(e) => setIsRetry(e.target.checked)}
                disabled={loading}
              />
              <span className="font-semibold">重生成模式</span>
            </label>
          </div>

          <BookTextarea
            label="写作指令（可选）"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={6}
            placeholder="例如：本章重点描写主角内心变化，减少对话，多用动作推动剧情…"
          />
        </div>
      </NovelDialogSection>

      {!data ? (
        <NovelDialogIntro
          eyebrow="Preview State"
          title="等待生成预览"
          description="点击上方“预览”后，将在这里展示系统提示词、用户提示词、RAG 查询和分段内容。"
        >
          <div className="flex flex-wrap gap-2">
            <span className="story-pill">提示词尚未生成</span>
            <span className="story-pill">可先调整写作指令</span>
          </div>
        </NovelDialogIntro>
      ) : (
        <>
          <NovelDialogSection
            eyebrow="Prompt Stats"
            title="预览统计"
            description="确认这次提示词的长度、RAG 命中规模和查询结构是否符合预期。"
            actions={(
              <BookButton variant="ghost" size="sm" onClick={handlePreview} disabled={loading}>
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                刷新
              </BookButton>
            )}
          >
            <NovelDialogMetricGrid className="xl:grid-cols-4">
              <NovelDialogMetric label="字符长度" value={data.total_length} note="合成后完整提示词长度。" />
              <NovelDialogMetric label="估算 Tokens" value={data.estimated_tokens} note="用于粗略判断模型预算。" />
              <NovelDialogMetric label="RAG Chunks" value={rag?.chunk_count ?? 0} note="命中的上下文切片数量。" />
              <NovelDialogMetric label="摘要条目" value={rag?.summary_count ?? 0} note="参与压缩的摘要段数。" />
            </NovelDialogMetricGrid>

            {(rag?.query_main || (rag?.query_characters || []).length || (rag?.query_foreshadowing || []).length) ? (
              <NovelDialogSurface className="mt-4 space-y-2 text-sm leading-relaxed text-book-text-sub">
                {rag?.query_main ? <div>主查询：{rag.query_main}</div> : null}
                {(rag?.query_characters || []).length ? (
                  <div>角色查询：{(rag?.query_characters || []).join(' / ')}</div>
                ) : null}
                {(rag?.query_foreshadowing || []).length ? (
                  <div>伏笔查询：{(rag?.query_foreshadowing || []).join(' / ')}</div>
                ) : null}
              </NovelDialogSurface>
            ) : null}
          </NovelDialogSection>

          <NovelDialogSection
            eyebrow="Prompt Payload"
            title="系统与用户提示词"
            description="展开查看最终传给模型的系统提示词与用户提示词。"
          >
            <div className="space-y-4">
              <NovelDialogSurface>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-semibold text-book-text-main">系统提示词</div>
                  <div className="flex gap-2">
                    <BookButton variant="ghost" size="sm" onClick={() => setShowSystem((v) => !v)}>
                      {showSystem ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      {showSystem ? '收起' : '展开'}
                    </BookButton>
                    <BookButton variant="secondary" size="sm" onClick={() => copyText(data.system_prompt, '系统提示词')}>
                      <Copy size={14} />
                      复制
                    </BookButton>
                  </div>
                </div>
                {showSystem ? (
                  <pre className="mt-3 overflow-auto whitespace-pre-wrap rounded-[20px] border border-book-border/40 bg-book-bg-paper px-4 py-4 font-mono text-xs leading-relaxed text-book-text-main">
                    {data.system_prompt}
                  </pre>
                ) : null}
              </NovelDialogSurface>

              <NovelDialogSurface>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-semibold text-book-text-main">用户提示词（写作上下文）</div>
                  <div className="flex gap-2">
                    <BookButton variant="ghost" size="sm" onClick={() => setShowUser((v) => !v)}>
                      {showUser ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      {showUser ? '收起' : '展开'}
                    </BookButton>
                    <BookButton variant="secondary" size="sm" onClick={() => copyText(data.user_prompt, '用户提示词')}>
                      <Copy size={14} />
                      复制
                    </BookButton>
                  </div>
                </div>
                {showUser ? (
                  <pre className="mt-3 overflow-auto whitespace-pre-wrap rounded-[20px] border border-book-border/40 bg-book-bg-paper px-4 py-4 font-mono text-xs leading-relaxed text-book-text-main">
                    {data.user_prompt}
                  </pre>
                ) : null}
              </NovelDialogSurface>
            </div>
          </NovelDialogSection>

          {sections.length > 0 ? (
            <NovelDialogSection
              eyebrow="Prompt Sections"
              title="分段预览"
              description="拆开查看每个阶段的内容拼接，判断哪一段造成提示词膨胀或语义偏差。"
            >
              <div className="space-y-3">
                {sections.map(([key, value]) => (
                  <NovelDialogSurface key={key}>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-sm font-semibold text-book-primary">{key}</div>
                      <BookButton variant="ghost" size="sm" onClick={() => copyText(value, key)}>
                        <Copy size={14} />
                        复制
                      </BookButton>
                    </div>
                    <pre className="mt-3 whitespace-pre-wrap font-mono text-xs leading-relaxed text-book-text-main">
                      {value}
                    </pre>
                  </NovelDialogSurface>
                ))}
              </div>
            </NovelDialogSection>
          ) : null}
        </>
      )}
    </NovelDialogStack>
  );
};
