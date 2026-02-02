import React, { useMemo, useState, useEffect, useCallback } from 'react';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';
import { Database, ScrollText, Loader2, RefreshCw } from 'lucide-react';
import { InsightCard } from './chapter/components/InsightCard';
import { writerApi } from '../../api/writer';
import { useToast } from '../feedback/Toast';

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
      // 获取当前章节内容
      const chapter = await writerApi.getChapter(projectId, chapterNumber);
      const content = chapter.content || '';
      // 触发RAG处理
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
      <div className="flex items-center justify-center p-8">
        <Loader2 size={24} className="animate-spin text-book-primary" />
      </div>
    );
  }

  if (!realSummary || !realSummary.trim()) {
    return (
      <div className="space-y-4">
        <InsightCard
          icon={<ScrollText size={16} className="text-book-primary" />}
          title="暂无章节摘要"
          description="章节摘要会在执行 RAG 处理后自动生成，用于后续章节生成的上下文优化与连贯性保障。"
          actions={
            <BookButton
              variant="secondary"
              size="sm"
              onClick={handleIngestRag}
              disabled={Boolean(isIngestingRag)}
            >
              <Database size={14} className="mr-1" />
              {isIngestingRag ? '入库中...' : '生成摘要'}
            </BookButton>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <InsightCard
        icon={<ScrollText size={16} className="text-book-primary" />}
        title="章节摘要（RAG）"
        description={`字数：${wordCount}`}
        descriptionClassName="text-xs text-book-text-muted mt-1"
        actions={
          <div className="flex items-center gap-2">
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
              <Database size={14} className="mr-1" />
              {isIngestingRag ? '入库中...' : '重新入库'}
            </BookButton>
          </div>
        }
      />

      <BookCard className="p-4">
        <div className="text-sm text-book-text-main whitespace-pre-wrap leading-relaxed font-serif">
          {realSummary}
        </div>
      </BookCard>
    </div>
  );
};
