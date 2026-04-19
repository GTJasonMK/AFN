import React from 'react';
import { Copy, FileDown, Image as ImageIcon, Trash2, XCircle } from 'lucide-react';
import { ChapterMangaPDFResponse, resolveAssetUrl } from '../../../api/imageGeneration';
import { MangaPromptResult } from '../../../api/writer';
import { BookCard } from '../../ui/BookCard';
import { BookButton } from '../../ui/BookButton';
import { BatchProgressState } from './shared';

type MangaSummarySectionProps = {
  manga: MangaPromptResult | null;
  pdfInfo: ChapterMangaPDFResponse | null;
  pdfGeneratingLayout: 'full' | 'manga' | null;
  onGeneratePdf: (layout: 'full' | 'manga') => void | Promise<void>;
  onDeleteMangaPrompts: () => void | Promise<void>;
  generatingPrompts: boolean;
  isProgressRunning: boolean;
  batchGenerating: boolean;
  pdfPreviewOpen: boolean;
  onPdfPreviewOpenChange: (open: boolean) => void;
  pdfPreviewUrl: string | null;
  batchSkipExistingImages: boolean;
  onBatchSkipExistingImagesChange: (checked: boolean) => void;
  onStopBatch: () => void;
  onBatchGeneratePanels: () => void | Promise<void>;
  onBatchGeneratePages: () => void | Promise<void>;
  batchProgress: BatchProgressState;
  batchErrors: string[];
  onCopyText: (text: string, label: string) => void | Promise<void>;
};

export const MangaSummarySection: React.FC<MangaSummarySectionProps> = ({
  manga,
  pdfInfo,
  pdfGeneratingLayout,
  onGeneratePdf,
  onDeleteMangaPrompts,
  generatingPrompts,
  isProgressRunning,
  batchGenerating,
  pdfPreviewOpen,
  onPdfPreviewOpenChange,
  pdfPreviewUrl,
  batchSkipExistingImages,
  onBatchSkipExistingImagesChange,
  onStopBatch,
  onBatchGeneratePanels,
  onBatchGeneratePages,
  batchProgress,
  batchErrors,
  onCopyText,
}) => {
  if (!manga) return null;

  return (
    <>
      <BookCard className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="text-sm text-book-text-main">
            共 <span className="font-bold">{manga.total_pages}</span> 页，
            <span className="font-bold">{manga.total_panels}</span> 个画格
            <span className="ml-2 text-xs text-book-text-muted">
              {manga.is_complete ? '已完成' : `已完成 ${manga.completed_pages_count || 0} 页`}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <BookButton
              variant="ghost"
              size="sm"
              onClick={() => onGeneratePdf('full')}
              disabled={pdfGeneratingLayout !== null}
            >
              <FileDown size={14} className="mr-1" />
              {pdfGeneratingLayout === 'full' ? '生成中…' : '导出PDF(全页)'}
            </BookButton>
            <BookButton
              variant="ghost"
              size="sm"
              onClick={() => onGeneratePdf('manga')}
              disabled={pdfGeneratingLayout !== null}
            >
              <FileDown size={14} className="mr-1" />
              {pdfGeneratingLayout === 'manga' ? '生成中…' : '导出PDF(分格)'}
            </BookButton>
            <BookButton
              variant="ghost"
              size="sm"
              onClick={onDeleteMangaPrompts}
              disabled={generatingPrompts || isProgressRunning || batchGenerating}
              className="text-book-accent hover:text-book-accent"
              title="删除本章漫画分镜数据（不删除图片）"
            >
              <Trash2 size={14} className="mr-1" />
              删除分镜
            </BookButton>
          </div>
        </div>

        {pdfInfo?.success && pdfInfo.download_url && (
          <div className="mt-3 space-y-3">
            <div className="flex items-center justify-between gap-2 text-xs text-book-text-muted">
              <div className="truncate">最新PDF：{pdfInfo.file_name || 'manga.pdf'}</div>
              <a
                className="font-bold text-book-primary hover:underline"
                href={resolveAssetUrl(pdfInfo.download_url)}
                target="_blank"
                rel="noreferrer"
              >
                下载
              </a>
            </div>

            <details
              open={pdfPreviewOpen}
              className="group rounded-lg border border-book-border/40 bg-book-bg-paper"
              onToggle={(event) => {
                const open = (event.currentTarget as HTMLDetailsElement).open;
                onPdfPreviewOpenChange(open);
              }}
            >
              <summary className="cursor-pointer select-none px-3 py-2 text-xs font-bold text-book-text-main">
                PDF 预览
                <span className="ml-2 text-[11px] font-normal text-book-text-muted">
                  点击展开（不会自动下载）
                </span>
              </summary>
              <div className="px-3 pb-3">
                {pdfPreviewOpen ? (
                  pdfPreviewUrl ? (
                    <iframe
                      src={pdfPreviewUrl}
                      className="h-[70vh] w-full rounded-md border border-book-border/40 bg-book-bg"
                      title="manga-pdf-preview"
                    />
                  ) : (
                    <div className="flex h-[70vh] items-center justify-center rounded-md border border-book-border/40 bg-book-bg text-xs text-book-text-muted">
                      PDF 加载中…
                    </div>
                  )
                ) : null}
              </div>
            </details>
          </div>
        )}
      </BookCard>

      <BookCard className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="font-bold text-book-text-main">批量生成图片</div>
            <div className="mt-1 text-xs text-book-text-muted">
              说明：按顺序逐个生成，避免一次性并发压垮本地模型/队列。
            </div>
          </div>
          <div className="flex flex-none items-center gap-2">
            <label className="flex items-center gap-2 text-xs text-book-text-main">
              <input
                type="checkbox"
                className="rounded border-book-border text-book-primary focus:ring-book-primary"
                checked={batchSkipExistingImages}
                onChange={(event) => onBatchSkipExistingImagesChange(event.target.checked)}
                disabled={batchGenerating}
              />
              跳过已有
            </label>
            {batchGenerating && (
              <BookButton variant="ghost" size="sm" onClick={onStopBatch}>
                <XCircle size={14} className="mr-1" />
                停止
              </BookButton>
            )}
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          <BookButton
            variant="primary"
            size="sm"
            onClick={onBatchGeneratePanels}
            disabled={batchGenerating || generatingPrompts || isProgressRunning}
            title="生成本章所有画格图片（按顺序）"
          >
            <ImageIcon size={14} className="mr-1" />
            生成所有画格
          </BookButton>
          <BookButton
            variant="ghost"
            size="sm"
            onClick={onBatchGeneratePages}
            disabled={batchGenerating || generatingPrompts || isProgressRunning}
            title="生成本章所有整页图片（需要 page_prompts）"
          >
            <ImageIcon size={14} className="mr-1" />
            生成所有整页
          </BookButton>
        </div>

        {batchProgress && (
          <div className="mt-3">
            <div className="truncate text-xs text-book-text-muted">{batchProgress.message}</div>
            <div className="mt-1 overflow-hidden rounded-full bg-book-border/30">
              <div
                className="h-2 bg-book-primary transition-all duration-300"
                style={{
                  width: `${Math.min(100, Math.max(0, (batchProgress.current / Math.max(1, batchProgress.total)) * 100))}%`,
                }}
              />
            </div>
            <div className="mt-1 text-[11px] text-book-text-muted">
              {batchProgress.current}/{batchProgress.total}
            </div>
          </div>
        )}

        {batchErrors.length > 0 && (
          <details className="group mt-3 rounded-lg border border-book-border/40 bg-book-bg-paper">
            <summary className="cursor-pointer select-none px-3 py-2 text-xs font-bold text-book-text-main">
              失败明细（{batchErrors.length}）
              <span className="ml-2 text-[11px] font-normal text-book-text-muted">点击展开</span>
            </summary>
            <div className="space-y-2 px-3 pb-3">
              <div className="flex justify-end">
                <BookButton
                  variant="ghost"
                  size="sm"
                  onClick={() => onCopyText(batchErrors.join('\n'), '批量生成失败明细')}
                >
                  <Copy size={14} className="mr-1" />
                  复制
                </BookButton>
              </div>
              <pre className="overflow-auto rounded border border-book-border/40 bg-book-bg p-2 font-mono text-xs leading-relaxed text-book-text-main whitespace-pre-wrap">
                {batchErrors.join('\n')}
              </pre>
            </div>
          </details>
        )}
      </BookCard>
    </>
  );
};
