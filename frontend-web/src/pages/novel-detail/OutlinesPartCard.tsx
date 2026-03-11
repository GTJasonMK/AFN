import React from 'react';
import { Sparkles } from 'lucide-react';
import { BookButton } from '../../components/ui/BookButton';
import { BookCard } from '../../components/ui/BookCard';

type OutlinesPartCardProps = {
  part: any;
  regeneratingPartKey: string | null;
  generatingPartChapters: number | null;
  setDetailPart: (part: any) => void;
  handleRegeneratePartOutline: (partNumber: number) => void | Promise<void>;
  handleGeneratePartChapters: (part: any) => void | Promise<void>;
  countOutlinesInRange: (startChapter: number, endChapter: number) => number;
};

export const OutlinesPartCard: React.FC<OutlinesPartCardProps> = ({
  part,
  regeneratingPartKey,
  generatingPartChapters,
  setDetailPart,
  handleRegeneratePartOutline,
  handleGeneratePartChapters,
  countOutlinesInRange,
}) => {
  const start = Number(part.start_chapter || 0);
  const end = Number(part.end_chapter || 0);
  const totalChaptersInPart = start > 0 && end >= start ? end - start + 1 : 0;
  const outlinesInPart = totalChaptersInPart > 0
    ? countOutlinesInRange(start, end)
    : 0;
  const partNumber = Number(part.part_number);
  const isRegeneratingCurrentPart = regeneratingPartKey === String(part.part_number);
  const isGeneratingCurrentPart = generatingPartChapters === partNumber;

  return (
    <BookCard
      className="p-5 hover:shadow-md transition-shadow"
      hover
      onClick={() => setDetailPart(part)}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="min-w-0">
          <div className="font-serif font-bold text-book-text-main truncate">
            第{part.part_number}部分：{part.title}
          </div>
          <div className="text-xs text-book-text-muted mt-1">
            章节 {part.start_chapter}–{part.end_chapter} · 状态 {part.generation_status} · {part.progress ?? 0}%
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={(event) => {
              event.stopPropagation();
              setDetailPart(part);
            }}
            className="text-xs text-book-primary font-bold hover:underline"
            title="查看完整部分大纲详情"
          >
            详情
          </button>
          <button
            onClick={(event) => {
              event.stopPropagation();
              handleRegeneratePartOutline(partNumber);
            }}
            className="text-xs text-book-accent font-bold hover:underline"
            disabled={regeneratingPartKey !== null}
            title="重生成该部分大纲（遵循串行生成原则：非最后部分将提示级联删除确认）"
          >
            {isRegeneratingCurrentPart ? '重生成中…' : '重生成'}
          </button>
          <span className="text-xs bg-book-bg px-2 py-1 rounded text-book-text-sub whitespace-nowrap">
            {part.theme || '主题'}
          </span>
        </div>
      </div>
      <div className="text-sm text-book-text-secondary leading-relaxed line-clamp-4 whitespace-pre-wrap">
        {part.summary}
      </div>

      <div className="mt-3 flex items-center justify-between gap-2">
        <div className="text-xs text-book-text-muted">
          章节大纲：{totalChaptersInPart ? `${outlinesInPart}/${totalChaptersInPart}` : '—'}
        </div>
        <BookButton
          variant="ghost"
          size="sm"
          onClick={(event) => {
            event.stopPropagation();
            handleGeneratePartChapters(part);
          }}
          disabled={generatingPartChapters !== null || regeneratingPartKey !== null}
          title="基于该部分大纲生成该部分范围内的章节大纲"
        >
          <Sparkles size={14} className={`mr-1 ${isGeneratingCurrentPart ? 'animate-spin' : ''}`} />
          {isGeneratingCurrentPart ? '生成中…' : '生成章节大纲'}
        </BookButton>
      </div>
    </BookCard>
  );
};
