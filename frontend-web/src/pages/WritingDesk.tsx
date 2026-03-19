import React, { lazy, Suspense, useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { ImportChapterModal } from '../components/business/ImportChapterModal';
import { WorkspaceTabs, type WorkspaceHandle } from '../components/business/WorkspaceTabs';
import { writerApi, Chapter } from '../api/writer';
import { novelsApi } from '../api/novels';
import { useSSE } from '../hooks/useSSE';
import { useConfirmTextModal } from '../hooks/useConfirmTextModal';
import { usePersistedState } from '../hooks/usePersistedState';
import { useToast } from '../components/feedback/Toast';
import { confirmDialog } from '../components/feedback/ConfirmDialog';
import { BookButton } from '../components/ui/BookButton';
import { readBootstrapCache, writeBootstrapCache } from '../utils/bootstrapCache';
import { downloadBlob } from '../utils/downloadFile';
import { sanitizeFilenamePart } from '../utils/sanitizeFilename';
import { clearBlueprintGenerationPending } from '../utils/blueprintPending';
import { getWritingDraftKey, readWritingDraft, removeWritingDraft, writeWritingDraft } from '../utils/writingDraft';
import { getNovelCapabilities, getWorkflowStatusLabel, resolveWorkflowStage } from '../utils/projectWorkflow';
import { PromptPreviewModal } from './writing-desk/PromptPreviewModal';
import { WritingDeskAssistant } from './writing-desk/WritingDeskAssistant';
import { WritingDeskHeader } from './writing-desk/WritingDeskHeader';
import { WritingDeskSidebar } from './writing-desk/WritingDeskSidebar';
import { WritingNotesModal } from './writing-desk/WritingNotesModal';
import { useWritingDeskPanels } from './writing-desk/useWritingDeskPanels';
import { AppViewportFrame, AppViewportShell, SegmentPager } from '../components/layout/AppViewport';

const OutlineEditModalLazy = lazy(() =>
  import('../components/business/OutlineEditModal').then((m) => ({ default: m.OutlineEditModal }))
);
const BatchGenerateModalLazy = lazy(() =>
  import('../components/business/BatchGenerateModal').then((m) => ({ default: m.BatchGenerateModal }))
);
const ProtagonistProfilesModalLazy = lazy(() =>
  import('../components/business/ProtagonistProfilesModal').then((m) => ({ default: m.ProtagonistProfilesModal }))
);

const DEFAULT_VERSION_CREATED_AT = '1970-01-01T00:00:00.000Z';
const WRITING_DESK_BOOTSTRAP_TTL_MS = 4 * 60 * 1000;

type WritingDeskBootstrapSnapshot = {
  chapters: Chapter[];
  projectInfo: any;
  projectStatus?: string;
  outlineChapterNumbers?: number[];
  needsPartOutlines?: boolean;
  partOutlineCount?: number;
  partOutlineCoverMax?: number | null;
  selectedChapterNumber: number | null;
};

const getWritingDeskBootstrapKey = (projectId: string) => `afn:web:writing-desk:${projectId}:bootstrap:v1`;

export const WritingDesk: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { addToast } = useToast();
  
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [currentChapter, setCurrentChapter] = useState<Chapter | null>(null);
  const [content, setContent] = useState('');
  const [loadedContent, setLoadedContent] = useState('');
  const [draftRevision, setDraftRevision] = useState(0);
  const {
    sidebarWidth,
    isSidebarOpen,
    setIsSidebarOpen,
    startSidebarResizing,
    assistantWidth,
    isAssistantOpen,
    setIsAssistantOpen,
    assistantMountReady,
    startAssistantResizing,
  } = useWritingDeskPanels(id);
		  const [isSaving, setIsSaving] = useState(false);
		  const [isGenerating, setIsGenerating] = useState(false);
		  const [projectInfo, setProjectInfo] = useState<any>(null);
		  const [projectStatusRaw, setProjectStatusRaw] = useState<string>('');
		  const [chapterOutlineNumbers, setChapterOutlineNumbers] = useState<number[]>([]);
		  const [needsPartOutlines, setNeedsPartOutlines] = useState(false);
		  const [partOutlineCount, setPartOutlineCount] = useState(0);
		  const [partOutlineCoverMax, setPartOutlineCoverMax] = useState<number | null>(null);
		  const [writingNotes, setWritingNotes] = usePersistedState<string>(
		    id ? `afn:writing_notes:${id}` : null,
		    '',
		    { serialize: (value) => value },
		  );
  const [isWritingNotesModalOpen, setIsWritingNotesModalOpen] = useState(false);
  const [writingNotesDraft, setWritingNotesDraft] = useState('');
  const [isPromptPreviewModalOpen, setIsPromptPreviewModalOpen] = useState(false);
  const [promptPreviewNotes, setPromptPreviewNotes] = useState('');
  const [isProtagonistModalOpen, setIsProtagonistModalOpen] = useState(false);
  const [isImportChapterModalOpen, setIsImportChapterModalOpen] = useState(false);
  const suggestedImportChapterNumber = useMemo(() => {
    if (!Array.isArray(chapters) || chapters.length === 0) return 1;
    const maxNo = chapters.reduce((acc, c) => Math.max(acc, Number(c.chapter_number) || 0), 0);
    return Math.max(1, maxNo + 1);
  }, [chapters]);
  const [genProgress, setGenProgress] = useState<{ stage?: string; message?: string; current?: number; total?: number } | null>(null);
  const isDirty = useMemo(() => content !== loadedContent, [content, loadedContent]);
	  const workspaceVersions = useMemo(() => {
	    if (!id || !currentChapter) return [];
	    const raw = Array.isArray(currentChapter?.versions) ? currentChapter.versions : [];
	    const chapterNo = Number(currentChapter.chapter_number || 0);
	    const chapterId = `${id}-${chapterNo}`;
	    const createdAt = DEFAULT_VERSION_CREATED_AT;
	    return raw.map((text, idx) => ({
	      id: `v-${idx}`,
	      chapter_id: chapterId,
	      version_label: `版本 ${idx + 1}`,
	      content: text,
	      created_at: createdAt,
	      provider: 'llm',
	    }));
	  }, [currentChapter, id]);
	  const chapterOutlineNumberSet = useMemo(() => new Set(chapterOutlineNumbers), [chapterOutlineNumbers]);
	  const latestOutlineChapterNumber = useMemo(() => {
	    if (!Array.isArray(chapterOutlineNumbers) || chapterOutlineNumbers.length === 0) return 0;
	    return chapterOutlineNumbers.reduce((acc, n) => Math.max(acc, Number(n) || 0), 0);
	  }, [chapterOutlineNumbers]);
	  const editorRef = useRef<WorkspaceHandle | null>(null);
	  const currentChapterRef = useRef<Chapter | null>(null);
	  const contentRef = useRef('');
  const isDirtyRef = useRef(false);
  const isGeneratingRef = useRef(false);
  const selectingChapterRef = useRef<number | null>(null);
  const draftPromptedRef = useRef<Set<string>>(new Set());
  const draftSaveWarnedRef = useRef(false);
  const [isCompactLayout, setIsCompactLayout] = useState(false);
  const [compactPane, setCompactPane] = useState<'chapters' | 'editor' | 'assistant'>('editor');

	      // 可选提示词弹窗（用于“重生成大纲”等可选优化方向输入）
	      const { open: openOptionalPromptModal, modal: optionalPromptModal } = useConfirmTextModal({
	        addToast,
        defaultTitle: '输入优化提示词（可选）',
        defaultLabel: '优化提示词（可选）',
        defaultRows: 8,
        defaultPlaceholder: '例如：强化冲突、补足动机、压缩节奏、增加悬疑…',
      });

  useEffect(() => {
    const syncLayoutMode = () => {
      setIsCompactLayout(window.innerWidth < 1280);
    };

    syncLayoutMode();
    window.addEventListener('resize', syncLayoutMode);
    return () => window.removeEventListener('resize', syncLayoutMode);
  }, []);

  useEffect(() => {
    if (!isCompactLayout) return;
    if (!isSidebarOpen || !isAssistantOpen) return;
    setIsAssistantOpen(false);
  }, [isAssistantOpen, isCompactLayout, isSidebarOpen, setIsAssistantOpen]);

  useEffect(() => {
    if (!id) return;
    const cached = readBootstrapCache<WritingDeskBootstrapSnapshot>(
      getWritingDeskBootstrapKey(id),
      WRITING_DESK_BOOTSTRAP_TTL_MS,
    );
	    if (!cached) {
	      setChapters([]);
	      setCurrentChapter(null);
	      currentChapterRef.current = null;
	      setProjectInfo(null);
	      setProjectStatusRaw('');
	      setChapterOutlineNumbers([]);
	      setNeedsPartOutlines(false);
	      setPartOutlineCount(0);
	      setPartOutlineCoverMax(null);
	      setContent('');
	      setLoadedContent('');
	      contentRef.current = '';
	      return;
	    }

    if (Array.isArray(cached.chapters)) {
      setChapters(cached.chapters);
      const selectedNo = Number(cached.selectedChapterNumber || 0);
      if (Number.isFinite(selectedNo) && selectedNo > 0) {
        const selected = cached.chapters.find((item) => Number(item.chapter_number) === selectedNo) || null;
        if (selected) {
          setCurrentChapter(selected);
          currentChapterRef.current = selected;
          const selectedContent = String(selected.content || '');
          setContent(selectedContent);
          setLoadedContent(selectedContent);
          contentRef.current = selectedContent;
        } else {
          setCurrentChapter(null);
          currentChapterRef.current = null;
          setContent('');
          setLoadedContent('');
          contentRef.current = '';
        }
      } else {
        setCurrentChapter(null);
        currentChapterRef.current = null;
        setContent('');
        setLoadedContent('');
        contentRef.current = '';
      }
    }

		    if (cached.projectInfo && typeof cached.projectInfo === 'object') {
		      setProjectInfo(cached.projectInfo);
		    }
		    if (cached.projectStatus) {
		      setProjectStatusRaw(String(cached.projectStatus || '').trim().toLowerCase());
		    }
		    if (Array.isArray(cached.outlineChapterNumbers)) {
		      setChapterOutlineNumbers(
		        cached.outlineChapterNumbers
		          .map((n) => Number(n))
		          .filter((n) => Number.isFinite(n) && n > 0)
		          .sort((a, b) => a - b),
		      );
		    }
		    if (typeof cached.needsPartOutlines === 'boolean') {
		      setNeedsPartOutlines(cached.needsPartOutlines);
		    }
		    if (typeof cached.partOutlineCount === 'number') {
		      setPartOutlineCount(Math.max(0, Math.floor(cached.partOutlineCount)));
		    }
		    if (cached.partOutlineCoverMax === null || typeof cached.partOutlineCoverMax === 'number') {
		      const v = cached.partOutlineCoverMax;
		      setPartOutlineCoverMax(v === null ? null : (Number.isFinite(v) && v > 0 ? Math.floor(v) : null));
		    }
		  }, [id]);

  useEffect(() => {
    if (!id) return;
    setPromptPreviewNotes('');
  }, [id]);

			  useEffect(() => {
			    currentChapterRef.current = currentChapter;
			  }, [currentChapter]);

		  useEffect(() => {
		    contentRef.current = content;
		  }, [content]);

		  useEffect(() => {
		    isDirtyRef.current = isDirty;
		  }, [isDirty]);

	  useEffect(() => {
	    isGeneratingRef.current = isGenerating;
	  }, [isGenerating]);

	  // Modal States
	  const [editingChapter, setEditingChapter] = useState<Chapter | null>(null);
	  const [isOutlineModalOpen, setIsOutlineModalOpen] = useState(false);
	  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
	  const [batchModalPreset, setBatchModalPreset] = useState<{ count: number; startFrom: number | '' }>({
	    count: 10,
	    startFrom: '',
	  });

		  const handleSelectChapter = useCallback(async (
		    chapterNumber: number,
		    opts?: { skipConfirm?: boolean; preserveLocalContent?: boolean; updateUrl?: boolean }
		  ) => {
		    if (!id) return false;
	    const skipConfirm = Boolean(opts?.skipConfirm);
	    const preserveLocalContent = Boolean(opts?.preserveLocalContent);
	    const updateUrl = opts?.updateUrl !== false;

		    if (!skipConfirm) {
		      if (isGeneratingRef.current) {
		        addToast('生成中，建议先点击右上角“停止”再切换章节', 'info');
		        return false;
		      }
			      if (isDirtyRef.current) {
			        // 先强制写入一次本地草稿，降低误操作丢稿概率
			        const currentNo = currentChapterRef.current?.chapter_number;
			        const draftOk = currentNo ? writeWritingDraft(getWritingDraftKey(id, currentNo), contentRef.current) : true;
			        if (draftOk) setDraftRevision((v) => v + 1);
			        if (!draftOk && !draftSaveWarnedRef.current) {
			          draftSaveWarnedRef.current = true;
			          addToast('本地草稿保存失败（浏览器存储不可用或容量不足），请尽快点击“保存”', 'info');
			        }
			        const ok = await confirmDialog({
			          title: '未保存修改',
			          message: draftOk
			            ? '当前章节有未保存修改。\n切换章节会离开当前编辑（已自动保存本地草稿，可随时恢复）。\n是否继续？'
			            : '当前章节有未保存修改。\n本地草稿保存失败，切换章节可能丢失未保存内容。\n是否继续？',
			          confirmText: '继续',
			          dialogType: 'warning',
			        });
			        if (!ok) return false;
			      }
			    }

	    const currentParam = searchParams.get('chapter');
	    if (updateUrl && String(chapterNumber) !== String(currentParam || '')) {
	      navigate(`/write/${id}?chapter=${chapterNumber}`, { replace: true });
	    }
	    try {
	      selectingChapterRef.current = chapterNumber;
	      const chapter = await writerApi.getChapter(id, chapterNumber);
	      setCurrentChapter(chapter);
      // 同步更新左侧章节列表状态（生成状态/字数/selected_version 等）
      setChapters((prev) => {
        const next = [...(Array.isArray(prev) ? prev : [])];
        const idx = next.findIndex((c) => Number(c.chapter_number) === Number(chapter.chapter_number));
        if (idx >= 0) next[idx] = chapter;
        else next.push(chapter);
        next.sort((a, b) => Number(a.chapter_number) - Number(b.chapter_number));
        return next;
      });

		      if (!preserveLocalContent) {
		        // 后端 ChapterSchema: content 为选中版本正文（若存在），versions 为字符串数组（候选版本正文）
		        let nextContent = '';
		        if (chapter.content && chapter.content.trim()) {
		          nextContent = chapter.content;
		        } else {
	          const versions = Array.isArray(chapter.versions) ? chapter.versions : [];
	          const selectedIdx = typeof chapter.selected_version === 'number' ? chapter.selected_version : null;
	          if (selectedIdx !== null && versions[selectedIdx]) nextContent = versions[selectedIdx];
	          else if (versions.length > 0) nextContent = versions[0];
		        }
		        setContent(nextContent);
		        setLoadedContent(nextContent);

		        // 检测是否存在本地草稿（避免刷新/误操作丢稿）
		        const draftKey = getWritingDraftKey(id, chapterNumber);
		        if (!draftPromptedRef.current.has(draftKey)) {
		          draftPromptedRef.current.add(draftKey);
		          const draft = readWritingDraft(draftKey);
			          if (draft && draft.content && draft.content !== nextContent) {
			            let ts = draft.updatedAt;
			            try {
			              ts = new Date(draft.updatedAt).toLocaleString();
			            } catch {
			              // ignore
			            }
			            const ok = await confirmDialog({
			              title: '恢复草稿',
			              message: `检测到本地草稿（${ts}）。\n是否恢复到编辑器？`,
			              confirmText: '恢复',
			              cancelText: '保持当前',
			              dialogType: 'warning',
			            });
			            if (ok) {
			              setContent(draft.content);
			              addToast('已恢复本地草稿（未保存）', 'success');
			            }
			          }
		        }
		      }
		      return true;
		    } catch (e) {
	      console.error("Failed to load chapter", e);
	      setCurrentChapter(null);
	      setContent('');
	      setLoadedContent('');
	      return false;
	    } finally {
	      if (selectingChapterRef.current === chapterNumber) selectingChapterRef.current = null;
	    }
		  }, [addToast, id, navigate, searchParams]);

		  // 本地草稿自动保存：未保存修改时写入 localStorage；保存后自动清理
		  useEffect(() => {
		    if (!id || !currentChapter) return;
		    const chapterNo = currentChapter.chapter_number;
		    const key = getWritingDraftKey(id, chapterNo);

		    if (!isDirty) {
		      removeWritingDraft(key);
		      return;
		    }

		    const t = window.setTimeout(() => {
		      const ok = writeWritingDraft(key, content);
		      if (ok) setDraftRevision((v) => v + 1);
		      if (!ok && !draftSaveWarnedRef.current) {
		        draftSaveWarnedRef.current = true;
		        addToast('本地草稿保存失败（浏览器存储不可用或容量不足），请尽快点击“保存”', 'info');
		      }
		    }, 500);
		    return () => window.clearTimeout(t);
		  }, [addToast, content, currentChapter, id, isDirty]);

			  const safeNavigate = useCallback(async (to: string) => {
			    if (!id) return;
			    if (isGeneratingRef.current) {
			      addToast('生成中，建议先点击右上角“停止”再离开写作台', 'info');
			      return;
			    }
			    if (isDirtyRef.current) {
			      const currentNo = currentChapterRef.current?.chapter_number;
			      const draftOk = currentNo ? writeWritingDraft(getWritingDraftKey(id, currentNo), contentRef.current) : true;
			      if (draftOk) setDraftRevision((v) => v + 1);
			      if (!draftOk && !draftSaveWarnedRef.current) {
			        draftSaveWarnedRef.current = true;
			        addToast('本地草稿保存失败（浏览器存储不可用或容量不足），请谨慎离开写作台', 'info');
			      }
			      const ok = await confirmDialog({
			        title: '未保存修改',
			        message: draftOk
			          ? '当前章节有未保存修改。\n离开写作台会结束当前编辑（已自动保存本地草稿，可随时恢复）。\n是否继续？'
			          : '当前章节有未保存修改。\n本地草稿保存失败，离开写作台可能丢失未保存内容。\n是否继续？',
			        confirmText: '继续',
			        dialogType: 'warning',
			      });
			      if (!ok) return;
			    }
			    navigate(to);
			  }, [addToast, id, navigate]);

  const handleToggleSidebar = useCallback(() => {
    if (isCompactLayout) {
      setCompactPane((prev) => (prev === 'chapters' ? 'editor' : 'chapters'));
      return;
    }
    setIsSidebarOpen((prev) => {
      const next = !prev;
      if (isCompactLayout && next) setIsAssistantOpen(false);
      return next;
    });
  }, [isCompactLayout, setIsAssistantOpen, setIsSidebarOpen]);

  const handleToggleAssistant = useCallback(() => {
    if (isCompactLayout) {
      setCompactPane((prev) => (prev === 'assistant' ? 'editor' : 'assistant'));
      return;
    }
    setIsAssistantOpen((prev) => {
      const next = !prev;
      if (isCompactLayout && next) setIsSidebarOpen(false);
      return next;
    });
  }, [isCompactLayout, setIsAssistantOpen, setIsSidebarOpen]);

		  const locateInEditor = useCallback((rawText: string) => {
		    const textRaw = String(rawText || '');
		    const text = textRaw.trim();
		    if (!text) return;
		    const hay = contentRef.current || '';
		    if (!hay) {
		      addToast('编辑器内容为空，无法定位', 'info');
		      return;
		    }

		    let idx = hay.indexOf(textRaw);
		    let length = textRaw.length;
		    if (idx < 0) {
		      idx = hay.indexOf(text);
		      length = text.length;
		    }
		    if (idx < 0) {
		      const short = text.slice(0, 120);
		      if (short) {
		        idx = hay.indexOf(short);
		        length = short.length;
		      }
		    }
		    if (idx < 0) {
		      addToast('未能在当前编辑器中定位该片段（可能已被修改/不匹配）', 'info');
		      return;
		    }

		    editorRef.current?.focusAndSelect(idx, idx + length);
		  }, [addToast]);

		  const selectRangeInEditor = useCallback((start: number, end: number) => {
		    editorRef.current?.focusAndSelect(start, end);
		  }, []);

			  const handleExport = async (format: 'txt' | 'markdown') => {
			    if (!id) return;
			    try {
			      const response = await novelsApi.exportNovel(id, format);
			      const blob = new Blob([response.data]);
			      const titleRaw = String(projectInfo?.title || 'novel').trim() || 'novel';
			      const title = sanitizeFilenamePart(titleRaw) || 'novel';
			      const ext = format === 'markdown' ? 'md' : 'txt';
            downloadBlob(blob, `${title}.${ext}`);
			      addToast('导出成功', 'success');
			    } catch (e) {
			      console.error(e);
			      addToast('导出失败', 'error');
			    }
			  };

	      const openImportChapterModal = useCallback(() => {
	        setIsImportChapterModalOpen(true);
	      }, []);

		  const loadProjectData = useCallback(async () => {
		    if (!id) return;
		    try {
		      const project = await writerApi.getProject(id);
	      const projectStatus = String(project?.status || '').trim().toLowerCase();
	      setProjectStatusRaw(projectStatus);
	      if (projectStatus === 'draft' || projectStatus === 'inspiration') {
	        navigate(`/inspiration/${id}`, { replace: true });
	        return;
	      }
      const blueprint = project?.blueprint;
      if (!blueprint || typeof blueprint !== 'object') {
        navigate(`/inspiration/${id}`, { replace: true });
        return;
      }

      clearBlueprintGenerationPending('novel', id);

	      const outlines = Array.isArray((blueprint as any)?.chapter_outline) ? (blueprint as any).chapter_outline : [];
	      const outlineMap = new Map<number, any>();
	      outlines.forEach((o: any) => outlineMap.set(Number(o.chapter_number), o));
	      setChapterOutlineNumbers(
	        Array.from(outlineMap.keys())
	          .filter((n) => Number.isFinite(n) && n > 0)
	          .sort((a, b) => a - b),
	      );
	      const needsPart = Boolean((blueprint as any)?.needs_part_outlines);
	      const partOutlines = Array.isArray((blueprint as any)?.part_outlines) ? (blueprint as any).part_outlines : [];
	      const partCount = partOutlines.length;
	      const coverMaxRaw = partCount > 0
	        ? Math.max(...partOutlines.map((po: any) => Number(po?.end_chapter) || 0))
	        : 0;
	      const coverMax = Number.isFinite(coverMaxRaw) && coverMaxRaw > 0 ? coverMaxRaw : null;
	      setNeedsPartOutlines(needsPart);
	      setPartOutlineCount(partCount);
	      setPartOutlineCoverMax(coverMax);

      const chaptersFromDb = Array.isArray(project.chapters) ? project.chapters : [];
      const chapterMap = new Map<number, Chapter>();
      chaptersFromDb.forEach((c: Chapter) => chapterMap.set(Number(c.chapter_number), c));

      const allNumbers = new Set<number>();
      for (const n of outlineMap.keys()) allNumbers.add(n);
      for (const n of chapterMap.keys()) allNumbers.add(n);

	      const merged: Chapter[] = Array.from(allNumbers)
	        .filter((n) => Number.isFinite(n) && n > 0)
	        .sort((a, b) => a - b)
	        .map((n) => {
	          const existing = chapterMap.get(n);
          if (existing) return existing;
          const o = outlineMap.get(n);
          return {
            chapter_number: n,
            title: String(o?.title || `第${n}章`),
            summary: String(o?.summary || ''),
            generation_status: 'not_generated',
            word_count: 0,
            selected_version: null,
            selected_version_id: null,
            versions: null,
            content: null,
            real_summary: null,
            evaluation: null,
            analysis_data: null,
          };
        });

	      setChapters(merged);

	      setProjectInfo({
	        title: project.title,
	        summary: (blueprint as any)?.one_sentence_summary || "暂无概要",
		        style: (blueprint as any)?.style || "自由创作"
	      });

	        writeBootstrapCache<WritingDeskBootstrapSnapshot>(getWritingDeskBootstrapKey(id), {
	          chapters: merged,
	          projectInfo: {
	            title: project.title,
	            summary: project.blueprint?.one_sentence_summary || '暂无概要',
	            style: project.blueprint?.style || '自由创作',
	          },
	          projectStatus,
	          outlineChapterNumbers: Array.from(outlineMap.keys())
	            .filter((n) => Number.isFinite(n) && n > 0)
	            .sort((a, b) => a - b),
	          needsPartOutlines: needsPart,
	          partOutlineCount: partCount,
	          partOutlineCoverMax: coverMax,
	          selectedChapterNumber: Number(currentChapterRef.current?.chapter_number || 0) || null,
	        });
		    } catch (e) {
		      console.error(e);
		    }
		  }, [id, navigate]);

  useEffect(() => {
    if (!id) return;
    if (!Array.isArray(chapters) || chapters.length === 0) return;
    if (!projectInfo || typeof projectInfo !== 'object') return;

	    writeBootstrapCache<WritingDeskBootstrapSnapshot>(getWritingDeskBootstrapKey(id), {
	      chapters,
	      projectInfo,
	      projectStatus: projectStatusRaw,
	      outlineChapterNumbers: chapterOutlineNumbers,
	      needsPartOutlines,
	      partOutlineCount,
	      partOutlineCoverMax,
	      selectedChapterNumber: Number(currentChapter?.chapter_number || 0) || null,
	    });
	  }, [chapterOutlineNumbers, chapters, currentChapter?.chapter_number, id, needsPartOutlines, partOutlineCount, partOutlineCoverMax, projectInfo, projectStatusRaw]);

	  useEffect(() => {
	    if (!id) return;
	    loadProjectData();
	  }, [id, loadProjectData]);

	  const chapterFromUrlParam = searchParams.get('chapter') || '';
	  useEffect(() => {
	    if (!id) return;
	    if (!chapters || chapters.length === 0) return;
	    const raw = chapterFromUrlParam.trim();
	    const chapterFromUrl = raw ? Number(raw) : null;
	    const currentNo = currentChapterRef.current?.chapter_number;

	    const selectFirst = async () => {
	      await handleSelectChapter(chapters[0].chapter_number, { skipConfirm: true });
	    };

	    const selectFromUrl = async () => {
	      if (!chapterFromUrl || !Number.isFinite(chapterFromUrl) || chapterFromUrl <= 0) return false;
	      if (selectingChapterRef.current === chapterFromUrl) return true;
	      if (Number(currentNo) === Number(chapterFromUrl)) return true;
	      const ok = await handleSelectChapter(chapterFromUrl, { skipConfirm: true, updateUrl: false });
	      if (!ok) await selectFirst();
	      return ok;
	    };

	    if (raw) {
	      selectFromUrl();
	      return;
	    }
		    if (!currentNo) selectFirst();
		  }, [chapterFromUrlParam, chapters, handleSelectChapter, id]);

		  const outlineGenerationGate = useMemo(() => {
		    const statusText = String(projectStatusRaw || '').trim();
		    if (!statusText) {
		      return { canGenerate: false, reason: '正在加载项目状态…' };
		    }

		    if (isGenerating) {
		      return { canGenerate: false, reason: '正文生成中，暂不支持生成章节大纲。' };
		    }

		    const stage = resolveWorkflowStage(statusText);
		    const caps = getNovelCapabilities(stage);
		    if (!caps.canGenerateChapterOutlines) {
		      const statusLabel = getWorkflowStatusLabel(statusText);
		      return {
		        canGenerate: false,
		        reason:
		          `当前进度为「${statusLabel}」，暂不支持生成章节大纲。\n` +
		          '请先在项目详情（Story Control）完成上一步。',
		      };
		    }

		    if (needsPartOutlines && partOutlineCount <= 0) {
		      return {
		        canGenerate: false,
		        reason:
		          '该项目需要先生成分部大纲，才能生成章节大纲。\n' +
		          '请在项目详情（Story Control）点击「生成分部大纲」。',
		      };
		    }

		    if (needsPartOutlines && partOutlineCoverMax && latestOutlineChapterNumber >= partOutlineCoverMax) {
		      return {
		        canGenerate: false,
		        reason:
		          `当前分部大纲只覆盖到第${partOutlineCoverMax}章，无法继续生成后续章节大纲。\n` +
		          '请先生成下一部分分部大纲。',
		      };
		    }

		    return { canGenerate: true, reason: null as string | null };
		  }, [isGenerating, latestOutlineChapterNumber, needsPartOutlines, partOutlineCount, partOutlineCoverMax, projectStatusRaw]);

		  type BatchModalPreset = { count: number; startFrom: number | '' };
		  const canGenerateOutlines = outlineGenerationGate.canGenerate;
		  const outlineDisabledReason = outlineGenerationGate.reason;

		  const openBatchGenerateModal = useCallback((preset: BatchModalPreset) => {
		    if (!id) return;
		    if (!canGenerateOutlines) {
		      addToast(outlineDisabledReason || '当前不满足生成章节大纲条件，请先完成上一步。', 'info');
		      return;
		    }

		    const nextCount = Math.max(1, Math.min(100, Math.floor(Number(preset.count) || 1)));
		    const nextStartFrom =
		      preset.startFrom === ''
		        ? ''
		        : Math.max(1, Math.floor(Number(preset.startFrom) || 1));
		    setBatchModalPreset({ count: nextCount, startFrom: nextStartFrom });
		    setIsBatchModalOpen(true);
		  }, [addToast, canGenerateOutlines, id, outlineDisabledReason]);

		  const handleOpenBatchGenerate = useCallback(() => {
		    openBatchGenerateModal({ count: 10, startFrom: '' });
		  }, [openBatchGenerateModal]);

		  // “新增章节”在 Web 写作台里更安全的语义：生成下一章的章节大纲（避免绕过工作流）
		  const handleCreateChapter = useCallback(() => {
		    openBatchGenerateModal({ count: 1, startFrom: '' });
		  }, [openBatchGenerateModal]);

		  const handleSave = async () => {
		    if (!id || !currentChapter) return;
		    setIsSaving(true);
	    try {
	      await writerApi.updateChapter(id, currentChapter.chapter_number, content);
	      await handleSelectChapter(currentChapter.chapter_number, { skipConfirm: true });
	      removeWritingDraft(getWritingDraftKey(id, currentChapter.chapter_number));
	      setDraftRevision((v) => v + 1);
	      addToast('保存成功', 'success');
	    } catch (e) {
	      console.error("Save failed", e);
	      addToast('保存失败', 'error');
	    } finally {
	      setIsSaving(false);
	    }
	  };

		  const { connect, disconnect } = useSSE((event, data) => {
	    if (event === 'progress') {
	      setGenProgress({
	        stage: data?.stage,
	        message: data?.message,
	        current: typeof data?.current === 'number' ? data.current : undefined,
	        total: typeof data?.total === 'number' ? data.total : undefined,
	      });
	      return;
	    }
	    if (event === 'cancelled') {
	      setIsGenerating(false);
	      setGenProgress(null);
	      addToast('生成已取消', 'info');
        const chapter = currentChapterRef.current;
        const dirty = isDirtyRef.current;
        if (id && chapter) {
          handleSelectChapter(chapter.chapter_number, { skipConfirm: true, preserveLocalContent: dirty, updateUrl: false });
        }
	      return;
	    }
		    if (event === 'complete') {
		      setIsGenerating(false);
		      setGenProgress(null);
		      addToast('生成完成', 'success');
	      const chapter = currentChapterRef.current;
	      const dirty = isDirtyRef.current;
	      if (id && chapter) {
	        handleSelectChapter(chapter.chapter_number, { skipConfirm: true, preserveLocalContent: dirty, updateUrl: false });
	        if (dirty) addToast('已更新版本列表；因未保存修改，未覆盖当前编辑内容', 'info');
	      }
	      return;
		    }
	    if (event === 'error') {
	      setIsGenerating(false);
	      setGenProgress(null);
	      addToast(data?.message || '生成失败', 'error');
        const chapter = currentChapterRef.current;
        const dirty = isDirtyRef.current;
        if (id && chapter) {
          handleSelectChapter(chapter.chapter_number, { skipConfirm: true, preserveLocalContent: dirty, updateUrl: false });
        }
	    }
	  });

	  const generateGate = useMemo(() => {
	    if (!currentChapter) {
	      return { canGenerate: false, reason: null as string | null };
	    }

	    const statusText = String(projectStatusRaw || '').trim();
	    if (!statusText) {
	      return { canGenerate: false, reason: '正在加载项目状态…' };
	    }

	    const stage = resolveWorkflowStage(statusText);
	    const caps = getNovelCapabilities(stage);
	    if (!caps.canGenerateChapterContent) {
	      const statusLabel = getWorkflowStatusLabel(statusText);
	      return {
	        canGenerate: false,
	        reason: `当前进度为「${statusLabel}」，暂不支持生成正文。请先在项目详情（Story Control）生成章节大纲后再继续。`,
	      };
	    }

	    const chapterNo = Number(currentChapter.chapter_number || 0);
	    if (!Number.isFinite(chapterNo) || chapterNo <= 0) {
	      return { canGenerate: false, reason: '章节编号异常，无法生成。' };
	    }

	    if (!chapterOutlineNumberSet.has(chapterNo)) {
	      return { canGenerate: false, reason: `第${chapterNo}章缺少章节大纲，请先生成/补全该章大纲。` };
	    }

	    if (chapterNo > 1) {
	      const prev = (Array.isArray(chapters) ? chapters : []).find(
	        (c) => Number(c.chapter_number) === chapterNo - 1,
	      );
	      const prevHasSelectedVersion = Boolean(prev?.selected_version_id);
	      const prevLooksNonEmpty =
	        String(prev?.generation_status || '').toLowerCase() === 'successful' ||
	        String(prev?.generation_status || '').toLowerCase() === 'completed' ||
	        (Number(prev?.word_count || 0) > 0);
	      if (!prevHasSelectedVersion) {
	        return {
	          canGenerate: false,
	          reason: `请先完成第${chapterNo - 1}章的生成并选择一个版本后，再生成第${chapterNo}章`,
	        };
	      }
	      if (!prevLooksNonEmpty) {
	        return {
	          canGenerate: false,
	          reason: `第${chapterNo - 1}章尚无正文内容，请先生成正文后再生成第${chapterNo}章`,
	        };
	      }
	    }

	    return { canGenerate: true, reason: null };
	  }, [chapterOutlineNumberSet, chapters, currentChapter, projectStatusRaw]);

		  const handleGenerate = async () => {
		    if (!id || !currentChapter) return;
	    if (isSaving) {
	      addToast('正在保存，请稍候…', 'info');
	      return;
	    }
		    if (!generateGate.canGenerate) {
		      addToast(generateGate.reason || '当前不满足生成条件，请先完成上一步。', 'info');
		      return;
		    }
		    if (isDirty) {
		      const draftOk = writeWritingDraft(getWritingDraftKey(id, currentChapter.chapter_number), contentRef.current);
		      if (draftOk) setDraftRevision((v) => v + 1);
		      if (!draftOk && !draftSaveWarnedRef.current) {
		        draftSaveWarnedRef.current = true;
		        addToast('本地草稿保存失败（浏览器存储不可用或容量不足），请尽快点击“保存”', 'info');
		      }
		      const ok = await confirmDialog({
		        title: '未保存修改',
		        message: '检测到未保存修改。\n\n请选择：\n- 先保存再生成（推荐）\n- 直接生成（不包含未保存修改）',
		        confirmText: '先保存再生成',
		        cancelText: '直接生成',
		        dialogType: 'warning',
		      });
		      if (ok) {
		        await handleSave();
		      } else {
		        addToast('将基于已保存内容生成（未保存修改不会参与）', 'info');
		      }
			    }
		    setIsGenerating(true);
		    setGenProgress({ stage: 'initializing', message: '初始化…' });
        // 让左侧列表立即显示“生成中”状态（对齐桌面端体验）
        setChapters((prev) =>
          (Array.isArray(prev) ? prev : []).map((c) =>
            Number(c.chapter_number) === Number(currentChapter.chapter_number)
              ? { ...c, generation_status: 'generating' }
              : c
          )
        );
        setCurrentChapter((prev) => {
          if (!prev) return prev;
          if (Number(prev.chapter_number) !== Number(currentChapter.chapter_number)) return prev;
          return { ...prev, generation_status: 'generating' };
        });
			    await connect(`/writer/novels/${id}/chapters/generate-stream`, {
			        chapter_number: currentChapter.chapter_number,
			        writing_notes: writingNotes?.trim() || undefined,
			    });
			  };

        // 对齐桌面端：章节页头提供“预览提示词”（用于测试 RAG 与上下文构建）
        const openPromptPreviewModal = useCallback(() => {
          if (!id) return;
          if (!currentChapter) {
            addToast('请先选择章节', 'info');
            return;
          }
          setPromptPreviewNotes((prev) => {
            const v = String(prev || '').trim();
            if (v) return prev;
            return writingNotes || '';
          });
          setIsPromptPreviewModalOpen(true);
        }, [addToast, currentChapter, id, writingNotes]);

        const openWritingNotesModal = useCallback(() => {
          if (!id) return;
          setWritingNotesDraft(writingNotes || '');
          setIsWritingNotesModalOpen(true);
        }, [id, writingNotes]);

  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  const handleStopGenerating = useCallback(() => {
    disconnect();
    setIsGenerating(false);
    setGenProgress(null);
    addToast('已停止生成', 'info');

    const chapter = currentChapterRef.current;
    if (id && chapter) {
      void handleSelectChapter(chapter.chapter_number, {
        skipConfirm: true,
        preserveLocalContent: isDirtyRef.current,
        updateUrl: false,
      });
    }
  }, [addToast, disconnect, handleSelectChapter, id]);

	  const handleVersionSelect = async (index: number) => {
	    if (!id || !currentChapter) return;
	    if (isGenerating) {
	      addToast('生成中，暂不支持切换版本', 'info');
	      return;
	    }
		    if (isDirty) {
		      const ok = await confirmDialog({
		        title: '切换版本',
		        message: '当前章节有未保存修改，切换版本会丢失本地改动。\n是否继续？',
		        confirmText: '继续切换',
		        dialogType: 'warning',
		      });
		      if (!ok) return;
		    }
	    const versions = Array.isArray(currentChapter.versions) ? currentChapter.versions : [];
	    const versionContent = versions[index];
	    if (!versionContent) return;

	    try {
	      await writerApi.selectVersion(id, currentChapter.chapter_number, index);
	      // 重新拉取，确保 selected_version / content / 版本列表同步
	      await handleSelectChapter(currentChapter.chapter_number, { skipConfirm: true });
	    } catch (e) {
	      console.error(e);
	      addToast('切换版本失败', 'error');
	    }
	  };

		  // Chapter Actions
		  const handleEditOutline = (chapter: Chapter) => {
		    setEditingChapter(chapter);
		    setIsOutlineModalOpen(true);
		  };

    const handleRegenerateOutline = async (chapter: Chapter) => {
      if (!id) return;
      if (isGeneratingRef.current) {
        addToast('生成中，建议先点击右上角“停止”再重生成大纲', 'info');
        return;
      }

      // 未保存修改：先写入本地草稿，降低误操作丢稿风险
	      if (isDirtyRef.current) {
	        const currentNo = currentChapterRef.current?.chapter_number;
	        const draftOk = currentNo ? writeWritingDraft(getWritingDraftKey(id, currentNo), contentRef.current) : true;
	        if (draftOk) setDraftRevision((v) => v + 1);
	        if (!draftOk && !draftSaveWarnedRef.current) {
	          draftSaveWarnedRef.current = true;
	          addToast('本地草稿保存失败（浏览器存储不可用或容量不足），请谨慎执行级联删除类操作', 'info');
	        }
	        const ok = await confirmDialog({
	          title: '未保存修改',
	          message: draftOk
	            ? '当前章节有未保存修改。\n继续“重生成大纲”可能导致后续数据变化（甚至级联删除）。\n已自动保存本地草稿（可随时恢复）。\n是否继续？'
	            : '当前章节有未保存修改。\n本地草稿保存失败，继续“重生成大纲”可能丢失未保存内容。\n是否继续？',
	          confirmText: '继续',
	          dialogType: 'warning',
	        });
	        if (!ok) return;
	      }

      const maxChapter = chapters.length
        ? Math.max(...chapters.map((c) => Number(c.chapter_number) || 0))
        : chapter.chapter_number;
      const isLast = Number(chapter.chapter_number) === Number(maxChapter);

	      let cascadeDelete = false;
	      if (!isLast && maxChapter > chapter.chapter_number) {
	        const ok = await confirmDialog({
	          title: '串行生成原则',
	          message:
	            `串行生成原则：只能直接重生成最后一章（当前最后一章为第${maxChapter}章）。\n\n` +
	            `若要重生成第${chapter.chapter_number}章，必须级联删除第${chapter.chapter_number + 1}-${maxChapter}章的大纲/章节内容/向量数据。\n\n是否继续？`,
	          confirmText: '继续',
	          dialogType: 'danger',
	        });
	        if (!ok) return;
	        cascadeDelete = true;
	      }

      openOptionalPromptModal({
        title: `重生成大纲 - 第${chapter.chapter_number}章`,
        hint: cascadeDelete
          ? '提示：已启用级联删除，确认后会清空后续章节的大纲/内容/向量数据。可在下方输入“可选优化提示词”。'
          : '可在下方输入“可选优化提示词”（留空则按默认策略重生成）。',
        onConfirm: async (promptText?: string) => {
          try {
            const result = await writerApi.regenerateChapterOutline(id, chapter.chapter_number, {
              prompt: promptText,
              cascadeDelete,
            });
            addToast(result?.message || '已提交重生成任务', 'success');
            if (result?.cascade_deleted?.message) addToast(String(result.cascade_deleted.message), 'info');

            await loadProjectData();

            const currentNo = currentChapterRef.current?.chapter_number;
            const dirty = isDirtyRef.current;
            // 如果当前章被级联删除（当前章号在目标章之后），切回目标章
            if (cascadeDelete && currentNo && currentNo > chapter.chapter_number) {
              await handleSelectChapter(chapter.chapter_number, { skipConfirm: true });
              if (dirty) addToast('已切回目标章节；当前未保存内容已保留为本地草稿', 'info');
              return;
            }

            // 若当前正在查看该章，刷新以更新大纲/版本列表（可选保留未保存正文）
            if (Number(currentNo) === Number(chapter.chapter_number)) {
              await handleSelectChapter(chapter.chapter_number, {
                skipConfirm: true,
                preserveLocalContent: dirty,
                updateUrl: false,
              });
              if (dirty) addToast('已更新大纲/版本列表；因未保存修改，未覆盖当前编辑内容', 'info');
            }
          } catch (e) {
            console.error(e);
            addToast('重生成失败', 'error');
          }
        },
      });
    };

			  const handleResetChapter = async (chapter: Chapter) => {
			    if (!id) return;
			    const ok = await confirmDialog({
			      title: '清空章节内容',
			      message: `确定要清空第 ${chapter.chapter_number} 章的内容吗？\n这将删除所有已生成的版本。`,
			      confirmText: '清空',
			      dialogType: 'danger',
			    });
			    if (!ok) return;
			    try {
	          await writerApi.resetChapter(id, chapter.chapter_number);
	          addToast('章节已重置', 'success');
	          const wasCurrent = currentChapter?.chapter_number === chapter.chapter_number;
	          await loadProjectData();
	          if (wasCurrent) {
	              await handleSelectChapter(chapter.chapter_number, { skipConfirm: true });
	          }
	      } catch (e) {
	          addToast('操作失败', 'error');
	      }
	  };

	  const handleDeleteChapter = async (chapter: Chapter) => {
		    if (!id) return;
		    const ok = await confirmDialog({
		      title: '删除章节',
		      message: `确定要删除第 ${chapter.chapter_number} 章吗？\n此操作不可恢复。`,
		      confirmText: '删除',
		      dialogType: 'danger',
		    });
		    if (!ok) return;
		    try {
		        await writerApi.deleteChapters(id, [chapter.chapter_number]);
		        addToast('章节已删除', 'success');
		        const wasCurrent = currentChapter?.chapter_number === chapter.chapter_number;
		        if (wasCurrent) {
		          setCurrentChapter(null);
		          setContent('');
		          setLoadedContent('');
		        }
		        await loadProjectData();
		    } catch (e) {
		        addToast('删除失败', 'error');
		    }
		  };

	  useEffect(() => {
	    const onBeforeUnload = (e: BeforeUnloadEvent) => {
	      if (!isDirty) return;
	      e.preventDefault();
	      e.returnValue = '';
	    };
	    window.addEventListener('beforeunload', onBeforeUnload);
	    return () => window.removeEventListener('beforeunload', onBeforeUnload);
		  }, [isDirty]);

  const handleSidebarSelectChapter = useCallback(async (chapterNumber: number) => {
    const ok = await handleSelectChapter(chapterNumber);
    if (ok && isCompactLayout) {
      setCompactPane('editor');
    }
  }, [handleSelectChapter, isCompactLayout]);

  const sidebarVisible = isCompactLayout ? compactPane === 'chapters' : isSidebarOpen;
  const assistantVisible = isCompactLayout ? compactPane === 'assistant' : isAssistantOpen;
  const compactPaneItems = [
    {
      id: 'chapters',
      label: '章节导航',
      hint: '锁定章节、创建章节、编辑大纲和批量生成。',
    },
    {
      id: 'editor',
      label: '编辑区',
      hint: '正文、版本切换和空态操作都收束在主工作区。',
    },
    {
      id: 'assistant',
      label: '写作助手',
      hint: 'RAG 检索和正文优化切到独立切面，不再用抽屉覆盖正文。',
    },
  ] as const;

	  const editorWorkspace = currentChapter ? (
	    <WorkspaceTabs
	      ref={editorRef}
	      projectId={id!}
	      chapter={currentChapter}
	      content={content}
	      selectedVersionIndex={
	        isDirty ? null : (typeof currentChapter?.selected_version === 'number' ? currentChapter.selected_version : null)
	      }
		      versions={workspaceVersions}
		      isSaving={isSaving}
		      isGenerating={isGenerating}
		      genProgress={genProgress}
		      canGenerate={generateGate.canGenerate}
		      generateDisabledReason={generateGate.reason}
		      onChange={setContent}
		      onSave={handleSave}
		      onGenerate={handleGenerate}
		      onStopGenerating={handleStopGenerating}
		      onSelectVersion={handleVersionSelect}
	    />
	  ) : (
    <div className="flex h-full w-full items-center justify-center p-6 sm:p-8">
      <div className="w-full max-w-2xl rounded-2xl border border-book-border/55 bg-book-bg-paper/78 p-6 shadow-surface-strong sm:p-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">写作台</div>
            <h2 className="mt-3 font-serif text-[clamp(1.8rem,3vw,2.6rem)] font-bold leading-[1.02] tracking-[-0.04em] text-book-text-main">
              {chapters.length > 0 ? '选择一个章节，继续推进故事。' : '先创建第一章，让写作台开始运转。'}
            </h2>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-book-text-sub sm:text-base">
              {chapters.length > 0
                ? '在左侧选择章节后，正文/版本/评审都会出现在主工作区。'
                : '当前项目还没有章节。你可以先新增一章，或批量生成章节大纲后再逐章写作。'}
            </p>
          </div>

          <div className="shrink-0 rounded-[18px] border border-book-border/55 bg-book-bg/72 px-4 py-3 text-sm text-book-text-sub shadow-surface">
            <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
              提示
            </div>
            <div className="mt-2 font-semibold text-book-text-main">
              {chapters.length > 0 ? `当前共有 ${chapters.length} 章` : '建议从第一章开始'}
            </div>
            <div className="mt-1 text-book-text-sub">
              章节栏/助手都可以在顶部命令栏一键开关。
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap justify-end gap-2">
          {!sidebarVisible ? (
            <BookButton variant="ghost" onClick={handleToggleSidebar}>
              显示章节栏
            </BookButton>
          ) : null}
          {!assistantVisible && chapters.length > 0 ? (
            <BookButton variant="ghost" onClick={handleToggleAssistant}>
              打开助手
            </BookButton>
          ) : null}
          <BookButton
            variant="ghost"
            onClick={handleOpenBatchGenerate}
            disabled={!canGenerateOutlines}
            title={canGenerateOutlines ? '批量生成章节大纲' : (outlineDisabledReason || '当前不满足生成章节大纲条件')}
          >
            批量生成大纲
          </BookButton>
          <BookButton
            variant="primary"
            onClick={handleCreateChapter}
            disabled={!canGenerateOutlines}
            title={canGenerateOutlines ? '生成下一章的章节大纲' : (outlineDisabledReason || '当前不满足生成章节大纲条件')}
          >
            生成下一章大纲
          </BookButton>
        </div>
      </div>
    </div>
  );

  if (!id) return null;

  return (
    <AppViewportShell>

	      <AppViewportFrame size="wide" className="gap-2 sm:gap-3">
	        <WritingDeskHeader
	          projectTitle={String(projectInfo?.title || '')}
	          currentChapterNumber={currentChapter?.chapter_number ? Number(currentChapter.chapter_number) : null}
	          onBack={() => safeNavigate('/')}
	          isSidebarOpen={sidebarVisible}
	          onToggleSidebar={handleToggleSidebar}
	          onOpenImportChapter={openImportChapterModal}
	          onExportTxt={() => handleExport('txt')}
	          onExportMarkdown={() => handleExport('markdown')}
	          onOpenWritingNotes={openWritingNotesModal}
	          onOpenPromptPreview={openPromptPreviewModal}
	          onOpenProjectDetail={() => safeNavigate(`/novel/${id}`)}
	          isAssistantOpen={assistantVisible}
	          onToggleAssistant={handleToggleAssistant}
	        />

        {isCompactLayout ? (
          <div className="relative overflow-hidden rounded-xl border border-book-border/55 bg-book-bg-paper/95 shadow-surface px-4 py-4">
            <div className="relative z-[1]">
              <SegmentPager
                items={[...compactPaneItems]}
                value={compactPane}
                onChange={(next) => setCompactPane(next as 'chapters' | 'editor' | 'assistant')}
              />
            </div>
          </div>
        ) : null}

        <div className="relative overflow-hidden min-h-0 flex-1 rounded-2xl border border-book-border/55 bg-book-bg-paper/95 shadow-surface-strong">
          <div className="relative z-[1] flex h-full min-h-0">
            {isCompactLayout ? (
              <>
                {compactPane === 'chapters' ? (
                  <div className="min-h-0 flex-1">
	                    <WritingDeskSidebar
	                      projectId={id}
	                      chapters={chapters}
	                      draftRevision={draftRevision}
	                      currentChapterNumber={currentChapter?.chapter_number}
	                      projectInfo={projectInfo}
	                      width={sidebarWidth}
	                      compact
	                      compactMode="pane"
	                      canCreateChapter={canGenerateOutlines}
	                      createChapterDisabledReason={outlineDisabledReason}
	                      canBatchGenerate={canGenerateOutlines}
	                      batchGenerateDisabledReason={outlineDisabledReason}
	                      onClose={() => setCompactPane('editor')}
	                      onResizeMouseDown={startSidebarResizing}
	                      onSelectChapter={handleSidebarSelectChapter}
	                      onCreateChapter={handleCreateChapter}
	                      onEditOutline={handleEditOutline}
	                      onRegenerateOutline={handleRegenerateOutline}
	                      onResetChapter={handleResetChapter}
	                      onDeleteChapter={handleDeleteChapter}
	                      onBatchGenerate={handleOpenBatchGenerate}
	                      onOpenProtagonistProfiles={() => setIsProtagonistModalOpen(true)}
	                    />
	                  </div>
	                ) : null}

                {compactPane === 'editor' ? (
                  <div className="min-w-0 flex-1 bg-book-bg">
                    {editorWorkspace}
                  </div>
                ) : null}

                {compactPane === 'assistant' ? (
                  <div className="min-h-0 flex-1">
                    <WritingDeskAssistant
                      projectId={id}
                      chapterNumber={currentChapter?.chapter_number}
                      content={content}
                      onChangeContent={setContent}
                      onLocateText={locateInEditor}
                      onSelectRange={selectRangeInEditor}
                      onJumpToChapter={async (chapterNo) => {
                        const ok = await handleSelectChapter(chapterNo);
                        if (ok) {
                          setCompactPane('editor');
                        }
                      }}
                      isOpen
                      width={assistantWidth}
                      compact
                      compactMode="pane"
                      onClose={() => setCompactPane('editor')}
                      mountReady={assistantMountReady}
                      onResizeMouseDown={startAssistantResizing}
                    />
                  </div>
                ) : null}
              </>
            ) : (
              <>
                {isSidebarOpen ? (
	                  <WritingDeskSidebar
	                    projectId={id}
	                    chapters={chapters}
	                    draftRevision={draftRevision}
	                    currentChapterNumber={currentChapter?.chapter_number}
	                    projectInfo={projectInfo}
	                    width={sidebarWidth}
	                    compact={false}
	                    canCreateChapter={canGenerateOutlines}
	                    createChapterDisabledReason={outlineDisabledReason}
	                    canBatchGenerate={canGenerateOutlines}
	                    batchGenerateDisabledReason={outlineDisabledReason}
	                    onClose={() => setIsSidebarOpen(false)}
	                    onResizeMouseDown={startSidebarResizing}
	                    onSelectChapter={handleSidebarSelectChapter}
	                    onCreateChapter={handleCreateChapter}
	                    onEditOutline={handleEditOutline}
	                    onRegenerateOutline={handleRegenerateOutline}
	                    onResetChapter={handleResetChapter}
	                    onDeleteChapter={handleDeleteChapter}
	                    onBatchGenerate={handleOpenBatchGenerate}
	                    onOpenProtagonistProfiles={() => setIsProtagonistModalOpen(true)}
	                  />
	                ) : null}

                <div className="min-w-0 flex-1 bg-book-bg">
                  {editorWorkspace}
                </div>

                <WritingDeskAssistant
                  projectId={id}
                  chapterNumber={currentChapter?.chapter_number}
                  content={content}
                  onChangeContent={setContent}
                  onLocateText={locateInEditor}
                  onSelectRange={selectRangeInEditor}
                  onJumpToChapter={async (chapterNo) => {
                    const ok = await handleSelectChapter(chapterNo);
                    if (ok && isCompactLayout) {
                      setCompactPane('editor');
                    }
                  }}
                  isOpen={isAssistantOpen}
                  width={assistantWidth}
                  compact={false}
                  onClose={() => setIsAssistantOpen(false)}
                  mountReady={assistantMountReady}
                  onResizeMouseDown={startAssistantResizing}
                />
              </>
            )}
          </div>
        </div>
      </AppViewportFrame>

      <PromptPreviewModal
        projectId={id}
        chapterNumber={currentChapter?.chapter_number ? Number(currentChapter.chapter_number) : null}
        isOpen={isPromptPreviewModalOpen}
        writingNotes={promptPreviewNotes}
        onChangeWritingNotes={setPromptPreviewNotes}
        onClose={() => setIsPromptPreviewModalOpen(false)}
      />

      {isOutlineModalOpen ? (
        <Suspense fallback={null}>
          <OutlineEditModalLazy
            isOpen={isOutlineModalOpen}
            onClose={() => setIsOutlineModalOpen(false)}
            chapter={editingChapter}
            projectId={id}
            onSuccess={loadProjectData}
          />
        </Suspense>
      ) : null}

	      {isBatchModalOpen ? (
	        <Suspense fallback={null}>
	          <BatchGenerateModalLazy
	            isOpen={isBatchModalOpen}
	            onClose={() => setIsBatchModalOpen(false)}
	            projectId={id}
	            initialCount={batchModalPreset.count}
	            initialStartFrom={batchModalPreset.startFrom}
	            latestOutlineChapterNumber={latestOutlineChapterNumber}
	            needsPartOutlines={needsPartOutlines}
	            partOutlineCount={partOutlineCount}
	            partOutlineMaxCoveredChapter={partOutlineCoverMax}
	            onSuccess={loadProjectData}
	          />
	        </Suspense>
	      ) : null}

      {isProtagonistModalOpen ? (
        <Suspense fallback={null}>
          <ProtagonistProfilesModalLazy
            isOpen={isProtagonistModalOpen}
            onClose={() => setIsProtagonistModalOpen(false)}
            projectId={id}
            currentChapterNumber={currentChapter?.chapter_number}
          />
        </Suspense>
      ) : null}

      <ImportChapterModal
        projectId={id}
        isOpen={isImportChapterModalOpen}
        onClose={() => setIsImportChapterModalOpen(false)}
        suggestedChapterNumber={suggestedImportChapterNumber}
        onImported={async (chapterNo) => {
          await loadProjectData();
          const ok = await handleSelectChapter(chapterNo);
          if (ok && isCompactLayout) {
            setCompactPane('editor');
          }
        }}
      />

      {optionalPromptModal}

      <WritingNotesModal
        isOpen={isWritingNotesModalOpen}
        draft={writingNotesDraft}
        onChangeDraft={setWritingNotesDraft}
        onClose={() => setIsWritingNotesModalOpen(false)}
        onCommit={(next) => setWritingNotes(next || '')}
      />
    </AppViewportShell>
  );
};
