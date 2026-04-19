import React from 'react';
import { Wand2 } from 'lucide-react';
import { BookCard } from '../../ui/BookCard';

interface ContentOptimizationStatusCardProps {
  statusText: string;
  currentParagraph: number | null;
  totalParagraphs: number | null;
}

export const ContentOptimizationStatusCard: React.FC<
  ContentOptimizationStatusCardProps
> = ({ statusText, currentParagraph, totalParagraphs }) => {
  return (
    <BookCard className="p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-bold text-book-text-main">
          <Wand2 size={16} className="text-book-primary" />
          正文优化
        </div>
        <div className="text-xs text-book-text-muted">
          状态：{statusText}
          {typeof currentParagraph === 'number' &&
          typeof totalParagraphs === 'number'
            ? ` · 段落 ${currentParagraph + 1}/${totalParagraphs}`
            : null}
        </div>
      </div>
    </BookCard>
  );
};
