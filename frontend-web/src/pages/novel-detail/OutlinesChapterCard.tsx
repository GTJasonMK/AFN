import React from 'react';
import { BookCard } from '../../components/ui/BookCard';

type OutlinesChapterCardProps = {
  projectId: string;
  outline: any;
  chapter: any;
  safeNavigate: (to: string) => void | Promise<void>;
  openOutlineEditor: (outline: any) => void | Promise<void>;
  handleRegenerateOutline: (chapterNumber: number) => void | Promise<void>;
};

export const OutlinesChapterCard: React.FC<OutlinesChapterCardProps> = ({
  projectId,
  outline,
  chapter,
  safeNavigate,
  openOutlineEditor,
  handleRegenerateOutline,
}) => {
  const chapterNumber = Number(outline.chapter_number);
  const status = String(chapter?.generation_status || 'not_generated');
  const isCompleted = status === 'successful' || status === 'completed';

  return (
    <BookCard
      className="p-5 hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => safeNavigate(`/write/${projectId}?chapter=${chapterNumber}`)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <div className="font-serif font-bold text-book-text-main truncate">
              第{chapterNumber}章：{outline.title || '（未命名）'}
            </div>
            <span
              className={`text-[10px] px-2 py-0.5 rounded-full border ${
                isCompleted
                  ? 'bg-green-500/10 text-green-700 border-green-500/20'
                  : 'bg-book-bg text-book-text-muted border-book-border/40'
              }`}
            >
              {isCompleted ? '已生成' : '仅大纲'}
            </span>
          </div>
          <div className="text-xs text-book-text-muted mt-1">
            {chapter?.word_count ? `字数 ${chapter.word_count} · ` : ''}
            状态 {status}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={(event) => {
              event.stopPropagation();
              openOutlineEditor(outline);
            }}
            className="text-xs text-book-primary font-bold hover:underline"
            title="编辑章节标题/摘要"
          >
            编辑
          </button>
          <button
            onClick={(event) => {
              event.stopPropagation();
              handleRegenerateOutline(chapterNumber);
            }}
            className="text-xs text-book-accent font-bold hover:underline"
            title="重生成该章大纲（遵循串行生成原则：非最后一章将级联删除后续大纲）"
          >
            重生成
          </button>
          <button
            onClick={(event) => {
              event.stopPropagation();
              safeNavigate(`/write/${projectId}?chapter=${chapterNumber}`);
            }}
            className="text-xs text-book-text-sub font-bold hover:underline"
            title="打开写作台并定位章节"
          >
            打开
          </button>
        </div>
      </div>

      <div className="mt-3 text-sm text-book-text-secondary whitespace-pre-wrap leading-relaxed line-clamp-5">
        {outline.summary || '（暂无摘要）'}
      </div>
    </BookCard>
  );
};
