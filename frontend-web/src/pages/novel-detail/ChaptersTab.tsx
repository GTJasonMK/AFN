import React, { useCallback, useState } from 'react';
import { FileText, Plus, Download, Play } from 'lucide-react';
import { BookButton } from '../../components/ui/BookButton';
import { BookCard } from '../../components/ui/BookCard';
import { BookInput, BookTextarea } from '../../components/ui/BookInput';
import { ImportChapterModal } from '../../components/business/ImportChapterModal';

export type ChaptersTabProps = {
  projectId: string;
  completedChapters: any[];
  visibleCompletedChapters: any[];
  remainingCompletedChapters: number;
  setCompletedChaptersRenderLimit: React.Dispatch<React.SetStateAction<number>>;
  renderBatchSize: number;
  chaptersSearch: string;
  setChaptersSearch: (text: string) => void;
  selectedCompletedChapterNumber: number | null;
  setSelectedCompletedChapterNumber: (chapterNumber: number) => void;
  selectedCompletedChapter: any | null;
  selectedCompletedChapterLoading: boolean;
  exportSelectedChapter: (format: 'txt' | 'markdown') => void | Promise<void>;
  suggestedImportChapterNumber: number;
  onChapterImported: (chapterNumber: number) => void | Promise<void>;
  safeNavigate: (to: string) => void | Promise<void>;
};

export const ChaptersTab: React.FC<ChaptersTabProps> = ({
  projectId,
  completedChapters,
  visibleCompletedChapters,
  remainingCompletedChapters,
  setCompletedChaptersRenderLimit,
  renderBatchSize,
  chaptersSearch,
  setChaptersSearch,
  selectedCompletedChapterNumber,
  setSelectedCompletedChapterNumber,
  selectedCompletedChapter,
  selectedCompletedChapterLoading,
  exportSelectedChapter,
  suggestedImportChapterNumber,
  onChapterImported,
  safeNavigate,
}) => {
  const [isImportChapterModalOpen, setIsImportChapterModalOpen] = useState(false);
  const openImportChapterModal = useCallback(() => {
    setIsImportChapterModalOpen(true);
  }, []);

  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
      {completedChapters.length ? (
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
          <BookCard className="p-4 h-fit lg:sticky lg:top-6">
            <div className="flex items-center justify-between gap-2 mb-3">
              <div className="font-serif font-bold text-lg text-book-text-main">已完成章节</div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-book-text-muted whitespace-nowrap">{completedChapters.length} 章</span>
                <BookButton variant="secondary" size="sm" onClick={openImportChapterModal}>
                  <Plus size={14} className="mr-1" />
                  导入
                </BookButton>
              </div>
            </div>

            <div className="mb-3">
              <BookInput
                label="搜索"
                placeholder="章节号或标题"
                value={chaptersSearch}
                onChange={(e) => setChaptersSearch(e.target.value)}
              />
            </div>

            <div className="space-y-1 max-h-[calc(100vh-260px)] overflow-y-auto custom-scrollbar pr-1">
              {visibleCompletedChapters.map((c: any) => {
                const no = Number(c?.chapter_number || 0);
                const title = String(c?.title || '').trim();
                const isSelected = Number(selectedCompletedChapterNumber || 0) === no;
                return (
                  <button
                    key={`completed-${no}`}
                    onClick={() => setSelectedCompletedChapterNumber(no)}
                    className={`
                      w-full text-left px-3 py-2 rounded-lg border transition-all
                      ${isSelected ? 'bg-book-primary/10 border-book-primary/40' : 'bg-book-bg-paper border-book-border/40 hover:border-book-primary/30 hover:bg-book-bg'}
                    `}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className={`font-bold text-sm ${isSelected ? 'text-book-primary' : 'text-book-text-main'}`}>
                          第{no}章
                        </div>
                        <div className="text-xs text-book-text-muted truncate">
                          {title || '（无标题）'}
                        </div>
                      </div>
                      <div className="text-[11px] text-book-text-muted font-mono whitespace-nowrap pt-0.5">
                        {c?.word_count ? `${c.word_count}字` : ''}
                      </div>
                    </div>
                  </button>
                );
              })}

              {remainingCompletedChapters > 0 ? (
                <div className="pt-2 flex justify-center">
                  <BookButton
                    size="sm"
                    variant="ghost"
                    onClick={() => setCompletedChaptersRenderLimit((prev) => prev + renderBatchSize)}
                  >
                    加载更多章节（剩余 {remainingCompletedChapters}）
                  </BookButton>
                </div>
              ) : null}
            </div>
          </BookCard>

          <BookCard className="p-6">
            {selectedCompletedChapterNumber ? (
              <>
                <div className="flex items-start justify-between gap-3 border-b border-book-border/40 pb-3 mb-4">
                  <div className="min-w-0">
                    <div className="font-serif font-bold text-lg text-book-text-main truncate">
                      第{selectedCompletedChapterNumber}章  {String(selectedCompletedChapter?.title || '').trim()}
                    </div>
                    <div className="mt-1 text-xs text-book-text-muted">
                      {selectedCompletedChapterLoading
                        ? '加载中…'
                        : (selectedCompletedChapter?.word_count ? `字数：${selectedCompletedChapter.word_count}` : '')}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <BookButton
                      variant="ghost"
                      size="sm"
                      onClick={() => exportSelectedChapter('txt')}
                      disabled={selectedCompletedChapterLoading}
                    >
                      <Download size={14} className="mr-1" /> 导出TXT
                    </BookButton>
                    <BookButton
                      variant="ghost"
                      size="sm"
                      onClick={() => exportSelectedChapter('markdown')}
                      disabled={selectedCompletedChapterLoading}
                    >
                      <Download size={14} className="mr-1" /> 导出MD
                    </BookButton>
                  </div>
                </div>

                {selectedCompletedChapterLoading ? (
                  <div className="text-center py-20 text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30">
                    加载章节正文...
                  </div>
                ) : (
                  <BookTextarea
                    label="正文（只读）"
                    value={String(selectedCompletedChapter?.content || '')}
                    readOnly
                    rows={18}
                    className="min-h-[520px] font-serif leading-relaxed"
                  />
                )}
              </>
            ) : (
              <div className="text-center py-20 text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30">
                选择章节查看正文
              </div>
            )}
          </BookCard>
        </div>
      ) : (
        <div className="text-center py-20 text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30">
          <FileText size={48} className="mx-auto mb-4 opacity-50" />
          <div className="font-serif font-bold text-lg text-book-text-main mb-2">暂无已完成章节</div>
          <div className="text-sm">在写作台生成章节并选择版本后，章节将显示在这里。</div>
          <div className="mt-6 flex justify-center">
            <BookButton variant="primary" size="sm" onClick={() => safeNavigate(`/write/${projectId}`)}>
              <Play size={16} className="mr-2 fill-current" />
              前往写作台
            </BookButton>
          </div>
        </div>
      )}

      <ImportChapterModal
        projectId={projectId}
        isOpen={isImportChapterModalOpen}
        onClose={() => setIsImportChapterModalOpen(false)}
        suggestedChapterNumber={suggestedImportChapterNumber}
        onImported={onChapterImported}
      />
    </div>
  );
};
