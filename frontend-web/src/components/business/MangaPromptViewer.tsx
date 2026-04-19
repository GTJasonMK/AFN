import React, { useMemo, useState, useEffect, useCallback, useRef } from 'react';
import { writerApi, MangaPromptResult, MangaPanel, MangaPagePrompt, MangaPromptProgress } from '../../api/writer';
import { imageGenerationApi, GeneratedImageInfo, resolveAssetUrl, ChapterMangaPDFResponse } from '../../api/imageGeneration';
import { BookButton } from '../ui/BookButton';
import { Layers, RefreshCw } from 'lucide-react';
import { useToast } from '../feedback/Toast';
import { confirmDialog } from '../feedback/ConfirmDialog';
import { usePersistedMangaGenOptions } from '../../hooks/usePersistedMangaGenOptions';
import { usePdfPreviewUrl } from '../../hooks/usePdfPreviewUrl';
import { MangaGenerationParams } from './manga-prompt-viewer/MangaGenerationParams';
import { MangaProgressCard } from './manga-prompt-viewer/MangaProgressCard';
import { MangaSummarySection } from './manga-prompt-viewer/MangaSummarySection';
import { MangaDetailsTab } from './manga-prompt-viewer/MangaDetailsTab';
import { MangaStoryboardTab } from './manga-prompt-viewer/MangaStoryboardTab';
import { BatchProgressState } from './manga-prompt-viewer/shared';

interface MangaPromptViewerProps {
  projectId: string;
  chapterNumber: number;
}

export const MangaPromptViewer: React.FC<MangaPromptViewerProps> = ({ projectId, chapterNumber }) => {
  const { addToast } = useToast();
  const [manga, setManga] = useState<MangaPromptResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [generatingPrompts, setGeneratingPrompts] = useState(false);
  const [progress, setProgress] = useState<MangaPromptProgress | null>(null);
  const progressPollRef = useRef<number | null>(null);
  const progressFailureCountRef = useRef(0);
  const generateAbortRef = useRef<AbortController | null>(null);
  const [cancelingPrompts, setCancelingPrompts] = useState(false);
  const viewKeyRef = useRef('');
  const isMountedRef = useRef(true);
  const lastGenerationStartAtRef = useRef<number | null>(null);
  const [activeTab, setActiveTab] = useState<'storyboard' | 'details'>('storyboard');

  const {
    genStyle,
    setGenStyle,
    customStyle,
    setCustomStyle,
    genLanguage,
    setGenLanguage,
    minPages,
    setMinPages,
    maxPages,
    setMaxPages,
    usePortraits,
    setUsePortraits,
    autoGeneratePortraits,
    setAutoGeneratePortraits,
    autoGeneratePageImages,
    setAutoGeneratePageImages,
    pagePromptConcurrency,
    setPagePromptConcurrency,
    startFromStage,
    setStartFromStage,
    forceRestart,
    setForceRestart,
  } = usePersistedMangaGenOptions(projectId);

  const [images, setImages] = useState<GeneratedImageInfo[]>([]);
  const [imagesLoading, setImagesLoading] = useState(false);
  const [activeImageByPanelId, setActiveImageByPanelId] = useState<Record<string, number | null>>({});
  const [generatingPanelId, setGeneratingPanelId] = useState<string | null>(null);
  const [generatingPageNumber, setGeneratingPageNumber] = useState<number | null>(null);

  const [pdfInfo, setPdfInfo] = useState<ChapterMangaPDFResponse | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfGeneratingLayout, setPdfGeneratingLayout] = useState<'full' | 'manga' | null>(null);
  const { pdfPreviewOpen, setPdfPreviewOpen, pdfPreviewUrl } = usePdfPreviewUrl({
    resetKey: `${projectId}:${chapterNumber}`,
    downloadUrl: pdfInfo?.success ? (pdfInfo.download_url || null) : null,
    resolveUrl: resolveAssetUrl,
    onError: (e) => {
      console.error(e);
      addToast('PDF 预览加载失败，请稍后重试或直接点击“下载”', 'error');
    },
  });
  const [batchSkipExistingImages, setBatchSkipExistingImages] = useState(true);
  const [batchGenerating, setBatchGenerating] = useState(false);
  const [batchProgress, setBatchProgress] = useState<BatchProgressState>(null);
  const [batchErrors, setBatchErrors] = useState<string[]>([]);
  const batchStopRequestedRef = useRef(false);
  const batchAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    viewKeyRef.current = `${projectId}:${chapterNumber}`;
  }, [chapterNumber, projectId]);

  // 章节切换时：停止任何进行中的批量图片生成，避免状态错乱
  useEffect(() => {
    batchStopRequestedRef.current = true;
    try {
      batchAbortRef.current?.abort();
    } catch {
      // ignore
    }
    batchAbortRef.current = null;
    setBatchGenerating(false);
    setBatchProgress(null);
    setBatchErrors([]);
    setGeneratingPanelId(null);
    setGeneratingPageNumber(null);
    batchStopRequestedRef.current = false;
  }, [chapterNumber, projectId]);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      try {
        generateAbortRef.current?.abort();
      } catch {
        // ignore
      }
      try {
        batchAbortRef.current?.abort();
      } catch {
        // ignore
      }
    };
  }, []);

  const fetchMangaPrompts = useCallback(async () => {
    setLoading(true);
    try {
      const response = await writerApi.getMangaPrompts(projectId, chapterNumber, { silent: true });
      setManga(response);
    } catch (e) {
      console.error(e);
      setManga(null);
    } finally {
      setLoading(false);
    }
  }, [projectId, chapterNumber]);

  const fetchImages = useCallback(async () => {
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
  }, [projectId, chapterNumber]);

  const fetchLatestPdf = useCallback(async () => {
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
  }, [projectId, chapterNumber]);

  const refreshAll = useCallback(async () => {
    await Promise.allSettled([
      fetchMangaPrompts(),
      fetchImages(),
      fetchLatestPdf(),
    ]);
  }, [fetchImages, fetchLatestPdf, fetchMangaPrompts]);

  const stopProgressPolling = useCallback(() => {
    if (progressPollRef.current !== null) {
      window.clearInterval(progressPollRef.current);
      progressPollRef.current = null;
    }
    progressFailureCountRef.current = 0;
  }, []);

  const pollProgressOnce = useCallback(async () => {
    if (!projectId || !chapterNumber) return;
    try {
      const data = await writerApi.getMangaPromptProgress(projectId, chapterNumber, { silent: true });
      progressFailureCountRef.current = 0;
      setProgress(data);

      if (data.status === 'completed') {
        stopProgressPolling();
        setGeneratingPrompts(false);
        await refreshAll();
        return;
      }

      if (data.status === 'cancelled') {
        stopProgressPolling();
        setGeneratingPrompts(false);
        return;
      }

      if (data.status !== 'pending') {
        lastGenerationStartAtRef.current = null;
        setGeneratingPrompts(true);
        return;
      }

      // 如果刚触发了生成，但进度长期停留在 pending，通常意味着启动失败/未落库
      if (lastGenerationStartAtRef.current && Date.now() - lastGenerationStartAtRef.current > 8000) {
        lastGenerationStartAtRef.current = null;
        stopProgressPolling();
        setGeneratingPrompts(false);
        addToast('分镜生成未启动（进度仍为“未开始”），请检查后端日志/模型配置', 'error');
      }
    } catch (e) {
      console.error(e);
      progressFailureCountRef.current += 1;
      if (progressFailureCountRef.current >= 3) {
        stopProgressPolling();
        setGeneratingPrompts(false);
        addToast('获取分镜进度失败（已停止轮询）', 'info');
      }
    }
  }, [addToast, chapterNumber, projectId, refreshAll, stopProgressPolling]);

  const startProgressPolling = useCallback(() => {
    if (progressPollRef.current !== null) return;
    void pollProgressOnce();
    progressPollRef.current = window.setInterval(() => {
      void pollProgressOnce();
    }, 1500);
  }, [pollProgressOnce]);

  useEffect(() => {
    if (!chapterNumber) return;
    refreshAll();
  }, [chapterNumber, refreshAll]);

  useEffect(() => {
    stopProgressPolling();
    setProgress(null);
    progressFailureCountRef.current = 0;

    if (!projectId || !chapterNumber) return;

    void (async () => {
      try {
        const data = await writerApi.getMangaPromptProgress(projectId, chapterNumber, { silent: true });
        if (!isMountedRef.current) return;
        setProgress(data);

        const status = data?.status;
        const isRunning = Boolean(status && status !== 'pending' && status !== 'completed' && status !== 'cancelled');
        if (isRunning) {
          setGeneratingPrompts(true);
          startProgressPolling();
        }
      } catch (e) {
        console.error(e);
      }
    })();

    return () => {
      stopProgressPolling();
    };
  }, [chapterNumber, projectId, startProgressPolling, stopProgressPolling]);

  useEffect(() => {
    setActiveTab('storyboard');
  }, [chapterNumber]);

  const copyText = async (text: string, label: string) => {
    const v = (text || '').trim();
    if (!v) {
      addToast(`无可复制内容：${label}`, 'info');
      return;
    }
    try {
      await navigator.clipboard.writeText(v);
      addToast(`已复制：${label}`, 'success');
    } catch (e) {
      console.error(e);
      addToast('复制失败（可能缺少剪贴板权限）', 'error');
    }
  };

  const handleSelectActiveImage = useCallback((key: string, imageId: number) => {
    setActiveImageByPanelId((prev) => ({ ...(prev || {}), [key]: imageId }));
  }, []);

  const handleGeneratePrompts = (override?: { forceRestart?: boolean }) => {
    // 参数基础校验：确保 min <= max
    const min = Math.max(3, Math.min(30, Math.floor(minPages || 8)));
    const max = Math.max(min, Math.min(30, Math.floor(maxPages || 15)));
    if (min !== minPages) setMinPages(min);
    if (max !== maxPages) setMaxPages(max);

    const requestForceRestart = typeof override?.forceRestart === 'boolean' ? override.forceRestart : forceRestart;
    const normalizedCustomStyle = (customStyle || '').trim();
    const requestStyle = genStyle === 'custom' ? (normalizedCustomStyle || 'manga') : genStyle;
    const requestStartStage = startFromStage === 'auto' ? undefined : startFromStage;
    const requestConcurrency = Math.max(1, Math.min(20, Math.floor(pagePromptConcurrency || 5)));
    if (requestConcurrency !== pagePromptConcurrency) setPagePromptConcurrency(requestConcurrency);
    const requestKey = `${projectId}:${chapterNumber}`;

    lastGenerationStartAtRef.current = Date.now();
    setGeneratingPrompts(true);
    setProgress({
      status: 'pending',
      stage: 'pending',
      stage_label: '准备中',
      current: 0,
      total: 0,
      message: '已发送生成请求，正在启动…',
      can_resume: false,
    });
    stopProgressPolling();
    startProgressPolling();

    try {
      generateAbortRef.current?.abort();
    } catch {
      // ignore
    }
    const controller = new AbortController();
    generateAbortRef.current = controller;

    void writerApi
      .generateMangaPromptsWithOptions(
        projectId,
        chapterNumber,
        {
          style: requestStyle,
          minPages: min,
          maxPages: max,
          language: genLanguage,
          usePortraits,
          autoGeneratePortraits,
          autoGeneratePageImages,
          pagePromptConcurrency: requestConcurrency,
          startFromStage: requestStartStage as any,
          forceRestart: requestForceRestart,
        },
        { timeout: 0, signal: controller.signal, silent: true }
      )
      .then((response) => {
        if (!isMountedRef.current) return;
        if (viewKeyRef.current !== requestKey) return;
        lastGenerationStartAtRef.current = null;
        setManga(response);
        addToast('分镜生成完成', 'success');
        setGeneratingPrompts(false);
        stopProgressPolling();
        void refreshAll();
      })
      .catch(async (e) => {
        console.error(e);
        if (!isMountedRef.current) return;
        if (viewKeyRef.current !== requestKey) return;
        lastGenerationStartAtRef.current = null;

        const code = (e as any)?.code;
        const name = (e as any)?.name;
        if (code === 'ERR_CANCELED' || name === 'CanceledError') {
          return;
        }

        const detail = (e as any)?.response?.data?.detail;
        addToast(detail || '生成请求失败（可查看进度或尝试继续生成）', 'error');

        // 立即拉一次进度：如果依然未启动，则结束“生成中”状态
        try {
          const data = await writerApi.getMangaPromptProgress(projectId, chapterNumber, { silent: true });
          if (!isMountedRef.current) return;
          if (viewKeyRef.current !== requestKey) return;
          setProgress(data);
          const status = data?.status;
          const running = Boolean(status && status !== 'pending' && status !== 'completed' && status !== 'cancelled');
          if (!running && status !== 'completed') {
            stopProgressPolling();
            setGeneratingPrompts(false);
          }
        } catch {
          stopProgressPolling();
          setGeneratingPrompts(false);
        }
      });
  };

  const handleCancelPrompts = async () => {
    if (cancelingPrompts) return;
    setCancelingPrompts(true);
    lastGenerationStartAtRef.current = null;
    try {
      generateAbortRef.current?.abort();
      const resp = await writerApi.cancelMangaPromptGeneration(projectId, chapterNumber, { silent: true });
      const ok = Boolean((resp as any)?.success);
      addToast((resp as any)?.message || (ok ? '已发送取消请求' : '取消失败'), ok ? 'success' : 'error');
      startProgressPolling();
      void pollProgressOnce();
    } catch (e) {
      console.error(e);
      addToast('取消失败，请检查后端状态', 'error');
    } finally {
      setCancelingPrompts(false);
    }
  };

  const handleResumePrompts = () => handleGeneratePrompts({ forceRestart: false });
  const handleForceRestartPrompts = () => handleGeneratePrompts({ forceRestart: true });

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

  // 图片列表变化后：清理已删除的“当前预览图片”选择
  useEffect(() => {
    if (!images || images.length === 0) {
      setActiveImageByPanelId({});
      return;
    }
    const existing = new Set(images.map((i) => i.id));
    setActiveImageByPanelId((prev) => {
      const next: Record<string, number | null> = {};
      for (const [k, v] of Object.entries(prev || {})) {
        if (typeof v === 'number' && existing.has(v)) next[k] = v;
      }
      return next;
    });
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

  const sortedCharacterProfiles = useMemo(() => {
    const profiles = (manga as any)?.character_profiles || {};
    if (!profiles || typeof profiles !== 'object' || Array.isArray(profiles)) return [];
    return Object.entries(profiles as Record<string, any>)
      .map(([name, desc]) => ({ name: String(name || '').trim(), desc: String(desc || '').trim() }))
      .filter((it) => it.name && it.desc);
  }, [manga]);

  const analysisData = useMemo(() => {
    const d = (manga as any)?.analysis_data ?? (progress as any)?.analysis_data;
    if (!d || typeof d !== 'object') return null;
    return d as any;
  }, [manga, progress]);

  const chapterInfo = useMemo(() => analysisData?.chapter_info || null, [analysisData]);
  const pagePlan = useMemo(() => analysisData?.page_plan || null, [analysisData]);

  const progressStatus = progress?.status || '';
  const isProgressRunning = Boolean(progressStatus && progressStatus !== 'pending' && progressStatus !== 'completed' && progressStatus !== 'cancelled');
  const isProgressCancelled = progressStatus === 'cancelled';
  const canResumeGeneration = Boolean(isProgressCancelled && progress?.can_resume);
  const showProgress = Boolean(generatingPrompts || (progress && progressStatus !== 'pending'));
  const progressPercent = useMemo(() => {
    const cur = Number(progress?.current || 0);
    const tot = Number(progress?.total || 0);
    if (!tot || tot <= 0) return null;
    return Math.max(0, Math.min(100, Math.round((cur / tot) * 100)));
  }, [progress]);

  const buildPanelImagePayload = useCallback((panel: MangaPanel) => {
    const firstDialogue = Array.isArray(panel.dialogues) && panel.dialogues.length > 0 ? panel.dialogues[0] : null;
    const dialogueText = firstDialogue ? String(firstDialogue?.text || firstDialogue?.content || '') : '';
    const speaker = firstDialogue ? String(firstDialogue?.speaker || firstDialogue?.character || '') : '';
    const bubbleType = firstDialogue ? String(firstDialogue?.bubble_type || firstDialogue?.bubbleType || '') : '';
    const emotion = firstDialogue ? String(firstDialogue?.emotion || '') : '';
    const position = firstDialogue ? String(firstDialogue?.position || '') : '';

    const narration = String((panel as any)?.narration || '');
    const narrationPos = String((panel as any)?.narration_position || (panel as any)?.narrationPosition || '');

    const rawSfx = (panel as any)?.sound_effects || (panel as any)?.soundEffects;
    const soundEffects = Array.isArray(rawSfx)
      ? rawSfx
          .map((s: any) => (typeof s === 'string' ? s : String(s?.text || s?.content || '').trim()))
          .filter((s: string) => Boolean(s))
      : null;

    const rawSfxDetails = (panel as any)?.sound_effect_details || (panel as any)?.soundEffectDetails;
    const soundEffectDetails = Array.isArray(rawSfxDetails) ? rawSfxDetails : null;

    return {
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
      dialogue_bubble_type: bubbleType || null,
      dialogue_emotion: emotion || null,
      dialogue_position: position || null,
      narration: narration || null,
      narration_position: narrationPos || null,
      sound_effects: soundEffects && soundEffects.length > 0 ? soundEffects : null,
      sound_effect_details: soundEffectDetails && soundEffectDetails.length > 0 ? soundEffectDetails : null,
      dialogue_language: panel.dialogue_language || manga?.dialogue_language || 'chinese',
      reference_image_paths: panel.reference_image_paths || null,
    };
  }, [manga?.dialogue_language]);

  const stopBatch = useCallback(() => {
    batchStopRequestedRef.current = true;
    try {
      batchAbortRef.current?.abort();
    } catch {
      // ignore
    }
  }, []);

  const handleDeleteImage = useCallback(async (img: GeneratedImageInfo, label: string) => {
    const ok = await confirmDialog({
      title: '删除图片',
      message: `确定要删除图片吗？\n${label}`,
      confirmText: '删除',
      dialogType: 'danger',
    });
    if (!ok) return;
    try {
      await imageGenerationApi.deleteImage(img.id, { silent: true });
      setActiveImageByPanelId((prev) => {
        const key = String(img.panel_id || '').trim();
        if (!key) return prev;
        if (prev?.[key] !== img.id) return prev;
        const next = { ...(prev || {}) };
        delete next[key];
        return next;
      });
      addToast('已删除图片', 'success');
      await fetchImages();
    } catch (e) {
      console.error(e);
      addToast('删除失败', 'error');
    }
  }, [addToast, fetchImages]);

  const handleGeneratePanelImage = async (panel: MangaPanel) => {
    setGeneratingPanelId(panel.panel_id);
    try {
      const result = await imageGenerationApi.generatePanelImage(
        projectId,
        chapterNumber,
        panel.scene_id || panel.page_number,
        buildPanelImagePayload(panel)
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

  const handleDeleteMangaPrompts = async () => {
    const ok = await confirmDialog({
      title: '删除分镜数据',
      message: '确定要删除本章的漫画分镜数据吗？\n（不会自动删除已生成的图片）',
      confirmText: '删除',
      dialogType: 'danger',
    });
    if (!ok) return;
    try {
      stopProgressPolling();
      lastGenerationStartAtRef.current = null;
      setGeneratingPrompts(false);
      setProgress(null);
      await writerApi.deleteMangaPrompts(projectId, chapterNumber, { silent: true });
      setManga(null);
      addToast('已删除分镜数据', 'success');
      await refreshAll();
    } catch (e) {
      console.error(e);
      addToast('删除失败', 'error');
    }
  };

  const handleBatchGeneratePanels = async () => {
    if (!manga || !Array.isArray(manga.panels) || manga.panels.length === 0) {
      addToast('暂无分镜画格数据，请先生成分镜', 'info');
      return;
    }
    if (batchGenerating) return;

    const requestKey = `${projectId}:${chapterNumber}`;
    batchStopRequestedRef.current = false;
    setBatchErrors([]);
    setBatchGenerating(true);

    const controller = new AbortController();
    batchAbortRef.current = controller;

    try {
      const sorted = [...manga.panels].sort((a, b) => {
        const pa = Number(a.page_number || 0);
        const pb = Number(b.page_number || 0);
        if (pa !== pb) return pa - pb;
        return Number(a.panel_number || 0) - Number(b.panel_number || 0);
      });

      const targets = sorted.filter((p) => {
        if (!p.panel_id) return false;
        if (!batchSkipExistingImages) return true;
        const existing = imagesByPanelId.get(p.panel_id) || [];
        return existing.length === 0;
      });

      if (targets.length === 0) {
        addToast('没有需要生成的画格图片（可能都已有图片）', 'info');
        return;
      }

      const errors: string[] = [];
      for (let i = 0; i < targets.length; i += 1) {
        if (!isMountedRef.current || viewKeyRef.current !== requestKey) break;
        if (batchStopRequestedRef.current) break;

        const panel = targets[i];
        setBatchProgress({
          current: i + 1,
          total: targets.length,
          message: `画格 ${panel.page_number}-${panel.panel_number}（${panel.panel_id}）`,
        });
        setGeneratingPanelId(panel.panel_id);

        try {
          const result = await imageGenerationApi.generatePanelImage(
            projectId,
            chapterNumber,
            panel.scene_id || panel.page_number,
            buildPanelImagePayload(panel),
            { signal: controller.signal, silent: true }
          );

          if (!result.success) {
            errors.push(`Panel ${panel.page_number}-${panel.panel_number}: ${result.error_message || '生成失败'}`);
          }
        } catch (e) {
          const code = (e as any)?.code;
          const name = (e as any)?.name;
          if (code === 'ERR_CANCELED' || name === 'CanceledError') {
            if (batchStopRequestedRef.current) break;
            errors.push(`Panel ${panel.page_number}-${panel.panel_number}: 请求被取消`);
            break;
          }
          const detail = (e as any)?.response?.data?.detail || (e as any)?.message || '请求失败';
          errors.push(`Panel ${panel.page_number}-${panel.panel_number}: ${detail}`);
        } finally {
          setGeneratingPanelId(null);
        }
      }

      if (!isMountedRef.current || viewKeyRef.current !== requestKey) return;
      setBatchErrors(errors);

      if (batchStopRequestedRef.current) {
        addToast('已停止批量生成画格图片', 'info');
      } else if (errors.length > 0) {
        addToast(`画格批量生成完成（失败 ${errors.length}）`, 'info');
      } else {
        addToast('画格批量生成完成', 'success');
      }

      await fetchImages();
    } finally {
      if (!isMountedRef.current || viewKeyRef.current !== requestKey) return;
      setBatchGenerating(false);
      setBatchProgress(null);
      batchAbortRef.current = null;
      batchStopRequestedRef.current = false;
      setGeneratingPanelId(null);
    }
  };

  const handleBatchGeneratePages = async () => {
    if (!manga || !Array.isArray(manga.pages) || manga.pages.length === 0) {
      addToast('暂无页面数据，请先生成分镜', 'info');
      return;
    }
    if (batchGenerating) return;

    const requestKey = `${projectId}:${chapterNumber}`;
    batchStopRequestedRef.current = false;
    setBatchErrors([]);
    setBatchGenerating(true);

    const controller = new AbortController();
    batchAbortRef.current = controller;

    try {
      const pages = [...manga.pages].sort((a, b) => Number(a.page_number || 0) - Number(b.page_number || 0));
      const targets = pages
        .map((p) => {
          const pp = pagePromptByPageNumber.get(p.page_number);
          return { page: p, pagePrompt: pp || null };
        })
        .filter(({ page, pagePrompt }) => {
          if (!pagePrompt) return false;
          const pageId = `page${page.page_number}`;
          if (!batchSkipExistingImages) return true;
          const existing = imagesByPanelId.get(pageId) || [];
          return existing.length === 0;
        });

      if (targets.length === 0) {
        addToast('没有需要生成的整页图片（可能缺少整页提示词或都已有图片）', 'info');
        return;
      }

      const errors: string[] = [];
      for (let i = 0; i < targets.length; i += 1) {
        if (!isMountedRef.current || viewKeyRef.current !== requestKey) break;
        if (batchStopRequestedRef.current) break;

        const { page, pagePrompt } = targets[i];
        if (!pagePrompt) continue;

        setBatchProgress({
          current: i + 1,
          total: targets.length,
          message: `第 ${page.page_number} 页`,
        });
        setGeneratingPageNumber(page.page_number);

        try {
          const result = await imageGenerationApi.generatePageImage(
            projectId,
            chapterNumber,
            page.page_number,
            {
              full_page_prompt: pagePrompt.full_page_prompt || '',
              negative_prompt: pagePrompt.negative_prompt || null,
              layout_template: pagePrompt.layout_template || '',
              layout_description: pagePrompt.layout_description || '',
              ratio: pagePrompt.aspect_ratio || '3:4',
              resolution: '2K',
              style: 'manga',
              panel_summaries: pagePrompt.panel_summaries || [],
              reference_image_paths: pagePrompt.reference_image_paths || null,
              dialogue_language: manga?.dialogue_language || 'chinese',
            },
            { signal: controller.signal, silent: true }
          );

          if (!result.success) {
            errors.push(`Page ${page.page_number}: ${result.error_message || '生成失败'}`);
          }
        } catch (e) {
          const code = (e as any)?.code;
          const name = (e as any)?.name;
          if (code === 'ERR_CANCELED' || name === 'CanceledError') {
            if (batchStopRequestedRef.current) break;
            errors.push(`Page ${page.page_number}: 请求被取消`);
            break;
          }
          const detail = (e as any)?.response?.data?.detail || (e as any)?.message || '请求失败';
          errors.push(`Page ${page.page_number}: ${detail}`);
        } finally {
          setGeneratingPageNumber(null);
        }
      }

      if (!isMountedRef.current || viewKeyRef.current !== requestKey) return;
      setBatchErrors(errors);

      if (batchStopRequestedRef.current) {
        addToast('已停止批量生成整页图片', 'info');
      } else if (errors.length > 0) {
        addToast(`整页批量生成完成（失败 ${errors.length}）`, 'info');
      } else {
        addToast('整页批量生成完成', 'success');
      }

      await fetchImages();
    } finally {
      if (!isMountedRef.current || viewKeyRef.current !== requestKey) return;
      setBatchGenerating(false);
      setBatchProgress(null);
      batchAbortRef.current = null;
      batchStopRequestedRef.current = false;
      setGeneratingPageNumber(null);
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
            variant={(manga && !canResumeGeneration) ? "ghost" : "primary"} 
            size="sm" 
            onClick={() => handleGeneratePrompts()}
            disabled={generatingPrompts || isProgressRunning || cancelingPrompts}
            title={`风格=${genStyle === 'custom' ? (customStyle.trim() || 'custom') : genStyle} · 语言=${genLanguage} · 页数=${minPages}-${maxPages} · 并发=${pagePromptConcurrency}${autoGeneratePageImages ? ' · 自动整页图片' : ''}${forceRestart ? ' · 强制重来' : ''}${startFromStage !== 'auto' ? ` · 从${startFromStage}开始` : ''}`}
          >
            <RefreshCw size={14} className={`mr-1 ${generatingPrompts ? 'animate-spin' : ''}`} />
            {(generatingPrompts || isProgressRunning)
              ? '生成中...'
              : (canResumeGeneration ? '继续生成分镜' : (manga ? '重新生成分镜' : '生成分镜'))}
          </BookButton>
        </div>
      </div>

      <MangaProgressCard
        showProgress={showProgress}
        progress={progress}
        progressStatus={progressStatus}
        generatingPrompts={generatingPrompts}
        isProgressRunning={isProgressRunning}
        cancelingPrompts={cancelingPrompts}
        canResumeGeneration={canResumeGeneration}
        progressPercent={progressPercent}
        onCancel={handleCancelPrompts}
        onResume={handleResumePrompts}
        onForceRestart={handleForceRestartPrompts}
      />

      <MangaGenerationParams
        genStyle={genStyle}
        setGenStyle={setGenStyle}
        customStyle={customStyle}
        setCustomStyle={setCustomStyle}
        genLanguage={genLanguage}
        setGenLanguage={setGenLanguage}
        minPages={minPages}
        setMinPages={setMinPages}
        maxPages={maxPages}
        setMaxPages={setMaxPages}
        startFromStage={startFromStage}
        setStartFromStage={setStartFromStage}
        pagePromptConcurrency={pagePromptConcurrency}
        setPagePromptConcurrency={setPagePromptConcurrency}
        usePortraits={usePortraits}
        setUsePortraits={setUsePortraits}
        autoGeneratePortraits={autoGeneratePortraits}
        setAutoGeneratePortraits={setAutoGeneratePortraits}
        autoGeneratePageImages={autoGeneratePageImages}
        setAutoGeneratePageImages={setAutoGeneratePageImages}
        forceRestart={forceRestart}
        setForceRestart={setForceRestart}
        disabled={generatingPrompts}
      />

      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab('storyboard')}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all ${
            activeTab === 'storyboard'
              ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
              : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
          }`}
        >
          分镜
        </button>
        <button
          onClick={() => setActiveTab('details')}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all ${
            activeTab === 'details'
              ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
              : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
          }`}
        >
          详细信息
        </button>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2].map(i => (
            <div key={i} className="h-32 bg-book-bg-paper animate-pulse rounded-lg" />
          ))}
        </div>
      ) : (
        <div className="space-y-8">
          <MangaSummarySection
            manga={manga}
            pdfInfo={pdfInfo}
            pdfGeneratingLayout={pdfGeneratingLayout}
            onGeneratePdf={handleGeneratePdf}
            onDeleteMangaPrompts={handleDeleteMangaPrompts}
            generatingPrompts={generatingPrompts}
            isProgressRunning={isProgressRunning}
            batchGenerating={batchGenerating}
            pdfPreviewOpen={pdfPreviewOpen}
            onPdfPreviewOpenChange={setPdfPreviewOpen}
            pdfPreviewUrl={pdfPreviewUrl}
            batchSkipExistingImages={batchSkipExistingImages}
            onBatchSkipExistingImagesChange={setBatchSkipExistingImages}
            onStopBatch={stopBatch}
            onBatchGeneratePanels={handleBatchGeneratePanels}
            onBatchGeneratePages={handleBatchGeneratePages}
            batchProgress={batchProgress}
            batchErrors={batchErrors}
            onCopyText={copyText}
          />

          {activeTab === 'details' && (
            <MangaDetailsTab
              sortedCharacterProfiles={sortedCharacterProfiles}
              analysisData={analysisData}
              chapterInfo={chapterInfo}
              pagePlan={pagePlan}
              onCopyText={copyText}
            />
          )}

          {activeTab === 'storyboard' && (
            <MangaStoryboardTab
              manga={manga}
              generatingPrompts={generatingPrompts}
              panelsByPageNumber={panelsByPageNumber}
              pagePromptByPageNumber={pagePromptByPageNumber}
              imagesByPanelId={imagesByPanelId}
              activeImageByPanelId={activeImageByPanelId}
              onSelectActiveImage={handleSelectActiveImage}
              generatingPageNumber={generatingPageNumber}
              generatingPanelId={generatingPanelId}
              batchGenerating={batchGenerating}
              onGeneratePageImage={handleGeneratePageImage}
              onGeneratePanelImage={handleGeneratePanelImage}
              onDeleteImage={handleDeleteImage}
              onCopyText={copyText}
            />
          )}
        </div>
      )}
    </div>
  );
};
