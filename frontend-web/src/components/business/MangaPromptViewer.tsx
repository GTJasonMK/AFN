import React, { useMemo, useState, useEffect } from 'react';
import { writerApi, MangaPromptResult, MangaPanel, MangaPagePrompt } from '../../api/writer';
import { imageGenerationApi, GeneratedImageInfo, resolveAssetUrl, ChapterMangaPDFResponse } from '../../api/imageGeneration';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';
import { Layers, RefreshCw, Image as ImageIcon, FileDown } from 'lucide-react';
import { useToast } from '../feedback/Toast';

interface MangaPromptViewerProps {
  projectId: string;
  chapterNumber: number;
}

export const MangaPromptViewer: React.FC<MangaPromptViewerProps> = ({ projectId, chapterNumber }) => {
  const { addToast } = useToast();
  const [manga, setManga] = useState<MangaPromptResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [generatingPrompts, setGeneratingPrompts] = useState(false);

  const [images, setImages] = useState<GeneratedImageInfo[]>([]);
  const [imagesLoading, setImagesLoading] = useState(false);
  const [generatingPanelId, setGeneratingPanelId] = useState<string | null>(null);
  const [generatingPageNumber, setGeneratingPageNumber] = useState<number | null>(null);

  const [pdfInfo, setPdfInfo] = useState<ChapterMangaPDFResponse | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfGeneratingLayout, setPdfGeneratingLayout] = useState<'full' | 'manga' | null>(null);

  useEffect(() => {
    if (!chapterNumber) return;
    refreshAll();
  }, [projectId, chapterNumber]);

  const fetchMangaPrompts = async () => {
    setLoading(true);
    try {
      const response = await writerApi.getMangaPrompts(projectId, chapterNumber);
      setManga(response);
    } catch (e) {
      console.error(e);
      setManga(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchImages = async () => {
    setImagesLoading(true);
    try {
      const list = await imageGenerationApi.listChapterImages(projectId, chapterNumber, { include_legacy: true });
      setImages(list || []);
    } catch (e) {
      console.error(e);
      setImages([]);
    } finally {
      setImagesLoading(false);
    }
  };

  const fetchLatestPdf = async () => {
    setPdfLoading(true);
    try {
      const latest = await imageGenerationApi.getLatestChapterMangaPDF(projectId, chapterNumber);
      setPdfInfo(latest);
    } catch (e) {
      console.error(e);
      setPdfInfo(null);
    } finally {
      setPdfLoading(false);
    }
  };

  const refreshAll = async () => {
    await Promise.allSettled([
      fetchMangaPrompts(),
      fetchImages(),
      fetchLatestPdf(),
    ]);
  };

  const handleGeneratePrompts = async () => {
    setGeneratingPrompts(true);
    try {
      const response = await writerApi.generateMangaPrompts(projectId, chapterNumber);
      setManga(response);
      addToast('分镜生成完成', 'success');
    } catch (e) {
      console.error(e);
    } finally {
      setGeneratingPrompts(false);
    }
  };

  const imagesByPanelId = useMemo(() => {
    const map = new Map<string, GeneratedImageInfo[]>();
    images.forEach((img) => {
      const key = img.panel_id || '';
      if (!key) return;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(img);
    });
    return map;
  }, [images]);

  const pagePromptByPageNumber = useMemo(() => {
    const map = new Map<number, MangaPagePrompt>();
    (manga?.page_prompts || []).forEach((pp) => {
      map.set(pp.page_number, pp);
    });
    return map;
  }, [manga]);

  const panelsByPageNumber = useMemo(() => {
    const map = new Map<number, MangaPanel[]>();
    (manga?.panels || []).forEach((p) => {
      const list = map.get(p.page_number) || [];
      list.push(p);
      map.set(p.page_number, list);
    });
    for (const [k, list] of map.entries()) {
      list.sort((a, b) => (a.panel_number || 0) - (b.panel_number || 0));
      map.set(k, list);
    }
    return map;
  }, [manga]);

  const handleGeneratePanelImage = async (panel: MangaPanel) => {
    setGeneratingPanelId(panel.panel_id);
    try {
      const dialogueText = Array.isArray(panel.dialogues) && panel.dialogues.length > 0
        ? String(panel.dialogues[0]?.text || panel.dialogues[0]?.content || '')
        : '';
      const speaker = Array.isArray(panel.dialogues) && panel.dialogues.length > 0
        ? String(panel.dialogues[0]?.speaker || panel.dialogues[0]?.character || '')
        : '';

      const result = await imageGenerationApi.generatePanelImage(
        projectId,
        chapterNumber,
        panel.scene_id || panel.page_number,
        {
          prompt: panel.prompt,
          negative_prompt: panel.negative_prompt,
          style: 'manga',
          ratio: panel.aspect_ratio || '4:3',
          resolution: '1K',
          quality: 'standard',
          count: 1,
          panel_id: panel.panel_id,
          characters: panel.characters || [],
          composition: panel.shot_type || '',
          dialogue: dialogueText || null,
          dialogue_speaker: speaker || null,
          dialogue_language: panel.dialogue_language || manga?.dialogue_language || 'chinese',
          reference_image_paths: panel.reference_image_paths || null,
        }
      );

      if (result.success) {
        addToast('画格图片生成完成', 'success');
        await fetchImages();
      } else {
        addToast(result.error_message || '生成失败', 'error');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setGeneratingPanelId(null);
    }
  };

  const handleGeneratePageImage = async (pageNumber: number) => {
    const pp = pagePromptByPageNumber.get(pageNumber);
    if (!pp) {
      addToast('缺少整页提示词，请先生成分镜并确保已生成 page_prompts', 'error');
      return;
    }
    setGeneratingPageNumber(pageNumber);
    try {
      const result = await imageGenerationApi.generatePageImage(
        projectId,
        chapterNumber,
        pageNumber,
        {
          full_page_prompt: pp.full_page_prompt || '',
          negative_prompt: pp.negative_prompt || null,
          layout_template: pp.layout_template || '',
          layout_description: pp.layout_description || '',
          ratio: pp.aspect_ratio || '3:4',
          resolution: '2K',
          style: 'manga',
          panel_summaries: pp.panel_summaries || [],
          reference_image_paths: pp.reference_image_paths || null,
          dialogue_language: manga?.dialogue_language || 'chinese',
        }
      );

      if (result.success) {
        addToast('整页图片生成完成', 'success');
        await fetchImages();
      } else {
        addToast(result.error_message || '生成失败', 'error');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setGeneratingPageNumber(null);
    }
  };

  const handleGeneratePdf = async (layout: 'full' | 'manga') => {
    setPdfGeneratingLayout(layout);
    try {
      const result = await imageGenerationApi.generateChapterMangaPDF(projectId, chapterNumber, {
        layout,
        include_prompts: false,
      });
      setPdfInfo(result);
      if (result.success) {
        addToast('PDF 已生成', 'success');
      } else {
        addToast(result.error_message || 'PDF 生成失败', 'error');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setPdfGeneratingLayout(null);
    }
  };

  if (!chapterNumber) return null;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="font-serif text-lg font-bold text-book-text-main flex items-center gap-2">
          <Layers size={20} className="text-book-primary" />
          漫画分镜
        </h3>
        <div className="flex items-center gap-2">
          <BookButton variant="ghost" size="sm" onClick={refreshAll} disabled={loading || imagesLoading || pdfLoading}>
            <RefreshCw size={14} className={`mr-1 ${(loading || imagesLoading || pdfLoading) ? 'animate-spin' : ''}`} />
            刷新
          </BookButton>
          <BookButton 
            variant={manga ? "ghost" : "primary"} 
            size="sm" 
            onClick={handleGeneratePrompts}
            disabled={generatingPrompts}
          >
            <RefreshCw size={14} className={`mr-1 ${generatingPrompts ? 'animate-spin' : ''}`} />
            {generatingPrompts ? '生成中...' : (manga ? '重新生成分镜' : '生成分镜')}
          </BookButton>
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2].map(i => (
            <div key={i} className="h-32 bg-book-bg-paper animate-pulse rounded-lg" />
          ))}
        </div>
      ) : (
        <div className="space-y-8">
          {manga && (
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
                    onClick={() => handleGeneratePdf('full')}
                    disabled={pdfGeneratingLayout !== null}
                  >
                    <FileDown size={14} className="mr-1" />
                    {pdfGeneratingLayout === 'full' ? '生成中…' : '导出PDF(全页)'}
                  </BookButton>
                  <BookButton
                    variant="ghost"
                    size="sm"
                    onClick={() => handleGeneratePdf('manga')}
                    disabled={pdfGeneratingLayout !== null}
                  >
                    <FileDown size={14} className="mr-1" />
                    {pdfGeneratingLayout === 'manga' ? '生成中…' : '导出PDF(分格)'}
                  </BookButton>
                </div>
              </div>

              {pdfInfo?.success && pdfInfo.download_url && (
                <div className="mt-3 text-xs text-book-text-muted flex items-center justify-between gap-2">
                  <div className="truncate">
                    最新PDF：{pdfInfo.file_name || 'manga.pdf'}
                  </div>
                  <a
                    className="text-book-primary font-bold hover:underline"
                    href={resolveAssetUrl(pdfInfo.download_url)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    下载
                  </a>
                </div>
              )}
            </BookCard>
          )}

          {(manga?.pages || []).map((page) => {
            const panels = panelsByPageNumber.get(page.page_number) || [];
            const pageId = `page${page.page_number}`;
            const pageImages = imagesByPanelId.get(pageId) || [];
            const pageImage = pageImages[0];
            const hasPagePrompt = pagePromptByPageNumber.has(page.page_number);

            return (
              <div key={page.page_number} className="space-y-3">
                <div className="flex items-center justify-between gap-2 border-b border-book-border/30 pb-1">
                  <div className="font-bold text-book-text-sub text-sm">
                    第 {page.page_number} 页 · {page.panel_count} 格
                  </div>
                  <div className="flex items-center gap-2">
                    <BookButton
                      variant="ghost"
                      size="sm"
                      onClick={() => handleGeneratePageImage(page.page_number)}
                      disabled={!hasPagePrompt || generatingPageNumber !== null}
                    >
                      <ImageIcon size={14} className={`mr-1 ${generatingPageNumber === page.page_number ? 'animate-spin' : ''}`} />
                      {generatingPageNumber === page.page_number ? '生成中…' : '生成整页'}
                    </BookButton>
                  </div>
                </div>

                {page.layout_description && (
                  <div className="text-xs text-book-text-muted leading-relaxed">
                    {page.layout_description}
                  </div>
                )}

                {pageImage && (
                  <BookCard className="p-3">
                    <div className="text-xs text-book-text-muted mb-2">整页图片</div>
                    <a href={resolveAssetUrl(pageImage.url)} target="_blank" rel="noreferrer">
                      <img
                        src={resolveAssetUrl(pageImage.url)}
                        alt={`page-${page.page_number}`}
                        className="w-full rounded-md border border-book-border/30"
                      />
                    </a>
                  </BookCard>
                )}

                <div className="grid gap-4">
                  {panels.map((panel) => {
                    const panelImages = imagesByPanelId.get(panel.panel_id) || [];
                    const img = panelImages[0];
                    return (
                      <BookCard key={panel.panel_id} className="p-3 text-sm">
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <div className="min-w-0">
                            <div className="font-bold text-book-primary">
                              Panel {panel.panel_number}
                            </div>
                            <div className="text-xs text-book-text-muted mt-1">
                              {panel.shot_type} · {panel.aspect_ratio} · {panel.shape}
                              {panel.characters?.length ? ` · 角色：${panel.characters.join(' / ')}` : ''}
                            </div>
                          </div>
                          <BookButton
                            variant="primary"
                            size="sm"
                            onClick={() => handleGeneratePanelImage(panel)}
                            disabled={generatingPanelId !== null}
                          >
                            <ImageIcon size={14} className={`mr-1 ${generatingPanelId === panel.panel_id ? 'animate-spin' : ''}`} />
                            {generatingPanelId === panel.panel_id ? '生成中…' : (img ? '重绘' : '生成')}
                          </BookButton>
                        </div>

                        {img && (
                          <a href={resolveAssetUrl(img.url)} target="_blank" rel="noreferrer" className="block mb-2">
                            <img
                              src={resolveAssetUrl(img.url)}
                              alt={panel.panel_id}
                              className="w-full rounded-md border border-book-border/30"
                            />
                          </a>
                        )}

                        <div className="bg-book-bg p-2 rounded text-xs font-mono text-book-text-tertiary whitespace-pre-wrap">
                          {panel.prompt}
                        </div>
                      </BookCard>
                    );
                  })}

                  {panels.length === 0 && (
                    <div className="py-6 text-center text-book-text-muted text-sm">
                      本页暂无分镜（请先生成分镜）
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {!manga && !generatingPrompts && (
            <div className="py-8 text-center text-book-text-muted text-sm">
              暂无分镜数据（可点击右上角“生成分镜”）
            </div>
          )}
        </div>
      )}
    </div>
  );
};
