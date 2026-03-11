import React from 'react';
import { Play, RefreshCw, Share, Sparkles, Trash2 } from 'lucide-react';
import { BookButton } from '../../components/ui/BookButton';
import { OutlinesChapterCard } from './OutlinesChapterCard';

export type OutlinesChapterSectionProps = {
  projectId: string;
  blueprintData: any;
  loading: boolean;
  safeNavigate: (to: string) => void | Promise<void>;
  fetchProjectButton: () => void | Promise<void>;
  chapterOutlines: any[];
  visibleChapterOutlines: any[];
  remainingChapterOutlines: number;
  chaptersByNumber: Map<number, any>;
  openOutlineEditor: (outline: any) => void | Promise<void>;
  handleRegenerateOutline: (chapterNumber: number) => void | Promise<void>;
  setChapterOutlinesRenderLimit: React.Dispatch<React.SetStateAction<number>>;
  chapterOutlinesRenderBatchSize: number;
  setDeleteLatestCount: (n: number) => void;
  setIsDeleteLatestModalOpen: (open: boolean) => void;
  setRegenerateLatestCount: (n: number) => void;
  setRegenerateLatestPrompt: (text: string) => void;
  setIsRegenerateLatestModalOpen: (open: boolean) => void;
  setIsBatchModalOpen: (open: boolean) => void;
};

export const OutlinesChapterSection: React.FC<OutlinesChapterSectionProps> = ({
  projectId,
  blueprintData,
  loading,
  safeNavigate,
  fetchProjectButton,
  chapterOutlines,
  visibleChapterOutlines,
  remainingChapterOutlines,
  chaptersByNumber,
  openOutlineEditor,
  handleRegenerateOutline,
  setChapterOutlinesRenderLimit,
  chapterOutlinesRenderBatchSize,
  setDeleteLatestCount,
  setIsDeleteLatestModalOpen,
  setRegenerateLatestCount,
  setRegenerateLatestPrompt,
  setIsRegenerateLatestModalOpen,
  setIsBatchModalOpen,
}) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-serif font-bold text-lg text-book-text-main">章节大纲</h3>
        <div className="flex items-center gap-2">
          <BookButton
            size="sm"
            variant="ghost"
            onClick={() => {
              setDeleteLatestCount(Math.min(5, Math.max(1, chapterOutlines.length || 1)));
              setIsDeleteLatestModalOpen(true);
            }}
            disabled={!chapterOutlines.length}
            title="删除最新 N 章大纲（如这些章节已有内容，将级联删除章节内容与向量库数据）"
          >
            <Trash2 size={16} className="mr-1" /> 删除最新
          </BookButton>
          <BookButton
            size="sm"
            variant="ghost"
            onClick={() => {
              setRegenerateLatestCount(1);
              setRegenerateLatestPrompt('');
              setIsRegenerateLatestModalOpen(true);
            }}
            disabled={!chapterOutlines.length}
            title="重生成最新 N 章大纲（按串行生成原则：会级联删除后续大纲，再重生成起始章）"
          >
            <RefreshCw size={16} className="mr-1" /> 重生成最新
          </BookButton>
          <BookButton size="sm" variant="ghost" onClick={() => setIsBatchModalOpen(true)}>
            <Sparkles size={16} className="mr-1" /> 批量生成章节大纲
          </BookButton>
          <BookButton size="sm" variant="ghost" onClick={() => safeNavigate(`/write/${projectId}`)}>
            <Play size={16} className="mr-1" /> 前往写作台
          </BookButton>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-book-text-muted">
        <span>
          已生成 {chapterOutlines.length} 章大纲
          {blueprintData?.total_chapters ? ` / 计划 ${blueprintData.total_chapters} 章` : ''}
        </span>
        <button
          onClick={fetchProjectButton}
          className="text-book-primary font-bold hover:underline"
          disabled={loading}
        >
          刷新
        </button>
      </div>

      {chapterOutlines.length ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {visibleChapterOutlines.map((outline: any) => {
              const chapterNumber = Number(outline.chapter_number);
              const chapter = chaptersByNumber.get(chapterNumber);

              return (
                <OutlinesChapterCard
                  key={chapterNumber}
                  projectId={projectId}
                  outline={outline}
                  chapter={chapter}
                  safeNavigate={safeNavigate}
                  openOutlineEditor={openOutlineEditor}
                  handleRegenerateOutline={handleRegenerateOutline}
                />
              );
            })}
          </div>

          {remainingChapterOutlines > 0 ? (
            <div className="flex justify-center">
              <BookButton
                size="sm"
                variant="ghost"
                onClick={() => setChapterOutlinesRenderLimit((prev) => prev + chapterOutlinesRenderBatchSize)}
              >
                加载更多章节大纲（剩余 {remainingChapterOutlines}）
              </BookButton>
            </div>
          ) : null}
        </>
      ) : (
        <div className="text-center py-20 text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30">
          <Share size={48} className="mx-auto mb-4 opacity-50" />
          <p>尚未生成章节大纲。你可以先点击右上角“批量生成章节大纲”。</p>
        </div>
      )}
    </div>
  );
};
