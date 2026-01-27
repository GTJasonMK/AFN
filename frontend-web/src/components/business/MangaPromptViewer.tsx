import React, { useMemo, useState, useEffect, useCallback, useRef } from 'react';
import { writerApi, MangaPromptResult, MangaPanel, MangaPagePrompt, MangaPromptProgress } from '../../api/writer';
import { imageGenerationApi, GeneratedImageInfo, resolveAssetUrl, ChapterMangaPDFResponse } from '../../api/imageGeneration';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';
import { Layers, RefreshCw, Image as ImageIcon, FileDown, Copy, Info, XCircle, Play, Trash2 } from 'lucide-react';
import { useToast } from '../feedback/Toast';

interface MangaPromptViewerProps {
  projectId: string;
  chapterNumber: number;
}

const safeJson = (value: any) => {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value ?? '');
  }
};

const widthRatioToSpan = (widthRatio: any): number => {
  const v = String(widthRatio || '').trim();
  if (v === 'full') return 12;
  if (v === 'two_thirds') return 8;
  if (v === 'half') return 6;
  if (v === 'third') return 4;
  return 6;
};

const aspectRatioToCss = (aspectRatio: any): string | undefined => {
  const v = String(aspectRatio || '').trim();
  const m = v.match(/^\s*(\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)\s*$/);
  if (!m) return undefined;
  return `${m[1]} / ${m[2]}`;
};

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

  const [genStyle, setGenStyle] = useState<'manga' | 'anime' | 'comic' | 'webtoon' | 'custom'>('manga');
  const [customStyle, setCustomStyle] = useState('漫画风格, 黑白漫画, 网点纸, 日式漫画, 精细线条, 高对比度');
  const [genLanguage, setGenLanguage] = useState<'chinese' | 'japanese' | 'english' | 'korean'>('chinese');
  const [minPages, setMinPages] = useState(8);
  const [maxPages, setMaxPages] = useState(15);
  const [usePortraits, setUsePortraits] = useState(true);
  const [autoGeneratePortraits, setAutoGeneratePortraits] = useState(true);
  const [autoGeneratePageImages, setAutoGeneratePageImages] = useState(false);
  const [pagePromptConcurrency, setPagePromptConcurrency] = useState(5);
  const [startFromStage, setStartFromStage] = useState<
    'auto' | 'extraction' | 'planning' | 'storyboard' | 'prompt_building' | 'page_prompt_building'
  >('auto');
  const [forceRestart, setForceRestart] = useState(false);

  const [images, setImages] = useState<GeneratedImageInfo[]>([]);
  const [imagesLoading, setImagesLoading] = useState(false);
  const [activeImageByPanelId, setActiveImageByPanelId] = useState<Record<string, number | null>>({});
  const [generatingPanelId, setGeneratingPanelId] = useState<string | null>(null);
  const [generatingPageNumber, setGeneratingPageNumber] = useState<number | null>(null);

  const [pdfInfo, setPdfInfo] = useState<ChapterMangaPDFResponse | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfGeneratingLayout, setPdfGeneratingLayout] = useState<'full' | 'manga' | null>(null);
  const [batchSkipExistingImages, setBatchSkipExistingImages] = useState(true);
  const [batchGenerating, setBatchGenerating] = useState(false);
  const [batchProgress, setBatchProgress] = useState<{ current: number; total: number; message: string } | null>(null);
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
      const response = await writerApi.getMangaPrompts(projectId, chapterNumber, { silent: true } as any);
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
      const data = await writerApi.getMangaPromptProgress(projectId, chapterNumber, { silent: true } as any);
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
        const data = await writerApi.getMangaPromptProgress(projectId, chapterNumber, { silent: true } as any);
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

  // 按项目持久化漫画分镜生成参数（避免每次重复设置）
  useEffect(() => {
    if (!projectId) return;
    try {
      const raw = localStorage.getItem(`afn:manga_gen_opts:${projectId}`);
      if (!raw) return;
      const d = JSON.parse(raw) as any;
      const styleMode = typeof d?.styleMode === 'string' ? d.styleMode : '';
      const style = typeof d?.style === 'string' ? d.style : '';
      const custom = typeof d?.customStyle === 'string' ? d.customStyle : '';
      const styleOptions = new Set(['manga', 'anime', 'comic', 'webtoon', 'custom']);

      if (styleMode && styleOptions.has(styleMode)) {
        setGenStyle(styleMode as any);
      } else if (style && styleOptions.has(style)) {
        setGenStyle(style as any);
      } else if (style) {
        // 兼容：旧数据可能直接把 style 写成了完整描述字符串
        setGenStyle('custom');
        setCustomStyle(style);
      }

      if (custom) setCustomStyle(custom);

      if (d?.language) setGenLanguage(d.language);
      if (typeof d?.minPages === 'number') setMinPages(d.minPages);
      if (typeof d?.maxPages === 'number') setMaxPages(d.maxPages);
      if (typeof d?.usePortraits === 'boolean') setUsePortraits(d.usePortraits);
      if (typeof d?.autoGeneratePortraits === 'boolean') setAutoGeneratePortraits(d.autoGeneratePortraits);
      if (typeof d?.autoGeneratePageImages === 'boolean') setAutoGeneratePageImages(d.autoGeneratePageImages);
      if (typeof d?.pagePromptConcurrency === 'number') {
        const v = Math.max(1, Math.min(20, Math.floor(d.pagePromptConcurrency)));
        setPagePromptConcurrency(v);
      }
      if (typeof d?.startFromStage === 'string') {
        const allowed = new Set(['auto', 'extraction', 'planning', 'storyboard', 'prompt_building', 'page_prompt_building']);
        if (allowed.has(d.startFromStage)) setStartFromStage(d.startFromStage);
      }
      if (typeof d?.forceRestart === 'boolean') setForceRestart(d.forceRestart);
    } catch {
      // ignore
    }
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;
    try {
      const normalizedCustomStyle = (customStyle || '').trim();
      const styleValue = genStyle === 'custom' ? (normalizedCustomStyle || 'manga') : genStyle;
      localStorage.setItem(
        `afn:manga_gen_opts:${projectId}`,
        JSON.stringify({
          styleMode: genStyle,
          style: styleValue,
          customStyle: normalizedCustomStyle || undefined,
          language: genLanguage,
          minPages,
          maxPages,
          usePortraits,
          autoGeneratePortraits,
          autoGeneratePageImages,
          pagePromptConcurrency,
          startFromStage,
          forceRestart,
        })
      );
    } catch {
      // ignore
    }
  }, [autoGeneratePageImages, autoGeneratePortraits, customStyle, forceRestart, genLanguage, genStyle, maxPages, minPages, pagePromptConcurrency, projectId, startFromStage, usePortraits]);

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
        { timeout: 0, signal: controller.signal, silent: true } as any
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
          const data = await writerApi.getMangaPromptProgress(projectId, chapterNumber, { silent: true } as any);
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
      const resp = await writerApi.cancelMangaPromptGeneration(projectId, chapterNumber, { silent: true } as any);
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
    const ok = confirm(`确定要删除图片吗？\n${label}`);
    if (!ok) return;
    try {
      await imageGenerationApi.deleteImage(img.id, { silent: true } as any);
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
    const ok = confirm('确定要删除本章的漫画分镜数据吗？（不会自动删除已生成的图片）');
    if (!ok) return;
    try {
      stopProgressPolling();
      lastGenerationStartAtRef.current = null;
      setGeneratingPrompts(false);
      setProgress(null);
      await writerApi.deleteMangaPrompts(projectId, chapterNumber, { silent: true } as any);
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
            { signal: controller.signal, silent: true } as any
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
            { signal: controller.signal, silent: true } as any
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

      {showProgress && (
        <BookCard className="p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="font-bold text-book-text-main">
                生成进度：{progress?.stage_label || (generatingPrompts ? '处理中' : '未开始')}
                {progressStatus === 'completed' ? '（已完成）' : null}
                {progressStatus === 'cancelled' ? '（已取消）' : null}
              </div>
              <div className="mt-1 text-xs text-book-text-muted whitespace-pre-wrap leading-relaxed">
                {progress?.message || (generatingPrompts ? '生成中…（可在此查看进度）' : '')}
              </div>
            </div>
            <div className="flex items-center gap-2 flex-none">
              {(generatingPrompts || isProgressRunning) && (
                <BookButton
                  variant="ghost"
                  size="sm"
                  onClick={handleCancelPrompts}
                  disabled={cancelingPrompts}
                >
                  <XCircle size={14} className="mr-1" />
                  {cancelingPrompts ? '停止中…' : '停止生成'}
                </BookButton>
              )}
              {canResumeGeneration && !generatingPrompts && (
                <>
                  <BookButton variant="primary" size="sm" onClick={handleResumePrompts} disabled={cancelingPrompts}>
                    <Play size={14} className="mr-1" />
                    继续生成
                  </BookButton>
                  <BookButton variant="ghost" size="sm" onClick={handleForceRestartPrompts} disabled={cancelingPrompts}>
                    <RefreshCw size={14} className="mr-1" />
                    强制重来
                  </BookButton>
                </>
              )}
            </div>
          </div>

          {progressPercent !== null && (
            <div className="mt-3">
              <div className="h-2 rounded-full bg-book-border/30 overflow-hidden">
                <div className="h-2 bg-book-primary" style={{ width: `${progressPercent}%` }} />
              </div>
              <div className="mt-1 text-[11px] text-book-text-muted">
                {progress?.current ?? 0}/{progress?.total ?? 0}（{progressPercent}%）
              </div>
            </div>
          )}
        </BookCard>
      )}

      <details className="group rounded-lg border border-book-border/40 bg-book-bg-paper">
        <summary className="cursor-pointer select-none px-4 py-3 font-bold text-book-text-main">
          生成参数
          <span className="ml-2 text-[11px] font-normal text-book-text-muted">
            {(genStyle === 'custom' ? 'custom' : genStyle)} · {genLanguage} · {minPages}-{maxPages}页{forceRestart ? ' · 强制重来' : ''}
          </span>
        </summary>
        <div className="px-4 pb-4 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <label className="text-xs font-bold text-book-text-sub">
              风格
              <select
                className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                value={genStyle}
                onChange={(e) => setGenStyle(e.target.value as any)}
                disabled={generatingPrompts}
              >
                <option value="manga">manga（日漫）</option>
                <option value="anime">anime（动画）</option>
                <option value="comic">comic（美漫）</option>
                <option value="webtoon">webtoon（条漫）</option>
                <option value="custom">custom（自定义）</option>
              </select>
            </label>

            <label className="text-xs font-bold text-book-text-sub">
              语言
              <select
                className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                value={genLanguage}
                onChange={(e) => setGenLanguage(e.target.value as any)}
                disabled={generatingPrompts}
              >
                <option value="chinese">中文</option>
                <option value="japanese">日文</option>
                <option value="english">英文</option>
                <option value="korean">韩文</option>
              </select>
            </label>
          </div>

          {genStyle === 'custom' && (
            <label className="text-xs font-bold text-book-text-sub">
              自定义风格描述
              <input
                type="text"
                className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                value={customStyle}
                onChange={(e) => setCustomStyle(e.target.value)}
                disabled={generatingPrompts}
                placeholder="例如：漫画风格, 黑白漫画, 网点纸, 日式漫画, 精细线条, 高对比度"
              />
            </label>
          )}

          <div className="grid grid-cols-2 gap-3">
            <label className="text-xs font-bold text-book-text-sub">
              最少页数
              <input
                type="number"
                min={3}
                max={30}
                className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                value={minPages}
                onChange={(e) => {
                  const v = Math.max(3, Math.min(30, Number(e.target.value) || 3));
                  setMinPages(v);
                  if (v > maxPages) setMaxPages(v);
                }}
                disabled={generatingPrompts}
              />
            </label>
            <label className="text-xs font-bold text-book-text-sub">
              最多页数
              <input
                type="number"
                min={3}
                max={30}
                className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                value={maxPages}
                onChange={(e) => {
                  const v = Math.max(3, Math.min(30, Number(e.target.value) || 3));
                  setMaxPages(v);
                  if (v < minPages) setMinPages(v);
                }}
                disabled={generatingPrompts}
              />
            </label>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <label className="text-xs font-bold text-book-text-sub">
              从阶段开始
              <select
                className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                value={startFromStage}
                onChange={(e) => setStartFromStage(e.target.value as any)}
                disabled={generatingPrompts}
              >
                <option value="auto">自动（断点续传/从头）</option>
                <option value="extraction">extraction（信息提取）</option>
                <option value="planning">planning（页面规划）</option>
                <option value="storyboard">storyboard（分镜设计）</option>
                <option value="prompt_building">prompt_building（画格提示词）</option>
                <option value="page_prompt_building">page_prompt_building（整页提示词）</option>
              </select>
            </label>

            <label className="text-xs font-bold text-book-text-sub">
              整页提示词并发数
              <input
                type="number"
                min={1}
                max={20}
                className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                value={pagePromptConcurrency}
                onChange={(e) => {
                  const v = Math.max(1, Math.min(20, Math.floor(Number(e.target.value) || 1)));
                  setPagePromptConcurrency(v);
                }}
                disabled={generatingPrompts}
              />
            </label>
          </div>

          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm text-book-text-main">
              <input
                type="checkbox"
                className="rounded border-book-border text-book-primary focus:ring-book-primary"
                checked={usePortraits}
                onChange={(e) => setUsePortraits(e.target.checked)}
                disabled={generatingPrompts}
              />
              <span className="font-bold">使用角色立绘作为参考图</span>
            </label>
            <label className="flex items-center gap-2 text-sm text-book-text-main">
              <input
                type="checkbox"
                className="rounded border-book-border text-book-primary focus:ring-book-primary"
                checked={autoGeneratePortraits}
                onChange={(e) => setAutoGeneratePortraits(e.target.checked)}
                disabled={generatingPrompts}
              />
              <span className="font-bold">缺失立绘自动生成</span>
            </label>
            <label className="flex items-center gap-2 text-sm text-book-text-main">
              <input
                type="checkbox"
                className="rounded border-book-border text-book-primary focus:ring-book-primary"
                checked={autoGeneratePageImages}
                onChange={(e) => setAutoGeneratePageImages(e.target.checked)}
                disabled={generatingPrompts}
              />
              <span className="font-bold">分镜完成后自动生成整页图片（耗时）</span>
            </label>
            <label className="flex items-center gap-2 text-sm text-book-text-main">
              <input
                type="checkbox"
                className="rounded border-book-border text-book-primary focus:ring-book-primary"
                checked={forceRestart}
                onChange={(e) => setForceRestart(e.target.checked)}
                disabled={generatingPrompts}
              />
              <span className="font-bold">强制从头开始（忽略断点）</span>
            </label>
          </div>

          <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 leading-relaxed">
            提示：页数越多生成越慢；“自动生成整页图片”会显著增加耗时；“强制从头开始”会忽略断点与已有结果（适合你想完全重做分镜的场景）。
          </div>
        </div>
      </details>

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
          {manga && (
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
                    <BookButton
                      variant="ghost"
                      size="sm"
                      onClick={handleDeleteMangaPrompts}
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
                    <div className="text-xs text-book-text-muted flex items-center justify-between gap-2">
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

                    <details className="group rounded-lg border border-book-border/40 bg-book-bg-paper">
                      <summary className="cursor-pointer select-none px-3 py-2 text-xs font-bold text-book-text-main">
                        PDF 预览
                        <span className="ml-2 text-[11px] font-normal text-book-text-muted">点击展开</span>
                      </summary>
                      <div className="px-3 pb-3">
                        <iframe
                          src={resolveAssetUrl(pdfInfo.download_url)}
                          className="w-full h-[70vh] rounded-md border border-book-border/40 bg-book-bg"
                          title="manga-pdf-preview"
                        />
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
                  <div className="flex items-center gap-2 flex-none">
                    <label className="flex items-center gap-2 text-xs text-book-text-main">
                      <input
                        type="checkbox"
                        className="rounded border-book-border text-book-primary focus:ring-book-primary"
                        checked={batchSkipExistingImages}
                        onChange={(e) => setBatchSkipExistingImages(e.target.checked)}
                        disabled={batchGenerating}
                      />
                      跳过已有
                    </label>
                    {batchGenerating && (
                      <BookButton variant="ghost" size="sm" onClick={stopBatch}>
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
                    onClick={handleBatchGeneratePanels}
                    disabled={batchGenerating || generatingPrompts || isProgressRunning}
                    title="生成本章所有画格图片（按顺序）"
                  >
                    <ImageIcon size={14} className="mr-1" />
                    生成所有画格
                  </BookButton>
                  <BookButton
                    variant="ghost"
                    size="sm"
                    onClick={handleBatchGeneratePages}
                    disabled={batchGenerating || generatingPrompts || isProgressRunning}
                    title="生成本章所有整页图片（需要 page_prompts）"
                  >
                    <ImageIcon size={14} className="mr-1" />
                    生成所有整页
                  </BookButton>
                </div>

                {batchProgress && (
                  <div className="mt-3">
                    <div className="text-xs text-book-text-muted truncate">
                      {batchProgress.message}
                    </div>
                    <div className="mt-1 h-2 rounded-full bg-book-border/30 overflow-hidden">
                      <div
                        className="h-2 bg-book-primary transition-all duration-300"
                        style={{ width: `${Math.min(100, Math.max(0, (batchProgress.current / Math.max(1, batchProgress.total)) * 100))}%` }}
                      />
                    </div>
                    <div className="mt-1 text-[11px] text-book-text-muted">
                      {batchProgress.current}/{batchProgress.total}
                    </div>
                  </div>
                )}

                {batchErrors.length > 0 && (
                  <details className="mt-3 group rounded-lg border border-book-border/40 bg-book-bg-paper">
                    <summary className="cursor-pointer select-none px-3 py-2 text-xs font-bold text-book-text-main">
                      失败明细（{batchErrors.length}）
                      <span className="ml-2 text-[11px] font-normal text-book-text-muted">点击展开</span>
                    </summary>
                    <div className="px-3 pb-3 space-y-2">
                      <div className="flex justify-end">
                        <BookButton variant="ghost" size="sm" onClick={() => copyText(batchErrors.join('\n'), '批量生成失败明细')}>
                          <Copy size={14} className="mr-1" />
                          复制
                        </BookButton>
                      </div>
                      <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed bg-book-bg p-2 rounded border border-book-border/40 overflow-auto">
                        {batchErrors.join('\n')}
                      </pre>
                    </div>
                  </details>
                )}
              </BookCard>
            </>
          )}

          {activeTab === 'details' && (
            <div className="space-y-4">
              {sortedCharacterProfiles.length > 0 && (
                <BookCard className="p-4">
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="font-bold text-book-text-main">角色外观（提示词）</div>
                    <BookButton
                      variant="ghost"
                      size="sm"
                      onClick={() => copyText(safeJson(Object.fromEntries(sortedCharacterProfiles.map((c) => [c.name, c.desc]))), '角色外观JSON')}
                    >
                      <Copy size={14} className="mr-1" />
                      复制JSON
                    </BookButton>
                  </div>
                  <div className="space-y-3">
                    {sortedCharacterProfiles.map((c) => (
                      <div key={c.name} className="border border-book-border/40 rounded-lg p-3 bg-book-bg">
                        <div className="font-bold text-book-primary">{c.name}</div>
                        <div className="mt-2 text-xs text-book-text-main whitespace-pre-wrap leading-relaxed font-mono">
                          {c.desc}
                        </div>
                      </div>
                    ))}
                  </div>
                </BookCard>
              )}

              {!analysisData && (
                <BookCard className="p-4">
                  <div className="flex items-start gap-2 text-xs text-book-text-muted leading-relaxed">
                    <Info size={16} className="mt-0.5 flex-none" />
                    <div>
                      暂无详细信息（analysis_data）。生成分镜后，如果后端返回分析数据，这里会展示“信息提取/页面规划”等结构化结果。
                    </div>
                  </div>
                </BookCard>
              )}

              {analysisData && (
                <div className="space-y-3">
                  <details className="group rounded-lg border border-book-border/40 bg-book-bg-paper">
                    <summary className="cursor-pointer select-none px-4 py-3 font-bold text-book-text-main">
                      步骤1：信息提取
                    </summary>
                    <div className="px-4 pb-4 space-y-3">
                      {chapterInfo?.chapter_summary ? (
                        <BookCard className="p-3 bg-book-bg/50 border-book-border/50">
                          <div className="text-xs font-bold text-book-text-sub mb-1">章节摘要</div>
                          <div className="text-sm text-book-text-main whitespace-pre-wrap leading-relaxed">
                            {String(chapterInfo.chapter_summary)}
                          </div>
                        </BookCard>
                      ) : null}

                      {chapterInfo?.characters && typeof chapterInfo.characters === 'object' && !Array.isArray(chapterInfo.characters) ? (
                        <BookCard className="p-3 bg-book-bg/50 border-book-border/50">
                          <div className="text-xs font-bold text-book-text-sub mb-2">角色信息</div>
                          <div className="space-y-2">
                            {Object.entries(chapterInfo.characters as Record<string, any>).map(([name, v]) => (
                              <div key={name} className="border border-book-border/40 rounded-lg p-2 bg-book-bg">
                                <div className="font-bold text-book-primary text-sm">{name}</div>
                                <div className="mt-1 text-xs text-book-text-main whitespace-pre-wrap leading-relaxed">
                                  {typeof v === 'string' ? v : safeJson(v)}
                                </div>
                              </div>
                            ))}
                          </div>
                        </BookCard>
                      ) : null}

                      {Array.isArray(chapterInfo?.events) && chapterInfo.events.length > 0 ? (
                        <BookCard className="p-3 bg-book-bg/50 border-book-border/50">
                          <div className="text-xs font-bold text-book-text-sub mb-2">事件列表</div>
                          <ul className="list-decimal list-inside text-xs text-book-text-main space-y-1">
                            {chapterInfo.events.map((evt: any, idx: number) => (
                              <li key={`evt-${idx}`} className="whitespace-pre-wrap">
                                {typeof evt === 'string' ? evt : safeJson(evt)}
                              </li>
                            ))}
                          </ul>
                        </BookCard>
                      ) : null}

                      {Array.isArray(chapterInfo?.dialogues) && chapterInfo.dialogues.length > 0 ? (
                        <BookCard className="p-3 bg-book-bg/50 border-book-border/50">
                          <div className="text-xs font-bold text-book-text-sub mb-2">对话列表</div>
                          <div className="space-y-2">
                            {chapterInfo.dialogues.map((d: any, idx: number) => {
                              const speaker = String(d?.speaker || d?.character || '').trim();
                              const text = String(d?.text || d?.content || '').trim();
                              return (
                                <div key={`dlg-${idx}`} className="border border-book-border/40 rounded-lg p-2 bg-book-bg">
                                  <div className="text-[11px] text-book-text-muted font-mono">
                                    {speaker ? `speaker: ${speaker}` : 'speaker: —'}
                                  </div>
                                  <div className="mt-1 text-xs text-book-text-main whitespace-pre-wrap leading-relaxed">
                                    {text || (typeof d === 'string' ? d : safeJson(d))}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </BookCard>
                      ) : null}

                      {Array.isArray(chapterInfo?.scenes) && chapterInfo.scenes.length > 0 ? (
                        <BookCard className="p-3 bg-book-bg/50 border-book-border/50">
                          <div className="text-xs font-bold text-book-text-sub mb-2">场景列表</div>
                          <ul className="list-disc list-inside text-xs text-book-text-main space-y-1">
                            {chapterInfo.scenes.map((s: any, idx: number) => (
                              <li key={`scene-${idx}`} className="whitespace-pre-wrap">
                                {typeof s === 'string' ? s : safeJson(s)}
                              </li>
                            ))}
                          </ul>
                        </BookCard>
                      ) : null}
                    </div>
                  </details>

                  <details className="group rounded-lg border border-book-border/40 bg-book-bg-paper">
                    <summary className="cursor-pointer select-none px-4 py-3 font-bold text-book-text-main">
                      步骤2：页面规划
                    </summary>
                    <div className="px-4 pb-4 space-y-3">
                      {Array.isArray(pagePlan?.pages) && pagePlan.pages.length > 0 ? (
                        <BookCard className="p-3 bg-book-bg/50 border-book-border/50">
                          <div className="text-xs font-bold text-book-text-sub mb-2">页面分配</div>
                          <div className="space-y-2">
                            {pagePlan.pages.map((p: any, idx: number) => (
                              <div key={`pp-${idx}`} className="border border-book-border/40 rounded-lg p-2 bg-book-bg">
                                <div className="text-xs font-bold text-book-primary">
                                  第 {p?.page_number ?? idx + 1} 页
                                </div>
                                <div className="mt-1 text-xs text-book-text-main whitespace-pre-wrap leading-relaxed">
                                  {p?.layout_description ? String(p.layout_description) : safeJson(p)}
                                </div>
                              </div>
                            ))}
                          </div>
                        </BookCard>
                      ) : (
                        <BookCard className="p-3 bg-book-bg/50 border-book-border/50">
                          <div className="text-xs text-book-text-muted">
                            无页面规划数据（page_plan.pages）。
                          </div>
                        </BookCard>
                      )}
                    </div>
                  </details>

                  <details className="group rounded-lg border border-book-border/40 bg-book-bg-paper">
                    <summary className="cursor-pointer select-none px-4 py-3 font-bold text-book-text-main">
                      原始数据（JSON）
                    </summary>
                    <div className="px-4 pb-4 space-y-2">
                      <div className="flex justify-end">
                        <BookButton variant="secondary" size="sm" onClick={() => copyText(safeJson(analysisData), 'analysis_data')}>
                          <Copy size={14} className="mr-1" />
                          复制
                        </BookButton>
                      </div>
                      <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/40 overflow-auto">
                        {safeJson(analysisData)}
                      </pre>
                    </div>
                  </details>
                </div>
              )}
            </div>
          )}

          {activeTab === 'storyboard' && (manga?.pages || []).map((page) => {
            const panels = panelsByPageNumber.get(page.page_number) || [];
            const pageId = `page${page.page_number}`;
            const pageImages = imagesByPanelId.get(pageId) || [];
            const activePageImageId = activeImageByPanelId[pageId];
            const pageImage = activePageImageId
              ? (pageImages.find((i) => i.id === activePageImageId) || pageImages[0])
              : pageImages[0];
            const pagePrompt = pagePromptByPageNumber.get(page.page_number) || null;
            const hasPagePrompt = Boolean(pagePrompt);
            const panelsByRow = new Map<number, MangaPanel[]>();
            panels.forEach((p) => {
              const rowId = Number((p as any).row_id || 1);
              const list = panelsByRow.get(rowId) || [];
              list.push(p);
              panelsByRow.set(rowId, list);
            });
            for (const [k, list] of panelsByRow.entries()) {
              list.sort((a, b) => Number(a.panel_number || 0) - Number(b.panel_number || 0));
              panelsByRow.set(k, list);
            }
            const rowIds = Array.from(panelsByRow.keys()).sort((a, b) => a - b);

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
                      disabled={!hasPagePrompt || generatingPageNumber !== null || batchGenerating}
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

                {pagePrompt && (
                  <details className="group rounded-lg border border-book-border/40 bg-book-bg-paper">
                    <summary className="cursor-pointer select-none px-3 py-2 text-xs font-bold text-book-text-main">
                      整页提示词（page_prompts）
                      <span className="ml-2 text-[11px] font-normal text-book-text-muted">
                        点击展开
                      </span>
                    </summary>
                    <div className="px-3 pb-3 space-y-2">
                      <div className="flex items-center justify-end gap-2">
                        <BookButton variant="ghost" size="sm" onClick={() => copyText(pagePrompt.full_page_prompt || '', `第${page.page_number}页整页提示词`)}>
                          <Copy size={14} className="mr-1" />
                          复制提示词
                        </BookButton>
                      </div>
                      {pagePrompt.layout_description && (
                        <div className="text-xs text-book-text-muted whitespace-pre-wrap">
                          {pagePrompt.layout_description}
                        </div>
                      )}
                      <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed bg-book-bg p-2 rounded border border-book-border/40 overflow-auto">
                        {pagePrompt.full_page_prompt || ''}
                      </pre>
                    </div>
                  </details>
                )}

                {pageImage && (
                  <BookCard className="p-3">
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="text-xs text-book-text-muted">整页图片</div>
                      <BookButton
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteImage(pageImage, `第${page.page_number}页整页图片（image_id=${pageImage.id}）`)}
                      >
                        <Trash2 size={14} className="mr-1" />
                        删除
                      </BookButton>
                    </div>
                    <a href={resolveAssetUrl(pageImage.url)} target="_blank" rel="noreferrer">
                      <img
                        src={resolveAssetUrl(pageImage.url)}
                        alt={`page-${page.page_number}`}
                        className="w-full rounded-md border border-book-border/30"
                      />
                    </a>

                    {pageImages.length > 1 && (
                      <div className="mt-2 flex gap-2 overflow-x-auto no-scrollbar">
                        {pageImages.map((im) => {
                          const selected = pageImage.id === im.id;
                          return (
                            <button
                              key={`page-thumb-${im.id}`}
                              type="button"
                              onClick={() => setActiveImageByPanelId((prev) => ({ ...(prev || {}), [pageId]: im.id }))}
                              className={`flex-none w-16 h-16 rounded-md border overflow-hidden ${selected ? 'border-book-primary' : 'border-book-border/40 hover:border-book-primary/40'}`}
                              title={`image_id=${im.id}`}
                            >
                              <img
                                src={resolveAssetUrl(im.url)}
                                alt={`thumb-${im.id}`}
                                className="w-full h-full object-cover"
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
                    <div className="px-3 pb-3 space-y-3">
                      {rowIds.map((rowId) => {
                        const rowPanels = panelsByRow.get(rowId) || [];
                        return (
                          <div key={`row-${page.page_number}-${rowId}`} className="grid grid-cols-12 gap-2">
                            {rowPanels.map((panel) => {
                              const span = widthRatioToSpan((panel as any).width_ratio);
                              const cssAspect = aspectRatioToCss((panel as any).aspect_ratio);
                              const panelImages = imagesByPanelId.get(panel.panel_id) || [];
                              const activeId = activeImageByPanelId[panel.panel_id];
                              const img = activeId
                                ? (panelImages.find((i) => i.id === activeId) || panelImages[0])
                                : panelImages[0];
                              return (
                                <div
                                  key={`layout-${panel.panel_id}`}
                                  className="min-w-0"
                                  style={{ gridColumn: `span ${span} / span ${span}` }}
                                >
                                  <div className="rounded-lg border border-book-border/40 bg-book-bg p-2">
                                    <div className="flex items-center justify-between gap-2 text-[11px]">
                                      <div className="font-bold text-book-primary truncate">
                                        Panel {panel.panel_number}
                                      </div>
                                      <div className="text-book-text-muted font-mono">
                                        {String((panel as any).width_ratio || 'half')}
                                      </div>
                                    </div>

                                    <div
                                      className="mt-2 rounded-md border border-book-border/30 overflow-hidden bg-book-bg-paper/50 min-h-[120px]"
                                      style={cssAspect ? { aspectRatio: cssAspect } : undefined}
                                    >
                                      {img ? (
                                        <a href={resolveAssetUrl(img.url)} target="_blank" rel="noreferrer" className="block w-full h-full">
                                          <img
                                            src={resolveAssetUrl(img.url)}
                                            alt={panel.panel_id}
                                            className="w-full h-full object-cover"
                                          />
                                        </a>
                                      ) : (
                                        <div className="w-full h-full flex items-center justify-center text-[11px] text-book-text-muted">
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
                    const img = activePanelImageId
                      ? (panelImages.find((i) => i.id === activePanelImageId) || panelImages[0])
                      : panelImages[0];
                    const firstDialogue = Array.isArray(panel.dialogues) && panel.dialogues.length > 0 ? panel.dialogues[0] : null;
                    const dialogueSpeaker = firstDialogue ? String(firstDialogue?.speaker || firstDialogue?.character || '') : '';
                    const dialogueText = firstDialogue ? String(firstDialogue?.text || firstDialogue?.content || '') : '';
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
                            {(dialogueSpeaker || dialogueText) && (
                              <div className="mt-1 text-[11px] text-book-text-muted leading-relaxed">
                                {dialogueSpeaker ? <span className="font-bold">{dialogueSpeaker}：</span> : null}
                                {dialogueText}
                              </div>
                            )}
                          </div>
                          <BookButton
                            variant="primary"
                            size="sm"
                            onClick={() => handleGeneratePanelImage(panel)}
                            disabled={generatingPanelId !== null || batchGenerating}
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

                        {panelImages.length > 1 && (
                          <div className="mb-2 flex gap-2 overflow-x-auto no-scrollbar">
                            {panelImages.map((im) => {
                              const selected = img?.id === im.id;
                              return (
                                <button
                                  key={`panel-thumb-${im.id}`}
                                  type="button"
                                  onClick={() => setActiveImageByPanelId((prev) => ({ ...(prev || {}), [panel.panel_id]: im.id }))}
                                  className={`flex-none w-14 h-14 rounded-md border overflow-hidden ${selected ? 'border-book-primary' : 'border-book-border/40 hover:border-book-primary/40'}`}
                                  title={`image_id=${im.id}`}
                                >
                                  <img
                                    src={resolveAssetUrl(im.url)}
                                    alt={`thumb-${im.id}`}
                                    className="w-full h-full object-cover"
                                  />
                                </button>
                              );
                            })}
                          </div>
                        )}

                        <div className="space-y-2">
                          <div className="flex justify-end gap-2">
                            {img && (
                              <BookButton
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteImage(img, `Panel ${panel.panel_number}（image_id=${img.id}）`)}
                              >
                                <Trash2 size={14} className="mr-1" />
                                删除
                              </BookButton>
                            )}
                            <BookButton variant="ghost" size="sm" onClick={() => copyText(panel.prompt || '', `Panel ${panel.panel_number} 提示词`)}>
                              <Copy size={14} className="mr-1" />
                              复制
                            </BookButton>
                          </div>
                          <div className="bg-book-bg p-2 rounded text-xs font-mono text-book-text-tertiary whitespace-pre-wrap">
                            {panel.prompt}
                          </div>
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

          {activeTab === 'storyboard' && !manga && !generatingPrompts && (
            <div className="py-8 text-center text-book-text-muted text-sm">
              暂无分镜数据（可点击右上角“生成分镜”）
            </div>
          )}
        </div>
      )}
    </div>
  );
};
