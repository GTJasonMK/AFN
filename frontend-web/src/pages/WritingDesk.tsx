import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
	import { ChapterList } from '../components/business/ChapterList';
	import { WorkspaceTabs, type WorkspaceHandle } from '../components/business/WorkspaceTabs';
	import { ChapterPromptPreviewView } from '../components/business/ChapterPromptPreviewView';
	import { AssistantPanel } from '../components/business/AssistantPanel';
	import { OutlineEditModal } from '../components/business/OutlineEditModal';
	import { BatchGenerateModal } from '../components/business/BatchGenerateModal';
	import { ProtagonistProfilesModal } from '../components/business/ProtagonistProfilesModal';
import { writerApi, Chapter } from '../api/writer';
import { novelsApi } from '../api/novels';
import { useSSE } from '../hooks/useSSE';
import { useToast } from '../components/feedback/Toast';
import { confirmDialog } from '../components/feedback/ConfirmDialog';
import { ArrowLeft } from 'lucide-react';
import { BookButton } from '../components/ui/BookButton';
import { BookCard } from '../components/ui/BookCard';
import { Dropdown } from '../components/ui/Dropdown';
import { Modal } from '../components/ui/Modal';
import { BookInput, BookTextarea } from '../components/ui/BookInput';

type LocalDraft = {
  content: string;
  updatedAt: string;
};

const getDraftKey = (projectId: string, chapterNumber: number) => `afn:writing_draft:${projectId}:${chapterNumber}`;
const getAssistantWidthKey = (projectId: string) => `afn:writing_assistant_width:${projectId}`;
const getSidebarWidthKey = (projectId: string) => `afn:writing_sidebar_width:${projectId}`;
const getSidebarOpenKey = (projectId: string) => `afn:writing_sidebar_open:${projectId}`;

const safeReadDraft = (key: string): LocalDraft | null => {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<LocalDraft>;
    if (!parsed || typeof parsed.content !== 'string') return null;
    return {
      content: parsed.content,
      updatedAt: typeof parsed.updatedAt === 'string' ? parsed.updatedAt : new Date().toISOString(),
    };
  } catch {
    return null;
  }
};

const safeWriteDraft = (key: string, content: string): boolean => {
  try {
    const payload: LocalDraft = { content, updatedAt: new Date().toISOString() };
    localStorage.setItem(key, JSON.stringify(payload));
    return true;
  } catch {
    // localStorage 可能被禁用或容量不足；忽略即可（仍可用“保存”走后端）
    return false;
  }
};

const safeRemoveDraft = (key: string) => {
  try {
    localStorage.removeItem(key);
  } catch {
    // ignore
  }
};

const sanitizeFilenamePart = (raw: string) => {
  // Windows 不允许的文件名字符：<>:"/\|?* + 控制字符
  return String(raw || '')
    .replace(/[<>:"/\\|?*\u0000-\u001F]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
};

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
			  const [sidebarWidth, setSidebarWidth] = useState<number>(() => {
			    if (!id) return 256;
			    try {
			      const raw = localStorage.getItem(getSidebarWidthKey(id));
			      const n = raw ? Number(raw) : 256;
			      if (!Number.isFinite(n)) return 256;
			      return Math.max(220, Math.min(420, Math.round(n)));
			    } catch {
			      return 256;
			    }
			  });
			  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
			    if (!id) return true;
			    try {
			      const raw = localStorage.getItem(getSidebarOpenKey(id));
			      if (raw === null) return true;
			      return raw !== '0';
			    } catch {
			      return true;
			    }
			  });
			  const [assistantWidth, setAssistantWidth] = useState<number>(() => {
			    if (!id) return 384;
			    try {
			      const raw = localStorage.getItem(getAssistantWidthKey(id));
			      const n = raw ? Number(raw) : 384;
		      if (!Number.isFinite(n)) return 384;
		      return Math.max(280, Math.min(720, Math.round(n)));
		    } catch {
		      return 384;
		    }
		  });
			  const [isAssistantOpen, setIsAssistantOpen] = useState(() => {
		    if (!id) return true;
		    try {
		      const raw = localStorage.getItem(`afn:writing_assistant_open:${id}`);
		      if (raw === null) return true;
		      return raw !== '0';
		    } catch {
		      return true;
		    }
		  });
				  const [isSaving, setIsSaving] = useState(false);
				  const [isGenerating, setIsGenerating] = useState(false);
				  const [isRagIngesting, setIsRagIngesting] = useState(false);
				  const [projectInfo, setProjectInfo] = useState<any>(null);
				  const [writingNotes, setWritingNotes] = useState(() => {
				    if (!id) return '';
				    try {
				      return localStorage.getItem(`afn:writing_notes:${id}`) || '';
				    } catch {
			      return '';
			    }
			  });
			  const [isWritingNotesModalOpen, setIsWritingNotesModalOpen] = useState(false);
			  const [writingNotesDraft, setWritingNotesDraft] = useState('');
			  const [isPromptPreviewModalOpen, setIsPromptPreviewModalOpen] = useState(false);
			  const [promptPreviewNotes, setPromptPreviewNotes] = useState('');
			  const [isProtagonistModalOpen, setIsProtagonistModalOpen] = useState(false);
			  const [isImportChapterModalOpen, setIsImportChapterModalOpen] = useState(false);
		  const [importChapterNumber, setImportChapterNumber] = useState<number>(1);
		  const [importChapterTitle, setImportChapterTitle] = useState('');
		  const [importChapterContent, setImportChapterContent] = useState('');
		  const [importEncoding, setImportEncoding] = useState<'utf-8' | 'gb18030'>('utf-8');
		  const [importFileName, setImportFileName] = useState<string>('');
		  const [importFileBuffer, setImportFileBuffer] = useState<ArrayBuffer | null>(null);
		  const [importingChapter, setImportingChapter] = useState(false);
		  const [genProgress, setGenProgress] = useState<{ stage?: string; message?: string; current?: number; total?: number } | null>(null);
			  const isDirty = useMemo(() => content !== loadedContent, [content, loadedContent]);
			  const contentChars = useMemo(() => (content || '').replace(/\s/g, '').length, [content]);
		  const editorRef = useRef<WorkspaceHandle | null>(null);
		  const currentChapterRef = useRef<Chapter | null>(null);
		  const contentRef = useRef('');
		  const isDirtyRef = useRef(false);
		  const isGeneratingRef = useRef(false);
		  const selectingChapterRef = useRef<number | null>(null);
		  const draftPromptedRef = useRef<Set<string>>(new Set());
			  const draftSaveWarnedRef = useRef(false);
		  const sidebarResizingRef = useRef(false);
		  const sidebarResizeRafRef = useRef<number | null>(null);
		  const sidebarResizeStartRef = useRef<{ x: number; w: number } | null>(null);
		  const assistantResizingRef = useRef(false);
		  const assistantResizeRafRef = useRef<number | null>(null);
		  const assistantResizeStartRef = useRef<{ x: number; w: number } | null>(null);
		  const importFileInputRef = useRef<HTMLInputElement | null>(null);

      // 可选提示词弹窗（用于“重生成大纲”等可选优化方向输入）
      const pendingPromptActionRef = useRef<((prompt?: string) => void | Promise<void>) | null>(null);
      const [isOptionalPromptModalOpen, setIsOptionalPromptModalOpen] = useState(false);
      const [optionalPromptTitle, setOptionalPromptTitle] = useState('输入优化提示词（可选）');
	      const [optionalPromptHint, setOptionalPromptHint] = useState<string | null>(null);
	      const [optionalPromptValue, setOptionalPromptValue] = useState('');

			  // 左侧章节栏显示状态：按项目持久化（避免每次进入都要手动开关）
			  useEffect(() => {
			    if (!id) return;
			    try {
			      localStorage.setItem(getSidebarOpenKey(id), isSidebarOpen ? '1' : '0');
			    } catch {
			      // ignore
			    }
			  }, [id, isSidebarOpen]);

			  // 右侧助手面板显示状态：按项目持久化（避免每次进入都要手动开关）
			  useEffect(() => {
			    if (!id) return;
			    try {
		      localStorage.setItem(`afn:writing_assistant_open:${id}`, isAssistantOpen ? '1' : '0');
		    } catch {
		      // ignore
		    }
		  }, [id, isAssistantOpen]);

		  // 右侧助手面板宽度：按项目持久化
		  useEffect(() => {
		    if (!id) return;
		    try {
		      localStorage.setItem(getAssistantWidthKey(id), String(Math.max(280, Math.min(720, Math.round(assistantWidth)))));
		    } catch {
		      // ignore
		    }
		  }, [assistantWidth, id]);

		  // 左侧章节栏宽度：按项目持久化
		  useEffect(() => {
		    if (!id) return;
		    try {
		      localStorage.setItem(getSidebarWidthKey(id), String(Math.max(220, Math.min(420, Math.round(sidebarWidth)))));
		    } catch {
		      // ignore
		    }
		  }, [id, sidebarWidth]);

		  // 写作指导：按项目持久化（避免刷新后丢失）
			  useEffect(() => {
			    if (!id) return;
			    try {
			      localStorage.setItem(`afn:writing_notes:${id}`, writingNotes || '');
			    } catch {
			      // ignore
			    }
			  }, [id, writingNotes]);

        // 导入章节：按编码解码文件内容（避免 Windows TXT 因编码不同出现乱码）
        useEffect(() => {
          if (!importFileBuffer) return;
          try {
            const decoder = new TextDecoder(importEncoding);
            const text = decoder.decode(new Uint8Array(importFileBuffer));
            setImportChapterContent(text);
          } catch (e) {
            console.error(e);
            if (importEncoding !== 'utf-8') {
              addToast('当前浏览器不支持该编码，已回退为 UTF-8', 'info');
              setImportEncoding('utf-8');
            } else {
              addToast('文件解码失败，请尝试重新选择文件或更换编码', 'error');
            }
          }
        }, [addToast, importEncoding, importFileBuffer]);

			  const clampAssistantWidth = useCallback((w: number) => {
			    const minEditor = 420;
			    const min = 280;
			    const sidebar = isSidebarOpen ? sidebarWidth : 0;
			    const maxByLayout = window.innerWidth - sidebar - minEditor - 20;
			    const max = Math.max(min, Math.min(720, Math.floor(maxByLayout)));
			    return Math.max(min, Math.min(max, Math.round(w)));
			  }, [isSidebarOpen, sidebarWidth]);

			  const clampSidebarWidth = useCallback((w: number) => {
			    const minEditor = 420;
			    const min = 220;
			    const hardMax = 420;
			    const assistant = isAssistantOpen ? assistantWidth : 0;
			    const maxByLayout = window.innerWidth - assistant - minEditor - 20;
			    const max = Math.max(min, Math.min(hardMax, Math.floor(maxByLayout)));
			    return Math.max(min, Math.min(max, Math.round(w)));
			  }, [assistantWidth, isAssistantOpen]);

			  // 窗口尺寸 / 面板开关变化时：自动夹紧宽度，保证中间编辑区最小宽度
			  useEffect(() => {
			    const onResize = () => {
			      if (isAssistantOpen) setAssistantWidth((w) => clampAssistantWidth(w));
			      if (isSidebarOpen) setSidebarWidth((w) => clampSidebarWidth(w));
			    };
			    onResize();
			    window.addEventListener('resize', onResize);
			    return () => window.removeEventListener('resize', onResize);
			  }, [clampAssistantWidth, clampSidebarWidth, isAssistantOpen, isSidebarOpen]);

			  const stopSidebarResizing = useCallback(() => {
			    sidebarResizingRef.current = false;
			    sidebarResizeStartRef.current = null;
		    if (sidebarResizeRafRef.current !== null) {
		      window.cancelAnimationFrame(sidebarResizeRafRef.current);
		      sidebarResizeRafRef.current = null;
		    }
		    try {
		      document.body.style.cursor = '';
		      document.body.style.userSelect = '';
		    } catch {
		      // ignore
		    }
		  }, []);

		  const onSidebarResizeMove = useCallback((ev: MouseEvent) => {
		    if (!sidebarResizingRef.current || !sidebarResizeStartRef.current) return;
		    const { x, w } = sidebarResizeStartRef.current;
		    const next = clampSidebarWidth(w + (ev.clientX - x));
		    if (sidebarResizeRafRef.current !== null) window.cancelAnimationFrame(sidebarResizeRafRef.current);
		    sidebarResizeRafRef.current = window.requestAnimationFrame(() => setSidebarWidth(next));
		  }, [clampSidebarWidth]);

		  const onSidebarResizeUp = useCallback(() => {
		    window.removeEventListener('mousemove', onSidebarResizeMove);
		    window.removeEventListener('mouseup', onSidebarResizeUp);
		    stopSidebarResizing();
		  }, [onSidebarResizeMove, stopSidebarResizing]);

		  const startSidebarResizing = useCallback((e: React.MouseEvent) => {
		    e.preventDefault();
		    e.stopPropagation();
		    sidebarResizingRef.current = true;
		    sidebarResizeStartRef.current = { x: e.clientX, w: sidebarWidth };
		    try {
		      document.body.style.cursor = 'col-resize';
		      document.body.style.userSelect = 'none';
		    } catch {
		      // ignore
		    }
		    window.addEventListener('mousemove', onSidebarResizeMove);
		    window.addEventListener('mouseup', onSidebarResizeUp);
		  }, [onSidebarResizeMove, onSidebarResizeUp, sidebarWidth]);

		  const stopAssistantResizing = useCallback(() => {
		    assistantResizingRef.current = false;
		    assistantResizeStartRef.current = null;
		    if (assistantResizeRafRef.current !== null) {
		      window.cancelAnimationFrame(assistantResizeRafRef.current);
		      assistantResizeRafRef.current = null;
		    }
		    try {
		      document.body.style.cursor = '';
		      document.body.style.userSelect = '';
		    } catch {
		      // ignore
		    }
		  }, []);

		  const onAssistantResizeMove = useCallback((ev: MouseEvent) => {
		    if (!assistantResizingRef.current || !assistantResizeStartRef.current) return;
		    const { x, w } = assistantResizeStartRef.current;
		    const next = clampAssistantWidth(w + (x - ev.clientX));
		    if (assistantResizeRafRef.current !== null) window.cancelAnimationFrame(assistantResizeRafRef.current);
		    assistantResizeRafRef.current = window.requestAnimationFrame(() => setAssistantWidth(next));
		  }, [clampAssistantWidth]);

		  const onAssistantResizeUp = useCallback(() => {
		    window.removeEventListener('mousemove', onAssistantResizeMove);
		    window.removeEventListener('mouseup', onAssistantResizeUp);
		    stopAssistantResizing();
		  }, [onAssistantResizeMove, stopAssistantResizing]);

		  const startAssistantResizing = useCallback((e: React.MouseEvent) => {
		    e.preventDefault();
		    e.stopPropagation();
		    assistantResizingRef.current = true;
		    assistantResizeStartRef.current = { x: e.clientX, w: assistantWidth };
		    try {
		      document.body.style.cursor = 'col-resize';
		      document.body.style.userSelect = 'none';
		    } catch {
		      // ignore
		    }
		    window.addEventListener('mousemove', onAssistantResizeMove);
		    window.addEventListener('mouseup', onAssistantResizeUp);
		  }, [assistantWidth, onAssistantResizeMove, onAssistantResizeUp]);

		  useEffect(() => {
		    return () => {
		      window.removeEventListener('mousemove', onSidebarResizeMove);
		      window.removeEventListener('mouseup', onSidebarResizeUp);
		      stopSidebarResizing();
		      window.removeEventListener('mousemove', onAssistantResizeMove);
		      window.removeEventListener('mouseup', onAssistantResizeUp);
		      stopAssistantResizing();
		    };
		  }, [onAssistantResizeMove, onAssistantResizeUp, onSidebarResizeMove, onSidebarResizeUp, stopAssistantResizing, stopSidebarResizing]);

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
			        const draftOk = currentNo ? safeWriteDraft(getDraftKey(id, currentNo), contentRef.current) : true;
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
		        const draftKey = getDraftKey(id, chapterNumber);
		        if (!draftPromptedRef.current.has(draftKey)) {
		          draftPromptedRef.current.add(draftKey);
		          const draft = safeReadDraft(draftKey);
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
		    const key = getDraftKey(id, chapterNo);

		    if (!isDirty) {
		      safeRemoveDraft(key);
		      return;
		    }

		    const t = window.setTimeout(() => {
		      const ok = safeWriteDraft(key, content);
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
			      const draftOk = currentNo ? safeWriteDraft(getDraftKey(id, currentNo), contentRef.current) : true;
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

        const openOptionalPromptModal = useCallback((opts: {
          title?: string;
          hint?: string;
          initialValue?: string;
          onConfirm: (prompt?: string) => void | Promise<void>;
        }) => {
          setOptionalPromptTitle(opts.title || '输入优化提示词（可选）');
          setOptionalPromptHint(opts.hint || null);
          setOptionalPromptValue(opts.initialValue || '');
          pendingPromptActionRef.current = opts.onConfirm;
          setIsOptionalPromptModalOpen(true);
        }, []);

        const confirmOptionalPromptModal = useCallback(async () => {
          const fn = pendingPromptActionRef.current;
          pendingPromptActionRef.current = null;
          setIsOptionalPromptModalOpen(false);

          const text = (optionalPromptValue || '').trim();
          try {
            await fn?.(text ? text : undefined);
          } catch (e) {
            console.error(e);
            addToast('操作失败', 'error');
          }
        }, [addToast, optionalPromptValue]);

		  const handleExport = async (format: 'txt' | 'markdown') => {
		    if (!id) return;
		    try {
		      const response = await novelsApi.exportNovel(id, format);
		      const blob = new Blob([response.data]);
		      const url = window.URL.createObjectURL(blob);
		      const link = document.createElement('a');
		      link.href = url;
		      const title = (projectInfo?.title || 'novel').trim() || 'novel';
		      const ext = format === 'markdown' ? 'md' : 'txt';
		      link.setAttribute('download', `${title}.${ext}`);
		      document.body.appendChild(link);
		      link.click();
		      link.remove();
		      window.URL.revokeObjectURL(url);
		      addToast('导出成功', 'success');
		    } catch (e) {
		      console.error(e);
		      addToast('导出失败', 'error');
		    }
		  };

      const openImportChapterModal = useCallback(() => {
        const nextChapterNum = chapters.length > 0
          ? Math.max(...chapters.map((c) => Number(c.chapter_number) || 0)) + 1
          : 1;
        setImportChapterNumber(Math.max(1, nextChapterNum));
        setImportChapterTitle(`第${Math.max(1, nextChapterNum)}章`);
        setImportChapterContent('');
        setImportFileName('');
        setImportFileBuffer(null);
        setImportEncoding('utf-8');
        setIsImportChapterModalOpen(true);
      }, [chapters]);


      const pickImportFile = useCallback(() => {
        importFileInputRef.current?.click();
      }, []);

      const onImportFileChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0] || null;
        e.target.value = '';
        if (!file) return;

        try {
          const buf = await file.arrayBuffer();
          setImportFileName(file.name);
          setImportFileBuffer(buf);
          const defaultTitle = sanitizeFilenamePart(file.name.replace(/\.[^.]+$/, ''));
          setImportChapterTitle((prev) => (String(prev || '').trim() ? prev : (defaultTitle || prev)));
        } catch (err) {
          console.error(err);
          addToast('读取文件失败', 'error');
        }
      }, [addToast]);

	  const loadProjectData = useCallback(async () => {
	    if (!id) return;
	    try {
	      const project = await writerApi.getProject(id);
      const outlines = Array.isArray(project.blueprint?.chapter_outline) ? project.blueprint.chapter_outline : [];
      const outlineMap = new Map<number, any>();
      outlines.forEach((o: any) => outlineMap.set(Number(o.chapter_number), o));

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
	        summary: project.blueprint?.one_sentence_summary || "暂无概要",
		        style: project.blueprint?.style || "自由创作"
	      });
	    } catch (e) {
	      console.error(e);
	    }
	  }, [id]);

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

	  const handleCreateChapter = async () => {
	    if (!id) return;
	    if (isGenerating) {
	      addToast('生成中，暂不支持新增章节', 'info');
	      return;
	    }
		    if (isDirty) {
		      const currentNo = currentChapterRef.current?.chapter_number;
		      const draftOk = currentNo ? safeWriteDraft(getDraftKey(id, currentNo), contentRef.current) : true;
		      if (draftOk) setDraftRevision((v) => v + 1);
		      if (!draftOk && !draftSaveWarnedRef.current) {
		        draftSaveWarnedRef.current = true;
		        addToast('本地草稿保存失败（浏览器存储不可用或容量不足），请尽快点击“保存”', 'info');
		      }
		      const ok = await confirmDialog({
		        title: '未保存修改',
		        message: draftOk
		          ? '当前章节有未保存修改。\n继续新增章节会离开当前编辑（已自动保存本地草稿，可随时恢复）。\n是否继续？'
		          : '当前章节有未保存修改。\n本地草稿保存失败，继续新增章节可能丢失未保存内容。\n是否继续？',
		        confirmText: '继续',
		        dialogType: 'warning',
		      });
		      if (!ok) return;
		    }
	    const nextChapterNum = chapters.length > 0 
	      ? Math.max(...chapters.map(c => c.chapter_number)) + 1 
	      : 1;
    
    // Optimistic update
    const newChapterStub: Chapter = {
      chapter_number: nextChapterNum,
      title: `第${nextChapterNum}章`,
      summary: '',
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
    
		    setChapters((prev) => [...prev, newChapterStub]);
		    
		    try {
		        await writerApi.createChapter(id, nextChapterNum);
		        await loadProjectData();
		        await handleSelectChapter(nextChapterNum, { skipConfirm: true });
		    } catch (e) {
		        console.error("Failed to create chapter", e);
		        // 回滚 optimistic stub，避免列表残留“空章节”
		        setChapters((prev) => (Array.isArray(prev) ? prev : []).filter((c) => Number(c.chapter_number) !== Number(nextChapterNum)));
		        addToast('创建章节失败', 'error');
		    }
		  };

	  const handleSave = async () => {
	    if (!id || !currentChapter) return;
	    setIsSaving(true);
	    try {
	      await writerApi.updateChapter(id, currentChapter.chapter_number, content);
	      await handleSelectChapter(currentChapter.chapter_number, { skipConfirm: true });
	      safeRemoveDraft(getDraftKey(id, currentChapter.chapter_number));
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

		  const handleGenerate = async () => {
		    if (!id || !currentChapter) return;
	    if (isSaving) {
	      addToast('正在保存，请稍候…', 'info');
	      return;
	    }
		    if (isDirty) {
		      const draftOk = safeWriteDraft(getDraftKey(id, currentChapter.chapter_number), contentRef.current);
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
          if (!id || !currentChapter) return;
          setPromptPreviewNotes((prev) => {
            const v = String(prev || '').trim();
            if (v) return prev;
            return writingNotes || '';
          });
          setIsPromptPreviewModalOpen(true);
        }, [currentChapter, id, writingNotes]);

  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

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

  const handleRagIngest = async () => {
    if (!id || !currentChapter) return;
    setIsRagIngesting(true);
    try {
      await writerApi.updateChapter(id, currentChapter.chapter_number, content, { triggerRag: true });
      addToast('已触发RAG处理（摘要/分析/索引/向量入库）', 'success');
      await handleSelectChapter(currentChapter.chapter_number, { skipConfirm: true });
    } catch (e) {
      console.error(e);
      addToast('RAG处理失败', 'error');
    } finally {
      setIsRagIngesting(false);
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
	        const draftOk = currentNo ? safeWriteDraft(getDraftKey(id, currentNo), contentRef.current) : true;
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

		  if (!id) return null;


		  return (
		    <div className="flex flex-col h-screen bg-book-bg">
		      {/* 简化的顶部导航栏 - 照抄桌面端 header.py */}
		      <div className="h-14 border-b border-book-border bg-book-bg-paper flex items-center px-4 justify-between shrink-0 z-30 shadow-sm">
		        {/* 左侧：返回按钮 */}
		        <button
		          onClick={() => safeNavigate('/')}
	          className="flex items-center justify-center w-9 h-9 rounded-full bg-book-primary text-white hover:opacity-90 transition-opacity"
	          title="返回项目列表"
	        >
	          <ArrowLeft size={18} />
        </button>

        {/* 中间：项目信息 */}
		        <div className="flex-1 min-w-0 mx-4 px-4 py-2 bg-book-bg rounded-lg border border-book-border/50">
		          <div className="font-serif font-bold text-book-text-main text-sm truncate">
		            {projectInfo?.title || '写作台'}
		          </div>
		          <div className="text-[11px] text-book-text-muted truncate">
		            {projectInfo?.style || '自由创作'}
		            {' · '}
		            {chapters.filter(ch => ch.content).length}/{chapters.length}章
		            {contentChars > 0 && ` · ${contentChars}字`}
		          </div>
		        </div>

	        {/* 右侧：操作按钮 */}
	        <div className="flex items-center gap-2">
	          {/* 导入/导出按钮（下拉菜单） */}
	          <Dropdown
	            label="导入/导出"
	            items={[
	              { label: '导入章节', onClick: openImportChapterModal },
	              { label: '导出为 TXT', onClick: () => handleExport('txt') },
	              { label: '导出为 Markdown', onClick: () => handleExport('markdown') },
	            ]}
	          />

	          {/* 项目详情按钮 */}
	          <BookButton
	            variant="primary"
	            size="sm"
	            onClick={() => safeNavigate(`/novel/${id}`)}
	            title="打开项目详情"
	          >
	            项目详情
	          </BookButton>

	          {/* RAG助手切换按钮 */}
	          <BookButton
	            variant={isAssistantOpen ? 'primary' : 'ghost'}
	            size="sm"
	            onClick={() => setIsAssistantOpen((v) => !v)}
	            title={isAssistantOpen ? '隐藏助手面板' : '显示助手面板'}
	          >
	            {isAssistantOpen ? '隐藏助手' : '显示助手'}
	          </BookButton>
	        </div>

          {/* 生成进度（仅在生成时显示） */}
	          {isGenerating && (
	            <div className="flex items-center gap-3 ml-4">
	              <div className="min-w-0 text-right">
	                <div className="text-[11px] text-book-text-muted truncate">
	                  {genProgress?.message || genProgress?.stage || '生成中...'}
                </div>
                {typeof genProgress?.current === 'number' && typeof genProgress?.total === 'number' && genProgress.total > 0 ? (
                  <div className="mt-1 h-1.5 w-32 bg-book-border/30 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-book-primary transition-all duration-300"
                      style={{ width: `${Math.min(100, Math.max(0, (genProgress.current / genProgress.total) * 100))}%` }}
                    />
                  </div>
                ) : (
                  <div className="mt-1 h-1.5 w-32 bg-book-border/30 rounded-full overflow-hidden">
                    <div className="h-full w-1/3 bg-book-primary animate-pulse" />
                  </div>
                )}
              </div>
              <button
                onClick={() => {
                  disconnect();
                  setIsGenerating(false);
                  setGenProgress(null);
                  addToast('已停止生成', 'info');
                }}
                className="text-xs text-book-accent hover:text-book-accent/80 transition-colors font-bold"
                title="停止生成"
              >
                停止
              </button>
            </div>
          )}
        </div>

		      <div className="flex-1 flex overflow-hidden">
		        {isSidebarOpen && (
		          <>
		            <div className="shrink-0 h-full" style={{ width: sidebarWidth }}>
			            <ChapterList 
			              chapters={chapters} 
			              projectId={id}
			              draftRevision={draftRevision}
			              currentChapterNumber={currentChapter?.chapter_number}
			              projectInfo={projectInfo}
			              onSelectChapter={handleSelectChapter}
			              onCreateChapter={handleCreateChapter}
			              onEditOutline={handleEditOutline}
		                onRegenerateOutline={handleRegenerateOutline}
		              onResetChapter={handleResetChapter}
		              onDeleteChapter={handleDeleteChapter}
		              onBatchGenerate={() => setIsBatchModalOpen(true)}
		              onOpenProtagonistProfiles={() => setIsProtagonistModalOpen(true)}
		            />
		            </div>

		            <div
		              className="w-1.5 shrink-0 cursor-col-resize bg-transparent hover:bg-book-primary/20 transition-colors"
		              onMouseDown={startSidebarResizing}
		              title="拖拽调整章节栏宽度"
		            />
		          </>
		        )}

		        <div className="flex-1 min-w-0 bg-book-bg">
		          {currentChapter ? (
				          <WorkspaceTabs
				            ref={editorRef}
				            projectId={id}
				            chapter={currentChapter}
				            content={content}
				            selectedVersionIndex={
				              isDirty ? null : (typeof currentChapter?.selected_version === 'number' ? currentChapter.selected_version : null)
				            }
			            versions={(Array.isArray(currentChapter?.versions) ? currentChapter?.versions : []).map((v, idx) => ({
			              id: `v-${idx}`,
			              chapter_id: `${id}-${currentChapter?.chapter_number || 0}`,
			              version_label: `版本 ${idx + 1}`,
			              content: v,
			              created_at: new Date().toISOString(),
			              provider: 'llm',
			            }))}
		            isSaving={isSaving}
		            isGenerating={isGenerating}
		            onChange={setContent}
		            onSave={handleSave}
		            onGenerate={handleGenerate}
		            onPreviewPrompt={openPromptPreviewModal}
		            onSelectVersion={handleVersionSelect}
		            onIngestRag={handleRagIngest}
		            isIngestingRag={isRagIngesting}
				          />
			          ) : (
		            <div className="h-full w-full flex items-center justify-center p-8">
		              <BookCard className="max-w-xl w-full p-6">
		                <div className="font-serif text-lg font-bold text-book-text-main">未选择章节</div>
		                <div className="mt-3 text-sm text-book-text-muted leading-relaxed">
		                  {chapters.length > 0
		                    ? '请从左侧章节列表选择章节开始写作。'
		                    : '当前项目暂无章节。你可以先创建第一章，或批量生成章节大纲。'}
		                </div>
		                <div className="mt-5 flex justify-end gap-2 flex-wrap">
		                  {!isSidebarOpen && (
		                    <BookButton variant="ghost" onClick={() => setIsSidebarOpen(true)}>
		                      显示章节栏
		                    </BookButton>
		                  )}
		                  <BookButton variant="ghost" onClick={() => setIsBatchModalOpen(true)}>
		                    批量生成大纲
		                  </BookButton>
		                  <BookButton variant="primary" onClick={handleCreateChapter}>
		                    新增章节
		                  </BookButton>
		                </div>
		              </BookCard>
		            </div>
		          )}
		        </div>

			        {isAssistantOpen && (
			          <>
			            <div
			              className="w-1.5 shrink-0 cursor-col-resize bg-transparent hover:bg-book-primary/20 transition-colors"
			              onMouseDown={startAssistantResizing}
			              title="拖拽调整助手面板宽度"
			            />
			            <div className="shrink-0 h-full" style={{ width: assistantWidth }}>
				              <AssistantPanel
				                  projectId={id}
				                  chapterNumber={currentChapter?.chapter_number}
				                  content={content}
				                  onChangeContent={setContent}
			                  onLocateText={locateInEditor}
			                  onSelectRange={selectRangeInEditor}
			                  onJumpToChapter={async (chapterNo) => {
			                    await handleSelectChapter(chapterNo);
			                  }}
			              />
			            </div>
			          </>
			        )}
		      </div>

	      {/* Modals */}
		      <input
		        ref={importFileInputRef}
		        type="file"
		        accept=".txt,.md,text/plain,text/markdown"
		        style={{ display: 'none' }}
		        onChange={onImportFileChange}
		      />

		      <Modal
		        isOpen={isPromptPreviewModalOpen}
		        onClose={() => setIsPromptPreviewModalOpen(false)}
		        title={`第 ${currentChapter?.chapter_number ?? ''} 章 - 提示词预览`}
		        maxWidthClassName="max-w-6xl"
		        className="max-h-[90vh]"
		        footer={
		          <div className="flex justify-end gap-2">
		            <BookButton variant="ghost" onClick={() => setIsPromptPreviewModalOpen(false)}>
		              关闭
		            </BookButton>
		          </div>
		        }
		      >
		        <div className="max-h-[75vh] overflow-auto custom-scrollbar pr-1">
		          {currentChapter ? (
		            <ChapterPromptPreviewView
		              projectId={id}
		              chapterNumber={currentChapter.chapter_number}
		              writingNotes={promptPreviewNotes}
		              onChangeWritingNotes={setPromptPreviewNotes}
		            />
		          ) : (
		            <div className="text-sm text-book-text-muted">请先选择章节</div>
		          )}
		        </div>
		      </Modal>

		      <OutlineEditModal 
		        isOpen={isOutlineModalOpen}
		        onClose={() => setIsOutlineModalOpen(false)}
		        chapter={editingChapter}
	        projectId={id}
        onSuccess={loadProjectData}
      />

	      <BatchGenerateModal
	        isOpen={isBatchModalOpen}
	        onClose={() => setIsBatchModalOpen(false)}
	        projectId={id}
	        onSuccess={loadProjectData}
	      />

		        <ProtagonistProfilesModal
		          isOpen={isProtagonistModalOpen}
		          onClose={() => setIsProtagonistModalOpen(false)}
		          projectId={id}
		          currentChapterNumber={currentChapter?.chapter_number}
		        />

	        <Modal
	          isOpen={isImportChapterModalOpen}
	          onClose={() => {
	            if (importingChapter) return;
	            setIsImportChapterModalOpen(false);
	          }}
	          title="导入章节"
	          maxWidthClassName="max-w-2xl"
	          footer={
	            <div className="flex justify-end gap-2">
	              <BookButton
	                variant="ghost"
	                onClick={() => setIsImportChapterModalOpen(false)}
	                disabled={importingChapter}
	              >
	                取消
	              </BookButton>
	              <BookButton
	                variant="primary"
	                onClick={async () => {
	                  if (!id) return;
	                  const chapterNo = Math.max(1, Number(importChapterNumber) || 1);
	                  const title = (importChapterTitle || '').trim() || `第${chapterNo}章`;
	                  const text = String(importChapterContent || '');

	                  setImportingChapter(true);
	                  try {
	                    await writerApi.importChapter(id, chapterNo, title, text, { timeout: 0 });
	                    addToast('章节已导入', 'success');
	                    setIsImportChapterModalOpen(false);
	                    setImportFileName('');
	                    setImportFileBuffer(null);
	                    await loadProjectData();
	                    await handleSelectChapter(chapterNo);
	                  } catch (e) {
	                    console.error(e);
	                    addToast('导入失败', 'error');
	                  } finally {
	                    setImportingChapter(false);
	                  }
	                }}
	                disabled={importingChapter}
	              >
	                {importingChapter ? '导入中…' : '导入'}
	              </BookButton>
	            </div>
	          }
	        >
	          <div className="space-y-4">
	            <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
	              说明：导入会创建（或更新）指定章节，并生成一个新的版本。支持直接粘贴正文，或选择 TXT/MD 文件自动填充内容。
	            </div>

	            <div className="flex items-end gap-3 flex-wrap">
	              <BookButton variant="secondary" size="sm" onClick={pickImportFile} disabled={importingChapter}>
	                选择文件
	              </BookButton>
	              <div className="text-xs text-book-text-muted">
	                {importFileName ? `已选择：${importFileName}` : '未选择文件（可直接粘贴内容）'}
	              </div>
	              <div className="ml-auto flex items-center gap-2">
	                <span className="text-xs text-book-text-muted">编码</span>
	                <select
	                  value={importEncoding}
	                  onChange={(e) => setImportEncoding(e.target.value === 'gb18030' ? 'gb18030' : 'utf-8')}
	                  disabled={importingChapter}
	                  className="text-xs bg-book-bg-paper border border-book-border/50 rounded-md px-2 py-1 outline-none focus:border-book-primary/50"
	                  title="若文件乱码，请切换为 GB18030"
	                >
	                  <option value="utf-8">UTF-8</option>
	                  <option value="gb18030">GB18030（Win 常见）</option>
	                </select>
	              </div>
	            </div>

	            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
	              <BookInput
	                label="章节号"
	                type="number"
	                min={1}
	                value={importChapterNumber}
	                onChange={(e) => setImportChapterNumber(parseInt(e.target.value, 10) || 1)}
	                disabled={importingChapter}
	              />
	              <BookInput
	                label="章节标题"
	                value={importChapterTitle}
	                onChange={(e) => setImportChapterTitle(e.target.value)}
	                disabled={importingChapter}
	              />
	            </div>

	            <BookTextarea
	              label="章节内容"
	              rows={12}
	              value={importChapterContent}
	              onChange={(e) => setImportChapterContent(e.target.value)}
	              placeholder="可直接粘贴；或选择 TXT/MD 文件自动填充"
	              disabled={importingChapter}
	            />
	          </div>
	        </Modal>

	        <Modal
	          isOpen={isOptionalPromptModalOpen}
	          onClose={() => {
	            pendingPromptActionRef.current = null;
	            setIsOptionalPromptModalOpen(false);
          }}
          title={optionalPromptTitle}
          maxWidthClassName="max-w-2xl"
          footer={
            <div className="flex justify-end gap-2">
              <BookButton
                variant="ghost"
                onClick={() => {
                  pendingPromptActionRef.current = null;
                  setIsOptionalPromptModalOpen(false);
                }}
              >
                取消
              </BookButton>
              <BookButton variant="primary" onClick={confirmOptionalPromptModal}>
                确定
              </BookButton>
            </div>
          }
        >
          <div className="space-y-4">
            {optionalPromptHint ? (
              <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
                {optionalPromptHint}
              </div>
            ) : null}
            <BookTextarea
              label="优化提示词（可选）"
              rows={8}
              value={optionalPromptValue}
              onChange={(e) => setOptionalPromptValue(e.target.value)}
              placeholder="例如：强化冲突、补足动机、压缩节奏、增加悬疑…"
            />
          </div>
        </Modal>

	        <Modal
	          isOpen={isWritingNotesModalOpen}
	          onClose={() => setIsWritingNotesModalOpen(false)}
	          title="写作指导（可选）"
          maxWidthClassName="max-w-2xl"
          footer={
            <div className="flex justify-end gap-2">
              <BookButton variant="ghost" onClick={() => setIsWritingNotesModalOpen(false)}>
                取消
              </BookButton>
	              <BookButton
	                variant="secondary"
	                onClick={async () => {
	                  const ok = await confirmDialog({
	                    title: '清空写作指导',
	                    message: '确定清空写作指导？',
	                    confirmText: '清空',
	                    dialogType: 'warning',
	                  });
	                  if (!ok) return;
	                  setWritingNotesDraft('');
	                }}
	              >
	                清空
	              </BookButton>
              <BookButton
                variant="primary"
                onClick={() => {
                  setWritingNotes(writingNotesDraft || '');
                  setIsWritingNotesModalOpen(false);
                  addToast((writingNotesDraft || '').trim() ? '已更新写作指导' : '已清空写作指导', 'success');
                }}
              >
                保存
              </BookButton>
            </div>
          }
        >
          <div className="space-y-4">
            <BookTextarea
              label="写作指导"
              rows={10}
              value={writingNotesDraft}
              onChange={(e) => setWritingNotesDraft(e.target.value)}
              placeholder="例如：本章重点描写主角内心变化，减少对话，多用动作推动剧情…"
            />
            <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 leading-relaxed">
              提示：写作指导会参与“提示词预览 / AI 续写 / RAG 检索”，用于控制本章写作方向。留空则按大纲与上下文自动生成。
            </div>
          </div>
        </Modal>
		    </div>
		  );
	};
