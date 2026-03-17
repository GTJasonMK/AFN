import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Database, Loader2, RefreshCw, ScrollText } from 'lucide-react';
import { BookButton } from '../ui/BookButton';
import { writerApi } from '../../api/writer';
import { useToast } from '../feedback/Toast';
import {
  NovelDialogIntro,
  NovelDialogMetric,
  NovelDialogMetricGrid,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from './novel/NovelDialogPrimitives';

const countChars = (text: string) => text.replace(/\s/g, '').length;

interface ChapterSummaryViewProps {
  projectId: string;
  chapterNumber: number;
}

export const ChapterSummaryView: React.FC<ChapterSummaryViewProps> = ({
  projectId,
  chapterNumber,
}) => {
  const { addToast } = useToast();
  const [realSummary, setRealSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isIngestingRag, setIsIngestingRag] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const chapter = await writerApi.getChapter(projectId, chapterNumber);
      setRealSummary(chapter.real_summary || null);
    } catch (e) {
      console.error(e);
      addToast('获取摘要数据失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast, chapterNumber, projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleIngestRag = async () => {
    setIsIngestingRag(true);
    try {
      const chapter = await writerApi.getChapter(projectId, chapterNumber);
      const content = chapter.content || '';
      await writerApi.updateChapter(projectId, chapterNumber, content, { triggerRag: true });
      addToast('RAG处理完成', 'success');
      await fetchData();
    } catch (e) {
      console.error(e);
      addToast('RAG处理失败', 'error');
    } finally {
      setIsIngestingRag(false);
    }
  };

  const wordCount = useMemo(() => {
    if (!realSummary) return 0;
    return countChars(realSummary);
  }, [realSummary]);

  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-[28px] border border-book-border/45 bg-book-bg-paper/72 p-10">
        <Loader2 size={24} className="animate-spin text-book-primary" />
      </div>
    );
  }

  if (!realSummary || !realSummary.trim()) {
    return (
      <NovelDialogStack>
        <NovelDialogIntro
          eyebrow="Summary Empty"
          title="摘要还没有生成"
          description="章节摘要会在执行 RAG 处理后自动生成，用来压缩章节信息，并为后续章节生成提供稳定上下文。"
          tone="warning"
        >
          <div className="flex flex-wrap gap-2">
            <span className="story-pill">第 {chapterNumber} 章</span>
            <span className="story-pill">等待首次 RAG 入库</span>
          </div>
        </NovelDialogIntro>

        <NovelDialogMetricGrid>
          <NovelDialogMetric label="当前状态" value="未生成" note="先执行 RAG 处理，摘要和分析会一起刷新。" />
          <NovelDialogMetric label="适用场景" value="续写前" note="适合在生成新章节前先确认上下文压缩是否完整。" />
        </NovelDialogMetricGrid>

        <NovelDialogSection
          eyebrow="Next Action"
          title="生成章节摘要"
          description="会同步刷新摘要、分析、索引和向量上下文。"
          actions={(
            <BookButton
              variant="secondary"
              size="sm"
              onClick={handleIngestRag}
              disabled={Boolean(isIngestingRag)}
            >
              <Database size={14} />
              {isIngestingRag ? '入库中…' : '生成摘要'}
            </BookButton>
          )}
        >
          <NovelDialogSurface className="text-sm leading-relaxed text-book-text-sub">
            当前章节还没有可供回看的摘要记录。完成首次入库后，这里会展示压缩后的章节概览与后续写作参考。
          </NovelDialogSurface>
        </NovelDialogSection>
      </NovelDialogStack>
    );
  }

  return (
    <NovelDialogStack>
      <NovelDialogSection
        eyebrow="Summary Stage"
        title="章节摘要（RAG）"
        description="确认摘要是否足够概括当前章节，保证后续章节生成能抓住主要推进点。"
        actions={(
          <>
            <BookButton variant="ghost" size="sm" onClick={fetchData}>
              <RefreshCw size={14} />
            </BookButton>
            <BookButton
              variant="ghost"
              size="sm"
              onClick={handleIngestRag}
              disabled={Boolean(isIngestingRag)}
              title="重新执行RAG处理（会刷新摘要/分析/索引/向量库）"
            >
              <Database size={14} />
              {isIngestingRag ? '入库中…' : '重新入库'}
            </BookButton>
          </>
        )}
      >
        <NovelDialogMetricGrid>
          <NovelDialogMetric label="摘要字数" value={wordCount} note="当前章节摘要压缩后的有效字数。" />
          <NovelDialogMetric
            label="当前状态"
            value={isIngestingRag ? '处理中' : '已生成'}
            note="可在正文或蓝图调整后重新入库刷新结果。"
          />
        </NovelDialogMetricGrid>
      </NovelDialogSection>

      <NovelDialogSurface className="space-y-4 p-5">
        <div className="flex items-center gap-2 text-book-text-main">
          <ScrollText size={16} className="text-book-primary" />
          <div className="font-semibold">摘要正文</div>
        </div>
        <div className="font-serif text-[1.02rem] leading-8 text-book-text-main whitespace-pre-wrap">
          {realSummary}
        </div>
      </NovelDialogSurface>
    </NovelDialogStack>
  );
};
