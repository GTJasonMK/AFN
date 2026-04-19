import React from 'react';
import { Copy, Image as ImageIcon, Trash2 } from 'lucide-react';
import { GeneratedImageInfo, resolveAssetUrl } from '../../../api/imageGeneration';
import { MangaPagePrompt, MangaPanel, MangaPromptResult } from '../../../api/writer';
import { BookCard } from '../../ui/BookCard';
import { BookButton } from '../../ui/BookButton';
import { aspectRatioToCss, widthRatioToSpan } from './shared';

type MangaStoryboardTabProps = {
  manga: MangaPromptResult | null;
  generatingPrompts: boolean;
  panelsByPageNumber: Map<number, MangaPanel[]>;
  pagePromptByPageNumber: Map<number, MangaPagePrompt>;
  imagesByPanelId: Map<string, GeneratedImageInfo[]>;
  activeImageByPanelId: Record<string, number | null>;
  onSelectActiveImage: (key: string, imageId: number) => void;
  generatingPageNumber: number | null;
  generatingPanelId: string | null;
  batchGenerating: boolean;
  onGeneratePageImage: (pageNumber: number) => void | Promise<void>;
  onGeneratePanelImage: (panel: MangaPanel) => void | Promise<void>;
  onDeleteImage: (img: GeneratedImageInfo, label: string) => void | Promise<void>;
  onCopyText: (text: string, label: string) => void | Promise<void>;
};

export const MangaStoryboardTab: React.FC<MangaStoryboardTabProps> = ({
  manga,
  generatingPrompts,
  panelsByPageNumber,
  pagePromptByPageNumber,
  imagesByPanelId,
  activeImageByPanelId,
  onSelectActiveImage,
  generatingPageNumber,
  generatingPanelId,
  batchGenerating,
  onGeneratePageImage,
  onGeneratePanelImage,
  onDeleteImage,
  onCopyText,
}) => {
  const pages = Array.isArray(manga?.pages) ? manga.pages : [];

  if (!manga && !generatingPrompts) {
    return (
      <div className="py-8 text-center text-sm text-book-text-muted">
        暂无分镜数据（可点击右上角“生成分镜”）
      </div>
    );
  }

  return (
    <>
      {pages.map((page: any) => {
        const panels = panelsByPageNumber.get(page.page_number) || [];
        const pageId = `page${page.page_number}`;
        const pageImages = imagesByPanelId.get(pageId) || [];
        const activePageImageId = activeImageByPanelId[pageId];
        const pageImage = activePageImageId
          ? (pageImages.find((image) => image.id === activePageImageId) || pageImages[0])
          : pageImages[0];
        const pagePrompt = pagePromptByPageNumber.get(page.page_number) || null;
        const hasPagePrompt = Boolean(pagePrompt);
        const panelsByRow = new Map<number, MangaPanel[]>();

        panels.forEach((panel) => {
          const rowId = Number((panel as any).row_id || 1);
          const rowPanels = panelsByRow.get(rowId) || [];
          rowPanels.push(panel);
          panelsByRow.set(rowId, rowPanels);
        });

        for (const [rowId, rowPanels] of panelsByRow.entries()) {
          rowPanels.sort((a, b) => Number(a.panel_number || 0) - Number(b.panel_number || 0));
          panelsByRow.set(rowId, rowPanels);
        }

        const rowIds = Array.from(panelsByRow.keys()).sort((a, b) => a - b);

        return (
          <div key={page.page_number} className="space-y-3">
            <div className="flex items-center justify-between gap-2 border-b border-book-border/30 pb-1">
              <div className="text-sm font-bold text-book-text-sub">
                第 {page.page_number} 页 · {page.panel_count} 格
              </div>
              <div className="flex items-center gap-2">
                <BookButton
                  variant="ghost"
                  size="sm"
                  onClick={() => onGeneratePageImage(page.page_number)}
                  disabled={!hasPagePrompt || generatingPageNumber !== null || batchGenerating}
                >
                  <ImageIcon
                    size={14}
                    className={`mr-1 ${generatingPageNumber === page.page_number ? 'animate-spin' : ''}`}
                  />
                  {generatingPageNumber === page.page_number ? '生成中…' : '生成整页'}
                </BookButton>
              </div>
            </div>

            {page.layout_description && (
              <div className="text-xs leading-relaxed text-book-text-muted">
                {page.layout_description}
              </div>
            )}

            {pagePrompt && (
              <details className="group rounded-lg border border-book-border/40 bg-book-bg-paper">
                <summary className="cursor-pointer select-none px-3 py-2 text-xs font-bold text-book-text-main">
                  整页提示词（page_prompts）
                  <span className="ml-2 text-[11px] font-normal text-book-text-muted">点击展开</span>
                </summary>
                <div className="space-y-2 px-3 pb-3">
                  <div className="flex items-center justify-end gap-2">
                    <BookButton
                      variant="ghost"
                      size="sm"
                      onClick={() => onCopyText(pagePrompt.full_page_prompt || '', `第${page.page_number}页整页提示词`)}
                    >
                      <Copy size={14} className="mr-1" />
                      复制提示词
                    </BookButton>
                  </div>
                  {pagePrompt.layout_description && (
                    <div className="whitespace-pre-wrap text-xs text-book-text-muted">
                      {pagePrompt.layout_description}
                    </div>
                  )}
                  <pre className="overflow-auto rounded border border-book-border/40 bg-book-bg p-2 font-mono text-xs leading-relaxed text-book-text-main whitespace-pre-wrap">
                    {pagePrompt.full_page_prompt || ''}
                  </pre>
                </div>
              </details>
            )}

            {pageImage && (
              <BookCard className="p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="text-xs text-book-text-muted">整页图片</div>
                  <BookButton
                    variant="ghost"
                    size="sm"
                    onClick={() => onDeleteImage(pageImage, `第${page.page_number}页整页图片（image_id=${pageImage.id}）`)}
                  >
                    <Trash2 size={14} className="mr-1" />
                    删除
                  </BookButton>
                </div>
                <a href={resolveAssetUrl(pageImage.url)} target="_blank" rel="noreferrer">
                  <img
                    src={resolveAssetUrl(pageImage.url)}
                    alt={`page-${page.page_number}`}
                    loading="lazy"
                    decoding="async"
                    className="w-full rounded-md border border-book-border/30"
                  />
                </a>

                {pageImages.length > 1 && (
                  <div className="mt-2 flex gap-2 overflow-x-auto no-scrollbar">
                    {pageImages.map((image) => {
                      const selected = pageImage.id === image.id;
                      return (
                        <button
                          key={`page-thumb-${image.id}`}
                          type="button"
                          onClick={() => onSelectActiveImage(pageId, image.id)}
                          className={`h-16 w-16 flex-none overflow-hidden rounded-md border ${
                            selected
                              ? 'border-book-primary'
                              : 'border-book-border/40 hover:border-book-primary/40'
                          }`}
                          title={`image_id=${image.id}`}
                        >
                          <img
                            src={resolveAssetUrl(image.url)}
                            alt={`thumb-${image.id}`}
                            loading="lazy"
                            decoding="async"
                            className="h-full w-full object-cover"
                          />
                        </button>
                      );
                    })}
                  </div>
                )}
              </BookCard>
            )}

            {panels.length > 0 && rowIds.length > 0 && (
              <details className="group rounded-lg border border-book-border/40 bg-book-bg-paper">
                <summary className="cursor-pointer select-none px-3 py-2 text-xs font-bold text-book-text-main">
                  页面排版预览
                  <span className="ml-2 text-[11px] font-normal text-book-text-muted">基于 row_id / width_ratio</span>
                </summary>
                <div className="space-y-3 px-3 pb-3">
                  {rowIds.map((rowId) => {
                    const rowPanels = panelsByRow.get(rowId) || [];
                    return (
                      <div key={`row-${page.page_number}-${rowId}`} className="grid grid-cols-12 gap-2">
                        {rowPanels.map((panel) => {
                          const span = widthRatioToSpan((panel as any).width_ratio);
                          const cssAspect = aspectRatioToCss((panel as any).aspect_ratio);
                          const panelImages = imagesByPanelId.get(panel.panel_id) || [];
                          const activeId = activeImageByPanelId[panel.panel_id];
                          const image = activeId
                            ? (panelImages.find((item) => item.id === activeId) || panelImages[0])
                            : panelImages[0];
                          return (
                            <div
                              key={`layout-${panel.panel_id}`}
                              className="min-w-0"
                              style={{ gridColumn: `span ${span} / span ${span}` }}
                            >
                              <div className="rounded-lg border border-book-border/40 bg-book-bg p-2">
                                <div className="flex items-center justify-between gap-2 text-[11px]">
                                  <div className="truncate font-bold text-book-primary">
                                    Panel {panel.panel_number}
                                  </div>
                                  <div className="font-mono text-book-text-muted">
                                    {String((panel as any).width_ratio || 'half')}
                                  </div>
                                </div>

                                <div
                                  className="mt-2 min-h-[120px] overflow-hidden rounded-md border border-book-border/30 bg-book-bg-paper/50"
                                  style={cssAspect ? { aspectRatio: cssAspect } : undefined}
                                >
                                  {image ? (
                                    <a
                                      href={resolveAssetUrl(image.url)}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="block h-full w-full"
                                    >
                                      <img
                                        src={resolveAssetUrl(image.url)}
                                        alt={panel.panel_id}
                                        loading="lazy"
                                        decoding="async"
                                        className="h-full w-full object-cover"
                                      />
                                    </a>
                                  ) : (
                                    <div className="flex h-full w-full items-center justify-center text-[11px] text-book-text-muted">
                                      暂无图片
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    );
                  })}
                </div>
              </details>
            )}

            <div className="grid gap-4">
              {panels.map((panel) => {
                const panelImages = imagesByPanelId.get(panel.panel_id) || [];
                const activePanelImageId = activeImageByPanelId[panel.panel_id];
                const image = activePanelImageId
                  ? (panelImages.find((item) => item.id === activePanelImageId) || panelImages[0])
                  : panelImages[0];
                const firstDialogue = Array.isArray(panel.dialogues) && panel.dialogues.length > 0 ? panel.dialogues[0] : null;
                const dialogueSpeaker = firstDialogue ? String(firstDialogue?.speaker || firstDialogue?.character || '') : '';
                const dialogueText = firstDialogue ? String(firstDialogue?.text || firstDialogue?.content || '') : '';

                return (
                  <BookCard key={panel.panel_id} className="p-3 text-sm">
                    <div className="mb-2 flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="font-bold text-book-primary">Panel {panel.panel_number}</div>
                        <div className="mt-1 text-xs text-book-text-muted">
                          {panel.shot_type} · {panel.aspect_ratio} · {panel.shape}
                          {panel.characters?.length ? ` · 角色：${panel.characters.join(' / ')}` : ''}
                        </div>
                        {(dialogueSpeaker || dialogueText) && (
                          <div className="mt-1 text-[11px] leading-relaxed text-book-text-muted">
                            {dialogueSpeaker ? <span className="font-bold">{dialogueSpeaker}：</span> : null}
                            {dialogueText}
                          </div>
                        )}
                      </div>
                      <BookButton
                        variant="primary"
                        size="sm"
                        onClick={() => onGeneratePanelImage(panel)}
                        disabled={generatingPanelId !== null || batchGenerating}
                      >
                        <ImageIcon
                          size={14}
                          className={`mr-1 ${generatingPanelId === panel.panel_id ? 'animate-spin' : ''}`}
                        />
                        {generatingPanelId === panel.panel_id ? '生成中…' : (image ? '重绘' : '生成')}
                      </BookButton>
                    </div>

                    {image && (
                      <a
                        href={resolveAssetUrl(image.url)}
                        target="_blank"
                        rel="noreferrer"
                        className="mb-2 block"
                      >
                        <img
                          src={resolveAssetUrl(image.url)}
                          alt={panel.panel_id}
                          loading="lazy"
                          decoding="async"
                          className="w-full rounded-md border border-book-border/30"
                        />
                      </a>
                    )}

                    {panelImages.length > 1 && (
                      <div className="mb-2 flex gap-2 overflow-x-auto no-scrollbar">
                        {panelImages.map((item) => {
                          const selected = image?.id === item.id;
                          return (
                            <button
                              key={`panel-thumb-${item.id}`}
                              type="button"
                              onClick={() => onSelectActiveImage(panel.panel_id, item.id)}
                              className={`h-14 w-14 flex-none overflow-hidden rounded-md border ${
                                selected
                                  ? 'border-book-primary'
                                  : 'border-book-border/40 hover:border-book-primary/40'
                              }`}
                              title={`image_id=${item.id}`}
                            >
                              <img
                                src={resolveAssetUrl(item.url)}
                                alt={`thumb-${item.id}`}
                                loading="lazy"
                                decoding="async"
                                className="h-full w-full object-cover"
                              />
                            </button>
                          );
                        })}
                      </div>
                    )}

                    <div className="space-y-2">
                      <div className="flex justify-end gap-2">
                        {image && (
                          <BookButton
                            variant="ghost"
                            size="sm"
                            onClick={() => onDeleteImage(image, `Panel ${panel.panel_number}（image_id=${image.id}）`)}
                          >
                            <Trash2 size={14} className="mr-1" />
                            删除
                          </BookButton>
                        )}
                        <BookButton
                          variant="ghost"
                          size="sm"
                          onClick={() => onCopyText(panel.prompt || '', `Panel ${panel.panel_number} 提示词`)}
                        >
                          <Copy size={14} className="mr-1" />
                          复制
                        </BookButton>
                      </div>
                      <div className="whitespace-pre-wrap rounded bg-book-bg p-2 font-mono text-xs text-book-text-tertiary">
                        {panel.prompt}
                      </div>
                    </div>
                  </BookCard>
                );
              })}

              {panels.length === 0 && (
                <div className="py-6 text-center text-sm text-book-text-muted">
                  本页暂无分镜（请先生成分镜）
                </div>
              )}
            </div>
          </div>
        );
      })}
    </>
  );
};
