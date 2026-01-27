import React, { useMemo } from 'react';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';
import { Database, ScrollText } from 'lucide-react';
import { InsightCard } from './chapter/components/InsightCard';

const countChars = (text: string) => text.replace(/\s/g, '').length;

interface ChapterSummaryViewProps {
  realSummary?: string | null;
  onIngestRag?: () => void;
  isIngestingRag?: boolean;
}

export const ChapterSummaryView: React.FC<ChapterSummaryViewProps> = ({
  realSummary,
  onIngestRag,
  isIngestingRag,
}) => {
  const wordCount = useMemo(() => {
    if (!realSummary) return 0;
    return countChars(realSummary);
  }, [realSummary]);

  if (!realSummary || !realSummary.trim()) {
    return (
      <div className="space-y-4">
        <InsightCard
          icon={<ScrollText size={16} className="text-book-primary" />}
          title="暂无章节摘要"
          description="章节摘要会在执行 RAG 处理后自动生成，用于后续章节生成的上下文优化与连贯性保障。"
          actions={
            onIngestRag ? (
              <BookButton
                variant="secondary"
                size="sm"
                onClick={onIngestRag}
                disabled={Boolean(isIngestingRag)}
              >
                <Database size={14} className="mr-1" />
                {isIngestingRag ? '入库中…' : '生成摘要'}
              </BookButton>
            ) : null
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
          onIngestRag ? (
            <BookButton
              variant="ghost"
              size="sm"
              onClick={onIngestRag}
              disabled={Boolean(isIngestingRag)}
              title="重新执行RAG处理（会刷新摘要/分析/索引/向量库）"
            >
              <Database size={14} className="mr-1" />
              {isIngestingRag ? '入库中…' : '重新入库'}
            </BookButton>
          ) : null
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
