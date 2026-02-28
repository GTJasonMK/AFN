import React from 'react';
import { Trash2, RefreshCw, Sparkles, Play, Share } from 'lucide-react';
import { BookButton } from '../../components/ui/BookButton';
import { BookCard } from '../../components/ui/BookCard';

export type OutlinesTabProps = {
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

  partLoading: boolean;
  partOutlines: any[];
  visiblePartOutlines: any[];
  remainingPartOutlines: number;
  partProgress: any | null;
  canContinuePartOutlines: boolean;
  partCoveredChapters: number;
  maxDeletablePartCount: number;
  deletingLatestParts: boolean;
  regeneratingLatestParts: boolean;
  regeneratingPartKey: string | null;
  generatingPartChapters: number | null;
  setIsDeleteLatestPartsModalOpen: (open: boolean) => void;
  setIsRegenerateLatestPartsModalOpen: (open: boolean) => void;
  openPartOutlinesModal: (mode: 'generate' | 'continue') => void | Promise<void>;
  handleRegenerateLastPartOutline: () => void | Promise<void>;
  handleRegenerateAllPartOutlines: () => void | Promise<void>;
  handleRegeneratePartOutline: (partNumber: number) => void | Promise<void>;
  handleGeneratePartChapters: (part: any) => void | Promise<void>;
  setDetailPart: (part: any) => void;
  countOutlinesInRange: (startChapter: number, endChapter: number) => number;
  setPartOutlinesRenderLimit: React.Dispatch<React.SetStateAction<number>>;
  partOutlinesRenderBatchSize: number;
};

export const OutlinesTab: React.FC<OutlinesTabProps> = ({
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
  partLoading,
  partOutlines,
  visiblePartOutlines,
  remainingPartOutlines,
  partProgress,
  canContinuePartOutlines,
  partCoveredChapters,
  maxDeletablePartCount,
  deletingLatestParts,
  regeneratingLatestParts,
  regeneratingPartKey,
  generatingPartChapters,
  setIsDeleteLatestPartsModalOpen,
  setIsRegenerateLatestPartsModalOpen,
  openPartOutlinesModal,
  handleRegenerateLastPartOutline,
  handleRegenerateAllPartOutlines,
  handleRegeneratePartOutline,
  handleGeneratePartChapters,
  setDetailPart,
  countOutlinesInRange,
  setPartOutlinesRenderLimit,
  partOutlinesRenderBatchSize,
}) => {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 space-y-10">
      {/* Chapter Outlines */}
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
              {visibleChapterOutlines.map((o: any) => {
                const chapterNumber = Number(o.chapter_number);
                const ch = chaptersByNumber.get(chapterNumber);
                const status = String(ch?.generation_status || 'not_generated');
                const isCompleted = status === 'successful' || status === 'completed';

                return (
                  <BookCard
                    key={chapterNumber}
                    className="p-5 hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => safeNavigate(`/write/${projectId}?chapter=${chapterNumber}`)}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <div className="font-serif font-bold text-book-text-main truncate">
                            第{chapterNumber}章：{o.title || '（未命名）'}
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
                          {ch?.word_count ? `字数 ${ch.word_count} · ` : ''}
                          状态 {status}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            openOutlineEditor(o);
                          }}
                          className="text-xs text-book-primary font-bold hover:underline"
                          title="编辑章节标题/摘要"
                        >
                          编辑
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRegenerateOutline(chapterNumber);
                          }}
                          className="text-xs text-book-accent font-bold hover:underline"
                          title="重生成该章大纲（遵循串行生成原则：非最后一章将级联删除后续大纲）"
                        >
                          重生成
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
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
                      {o.summary || '（暂无摘要）'}
                    </div>
                  </BookCard>
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

      {/* Part Outlines */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="font-serif font-bold text-lg text-book-text-main">部分大纲</h3>
          <div className="flex items-center gap-2">
            {partOutlines.length ? (
              <>
                {canContinuePartOutlines ? (
                  <BookButton
                    size="sm"
                    variant="ghost"
                    onClick={() => openPartOutlinesModal('continue')}
                    disabled={regeneratingPartKey !== null}
                    title={partCoveredChapters ? `继续生成（当前已覆盖到第${partCoveredChapters}章）` : '继续生成部分大纲'}
                  >
                    <Play size={16} className="mr-1" />
                    继续生成
                  </BookButton>
                ) : null}
                <BookButton
                  size="sm"
                  variant="ghost"
                  onClick={() => setIsDeleteLatestPartsModalOpen(true)}
                  disabled={deletingLatestParts || regeneratingPartKey !== null || maxDeletablePartCount === 0}
                  title={
                    maxDeletablePartCount === 0
                      ? '至少需要保留 1 个部分大纲，当前无法删除'
                      : '删除最后 N 个部分大纲（会级联删除对应章节大纲）'
                  }
                >
                  <Trash2 size={16} className={`mr-1 ${deletingLatestParts ? 'animate-spin' : ''}`} />
                  {deletingLatestParts ? '删除中…' : '删除最新'}
                </BookButton>
                <BookButton
                  size="sm"
                  variant="ghost"
                  onClick={() => setIsRegenerateLatestPartsModalOpen(true)}
                  disabled={regeneratingPartKey !== null || regeneratingLatestParts || !partOutlines.length}
                  title="重生成最新 N 个部分大纲（会级联删除对应章节大纲/内容/向量数据）"
                >
                  <RefreshCw size={16} className={`mr-1 ${regeneratingLatestParts ? 'animate-spin' : ''}`} />
                  {regeneratingLatestParts ? '重生成中…' : '重生成最新'}
                </BookButton>
                <BookButton
                  size="sm"
                  variant="ghost"
                  onClick={handleRegenerateLastPartOutline}
                  disabled={regeneratingPartKey !== null}
                  title="重生成最后一个部分大纲（会删除该部分对应章节大纲/内容/向量数据）"
                >
                  <Sparkles size={16} className={`mr-1 ${regeneratingPartKey === 'last' ? 'animate-spin' : ''}`} />
                  {regeneratingPartKey === 'last' ? '重生成中…' : '重生成最后'}
                </BookButton>
                <BookButton
                  size="sm"
                  variant="ghost"
                  onClick={handleRegenerateAllPartOutlines}
                  disabled={regeneratingPartKey !== null}
                  title="重生成所有部分大纲（会删除所有章节大纲/内容/向量数据）"
                >
                  <Sparkles size={16} className={`mr-1 ${regeneratingPartKey === 'all' ? 'animate-spin' : ''}`} />
                  {regeneratingPartKey === 'all' ? '重生成中…' : '重生成全部'}
                </BookButton>
              </>
            ) : (
              <BookButton
                size="sm"
                onClick={() => openPartOutlinesModal('generate')}
                disabled={regeneratingPartKey !== null}
              >
                <Sparkles size={16} className="mr-1" /> 生成部分大纲
              </BookButton>
            )}
          </div>
        </div>

        {partLoading ? (
          <div className="text-center py-20 text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30">
            加载中...
          </div>
        ) : partOutlines.length ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm text-book-text-muted">
              <span>进度：{partProgress?.completed_parts ?? 0}/{partProgress?.total_parts ?? partOutlines.length}</span>
              <button
                onClick={() => safeNavigate(`/write/${projectId}`)}
                className="text-book-primary hover:text-book-primary-light transition-colors font-bold"
              >
                前往写作台 →
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {visiblePartOutlines.map((p: any) => {
                const start = Number(p.start_chapter || 0);
                const end = Number(p.end_chapter || 0);
                const totalChaptersInPart = start > 0 && end >= start ? end - start + 1 : 0;
                const outlinesInPart = totalChaptersInPart > 0
                  ? countOutlinesInRange(start, end)
                  : 0;

                return (
                  <BookCard
                    key={p.part_number}
                    className="p-5 hover:shadow-md transition-shadow"
                    hover
                    onClick={() => setDetailPart(p)}
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="min-w-0">
                        <div className="font-serif font-bold text-book-text-main truncate">
                          第{p.part_number}部分：{p.title}
                        </div>
                        <div className="text-xs text-book-text-muted mt-1">
                          章节 {p.start_chapter}–{p.end_chapter} · 状态 {p.generation_status} · {p.progress ?? 0}%
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setDetailPart(p);
                          }}
                          className="text-xs text-book-primary font-bold hover:underline"
                          title="查看完整部分大纲详情"
                        >
                          详情
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRegeneratePartOutline(Number(p.part_number));
                          }}
                          className="text-xs text-book-accent font-bold hover:underline"
                          disabled={regeneratingPartKey !== null}
                          title="重生成该部分大纲（遵循串行生成原则：非最后部分将提示级联删除确认）"
                        >
                          {regeneratingPartKey === String(p.part_number) ? '重生成中…' : '重生成'}
                        </button>
                        <span className="text-xs bg-book-bg px-2 py-1 rounded text-book-text-sub whitespace-nowrap">
                          {p.theme || '主题'}
                        </span>
                      </div>
                    </div>
                    <div className="text-sm text-book-text-secondary leading-relaxed line-clamp-4 whitespace-pre-wrap">
                      {p.summary}
                    </div>

                    <div className="mt-3 flex items-center justify-between gap-2">
                      <div className="text-xs text-book-text-muted">
                        章节大纲：{totalChaptersInPart ? `${outlinesInPart}/${totalChaptersInPart}` : '—'}
                      </div>
                      <BookButton
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleGeneratePartChapters(p);
                        }}
                        disabled={generatingPartChapters !== null || regeneratingPartKey !== null}
                        title="基于该部分大纲生成该部分范围内的章节大纲"
                      >
                        <Sparkles size={14} className={`mr-1 ${generatingPartChapters === Number(p.part_number) ? 'animate-spin' : ''}`} />
                        {generatingPartChapters === Number(p.part_number) ? '生成中…' : '生成章节大纲'}
                      </BookButton>
                    </div>
                  </BookCard>
                );
              })}
            </div>

            {remainingPartOutlines > 0 ? (
              <div className="flex justify-center">
                <BookButton
                  size="sm"
                  variant="ghost"
                  onClick={() => setPartOutlinesRenderLimit((prev) => prev + partOutlinesRenderBatchSize)}
                >
                  加载更多部分大纲（剩余 {remainingPartOutlines}）
                </BookButton>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="text-center py-20 text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30">
            <Share size={48} className="mx-auto mb-4 opacity-50" />
            <p>尚未生成部分大纲。生成后可在此查看进度与内容。</p>
          </div>
        )}
      </div>
    </div>
  );
};
