import React, { lazy, Suspense, useState, useEffect, useCallback, useMemo, useRef, useDeferredValue } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { novelsApi } from '../api/novels';
import { writerApi } from '../api/writer';
import { BookButton } from '../components/ui/BookButton';
import { BookCard } from '../components/ui/BookCard';
import { BookInput, BookTextarea } from '../components/ui/BookInput';
import { Play, Sparkles, RefreshCw, Map as MapIcon, Users, FileText, Share, Plus, Trash2, Download, Link2 } from 'lucide-react';
import { useToast } from '../components/feedback/Toast';
import { confirmDialog } from '../components/feedback/ConfirmDialog';
import { Modal } from '../components/ui/Modal';
import { scheduleIdleTask } from '../utils/scheduleIdleTask';
import { readBootstrapCache, writeBootstrapCache } from '../utils/bootstrapCache';

const OutlineEditModalLazy = lazy(() =>
  import('../components/business/OutlineEditModal').then((m) => ({ default: m.OutlineEditModal }))
);
const BatchGenerateModalLazy = lazy(() =>
  import('../components/business/BatchGenerateModal').then((m) => ({ default: m.BatchGenerateModal }))
);
const CharacterPortraitGalleryLazy = lazy(() =>
  import('../components/business/CharacterPortraitGallery').then((m) => ({ default: m.CharacterPortraitGallery }))
);
const ProtagonistProfilesModalLazy = lazy(() =>
  import('../components/business/ProtagonistProfilesModal').then((m) => ({ default: m.ProtagonistProfilesModal }))
);
const PartOutlineGenerateModalLazy = lazy(() =>
  import('../components/business/PartOutlineGenerateModal').then((m) => ({ default: m.PartOutlineGenerateModal }))
);
const PartOutlineDetailModalLazy = lazy(() =>
  import('../components/business/PartOutlineDetailModal').then((m) => ({ default: m.PartOutlineDetailModal }))
);

type Tab = 'overview' | 'world' | 'characters' | 'relationships' | 'outlines' | 'chapters';

type NovelDetailBootstrapSnapshot = {
  project: any;
};

type NovelDetailImportStatusSnapshot = {
  importStatus: any | null;
};

type NovelDetailPartProgressSnapshot = {
  partProgress: any | null;
};

type NovelDetailChapterDetailSnapshot = {
  chapterDetail: any | null;
};

type NovelDetailChapterSelectionSnapshot = {
  chapterNumber: number | null;
  chapterDetail: any | null;
};

const INITIAL_CHARACTERS_RENDER_LIMIT = 24;
const CHARACTERS_RENDER_BATCH_SIZE = 24;
const INITIAL_RELATIONSHIPS_RENDER_LIMIT = 24;
const RELATIONSHIPS_RENDER_BATCH_SIZE = 24;
const INITIAL_CHAPTER_OUTLINES_RENDER_LIMIT = 40;
const CHAPTER_OUTLINES_RENDER_BATCH_SIZE = 40;
const INITIAL_PART_OUTLINES_RENDER_LIMIT = 20;
const PART_OUTLINES_RENDER_BATCH_SIZE = 20;
const INITIAL_COMPLETED_CHAPTERS_RENDER_LIMIT = 120;
const COMPLETED_CHAPTERS_RENDER_BATCH_SIZE = 120;
const NOVEL_DETAIL_BOOTSTRAP_TTL_MS = 4 * 60 * 1000;
const NOVEL_DETAIL_SECTION_TTL_MS = 4 * 60 * 1000;
const NOVEL_DETAIL_CHAPTER_DETAIL_TTL_MS = 10 * 60 * 1000;

const getNovelDetailBootstrapKey = (projectId: string) => `afn:web:novel-detail:${projectId}:bootstrap:v1`;
const getNovelDetailImportStatusKey = (projectId: string) => `afn:web:novel-detail:${projectId}:import-status:v1`;
const getNovelDetailPartProgressKey = (projectId: string) => `afn:web:novel-detail:${projectId}:part-progress:v1`;
const getNovelDetailChapterDetailKey = (projectId: string, chapterNo: number) =>
  `afn:web:novel-detail:${projectId}:chapter-detail:${chapterNo}:v1`;
const getNovelDetailChapterSelectionKey = (projectId: string) => `afn:web:novel-detail:${projectId}:chapter-selection:v1`;

const lowerBound = (list: number[], target: number): number => {
  let left = 0;
  let right = list.length;

  while (left < right) {
    const mid = Math.floor((left + right) / 2);
    if (list[mid] < target) left = mid + 1;
    else right = mid;
  }

  return left;
};

const upperBound = (list: number[], target: number): number => {
  let left = 0;
  let right = list.length;

  while (left < right) {
    const mid = Math.floor((left + right) / 2);
    if (list[mid] <= target) left = mid + 1;
    else right = mid;
  }

  return left;
};

const sanitizeFilenamePart = (raw: string) => {
  // Windows 不允许的文件名字符：<>:"/\\|?* + 控制字符
  return String(raw || '')
    .replace(/[<>:"/\\|?*\u0000-\u001F]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
};

const stableStringify = (value: any): string => {
  const seen = new WeakSet<object>();

  const normalize = (v: any): any => {
    if (v === null || v === undefined) return v;
    const t = typeof v;
    if (t === 'string' || t === 'number' || t === 'boolean') return v;
    if (Array.isArray(v)) return v.map(normalize);
    if (t !== 'object') return String(v);

    if (seen.has(v)) return null;
    seen.add(v);

    const out: Record<string, any> = {};
    for (const key of Object.keys(v).sort()) {
      const nv = normalize(v[key]);
      if (nv !== undefined) out[key] = nv;
    }
    return out;
  };

  try {
    return JSON.stringify(normalize(value));
  } catch {
    return JSON.stringify(String(value ?? ''));
  }
};

const buildNovelBlueprintSnapshot = (blueprint: any): string => {
  const bp = blueprint || {};
  return stableStringify({
    one_sentence_summary: String(bp.one_sentence_summary || ''),
    full_synopsis: String(bp.full_synopsis || ''),
    genre: String(bp.genre || ''),
    target_audience: String(bp.target_audience || ''),
    style: String(bp.style || ''),
    tone: String(bp.tone || ''),
    characters: Array.isArray(bp.characters) ? bp.characters : [],
    relationships: Array.isArray(bp.relationships) ? bp.relationships : [],
  });
};

export const NovelDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  const [project, setProject] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const activeTabStorageKey = useMemo(() => (id ? `afn:novel_detail:active_tab:${id}` : ''), [id]);

  // 对齐桌面端“页缓存”体验：Web 侧记忆上次停留的 Tab（避免路由重建后总回到 overview）
  useEffect(() => {
    if (!activeTabStorageKey) return;
    try {
      const saved = localStorage.getItem(activeTabStorageKey) || '';
      if (
        saved === 'overview' ||
        saved === 'world' ||
        saved === 'characters' ||
        saved === 'relationships' ||
        saved === 'outlines' ||
        saved === 'chapters'
      ) {
        setActiveTab(saved);
      }
    } catch {
      // ignore
    }
  }, [activeTabStorageKey]);

  useEffect(() => {
    if (!activeTabStorageKey) return;
    try {
      localStorage.setItem(activeTabStorageKey, activeTab);
    } catch {
      // ignore
    }
  }, [activeTab, activeTabStorageKey]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [avatarLoading, setAvatarLoading] = useState(false);
  const [ragSyncing, setRagSyncing] = useState(false);
  const [isEditTitleModalOpen, setIsEditTitleModalOpen] = useState(false);
  const [editTitleValue, setEditTitleValue] = useState('');
  const [editTitleSaving, setEditTitleSaving] = useState(false);

  // Form states
  const [blueprintData, setBlueprintData] = useState<any>({});
  const [worldSettingDraft, setWorldSettingDraft] = useState<string>('{}');
  const [worldEditMode, setWorldEditMode] = useState<'structured' | 'json'>('structured');
  const [savedBlueprintSnapshot, setSavedBlueprintSnapshot] = useState<string>('');
  const [savedWorldSettingDraft, setSavedWorldSettingDraft] = useState<string>('{}');

  // Chapter outlines edit
  const [editingChapter, setEditingChapter] = useState<any | null>(null);
  const [isOutlineModalOpen, setIsOutlineModalOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [isDeleteLatestModalOpen, setIsDeleteLatestModalOpen] = useState(false);
  const [deleteLatestCount, setDeleteLatestCount] = useState(5);
  const [deletingLatest, setDeletingLatest] = useState(false);
  const [isRegenerateLatestModalOpen, setIsRegenerateLatestModalOpen] = useState(false);
  const [regenerateLatestCount, setRegenerateLatestCount] = useState(1);
  const [regenerateLatestPrompt, setRegenerateLatestPrompt] = useState('');
  const [regeneratingLatest, setRegeneratingLatest] = useState(false);

  // Part outlines progress
  const [partProgress, setPartProgress] = useState<any | null>(null);
  const [partLoading, setPartLoading] = useState(false);
  const [regeneratingPartKey, setRegeneratingPartKey] = useState<string | null>(null);
  const [generatingPartChapters, setGeneratingPartChapters] = useState<number | null>(null);
  const [isPartGenerateModalOpen, setIsPartGenerateModalOpen] = useState(false);
  const [partGenerateMode, setPartGenerateMode] = useState<'generate' | 'continue'>('generate');
  const [isDeleteLatestPartsModalOpen, setIsDeleteLatestPartsModalOpen] = useState(false);
  const [deleteLatestPartsCount, setDeleteLatestPartsCount] = useState(1);
  const [deletingLatestParts, setDeletingLatestParts] = useState(false);
  const [isRegenerateLatestPartsModalOpen, setIsRegenerateLatestPartsModalOpen] = useState(false);
  const [regenerateLatestPartsCount, setRegenerateLatestPartsCount] = useState(1);
  const [regenerateLatestPartsPrompt, setRegenerateLatestPartsPrompt] = useState('');
  const [regeneratingLatestParts, setRegeneratingLatestParts] = useState(false);
  const [detailPart, setDetailPart] = useState<any | null>(null);

  // 导入分析进度（导入小说专用）
  const [importStatus, setImportStatus] = useState<any | null>(null);
  const [importStatusLoading, setImportStatusLoading] = useState(false);
  const [importStarting, setImportStarting] = useState(false);

  // 已完成章节（项目详情页展示，桌面端 ChaptersSection 对齐）
  const [chaptersSearch, setChaptersSearch] = useState('');
  const [selectedCompletedChapterNumber, setSelectedCompletedChapterNumber] = useState<number | null>(null);
  const [selectedCompletedChapter, setSelectedCompletedChapter] = useState<any | null>(null);
  const [selectedCompletedChapterLoading, setSelectedCompletedChapterLoading] = useState(false);

  const [charactersRenderLimit, setCharactersRenderLimit] = useState(INITIAL_CHARACTERS_RENDER_LIMIT);
  const [relationshipsRenderLimit, setRelationshipsRenderLimit] = useState(INITIAL_RELATIONSHIPS_RENDER_LIMIT);
  const [chapterOutlinesRenderLimit, setChapterOutlinesRenderLimit] = useState(INITIAL_CHAPTER_OUTLINES_RENDER_LIMIT);
  const [partOutlinesRenderLimit, setPartOutlinesRenderLimit] = useState(INITIAL_PART_OUTLINES_RENDER_LIMIT);
  const [completedChaptersRenderLimit, setCompletedChaptersRenderLimit] = useState(INITIAL_COMPLETED_CHAPTERS_RENDER_LIMIT);

  // 章节导入（TXT/MD，支持 utf-8/gb18030）
  const [isImportChapterModalOpen, setIsImportChapterModalOpen] = useState(false);
  const [importChapterNumber, setImportChapterNumber] = useState<number>(1);
  const [importChapterTitle, setImportChapterTitle] = useState('');
  const [importChapterContent, setImportChapterContent] = useState('');
  const [importEncoding, setImportEncoding] = useState<'utf-8' | 'gb18030'>('utf-8');
  const [importFileName, setImportFileName] = useState('');
  const [importFileBuffer, setImportFileBuffer] = useState<ArrayBuffer | null>(null);
  const [importingChapter, setImportingChapter] = useState(false);
  const importFileInputRef = useRef<HTMLInputElement | null>(null);
  
  // Character Edit State
  const [editingCharIndex, setEditingCharIndex] = useState<number | null>(null);
  const [charForm, setCharForm] = useState<any>({});
  const [isCharModalOpen, setIsCharModalOpen] = useState(false);
  const [charactersView, setCharactersView] = useState<'info' | 'portraits'>('info');
  const [isProtagonistModalOpen, setIsProtagonistModalOpen] = useState(false);

  // Relationships Edit State
  const [editingRelIndex, setEditingRelIndex] = useState<number | null>(null);
  const [relForm, setRelForm] = useState<{ character_from: string; character_to: string; description: string }>({
    character_from: '',
    character_to: '',
    description: '',
  });
  const [isRelModalOpen, setIsRelModalOpen] = useState(false);

  // Blueprint Refine（优化蓝图）State
  const [isRefineModalOpen, setIsRefineModalOpen] = useState(false);
  const [refineInstruction, setRefineInstruction] = useState('');
  const [refineForce, setRefineForce] = useState(false);
  const [refining, setRefining] = useState(false);
  const [refineResult, setRefineResult] = useState<string | null>(null);

  // 输入优化提示词（可选）：替代浏览器 prompt()，统一为 Modal 交互
  const pendingPromptActionRef = useRef<((prompt?: string) => void | Promise<void>) | null>(null);
  const [isPromptModalOpen, setIsPromptModalOpen] = useState(false);
  const [promptModalTitle, setPromptModalTitle] = useState('输入优化提示词（可选）');
  const [promptModalHint, setPromptModalHint] = useState<string | null>(null);
  const [promptModalValue, setPromptModalValue] = useState('');

  const openOptionalPromptModal = useCallback((opts: {
    title?: string;
    hint?: string;
    initialValue?: string;
    onConfirm: (prompt?: string) => void | Promise<void>;
  }) => {
    setPromptModalTitle(opts.title || '输入优化提示词（可选）');
    setPromptModalHint(opts.hint || null);
    setPromptModalValue(opts.initialValue || '');
    pendingPromptActionRef.current = opts.onConfirm;
    setIsPromptModalOpen(true);
  }, []);

  const confirmOptionalPromptModal = useCallback(async () => {
    const fn = pendingPromptActionRef.current;
    pendingPromptActionRef.current = null;
    setIsPromptModalOpen(false);
    const text = (promptModalValue || '').trim();
    try {
      await fn?.(text ? text : undefined);
    } catch (e) {
      console.error(e);
      addToast('操作失败', 'error');
    }
  }, [addToast, promptModalValue]);

  const hasImportStatusBootstrapRef = useRef(false);
  const hasPartProgressBootstrapRef = useRef(false);

  const chapterOutlines = useMemo(() => {
    const list = Array.isArray(blueprintData?.chapter_outline) ? blueprintData.chapter_outline : [];
    return [...list].sort((a: any, b: any) => Number(a.chapter_number || 0) - Number(b.chapter_number || 0));
  }, [blueprintData]);

  const partOutlines = useMemo(() => {
    const list = Array.isArray(partProgress?.parts) ? partProgress.parts : [];
    return [...list].sort((a: any, b: any) => Number(a?.part_number || 0) - Number(b?.part_number || 0));
  }, [partProgress]);

  const partCoveredChapters = useMemo(() => {
    if (!partOutlines.length) return 0;
    return partOutlines.reduce((max: number, p: any) => {
      const end = Number(p?.end_chapter || 0);
      return Math.max(max, Number.isFinite(end) ? end : 0);
    }, 0);
  }, [partOutlines]);

  const partTotalChapters = useMemo(() => {
    const n = Number(blueprintData?.total_chapters || 0);
    return Number.isFinite(n) ? n : 0;
  }, [blueprintData]);

  const canContinuePartOutlines = useMemo(() => {
    if (!partTotalChapters) return false;
    if (!partOutlines.length) return false;
    return partCoveredChapters > 0 && partCoveredChapters < partTotalChapters;
  }, [partCoveredChapters, partOutlines.length, partTotalChapters]);

  const maxDeletablePartCount = useMemo(() => {
    // 后端禁止删除全部部分大纲：最多删除到只剩 1 个部分
    return Math.max(0, partOutlines.length - 1);
  }, [partOutlines.length]);

  const chaptersByNumber = useMemo(() => {
    const map = new Map<number, any>();
    const list = Array.isArray(project?.chapters) ? project.chapters : [];
    list.forEach((c: any) => map.set(Number(c.chapter_number), c));
    return map;
  }, [project]);

  const completedChapters = useMemo(() => {
    const list = Array.isArray(project?.chapters) ? project.chapters : [];
    const completed = list.filter((c: any) => {
      const hasSelected = typeof c?.selected_version === 'number';
      const hasContent = Boolean(String(c?.content || '').trim());
      return hasSelected || hasContent;
    });
    return [...completed].sort((a, b) => Number(a?.chapter_number || 0) - Number(b?.chapter_number || 0));
  }, [project]);

  const deferredChaptersSearch = useDeferredValue(chaptersSearch);

  const filteredCompletedChapters = useMemo(() => {
    const q = String(deferredChaptersSearch || '').trim().toLowerCase();
    if (!q) return completedChapters;

    return completedChapters.filter((c: any) => {
      const n = String(c?.chapter_number || '').toLowerCase();
      const title = String(c?.title || '').toLowerCase();
      return n.includes(q) || title.includes(q) || `第${n}章`.includes(q);
    });
  }, [completedChapters, deferredChaptersSearch]);

  const charactersList = useMemo(() => {
    return Array.isArray(blueprintData?.characters) ? blueprintData.characters : [];
  }, [blueprintData]);

  const relationshipsList = useMemo(() => {
    return Array.isArray(blueprintData?.relationships) ? blueprintData.relationships : [];
  }, [blueprintData]);

  const characterNames = useMemo(() => {
    const set = new Set<string>();
    charactersList.forEach((c: any) => {
      const name = String(c?.name || '').trim();
      if (name) set.add(name);
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'zh-CN'));
  }, [charactersList]);

  const characterProfiles = useMemo(() => {
    const list = charactersList;
    const map: Record<string, string> = {};
    for (const c of list) {
      const name = String((c as any)?.name || '').trim();
      if (!name) continue;

      const keys = [
        'appearance',
        'appearance_description',
        'looks',
        'look',
        'visual',
        'portrait',
        'portrait_prompt',
        'image_prompt',
        'description',
        'desc',
        'profile',
        '外貌',
        '外观',
        '形象',
        '描述',
      ];

      let desc = '';
      for (const k of keys) {
        const v = (c as any)?.[k];
        if (typeof v === 'string' && v.trim()) {
          desc = v.trim();
          break;
        }
      }

      if (!desc) {
        // 兜底：拼接其它字符串字段（避免完全空白导致“生成缺失立绘”无可用描述）
        const parts: string[] = [];
        for (const [k, v] of Object.entries(c || {})) {
          if (k === 'name') continue;
          if (typeof v === 'string' && v.trim()) parts.push(v.trim());
        }
        desc = parts.join('；').trim();
      }

      if (desc) map[name] = desc.length > 600 ? desc.slice(0, 600) : desc;
    }
    return map;
  }, [charactersList]);

  const chapterOutlineNumbers = useMemo(() => {
    return chapterOutlines
      .map((outline: any) => Number(outline?.chapter_number || 0))
      .filter((num: number) => Number.isFinite(num) && num > 0);
  }, [chapterOutlines]);

  const countOutlinesInRange = useCallback((startChapter: number, endChapter: number) => {
    if (!Number.isFinite(startChapter) || !Number.isFinite(endChapter)) return 0;
    if (endChapter < startChapter) return 0;

    const startIndex = lowerBound(chapterOutlineNumbers, Math.max(1, Math.floor(startChapter)));
    const endIndex = upperBound(chapterOutlineNumbers, Math.floor(endChapter));
    return Math.max(0, endIndex - startIndex);
  }, [chapterOutlineNumbers]);

  const visibleCharacters = useMemo(() => {
    return charactersList.slice(0, charactersRenderLimit);
  }, [charactersList, charactersRenderLimit]);

  const visibleRelationships = useMemo(() => {
    return relationshipsList.slice(0, relationshipsRenderLimit);
  }, [relationshipsList, relationshipsRenderLimit]);

  const visibleChapterOutlines = useMemo(() => {
    return chapterOutlines.slice(0, chapterOutlinesRenderLimit);
  }, [chapterOutlines, chapterOutlinesRenderLimit]);

  const visiblePartOutlines = useMemo(() => {
    return partOutlines.slice(0, partOutlinesRenderLimit);
  }, [partOutlines, partOutlinesRenderLimit]);

  const visibleCompletedChapters = useMemo(() => {
    return filteredCompletedChapters.slice(0, completedChaptersRenderLimit);
  }, [filteredCompletedChapters, completedChaptersRenderLimit]);

  const remainingCharacters = Math.max(0, charactersList.length - visibleCharacters.length);
  const remainingRelationships = Math.max(0, relationshipsList.length - visibleRelationships.length);
  const remainingChapterOutlines = Math.max(0, chapterOutlines.length - visibleChapterOutlines.length);
  const remainingPartOutlines = Math.max(0, partOutlines.length - visiblePartOutlines.length);
  const remainingCompletedChapters = Math.max(0, filteredCompletedChapters.length - visibleCompletedChapters.length);

  const latestChapterNumber = useMemo(() => {
    const fromDb = Array.isArray(project?.chapters)
      ? Math.max(0, ...project.chapters.map((c: any) => Number(c?.chapter_number || 0)))
      : 0;
    const fromOutline = chapterOutlines.length
      ? Number(chapterOutlines[chapterOutlines.length - 1]?.chapter_number || 0)
      : 0;
    return Math.max(1, fromDb, fromOutline);
  }, [chapterOutlines, project]);

  const openOutlineEditor = useCallback((outline: any) => {
    const chapterNumber = Number(outline?.chapter_number || 0);
    if (!chapterNumber) return;
    setEditingChapter({
      chapter_number: chapterNumber,
      title: String(outline?.title || `第${chapterNumber}章`),
      summary: String(outline?.summary || ''),
      generation_status: 'not_generated',
    });
    setIsOutlineModalOpen(true);
  }, []);

  const worldSettingError = useMemo(() => {
    try {
      const txt = (worldSettingDraft || '').trim();
      const parsed = txt ? JSON.parse(txt) : {};
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return '请输入合法 JSON 对象';
      return '';
    } catch {
      return '请输入合法 JSON 对象';
    }
  }, [worldSettingDraft]);

  const currentBlueprintSnapshot = useMemo(() => {
    return buildNovelBlueprintSnapshot(blueprintData);
  }, [blueprintData]);

  const isBlueprintDirty = useMemo(() => {
    // 首次加载前不提示“未保存”
    if (!savedBlueprintSnapshot) return false;
    return currentBlueprintSnapshot !== savedBlueprintSnapshot || worldSettingDraft !== savedWorldSettingDraft;
  }, [currentBlueprintSnapshot, savedBlueprintSnapshot, savedWorldSettingDraft, worldSettingDraft]);

  const dirtySummary = useMemo(() => {
    if (!isBlueprintDirty) return '';

    const parts: string[] = [];
    try {
      const saved = savedBlueprintSnapshot ? JSON.parse(savedBlueprintSnapshot) : null;
      const cur = currentBlueprintSnapshot ? JSON.parse(currentBlueprintSnapshot) : null;
      if (saved && cur) {
        const overviewChanged =
          cur.one_sentence_summary !== saved.one_sentence_summary ||
          cur.full_synopsis !== saved.full_synopsis ||
          cur.genre !== saved.genre ||
          cur.target_audience !== saved.target_audience ||
          cur.style !== saved.style ||
          cur.tone !== saved.tone;
        if (overviewChanged) parts.push('概览');

        const charsChanged = stableStringify(cur.characters) !== stableStringify(saved.characters);
        if (charsChanged) parts.push('角色');

        const relChanged = stableStringify(cur.relationships) !== stableStringify(saved.relationships);
        if (relChanged) parts.push('关系');
      }
    } catch {
      // ignore
    }

    if (worldSettingDraft !== savedWorldSettingDraft) parts.push('世界观');

    if (!parts.length) return '有未保存的修改';
    return `有未保存的修改：${parts.join('、')}`;
  }, [currentBlueprintSnapshot, isBlueprintDirty, savedBlueprintSnapshot, savedWorldSettingDraft, worldSettingDraft]);

  const safeNavigate = useCallback(async (to: string) => {
    if (isBlueprintDirty) {
      const ok = await confirmDialog({
        title: '未保存修改',
        message: `${dirtySummary || '有未保存的修改'}。\n\n确定要离开当前页面吗？`,
        confirmText: '离开',
        dialogType: 'warning',
      });
      if (!ok) return;
    }
    navigate(to);
  }, [dirtySummary, isBlueprintDirty, navigate]);

  // 仅用 ref 保存脏状态，避免频繁重绑 popstate 监听（编辑表单时会高频 re-render）
  const isBlueprintDirtyRef = useRef(false);
  const dirtySummaryRef = useRef('');
  const historyIdxRef = useRef<number>(0);
  const ignoreNextPopStateRef = useRef(false);

  useEffect(() => {
    isBlueprintDirtyRef.current = isBlueprintDirty;
    dirtySummaryRef.current = dirtySummary;
  }, [dirtySummary, isBlueprintDirty]);

  useEffect(() => {
    // React Router 会在 history.state 里维护 idx（0,1,2...），用于判断 back/forward 方向
    try {
      const idx = Number((window.history.state as any)?.idx);
      if (Number.isFinite(idx)) historyIdxRef.current = idx;
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    const onPopState = () => {
      let nextIdx = NaN;
      try {
        nextIdx = Number((window.history.state as any)?.idx);
      } catch {
        nextIdx = NaN;
      }

      // 处理“我们自己 go(-1/+1) 回滚”的二次 popstate
      if (ignoreNextPopStateRef.current) {
        ignoreNextPopStateRef.current = false;
        if (Number.isFinite(nextIdx)) historyIdxRef.current = nextIdx;
        return;
      }

      // 非脏状态：仅更新 idx 基线，允许正常后退/前进
      if (!isBlueprintDirtyRef.current) {
        if (Number.isFinite(nextIdx)) historyIdxRef.current = nextIdx;
        return;
      }

      const prevIdx = historyIdxRef.current;
      const delta = Number.isFinite(nextIdx) ? nextIdx - prevIdx : 0;
      const ok = confirm(`${dirtySummaryRef.current || '有未保存的修改'}。\n\n确定要离开当前页面吗？`);
      if (ok) {
        if (Number.isFinite(nextIdx)) historyIdxRef.current = nextIdx;
        return;
      }

      ignoreNextPopStateRef.current = true;
      // 尝试回滚：用户点 back => delta<0 => go(+1)；点 forward => delta>0 => go(-1)
      if (delta < 0) {
        navigate(1);
        return;
      }
      if (delta > 0) {
        navigate(-1);
        return;
      }

      // 无法判断方向时尽量回到原页面（通常是 back 场景）
      navigate(1);
    };

    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, [navigate]);

  const worldSettingObj = useMemo(() => {
    try {
      const txt = (worldSettingDraft || '').trim();
      const parsed = txt ? JSON.parse(txt) : {};
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
      return parsed as any;
    } catch {
      return null;
    }
  }, [worldSettingDraft]);

  const worldListToText = useCallback((value: any) => {
    if (!Array.isArray(value) || value.length === 0) return '';
    return value
      .map((it) => {
        if (typeof it === 'string') return it.trim();
        if (!it || typeof it !== 'object') return '';
        const title = String(it.title || it.name || '').trim();
        const desc = String(it.description || '').trim();
        if (!title && !desc) return '';
        if (!desc) return title || '';
        return `${title || '（未命名）'}｜${desc}`;
      })
      .filter(Boolean)
      .join('\n');
  }, []);

  const worldTextToList = useCallback((text: string) => {
    const lines = (text || '')
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);

    return lines.map((line) => {
      const sepIdx = line.includes('｜') ? line.indexOf('｜') : (line.includes('|') ? line.indexOf('|') : -1);
      if (sepIdx >= 0) {
        const title = line.slice(0, sepIdx).trim();
        const desc = line.slice(sepIdx + 1).trim();
        if (desc) return { title: title || '（未命名）', description: desc };
        return title;
      }
      return line;
    });
  }, []);

  const updateWorldSettingDraft = useCallback((patch: (obj: any) => void) => {
    if (!worldSettingObj) return;
    const next = { ...worldSettingObj };
    patch(next);
    setWorldSettingDraft(JSON.stringify(next, null, 2));
  }, [worldSettingObj]);

  const applyProjectPayload = useCallback((data: any) => {
    setProject(data);
    if (data?.blueprint) {
      setBlueprintData(data.blueprint);
      const raw = data.blueprint.world_setting;
      let ws: any = raw;
      if (typeof raw === 'string') {
        try {
          ws = JSON.parse(raw);
        } catch {
          ws = { text: raw };
        }
      }
      if (!ws || typeof ws !== 'object' || Array.isArray(ws)) ws = {};
      const pretty = JSON.stringify(ws, null, 2);
      setWorldSettingDraft(pretty);
      setSavedWorldSettingDraft(pretty);
      setSavedBlueprintSnapshot(buildNovelBlueprintSnapshot(data.blueprint));
    } else {
      setSavedBlueprintSnapshot(buildNovelBlueprintSnapshot({}));
      setSavedWorldSettingDraft('{}');
    }
  }, []);

  useEffect(() => {
    if (!id) return;
    const cached = readBootstrapCache<NovelDetailBootstrapSnapshot>(
      getNovelDetailBootstrapKey(id),
      NOVEL_DETAIL_BOOTSTRAP_TTL_MS,
    );
    if (!cached?.project) {
      setProject(null);
      setLoading(true);
      return;
    }
    applyProjectPayload(cached.project);
    setLoading(false);
  }, [applyProjectPayload, id]);

  useEffect(() => {
    if (!id) return;

    const importCached = readBootstrapCache<NovelDetailImportStatusSnapshot>(
      getNovelDetailImportStatusKey(id),
      NOVEL_DETAIL_SECTION_TTL_MS,
    );
    if (importCached) {
      setImportStatus(importCached.importStatus ?? null);
      hasImportStatusBootstrapRef.current = importCached.importStatus !== null;
    } else {
      setImportStatus(null);
      hasImportStatusBootstrapRef.current = false;
    }

    const partCached = readBootstrapCache<NovelDetailPartProgressSnapshot>(
      getNovelDetailPartProgressKey(id),
      NOVEL_DETAIL_SECTION_TTL_MS,
    );
    if (partCached) {
      setPartProgress(partCached.partProgress ?? null);
      hasPartProgressBootstrapRef.current = partCached.partProgress !== null;
    } else {
      setPartProgress(null);
      hasPartProgressBootstrapRef.current = false;
    }

    const chapterSelectionCached = readBootstrapCache<NovelDetailChapterSelectionSnapshot>(
      getNovelDetailChapterSelectionKey(id),
      NOVEL_DETAIL_CHAPTER_DETAIL_TTL_MS,
    );
    const chapterNo = Number(chapterSelectionCached?.chapterNumber || 0);
    if (Number.isFinite(chapterNo) && chapterNo > 0) {
      setSelectedCompletedChapterNumber(chapterNo);
      setSelectedCompletedChapter(chapterSelectionCached?.chapterDetail ?? null);
    } else {
      setSelectedCompletedChapterNumber(null);
      setSelectedCompletedChapter(null);
    }
  }, [id]);

  const fetchProject = useCallback(async () => {
    try {
      const data = await novelsApi.get(id!);
      applyProjectPayload(data);
      writeBootstrapCache<NovelDetailBootstrapSnapshot>(getNovelDetailBootstrapKey(id!), { project: data });

      // 导入小说：进度查询延后到空闲阶段，避免阻塞详情首屏
      if (data.is_imported) {
        const hadImportSnapshot = hasImportStatusBootstrapRef.current;
        if (!hadImportSnapshot) {
          setImportStatusLoading(true);
        } else {
          setImportStatusLoading(false);
        }
        scheduleIdleTask(() => {
          void novelsApi
            .getImportAnalysisStatus(id!)
            .then((status) => {
              setImportStatus(status);
              hasImportStatusBootstrapRef.current = status !== null;
              writeBootstrapCache<NovelDetailImportStatusSnapshot>(getNovelDetailImportStatusKey(id!), {
                importStatus: status ?? null,
              });
            })
            .catch((e) => {
              console.error(e);
              if (!hadImportSnapshot) {
                setImportStatus(null);
                hasImportStatusBootstrapRef.current = false;
              }
            })
            .finally(() => {
              setImportStatusLoading(false);
            });
        }, { delay: 120, timeout: 2200 });
      } else {
        setImportStatus(null);
        hasImportStatusBootstrapRef.current = false;
        setImportStatusLoading(false);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [applyProjectPayload, id]);

  const fetchProjectButton = useCallback(async () => {
    if (isBlueprintDirty) {
      const ok = await confirmDialog({
        title: '刷新确认',
        message: `${dirtySummary || '有未保存的修改'}。\n\n确定要刷新并丢弃本地修改吗？`,
        confirmText: '刷新并丢弃',
        dialogType: 'warning',
      });
      if (!ok) return;
    }
    await fetchProject();
  }, [dirtySummary, fetchProject, isBlueprintDirty]);

  const openEditTitleModal = useCallback(() => {
    setEditTitleValue(String(project?.title || '').trim());
    setIsEditTitleModalOpen(true);
  }, [project?.title]);

  const saveProjectTitle = useCallback(async () => {
    if (!id) return;
    const next = (editTitleValue || '').trim();
    if (!next) {
      addToast('标题不能为空', 'error');
      return;
    }

    setEditTitleSaving(true);
    try {
      await novelsApi.update(id, { title: next });
      addToast('标题已更新', 'success');
      setIsEditTitleModalOpen(false);
      await fetchProject();
    } catch (e) {
      console.error(e);
      addToast('标题更新失败', 'error');
    } finally {
      setEditTitleSaving(false);
    }
  }, [addToast, editTitleValue, fetchProject, id]);

  const refreshImportStatus = useCallback(async () => {
    if (!id) return;
    setImportStatusLoading(true);
    const hadImportSnapshot = hasImportStatusBootstrapRef.current;
    try {
      const status = await novelsApi.getImportAnalysisStatus(id);
      setImportStatus(status);
      hasImportStatusBootstrapRef.current = status !== null;
      writeBootstrapCache<NovelDetailImportStatusSnapshot>(getNovelDetailImportStatusKey(id), {
        importStatus: status ?? null,
      });
    } catch (e) {
      console.error(e);
      if (!hadImportSnapshot) {
        setImportStatus(null);
        hasImportStatusBootstrapRef.current = false;
      }
    } finally {
      setImportStatusLoading(false);
    }
  }, [id]);

  const cancelImportAnalysis = useCallback(async () => {
    if (!id) return;
    try {
      await novelsApi.cancelImportAnalysis(id);
      addToast('已请求取消分析任务', 'success');
      await refreshImportStatus();
      await fetchProject();
    } catch (e) {
      console.error(e);
      addToast('取消失败', 'error');
    }
  }, [addToast, fetchProject, id, refreshImportStatus]);

  const startImportAnalysis = useCallback(async () => {
    if (!id) return;

    const status = String(importStatus?.status || project?.import_analysis_status || 'pending');
    const isResume = status === 'failed' || status === 'cancelled';

    const ok = await confirmDialog({
      title: '导入分析',
      message: isResume
        ? '检测到之前的分析未完成，将尝试从断点继续。\n\n确定要继续分析吗？'
        : '将开始分析导入的小说内容，过程可能较久。\n\n确定要开始分析吗？',
      confirmText: isResume ? '继续分析' : '开始分析',
      dialogType: 'warning',
    });
    if (!ok) return;

    setImportStarting(true);
    try {
      await novelsApi.startImportAnalysis(id);
      addToast(isResume ? '已开始继续分析…' : '已开始分析…', 'success');
      await refreshImportStatus();
      await fetchProject();
    } catch (e) {
      console.error(e);
      addToast('启动失败', 'error');
    } finally {
      setImportStarting(false);
    }
  }, [addToast, fetchProject, id, importStatus?.status, project?.import_analysis_status, refreshImportStatus]);

  // 导入分析进行中：自动刷新进度（替代桌面端的进度对话框轮询体验）
  useEffect(() => {
    if (!id) return;
    const status = String(importStatus?.status || project?.import_analysis_status || '');
    if (status !== 'analyzing') return;

    const timer = window.setInterval(() => {
      refreshImportStatus().catch(() => {});
    }, 2000);
    return () => window.clearInterval(timer);
  }, [id, importStatus?.status, project?.import_analysis_status, refreshImportStatus]);

  useEffect(() => {
    if (!id) return;
    writeBootstrapCache<NovelDetailImportStatusSnapshot>(getNovelDetailImportStatusKey(id), {
      importStatus: importStatus ?? null,
    });
    hasImportStatusBootstrapRef.current = importStatus !== null;
  }, [id, importStatus]);

  useEffect(() => {
    if (!id) return;
    writeBootstrapCache<NovelDetailPartProgressSnapshot>(getNovelDetailPartProgressKey(id), {
      partProgress: partProgress ?? null,
    });
    hasPartProgressBootstrapRef.current = partProgress !== null;
  }, [id, partProgress]);

  useEffect(() => {
    if (!id) return;
    const chapterNo = Number(selectedCompletedChapterNumber || 0);
    const detailChapterNo = Number(selectedCompletedChapter?.chapter_number || 0);
    const matchedDetail =
      chapterNo > 0 && detailChapterNo === chapterNo ? selectedCompletedChapter : null;

    writeBootstrapCache<NovelDetailChapterSelectionSnapshot>(getNovelDetailChapterSelectionKey(id), {
      chapterNumber: chapterNo > 0 ? chapterNo : null,
      chapterDetail: matchedDetail,
    });
  }, [id, selectedCompletedChapter, selectedCompletedChapterNumber]);

  const handleRegenerateOutline = useCallback(async (chapterNumber: number) => {
    if (!id) return;
    const max = chapterOutlines.length ? Number(chapterOutlines[chapterOutlines.length - 1]?.chapter_number || 0) : chapterNumber;
    const isLast = chapterNumber === max;

    let cascadeDelete = false;
    if (!isLast && max > 0) {
      const ok = await confirmDialog({
        title: '串行生成原则',
        message:
          `串行生成原则：只能直接重生成最后一章（当前最后一章为第${max}章）。\n\n` +
          `若要重生成第${chapterNumber}章，必须级联删除第${chapterNumber + 1}-${max}章的大纲/章节内容/向量数据。\n\n是否继续？`,
        confirmText: '继续',
        dialogType: 'danger',
      });
      if (!ok) return;
      cascadeDelete = true;
    }

    openOptionalPromptModal({
      title: '输入优化提示词（可选）',
      hint: '留空则按默认策略重生成；填写则会作为优化方向参与生成。',
      onConfirm: async (promptText?: string) => {
        try {
          const result = await writerApi.regenerateChapterOutline(id, chapterNumber, {
            prompt: promptText,
            cascadeDelete,
          });
          addToast(result?.message || '已重新生成章节大纲', 'success');
          if (result?.cascade_deleted?.message) {
            addToast(String(result.cascade_deleted.message), 'info');
          }
          await fetchProject();
        } catch (e) {
          console.error(e);
          addToast('重生成失败', 'error');
        }
      },
    });
  }, [addToast, chapterOutlines, fetchProject, id, openOptionalPromptModal]);

  const handleSave = async () => {
    if (!id) return;
    setSaving(true);
    try {
      // world_setting 必须是 JSON 对象（后端会 merge update）
      let parsedWorldSetting: any = {};
      try {
        const txt = (worldSettingDraft || '').trim();
        parsedWorldSetting = txt ? JSON.parse(txt) : {};
        if (!parsedWorldSetting || typeof parsedWorldSetting !== 'object' || Array.isArray(parsedWorldSetting)) {
          throw new Error('world_setting must be an object');
        }
      } catch {
        addToast('世界观格式无效：请填写合法的 JSON 对象', 'error');
        setActiveTab('world');
        return;
      }

      const prettyWorld = JSON.stringify(parsedWorldSetting, null, 2);
      const payload = { ...blueprintData, world_setting: parsedWorldSetting };
      await novelsApi.updateBlueprint(id, payload);
      setBlueprintData(payload);
      setWorldSettingDraft(prettyWorld);
      setSavedWorldSettingDraft(prettyWorld);
      setSavedBlueprintSnapshot(buildNovelBlueprintSnapshot(payload));
      addToast('蓝图已保存', 'success');
    } catch (e) {
      console.error(e);
      addToast('保存失败', 'error');
    } finally {
      setSaving(false);
    }
  };

  const openRefineModal = () => {
    setRefineInstruction('');
    setRefineForce(false);
    setRefineResult(null);
    setIsRefineModalOpen(true);
  };

  const handleRefineBlueprint = async () => {
    if (!id) return;
    const instruction = refineInstruction.trim();
    if (!instruction) {
      addToast('请输入优化指令', 'error');
      return;
    }

    setRefining(true);
    setRefineResult(null);

    const run = async (force: boolean) => {
      const result = await novelsApi.refineBlueprint(id, instruction, force);
      if (result?.blueprint) setBlueprintData(result.blueprint);
      setRefineResult(result?.ai_message || null);
      addToast('蓝图优化完成', 'success');
      await fetchProject();
    };

    try {
      await run(refineForce);
    } catch (e: any) {
      const status = e?.response?.status;
      const detail = e?.response?.data?.detail;

      // 后端会在存在章节大纲/章节内容时返回 409，提示需要用户确认 force
      if (status === 409 && !refineForce) {
        const ok = await confirmDialog({
          title: '强制优化蓝图',
          message: `${detail || '检测到已有后续数据，优化蓝图会清空这些数据。'}\n\n是否强制优化？`,
          confirmText: '强制优化',
          dialogType: 'danger',
        });
        if (ok) {
          try {
            setRefineForce(true);
            await run(true);
          } catch (e2) {
            console.error(e2);
          }
        }
        return;
      }

      console.error(e);
    } finally {
      setRefining(false);
    }
  };

  const handleExport = async () => {
    if (!id) return;
    try {
      const response = await novelsApi.exportNovel(id, 'txt');
      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      // Content-Disposition header usually has filename, but we can fallback
      const filename = `${project.title || 'novel'}.txt`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      addToast('导出成功', 'success');
    } catch (e) {
      console.error(e);
      addToast('导出失败', 'error');
    }
  };

  const handleRagSync = async () => {
	    if (!id) return;
	    if (ragSyncing) return;

	    const ok = await confirmDialog({
	      title: 'RAG 同步',
	      message: '将同步项目到向量库：摘要/分析/索引/向量入库。\n\n强制全量入库会对所有类型重新入库，耗时更长。\n\n是否继续？',
	      confirmText: '继续',
	      dialogType: 'warning',
	    });
	    if (!ok) return;

    setRagSyncing(true);
    try {
      try {
        const diag = await novelsApi.getRagDiagnose(id);
        if (diag && diag.vector_store_enabled === false) {
          addToast('向量库未启用，无法同步（请先在设置中启用/配置）', 'error');
          return;
        }
        if (diag && diag.embedding_service_enabled === false) {
          addToast('嵌入服务未启用，无法同步（请先在设置中配置嵌入）', 'error');
          return;
        }
      } catch (e) {
        // 诊断失败不阻塞同步，交给后端返回更具体错误
        console.error(e);
      }

      const res = await novelsApi.ingestAllRagData(id, true);
      if (res.success) addToast('RAG 同步完成', 'success');
      else addToast('RAG 同步失败（请查看后端日志/结果详情）', 'error');
    } catch (e) {
      console.error(e);
      addToast('RAG 同步失败', 'error');
    } finally {
      setRagSyncing(false);
    }
  };

  const handleGenerateAvatar = async () => {
    if (!id) return;
    setAvatarLoading(true);
    try {
      const result = await novelsApi.generateAvatar(id);
      setBlueprintData((prev: any) => ({
        ...prev,
        avatar_svg: result.avatar_svg,
        avatar_animal: result.animal,
      }));
      addToast('头像已生成', 'success');
    } catch (e) {
      console.error(e);
      addToast('头像生成失败（请检查 LLM 配置与后端日志）', 'error');
    } finally {
      setAvatarLoading(false);
    }
  };

  const handleDeleteAvatar = async () => {
    if (!id) return;
    const ok = await confirmDialog({
      title: '删除头像',
      message: '确定要删除该小说头像吗？',
      confirmText: '删除',
      dialogType: 'danger',
    });
    if (!ok) return;
    setAvatarLoading(true);
    try {
      await novelsApi.deleteAvatar(id);
      setBlueprintData((prev: any) => ({
        ...prev,
        avatar_svg: null,
        avatar_animal: null,
      }));
      addToast('头像已删除', 'success');
    } catch (e) {
      console.error(e);
      addToast('头像删除失败', 'error');
    } finally {
      setAvatarLoading(false);
    }
  };

  const fetchPartProgress = useCallback(async () => {
    if (!id) return;
    const hadPartSnapshot = hasPartProgressBootstrapRef.current;
    if (!hadPartSnapshot) {
      setPartLoading(true);
    }
    try {
      const data = await writerApi.getPartOutlines(id);
      setPartProgress(data);
      hasPartProgressBootstrapRef.current = data !== null;
      writeBootstrapCache<NovelDetailPartProgressSnapshot>(getNovelDetailPartProgressKey(id), {
        partProgress: data ?? null,
      });
    } catch (e) {
      if (!hadPartSnapshot) {
        setPartProgress(null);
        hasPartProgressBootstrapRef.current = false;
      }
    } finally {
      setPartLoading(false);
    }
  }, [id]);

  const openPartOutlinesModal = useCallback((mode: 'generate' | 'continue') => {
    if (!id) return;
    if (!partTotalChapters) {
      addToast('无法获取总章节数，请先生成蓝图', 'error');
      return;
    }
    setPartGenerateMode(mode);
    setIsPartGenerateModalOpen(true);
  }, [addToast, id, partTotalChapters]);

	  const handleRegenerateAllPartOutlines = useCallback(async () => {
	    if (!id) return;
	    const ok = await confirmDialog({
	      title: '重生成所有部分大纲',
	      message: '重生成所有部分大纲将删除所有已生成的章节大纲（以及可能存在的章节内容/向量数据）。\n\n是否继续？',
	      confirmText: '继续',
	      dialogType: 'danger',
	    });
	    if (!ok) return;
	    openOptionalPromptModal({
	      title: '输入优化提示词（可选）',
	      hint: '留空则按默认策略重生成；填写则会作为优化方向参与生成。',
	          onConfirm: async (promptText?: string) => {
        setRegeneratingPartKey('all');
        try {
          const res = await writerApi.regenerateAllPartOutlines(id, promptText, { timeout: 0 });
          setPartProgress(res);
          addToast('部分大纲已重生成', 'success');
          await fetchProject();
          await fetchPartProgress();
        } catch (e) {
          console.error(e);
          addToast('重生成失败', 'error');
        } finally {
          setRegeneratingPartKey(null);
        }
      },
    });
  }, [addToast, fetchPartProgress, fetchProject, id, openOptionalPromptModal]);

	  const handleRegenerateLastPartOutline = useCallback(async () => {
	    if (!id) return;
	    const ok = await confirmDialog({
	      title: '重生成最后一个部分',
	      message: '重生成最后一个部分大纲将删除该部分对应的章节大纲（以及可能存在的章节内容/向量数据）。\n\n是否继续？',
	      confirmText: '继续',
	      dialogType: 'danger',
	    });
	    if (!ok) return;
	    openOptionalPromptModal({
	      title: '输入优化提示词（可选）',
	      hint: '留空则按默认策略重生成；填写则会作为优化方向参与生成。',
	      onConfirm: async (promptText?: string) => {
        setRegeneratingPartKey('last');
        try {
          const res = await writerApi.regenerateLastPartOutline(id, promptText, { timeout: 0 });
          setPartProgress(res);
          addToast('最后一个部分大纲已重生成', 'success');
          await fetchProject();
          await fetchPartProgress();
        } catch (e) {
          console.error(e);
          addToast('重生成失败', 'error');
        } finally {
          setRegeneratingPartKey(null);
        }
      },
    });
  }, [addToast, fetchPartProgress, fetchProject, id, openOptionalPromptModal]);

  const handleRegeneratePartOutline = useCallback(async (partNumber: number) => {
    if (!id) return;
    const parts = Array.isArray(partProgress?.parts) ? partProgress.parts : [];
    const maxPart = parts.length ? Math.max(...parts.map((p: any) => Number(p.part_number || 0))) : partNumber;
    const isLast = partNumber === maxPart;

	    let cascadeDelete = false;
	    if (!isLast && maxPart > 0) {
	      const ok = await confirmDialog({
	        title: '串行生成原则',
	        message:
	          `串行生成原则：只能直接重生成最后一个部分（当前最后一个为第${maxPart}部分）。\n\n` +
	          `若要重生成第${partNumber}部分，必须级联删除第${partNumber + 1}-${maxPart}部分的大纲，以及对应章节大纲/内容/向量数据。\n\n是否继续？`,
	        confirmText: '继续',
	        dialogType: 'danger',
	      });
	      if (!ok) return;
	      cascadeDelete = true;
	    }

    openOptionalPromptModal({
      title: '输入优化提示词（可选）',
      hint: '留空则按默认策略重生成；填写则会作为优化方向参与生成。',
      onConfirm: async (promptText?: string) => {
        setRegeneratingPartKey(String(partNumber));
        try {
          const res = await writerApi.regeneratePartOutline(
            id,
            partNumber,
            { prompt: promptText, cascadeDelete },
            { timeout: 0 }
          );
          setPartProgress(res);
          addToast(`第${partNumber}部分大纲已重生成`, 'success');
          await fetchProject();
          await fetchPartProgress();
        } catch (e) {
          console.error(e);
          addToast('重生成失败', 'error');
        } finally {
          setRegeneratingPartKey(null);
        }
      },
    });
  }, [addToast, fetchPartProgress, fetchProject, id, openOptionalPromptModal, partProgress]);

  const handleGeneratePartChapters = useCallback(async (part: any) => {
    if (!id) return;
    const partNumber = Number(part?.part_number || 0);
    const start = Number(part?.start_chapter || 0);
    const end = Number(part?.end_chapter || 0);
	    if (!partNumber || !start || !end || end < start) {
	      addToast('部分信息不完整，无法生成章节大纲', 'error');
	      return;
	    }

	    const ok = await confirmDialog({
	      title: '生成章节大纲',
	      message: `为第${partNumber}部分生成章节大纲（第${start}-${end}章）？`,
	      confirmText: '生成',
	      dialogType: 'warning',
	    });
	    if (!ok) return;

    const hasExisting = chapterOutlines.some((o: any) => {
      const n = Number(o?.chapter_number || 0);
      return n >= start && n <= end;
    });
	    let regenerate = false;
	    if (hasExisting) {
	      regenerate = await confirmDialog({
	        title: '覆盖确认',
	        message: '检测到该部分范围内已存在章节大纲，是否重新生成并覆盖？\n（不覆盖则仅补齐缺失章节）',
	        confirmText: '重新生成并覆盖',
	        cancelText: '仅补齐缺失',
	        dialogType: 'warning',
	      });
	    }

    setGeneratingPartChapters(partNumber);
    try {
      await writerApi.generatePartChapters(id, partNumber, regenerate, { timeout: 0 });
      addToast(`第${partNumber}部分章节大纲生成完成`, 'success');
      await fetchProject();
      await fetchPartProgress();
    } catch (e) {
      console.error(e);
      addToast('生成失败', 'error');
    } finally {
      setGeneratingPartChapters(null);
    }
  }, [addToast, chapterOutlines, fetchPartProgress, fetchProject, id]);

  useEffect(() => {
    if (id) {
      fetchProject();
    }
  }, [id, fetchProject]);

  useEffect(() => {
    if (id && activeTab === 'outlines') {
      fetchPartProgress();
    }
  }, [id, activeTab, fetchPartProgress]);

  useEffect(() => {
    setCharactersRenderLimit(INITIAL_CHARACTERS_RENDER_LIMIT);
    setRelationshipsRenderLimit(INITIAL_RELATIONSHIPS_RENDER_LIMIT);
    setChapterOutlinesRenderLimit(INITIAL_CHAPTER_OUTLINES_RENDER_LIMIT);
    setPartOutlinesRenderLimit(INITIAL_PART_OUTLINES_RENDER_LIMIT);
    setCompletedChaptersRenderLimit(INITIAL_COMPLETED_CHAPTERS_RENDER_LIMIT);
  }, [id]);

  useEffect(() => {
    if (activeTab === 'characters') {
      setCharactersRenderLimit(INITIAL_CHARACTERS_RENDER_LIMIT);
      return;
    }
    if (activeTab === 'relationships') {
      setRelationshipsRenderLimit(INITIAL_RELATIONSHIPS_RENDER_LIMIT);
      return;
    }
    if (activeTab === 'outlines') {
      setChapterOutlinesRenderLimit(INITIAL_CHAPTER_OUTLINES_RENDER_LIMIT);
      setPartOutlinesRenderLimit(INITIAL_PART_OUTLINES_RENDER_LIMIT);
      return;
    }
    if (activeTab === 'chapters') {
      setCompletedChaptersRenderLimit(INITIAL_COMPLETED_CHAPTERS_RENDER_LIMIT);
    }
  }, [activeTab]);

  useEffect(() => {
    if (activeTab !== 'chapters') return;
    setCompletedChaptersRenderLimit(INITIAL_COMPLETED_CHAPTERS_RENDER_LIMIT);
  }, [activeTab, deferredChaptersSearch]);

  // 章节导入：按编码解码文件内容（避免 Windows TXT 因编码不同出现乱码）
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

  // 已完成章节 Tab：默认选中第一章；若选择的章节被删除则自动回退到第一章
  useEffect(() => {
    if (activeTab !== 'chapters') return;
    if (!completedChapters.length) {
      setSelectedCompletedChapterNumber(null);
      setSelectedCompletedChapter(null);
      return;
    }
    setSelectedCompletedChapterNumber((prev) => {
      if (prev && completedChapters.some((c: any) => Number(c?.chapter_number || 0) === Number(prev))) return prev;
      const first = Number(completedChapters[0]?.chapter_number || 0);
      return first || null;
    });
  }, [activeTab, completedChapters]);

  // 已完成章节 Tab：按需加载正文（避免一次性把所有正文塞进页面）
  useEffect(() => {
    if (activeTab !== 'chapters') return;
    if (!id) return;
    const chapterNo = Number(selectedCompletedChapterNumber || 0);
    if (!chapterNo) {
      setSelectedCompletedChapter(null);
      setSelectedCompletedChapterLoading(false);
      writeBootstrapCache<NovelDetailChapterSelectionSnapshot>(getNovelDetailChapterSelectionKey(id), {
        chapterNumber: null,
        chapterDetail: null,
      });
      return;
    }

    const chapterDetailCache = readBootstrapCache<NovelDetailChapterDetailSnapshot>(
      getNovelDetailChapterDetailKey(id, chapterNo),
      NOVEL_DETAIL_CHAPTER_DETAIL_TTL_MS,
    );
    const hasCachedDetail = Boolean(chapterDetailCache?.chapterDetail);
    if (hasCachedDetail) {
      setSelectedCompletedChapter(chapterDetailCache?.chapterDetail ?? null);
      setSelectedCompletedChapterLoading(false);
      writeBootstrapCache<NovelDetailChapterSelectionSnapshot>(getNovelDetailChapterSelectionKey(id), {
        chapterNumber: chapterNo,
        chapterDetail: chapterDetailCache?.chapterDetail ?? null,
      });
    } else {
      setSelectedCompletedChapterLoading(true);
    }

    let cancelled = false;
    writerApi
      .getChapter(id, chapterNo)
      .then((data) => {
        if (cancelled) return;
        setSelectedCompletedChapter(data);
        writeBootstrapCache<NovelDetailChapterDetailSnapshot>(getNovelDetailChapterDetailKey(id, chapterNo), {
          chapterDetail: data ?? null,
        });
        writeBootstrapCache<NovelDetailChapterSelectionSnapshot>(getNovelDetailChapterSelectionKey(id), {
          chapterNumber: chapterNo,
          chapterDetail: data ?? null,
        });
      })
      .catch((e) => {
        console.error(e);
        if (cancelled) return;
        if (!hasCachedDetail) {
          setSelectedCompletedChapter(null);
        }
      })
      .finally(() => {
        if (cancelled) return;
        setSelectedCompletedChapterLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeTab, id, selectedCompletedChapterNumber]);

  const openImportChapterModal = useCallback(() => {
    const maxOutline = chapterOutlines.length
      ? Math.max(0, ...chapterOutlines.map((o: any) => Number(o?.chapter_number || 0)))
      : 0;
    const fromDb = Array.isArray(project?.chapters)
      ? Math.max(0, ...project.chapters.map((c: any) => Number(c?.chapter_number || 0)))
      : 0;
    const next = Math.max(maxOutline, fromDb) + 1;
    const chapterNo = Math.max(1, Number.isFinite(next) ? next : 1);

    setImportChapterNumber(chapterNo);
    setImportChapterTitle(`第${chapterNo}章`);
    setImportChapterContent('');
    setImportFileName('');
    setImportFileBuffer(null);
    setImportEncoding('utf-8');
    setIsImportChapterModalOpen(true);
  }, [chapterOutlines, project]);

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

  const exportSelectedChapter = useCallback((format: 'txt' | 'markdown') => {
    if (!id) return;
    const chapterNo = Number(selectedCompletedChapterNumber || 0);
    if (!chapterNo) {
      addToast('请先选择章节', 'info');
      return;
    }

    const titleRaw = String(selectedCompletedChapter?.title || `第${chapterNo}章`).trim();
    const filenameTitle = sanitizeFilenamePart(titleRaw ? `第${chapterNo}章_${titleRaw}` : `第${chapterNo}章`);
    const baseTitle = sanitizeFilenamePart(String(project?.title || 'novel').trim()) || 'novel';

    const body = String(selectedCompletedChapter?.content || '').trimEnd();
    const ext = format === 'markdown' ? 'md' : 'txt';
    const prefix = format === 'markdown' ? `# 第${chapterNo}章 ${titleRaw}\n\n` : `第${chapterNo}章  ${titleRaw}\n\n`;
    const text = `${prefix}${body}\n`;

    try {
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${baseTitle}_${filenameTitle || `chapter_${chapterNo}`}.${ext}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      addToast('已导出本章', 'success');
    } catch (e) {
      console.error(e);
      addToast('导出失败', 'error');
    }
  }, [addToast, id, project?.title, selectedCompletedChapter?.content, selectedCompletedChapter?.title, selectedCompletedChapterNumber]);

  const handleEditChar = (index: number) => {
    setEditingCharIndex(index);
    setCharForm({ ...blueprintData.characters[index] });
    setIsCharModalOpen(true);
  };

  const handleAddChar = () => {
    setEditingCharIndex(null); // null means adding
    setCharForm({ name: '', identity: '', personality: '', goal: '', ability: '', background: '', relationship_with_protagonist: '' });
    setIsCharModalOpen(true);
  };

  const handleSaveChar = () => {
    const newChars = [...(blueprintData.characters || [])];
    if (editingCharIndex !== null) {
      newChars[editingCharIndex] = charForm;
    } else {
      newChars.push(charForm);
    }
    setBlueprintData({ ...blueprintData, characters: newChars });
    setIsCharModalOpen(false);
  };

  const handleDeleteChar = async (index: number) => {
    const ok = await confirmDialog({
      title: '删除角色',
      message: '确定要删除这个角色吗？',
      confirmText: '删除',
      dialogType: 'danger',
    });
    if (!ok) return;
    const newChars = [...blueprintData.characters];
    newChars.splice(index, 1);
    setBlueprintData({ ...blueprintData, characters: newChars });
  };

  const handleAddRel = () => {
    setEditingRelIndex(null);
    setRelForm({ character_from: '', character_to: '', description: '' });
    setIsRelModalOpen(true);
  };

  const handleEditRel = (index: number) => {
    const list = Array.isArray(blueprintData.relationships) ? blueprintData.relationships : [];
    const rel = list[index];
    if (!rel) return;
    setEditingRelIndex(index);
    setRelForm({
      character_from: String(rel.character_from || ''),
      character_to: String(rel.character_to || ''),
      description: String(rel.description || ''),
    });
    setIsRelModalOpen(true);
  };

  const handleSaveRel = () => {
    const from = relForm.character_from.trim();
    const to = relForm.character_to.trim();
    const description = relForm.description.trim();
    if (!from || !to) {
      addToast('请输入关系双方角色名', 'error');
      return;
    }

    const list = [...(Array.isArray(blueprintData.relationships) ? blueprintData.relationships : [])];
    const item = { character_from: from, character_to: to, description };
    if (editingRelIndex !== null) {
      list[editingRelIndex] = item;
    } else {
      list.push(item);
    }
    setBlueprintData({ ...blueprintData, relationships: list });
    setIsRelModalOpen(false);
  };

  const handleDeleteRel = async (index: number) => {
    const list = Array.isArray(blueprintData.relationships) ? blueprintData.relationships : [];
    const rel = list[index];
    if (!rel) return;
    const label = `${rel.character_from || ''} → ${rel.character_to || ''}`;
    const ok = await confirmDialog({
      title: '删除关系',
      message: `确定要删除该关系吗？\n${label}`,
      confirmText: '删除',
      dialogType: 'danger',
    });
    if (!ok) return;
    const next = list.filter((_: any, i: number) => i !== index);
    setBlueprintData({ ...blueprintData, relationships: next });
  };

  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!isBlueprintDirty) return;
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [isBlueprintDirty]);

  if (loading) return <div className="flex h-screen items-center justify-center text-book-text-muted">加载中...</div>;
  if (!project) return <div className="flex h-screen items-center justify-center text-book-text-muted">项目不存在</div>;

  return (
    <div className="min-h-screen bg-book-bg flex flex-col">
	      {/* Header - 完全照抄桌面端 novel_detail/mixins/header_manager.py */}
	      <div className="h-[100px] border-b border-book-border bg-book-bg-paper flex items-center justify-between px-6 sticky top-0 z-20">
	        {/* 左侧：项目图标 + 信息 */}
	        <div className="flex items-center gap-4">
	          {/* 项目图标 64x64 */}
		          <button
	              type="button"
	              onClick={async () => {
	                if (avatarLoading) return;
	                if (!project?.blueprint) {
	                  addToast('请先生成蓝图后再生成头像', 'error');
	                  return;
	                }
	                if (blueprintData?.avatar_svg) {
	                  const ok = await confirmDialog({
	                    title: '重新生成头像',
	                    message: '确定要重新生成头像吗？\n当前头像将被替换。',
	                    confirmText: '重新生成',
	                    dialogType: 'warning',
	                  });
	                  if (!ok) return;
	                }
	                handleGenerateAvatar();
	              }}
              disabled={avatarLoading}
              className="w-16 h-16 rounded border-2 border-book-primary flex items-center justify-center shrink-0 hover:border-book-primary/70 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              title={blueprintData?.avatar_svg ? '点击重新生成头像' : '点击生成小说头像'}
            >
	            {blueprintData?.avatar_svg ? (
	              <div
	                className="w-full h-full"
	                dangerouslySetInnerHTML={{ __html: String(blueprintData.avatar_svg) }}
	              />
	            ) : (
	              <span className="text-3xl font-bold text-book-text-main">
                  {String(project?.title || 'B').trim().slice(0, 1) || 'B'}
                </span>
	            )}
	          </button>

	          {/* 项目信息 */}
	          <div className="flex flex-col gap-1">
	            {/* 标题行 */}
	            <div className="flex items-center gap-2">
	              <h1 className="font-serif font-bold text-[28px] text-book-text-main tracking-wide">{project.title}</h1>
	              <button
	                className="text-xs text-book-text-sub underline hover:text-book-primary"
	                onClick={openEditTitleModal}
	              >
	                编辑
	              </button>
                {blueprintData?.avatar_svg ? (
                  <button
                    className="text-xs text-book-text-sub underline hover:text-red-600 disabled:opacity-50"
                    onClick={handleDeleteAvatar}
                    disabled={avatarLoading}
                    title="删除当前小说头像"
                  >
                    删除头像
                  </button>
                ) : null}
	            </div>
	            {/* 元信息行：类型 + 状态 */}
	            <div className="flex items-center gap-2 text-xs">
	              <span className="px-2 py-0.5 border border-book-border rounded text-book-text-sub">
	                {blueprintData.genre || '未分类'}
	              </span>
	              <span className="px-2 py-0.5 border border-book-border rounded text-book-text-sub italic">
	                {project.status}
	              </span>
	            </div>
	          </div>
	        </div>

	        {/* 右侧操作按钮 - 完全照抄桌面端：保存、返回写作台、导出、RAG同步、优化蓝图、开始创作 */}
	        <div className="flex items-center gap-3">
	          <BookButton
              variant={isBlueprintDirty ? 'primary' : 'secondary'}
              size="sm"
              onClick={handleSave}
              disabled={saving || Boolean(worldSettingError)}
              title={
                worldSettingError
                  ? '世界观 JSON 无效：请先修正再保存'
                  : (isBlueprintDirty ? (dirtySummary || '有未保存的修改') : '保存蓝图')
              }
            >
	            {saving ? '保存中...' : (isBlueprintDirty ? '保存*' : '保存')}
	          </BookButton>
	          <BookButton variant="secondary" size="sm" onClick={() => safeNavigate(`/write/${id}`)}>
	            返回写作台
	          </BookButton>
	          <BookButton variant="secondary" size="sm" onClick={handleExport}>
	            导出
	          </BookButton>
	          <BookButton
	            variant="secondary"
	            size="sm"
	            onClick={handleRagSync}
	            disabled={ragSyncing}
	            title="同步项目到向量库"
	          >
	            {ragSyncing ? 'RAG同步中…' : 'RAG同步'}
	          </BookButton>
	          <BookButton variant="secondary" size="sm" onClick={openRefineModal}>
	            优化蓝图
	          </BookButton>
	          <BookButton variant="primary" size="sm" onClick={() => safeNavigate(`/write/${id}`)}>
	            开始创作
	          </BookButton>
	        </div>
      </div>

      {/* Tabs - 照抄桌面端 novel_detail/mixins/tab_manager.py */}
      <div className="border-b border-book-border/40 bg-book-bg-paper px-8">
        <div className="flex gap-8">
            {[
              { id: 'overview', label: '概览', icon: FileText },
            { id: 'world', label: '世界观', icon: MapIcon },
            { id: 'characters', label: '角色', icon: Users },
            { id: 'relationships', label: '关系', icon: Link2 },
            { id: 'outlines', label: '章节大纲', icon: Share },
            { id: 'chapters', label: '已生成章节', icon: FileText },
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`
                  flex items-center gap-2 py-4 text-sm font-bold transition-all relative
                  ${isActive ? 'text-book-primary' : 'text-book-text-sub hover:text-book-text-main'}
                `}
              >
                <Icon size={16} />
                {tab.label}
                {isActive && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-book-primary rounded-t-full" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-8 max-w-5xl mx-auto w-full custom-scrollbar">
        {activeTab === 'overview' && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <div className="grid grid-cols-3 gap-6">
              <div className="col-span-2 space-y-6">
                <BookCard className="p-6 space-y-4">
                  <h3 className="font-serif font-bold text-lg text-book-text-main border-b border-book-border/40 pb-2">
                    一句话梗概
                  </h3>
                  <BookTextarea 
                    value={blueprintData.one_sentence_summary || ''}
                    onChange={(e) => setBlueprintData({...blueprintData, one_sentence_summary: e.target.value})}
                    className="min-h-[80px] text-base font-serif leading-relaxed"
                  />
                </BookCard>

                <BookCard className="p-6 space-y-4">
                  <h3 className="font-serif font-bold text-lg text-book-text-main border-b border-book-border/40 pb-2">
                    故事全貌
                  </h3>
                  <BookTextarea 
                    value={blueprintData.full_synopsis || ''}
                    onChange={(e) => setBlueprintData({...blueprintData, full_synopsis: e.target.value})}
                    className="min-h-[300px] text-base font-serif leading-relaxed"
                  />
                </BookCard>
              </div>

              <div className="space-y-6">
                {project?.is_imported && (
                  <BookCard className="p-5 space-y-4">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="font-bold text-sm text-book-text-main">导入分析</h3>
                      <div className="flex items-center gap-2">
                        {(() => {
                          const status = String(importStatus?.status || project.import_analysis_status || 'pending');
                          const canStart = status !== 'completed' && status !== 'analyzing';
                          if (!canStart) return null;
                          const isResume = status === 'failed' || status === 'cancelled';
                          return (
                            <button
                              onClick={startImportAnalysis}
                              className="text-xs text-book-primary font-bold hover:underline disabled:opacity-50"
                              disabled={importStatusLoading || importStarting}
                              title={isResume ? '继续导入分析（从断点尝试恢复）' : '开始导入分析'}
                            >
                              {importStarting ? '启动中…' : (isResume ? '继续分析' : '开始分析')}
                            </button>
                          );
                        })()}
                        <button
                          onClick={refreshImportStatus}
                          className="text-xs text-book-primary font-bold hover:underline"
                          disabled={importStatusLoading}
                        >
                          {importStatusLoading ? '刷新中…' : '刷新'}
                        </button>
                        {importStatus?.status === 'analyzing' && (
                          <button
                            onClick={cancelImportAnalysis}
                            className="text-xs text-red-600 font-bold hover:underline"
                            disabled={importStatusLoading}
                          >
                            取消
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="text-xs text-book-text-muted">
                      状态：{importStatusLoading ? '加载中…' : (importStatus?.status || project.import_analysis_status || 'pending')}
                    </div>

                    <div className="space-y-2">
                      <div className="h-2 rounded bg-book-bg border border-book-border/40 overflow-hidden">
                        <div
                          className="h-full bg-book-primary"
                          style={{ width: `${Math.max(0, Math.min(100, Number(importStatus?.progress?.overall_progress || 0)))}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-book-text-muted">
                        <span>{String(importStatus?.progress?.message || '等待开始分析')}</span>
                        <span>{Number(importStatus?.progress?.overall_progress || 0)}%</span>
                      </div>
                    </div>

                    {importStatus?.progress?.stages && (
                      <div className="space-y-2">
                        <div className="text-xs font-bold text-book-text-sub">阶段</div>
                        <div className="space-y-2">
                          {Object.entries(importStatus.progress.stages as Record<string, any>).slice(0, 6).map(([k, v]) => (
                            <div key={k} className="text-[11px] text-book-text-muted flex items-center justify-between gap-2">
                              <span className="truncate">
                                {String(v.name || k)}{v.status === 'in_progress' ? '（进行中）' : ''}
                              </span>
                              <span className="font-mono">
                                {Number(v.completed || 0)}/{Number(v.total || 0)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </BookCard>
                )}

                <BookCard className="p-5 space-y-4 sticky top-4">
                  <h3 className="font-bold text-sm text-book-text-main">基础设定</h3>
                  <div className="space-y-3">
                    <BookInput 
                      label="作品类型" 
                      value={blueprintData.genre || ''}
                      onChange={(e) => setBlueprintData({...blueprintData, genre: e.target.value})}
                    />
                    <BookInput 
                      label="目标读者" 
                      value={blueprintData.target_audience || ''}
                      onChange={(e) => setBlueprintData({...blueprintData, target_audience: e.target.value})}
                    />
                    <BookInput 
                      label="叙事风格" 
                      value={blueprintData.style || ''}
                      onChange={(e) => setBlueprintData({...blueprintData, style: e.target.value})}
                    />
                    <BookInput 
                      label="情感基调" 
                      value={blueprintData.tone || ''}
                      onChange={(e) => setBlueprintData({...blueprintData, tone: e.target.value})}
                    />
                  </div>
                </BookCard>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'world' && (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 space-y-6">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-serif font-bold text-lg text-book-text-main">世界观设定</h3>
              <div className="flex items-center gap-2">
                <BookButton
                  size="sm"
                  variant={worldEditMode === 'structured' ? 'primary' : 'ghost'}
                  onClick={() => setWorldEditMode('structured')}
                >
                  结构化
                </BookButton>
                <BookButton
                  size="sm"
                  variant={worldEditMode === 'json' ? 'primary' : 'ghost'}
                  onClick={() => setWorldEditMode('json')}
                >
                  JSON
                </BookButton>
              </div>
            </div>

            {worldEditMode === 'structured' ? (
              worldSettingObj ? (
                <>
                  <BookCard className="p-6 space-y-4">
                    <h4 className="font-serif font-bold text-base text-book-text-main border-b border-book-border/40 pb-2">
                      核心规则
                    </h4>
                    <BookTextarea
                      value={String(worldSettingObj.core_rules || '')}
                      onChange={(e) => updateWorldSettingDraft((obj) => { obj.core_rules = e.target.value; })}
                      className="min-h-[140px] text-base font-serif leading-relaxed"
                      placeholder="例如：魔法来源/限制、社会规则、科技水平、禁忌与代价…"
                    />
                  </BookCard>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <BookCard className="p-6 space-y-4">
                      <h4 className="font-serif font-bold text-base text-book-text-main border-b border-book-border/40 pb-2">
                        关键地点
                      </h4>
                      <div className="text-xs text-book-text-muted">
                        每行一条；可写“名称｜描述”（支持中文竖线或英文 |）。
                      </div>
                      <BookTextarea
                        value={worldListToText(worldSettingObj.key_locations)}
                        onChange={(e) => updateWorldSettingDraft((obj) => { obj.key_locations = worldTextToList(e.target.value); })}
                        className="min-h-[220px] text-sm font-mono leading-relaxed"
                        placeholder="王都｜政治中心，暗流涌动\n灰港｜走私与情报交易之城\n禁林"
                      />
                    </BookCard>

                    <BookCard className="p-6 space-y-4">
                      <h4 className="font-serif font-bold text-base text-book-text-main border-b border-book-border/40 pb-2">
                        主要阵营
                      </h4>
                      <div className="text-xs text-book-text-muted">
                        每行一条；可写“名称｜描述”（支持中文竖线或英文 |）。
                      </div>
                      <BookTextarea
                        value={worldListToText(worldSettingObj.factions)}
                        onChange={(e) => updateWorldSettingDraft((obj) => { obj.factions = worldTextToList(e.target.value); })}
                        className="min-h-[220px] text-sm font-mono leading-relaxed"
                        placeholder="学院派｜重视秩序与传承\n流亡者｜被放逐的旧贵族残党"
                      />
                    </BookCard>
                  </div>

                  <div className="text-xs text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30 p-4 leading-relaxed">
                    提示：结构化编辑只覆盖常用字段（core_rules/key_locations/factions）。如需编辑更多字段，可切换到 JSON 模式。
                  </div>
                </>
              ) : (
                <BookCard className="p-6 space-y-3">
                  <div className="font-bold text-book-text-main">世界观 JSON 无效</div>
                  <div className="text-sm text-book-text-muted leading-relaxed">
                    当前 world_setting 不是合法 JSON 对象，无法进行结构化编辑。请先切换到 JSON 模式修复格式。
                  </div>
                  <div className="flex justify-end">
                    <BookButton size="sm" variant="primary" onClick={() => setWorldEditMode('json')}>
                      切到 JSON
                    </BookButton>
                  </div>
                </BookCard>
              )
            ) : (
              <BookCard className="p-6 space-y-4">
                <h4 className="font-serif font-bold text-base text-book-text-main border-b border-book-border/40 pb-2">
                  JSON（高级）
                </h4>
                <BookTextarea 
                  value={worldSettingDraft}
                  onChange={(e) => setWorldSettingDraft(e.target.value)}
                  error={worldSettingError || undefined}
                  className="min-h-[520px] text-sm font-mono leading-relaxed"
                  placeholder="请输入 JSON 对象（保存时会合并更新 world_setting）"
                />
              </BookCard>
            )}
          </div>
        )}

        {activeTab === 'characters' && (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 space-y-6">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <h3 className="font-serif font-bold text-lg text-book-text-main">
                  主要角色 ({charactersList.length})
                </h3>
                <div className="flex items-center gap-1 bg-book-bg-paper rounded-lg border border-book-border/40 p-1">
                  <button
                    className={`px-3 py-1 text-xs font-bold rounded-md transition-colors ${
                      charactersView === 'info' ? 'bg-book-bg text-book-primary' : 'text-book-text-muted hover:text-book-text-main'
                    }`}
                    onClick={() => setCharactersView('info')}
                  >
                    基本信息
                  </button>
                  <button
                    className={`px-3 py-1 text-xs font-bold rounded-md transition-colors ${
                      charactersView === 'portraits' ? 'bg-book-bg text-book-primary' : 'text-book-text-muted hover:text-book-text-main'
                    }`}
                    onClick={() => setCharactersView('portraits')}
                  >
                    角色立绘
                  </button>
                </div>
              </div>

              {charactersView === 'info' && (
                <BookButton size="sm" onClick={handleAddChar}>
                  <Plus size={16} className="mr-1" /> 添加角色
                </BookButton>
              )}
            </div>

            {charactersView === 'portraits' ? (
              <Suspense fallback={<div className="text-sm text-book-text-muted">角色立绘加载中…</div>}>
                <CharacterPortraitGalleryLazy
                  projectId={id!}
                  characterNames={characterNames}
                  characterProfiles={characterProfiles}
                />
              </Suspense>
            ) : (
              <>
                {charactersList.length > 0 ? (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {visibleCharacters.map((char: any, idx: number) => (
                        <BookCard key={idx} className="p-5 hover:shadow-md transition-shadow group relative">
                          <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                            <button onClick={() => handleEditChar(idx)} className="p-1.5 rounded-full bg-book-bg hover:text-book-primary">
                              <FileText size={14} />
                            </button>
                            <button onClick={() => handleDeleteChar(idx)} className="p-1.5 rounded-full bg-book-bg hover:text-red-500">
                              <Trash2 size={14} />
                            </button>
                          </div>

                          <div className="flex justify-between items-start mb-3 border-b border-book-border/30 pb-2">
                            <h4 className="font-serif font-bold text-lg text-book-text-main truncate">{char.name || '（未命名）'}</h4>
                            {char.identity ? (
                              <span className="text-xs bg-book-bg px-2 py-1 rounded text-book-text-sub">{char.identity}</span>
                            ) : null}
                          </div>
                          <div className="space-y-2 text-sm text-book-text-secondary">
                            {char.personality ? (
                              <p className="line-clamp-2"><span className="font-bold text-book-text-muted">性格：</span>{char.personality}</p>
                            ) : null}
                            {char.goal ? (
                              <p className="line-clamp-2"><span className="font-bold text-book-text-muted">目标：</span>{char.goal}</p>
                            ) : null}
                            {char.ability ? (
                              <p className="line-clamp-2"><span className="font-bold text-book-text-muted">能力：</span>{char.ability}</p>
                            ) : null}
                          </div>
                        </BookCard>
                      ))}
                    </div>

                    {remainingCharacters > 0 ? (
                      <div className="flex justify-center">
                        <BookButton
                          size="sm"
                          variant="ghost"
                          onClick={() => setCharactersRenderLimit((prev) => prev + CHARACTERS_RENDER_BATCH_SIZE)}
                        >
                          加载更多角色（剩余 {remainingCharacters}）
                        </BookButton>
                      </div>
                    ) : null}
                  </>
                ) : (
                  <div className="text-center py-20 text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30">
                    <Users size={48} className="mx-auto mb-4 opacity-50" />
                    <p>尚未添加角色。你可以点击右上角“添加角色”。</p>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'relationships' && (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-serif font-bold text-lg text-book-text-main">
                关系网 ({relationshipsList.length})
              </h3>
              <BookButton size="sm" onClick={handleAddRel}>
                <Plus size={16} className="mr-1" /> 添加关系
              </BookButton>
            </div>

            {relationshipsList.length > 0 ? (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {visibleRelationships.map((rel: any, idx: number) => (
                    <BookCard key={idx} className="p-5 hover:shadow-md transition-shadow group relative">
                      <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                        <button onClick={() => handleEditRel(idx)} className="p-1.5 rounded-full bg-book-bg hover:text-book-primary">
                          <FileText size={14} />
                        </button>
                        <button onClick={() => handleDeleteRel(idx)} className="p-1.5 rounded-full bg-book-bg hover:text-red-500">
                          <Trash2 size={14} />
                        </button>
                      </div>

                      <div className="flex items-center gap-2 font-bold text-book-text-main">
                        <span className="truncate">{rel.character_from}</span>
                        <span className="text-book-text-muted">→</span>
                        <span className="truncate">{rel.character_to}</span>
                      </div>
                      <div className="mt-2 text-sm text-book-text-secondary whitespace-pre-wrap leading-relaxed">
                        {rel.description || '（无描述）'}
                      </div>
                    </BookCard>
                  ))}
                </div>

                {remainingRelationships > 0 ? (
                  <div className="flex justify-center">
                    <BookButton
                      size="sm"
                      variant="ghost"
                      onClick={() => setRelationshipsRenderLimit((prev) => prev + RELATIONSHIPS_RENDER_BATCH_SIZE)}
                    >
                      加载更多关系（剩余 {remainingRelationships}）
                    </BookButton>
                  </div>
                ) : null}
              </>
            ) : (
              <div className="text-center py-20 text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30">
                <Link2 size={48} className="mx-auto mb-4 opacity-50" />
                <p>尚未添加角色关系。你可以先从“角色”里补齐人物，再在此建立关系网。</p>
              </div>
            )}
          </div>
        )}
        
	        {activeTab === 'outlines' && (
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
                  <BookButton size="sm" variant="ghost" onClick={() => safeNavigate(`/write/${id}`)}>
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
                          onClick={() => safeNavigate(`/write/${id}?chapter=${chapterNumber}`)}
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
                                  safeNavigate(`/write/${id}?chapter=${chapterNumber}`);
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
                        onClick={() => setChapterOutlinesRenderLimit((prev) => prev + CHAPTER_OUTLINES_RENDER_BATCH_SIZE)}
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
                      onClick={() => safeNavigate(`/write/${id}`)}
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
                        onClick={() => setPartOutlinesRenderLimit((prev) => prev + PART_OUTLINES_RENDER_BATCH_SIZE)}
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
	        )}

	        {activeTab === 'chapters' && (
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
		                        onClick={() => setCompletedChaptersRenderLimit((prev) => prev + COMPLETED_CHAPTERS_RENDER_BATCH_SIZE)}
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
	                  <BookButton variant="primary" size="sm" onClick={() => safeNavigate(`/write/${id}`)}>
	                    <Play size={16} className="mr-2 fill-current" />
	                    前往写作台
	                  </BookButton>
	                </div>
	              </div>
	            )}
	          </div>
	        )}
	      </div>

	      {/* Import Chapter（项目详情 -> 章节 Tab） */}
	      <input
	        ref={importFileInputRef}
	        type="file"
	        accept=".txt,.md,text/plain,text/markdown"
	        style={{ display: 'none' }}
	        onChange={onImportFileChange}
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
	                  await fetchProject();
	                  setActiveTab('chapters');
	                  setSelectedCompletedChapterNumber(chapterNo);
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
	                title="若文件乱码，请切换为 GB18030（部分浏览器可能不支持）"
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

	      {/* Optional Prompt Modal（用于“重生成”类操作的可选优化提示词） */}
	      <Modal
	        isOpen={isPromptModalOpen}
	        onClose={() => {
          pendingPromptActionRef.current = null;
          setIsPromptModalOpen(false);
        }}
        title={promptModalTitle}
        maxWidthClassName="max-w-2xl"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton
              variant="ghost"
              onClick={() => {
                pendingPromptActionRef.current = null;
                setIsPromptModalOpen(false);
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
          {promptModalHint ? (
            <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
              {promptModalHint}
            </div>
          ) : null}
          <BookTextarea
            label="优化提示词（可选）"
            value={promptModalValue}
            onChange={(e) => setPromptModalValue(e.target.value)}
            rows={6}
            placeholder="例如：加强伏笔回收、提升冲突强度、强化人物动机、优化节奏…"
          />
        </div>
      </Modal>

      {/* Blueprint Refine Modal */}
      <Modal
        isOpen={isRefineModalOpen}
        onClose={() => setIsRefineModalOpen(false)}
        title="优化蓝图"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={() => setIsRefineModalOpen(false)}>关闭</BookButton>
            <BookButton
              variant="primary"
              onClick={handleRefineBlueprint}
              disabled={refining || !refineInstruction.trim()}
            >
              {refining ? '优化中...' : '开始优化'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
            说明：优化蓝图会重置已生成的章节大纲、章节内容以及向量库等后续数据。建议先导出/备份再执行。
          </div>

          <BookTextarea
            label="优化指令"
            value={refineInstruction}
            onChange={(e) => setRefineInstruction(e.target.value)}
            rows={6}
            placeholder="例如：把世界观从现代都市改为架空蒸汽朋克，并强化主角动机与成长线…"
          />

          <label className="flex items-center gap-2 text-sm text-book-text-main">
            <input
              type="checkbox"
              className="rounded border-book-border text-book-primary focus:ring-book-primary"
              checked={refineForce}
              onChange={(e) => setRefineForce(e.target.checked)}
            />
            <span className="font-bold">强制优化（存在后续数据时也继续）</span>
          </label>

          {refineResult && (
            <BookCard className="p-4">
              <div className="text-xs text-book-text-muted mb-2">AI 说明</div>
              <div className="text-sm text-book-text-main whitespace-pre-wrap leading-relaxed">
                {refineResult}
              </div>
            </BookCard>
          )}
        </div>
      </Modal>

      {/* Character Edit Modal */}
      <Modal
        isOpen={isCharModalOpen}
        onClose={() => setIsCharModalOpen(false)}
        title={editingCharIndex !== null ? "编辑角色" : "添加新角色"}
        footer={
            <div className="flex justify-end gap-2">
                <BookButton variant="ghost" onClick={() => setIsCharModalOpen(false)}>取消</BookButton>
                <BookButton variant="primary" onClick={handleSaveChar}>保存</BookButton>
            </div>
        }
      >
        <div className="space-y-4">
            <BookInput 
                label="姓名" 
                value={charForm.name || ''} 
                onChange={e => setCharForm({...charForm, name: e.target.value})}
            />
            <BookInput 
                label="身份" 
                value={charForm.identity || ''} 
                onChange={e => setCharForm({...charForm, identity: e.target.value})}
            />
            <BookTextarea 
                label="性格特征" 
                value={charForm.personality || ''} 
                onChange={e => setCharForm({...charForm, personality: e.target.value})}
            />
            <BookTextarea 
                label="目标与动机" 
                value={charForm.goal || ''} 
                onChange={e => setCharForm({...charForm, goal: e.target.value})}
            />
            <BookTextarea
                label="能力（可选）"
                value={charForm.ability || ''}
                onChange={e => setCharForm({...charForm, ability: e.target.value})}
                rows={3}
                placeholder="例如：剑术、推理、黑客技能、魔法天赋…"
            />
            <BookTextarea
                label="背景（可选）"
                value={charForm.background || ''}
                onChange={e => setCharForm({...charForm, background: e.target.value})}
                rows={4}
                placeholder="例如：出身、经历、创伤、转折点…"
            />
            <BookTextarea
                label="与主角关系（可选）"
                value={charForm.relationship_with_protagonist || ''}
                onChange={e => setCharForm({...charForm, relationship_with_protagonist: e.target.value})}
                rows={3}
                placeholder="例如：盟友/对手/师徒/亲属/互相利用…"
            />
        </div>
      </Modal>

      {/* Edit Title Modal（对齐桌面端：编辑项目标题） */}
      <Modal
        isOpen={isEditTitleModalOpen}
        onClose={() => {
          if (editTitleSaving) return;
          setIsEditTitleModalOpen(false);
        }}
        title="编辑项目标题"
        maxWidthClassName="max-w-lg"
        footer={
          <>
            <BookButton
              variant="ghost"
              onClick={() => setIsEditTitleModalOpen(false)}
              disabled={editTitleSaving}
            >
              取消
            </BookButton>
            <BookButton
              variant="primary"
              onClick={saveProjectTitle}
              disabled={editTitleSaving || !editTitleValue.trim()}
            >
              {editTitleSaving ? '保存中…' : '保存'}
            </BookButton>
          </>
        }
      >
        <div className="space-y-4">
          <BookInput
            label="标题"
            value={editTitleValue}
            onChange={(e) => setEditTitleValue(e.target.value)}
            placeholder="请输入新标题"
            autoFocus
          />
          <div className="text-xs text-book-text-muted">
            提示：标题为项目基本信息（与蓝图字段独立）。桌面端同款入口位于标题旁“编辑”按钮。
          </div>
        </div>
      </Modal>

      {/* Relationship Edit Modal */}
      <Modal
        isOpen={isRelModalOpen}
        onClose={() => setIsRelModalOpen(false)}
        title={editingRelIndex !== null ? '编辑关系' : '添加关系'}
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={() => setIsRelModalOpen(false)}>取消</BookButton>
            <BookButton variant="primary" onClick={handleSaveRel}>保存</BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <datalist id="novel-character-names">
            {characterNames.map((n) => (
              <option key={`c-${n}`} value={n} />
            ))}
          </datalist>

          <BookInput
            label="角色A"
            value={relForm.character_from}
            onChange={(e) => setRelForm({ ...relForm, character_from: e.target.value })}
            placeholder="例如：林远"
            list="novel-character-names"
          />
          <BookInput
            label="角色B"
            value={relForm.character_to}
            onChange={(e) => setRelForm({ ...relForm, character_to: e.target.value })}
            placeholder="例如：苏鸢"
            list="novel-character-names"
          />
          <BookTextarea
            label="关系描述"
            value={relForm.description}
            onChange={(e) => setRelForm({ ...relForm, description: e.target.value })}
            rows={4}
            placeholder="例如：青梅竹马，因一次误会渐行渐远…"
          />
        </div>
      </Modal>

      {/* Chapter Outline Modals */}
      {isOutlineModalOpen ? (
        <Suspense fallback={null}>
          <OutlineEditModalLazy
            isOpen={isOutlineModalOpen}
            onClose={() => setIsOutlineModalOpen(false)}
            chapter={editingChapter}
            projectId={id!}
            onSuccess={() => {
              fetchProject();
            }}
          />
        </Suspense>
      ) : null}

      {isBatchModalOpen ? (
        <Suspense fallback={null}>
          <BatchGenerateModalLazy
            isOpen={isBatchModalOpen}
            onClose={() => setIsBatchModalOpen(false)}
            projectId={id!}
            onSuccess={() => {
              fetchProject();
            }}
          />
        </Suspense>
      ) : null}

      {isProtagonistModalOpen ? (
        <Suspense fallback={null}>
          <ProtagonistProfilesModalLazy
            isOpen={isProtagonistModalOpen}
            onClose={() => setIsProtagonistModalOpen(false)}
            projectId={id!}
            currentChapterNumber={latestChapterNumber}
          />
        </Suspense>
      ) : null}

      {isPartGenerateModalOpen ? (
        <Suspense fallback={null}>
          <PartOutlineGenerateModalLazy
            isOpen={isPartGenerateModalOpen}
            onClose={() => setIsPartGenerateModalOpen(false)}
            projectId={id!}
            mode={partGenerateMode}
            totalChapters={Math.max(10, partTotalChapters || 10)}
            defaultChaptersPerPart={Number(blueprintData?.chapters_per_part || 25) || 25}
            currentCoveredChapters={partCoveredChapters || undefined}
            currentPartsCount={partOutlines.length || undefined}
            onSuccess={async () => {
              await fetchProject();
              await fetchPartProgress();
            }}
          />
        </Suspense>
      ) : null}

      {detailPart ? (
        <Suspense fallback={null}>
          <PartOutlineDetailModalLazy
            isOpen={Boolean(detailPart)}
            onClose={() => setDetailPart(null)}
            part={detailPart}
          />
        </Suspense>
      ) : null}

      <Modal
        isOpen={isDeleteLatestPartsModalOpen}
        onClose={() => setIsDeleteLatestPartsModalOpen(false)}
        title="删除最新部分大纲"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton
              variant="ghost"
              onClick={() => setIsDeleteLatestPartsModalOpen(false)}
              disabled={deletingLatestParts}
            >
              取消
            </BookButton>
            <BookButton
              variant="primary"
              onClick={async () => {
                if (!id) return;
	                if (maxDeletablePartCount <= 0) {
	                  addToast('至少需要保留 1 个部分大纲，当前无法删除', 'error');
	                  return;
	                }
	                const count = Math.max(1, Math.min(Number(deleteLatestPartsCount) || 1, maxDeletablePartCount));
	                const ok = await confirmDialog({
	                  title: '删除最新部分大纲',
	                  message:
	                    `确定要删除最后 ${count} 个部分大纲吗？\n\n` +
	                    `这些部分对应的章节大纲也会被一起删除。\n` +
	                    `此操作不可恢复。`,
	                  confirmText: '删除',
	                  dialogType: 'danger',
	                });
	                if (!ok) return;
                setDeletingLatestParts(true);
                try {
                  const result = await writerApi.deleteLatestPartOutlines(id, count);
                  addToast(result?.message || `已删除最后 ${count} 个部分大纲`, 'success');
                  setIsDeleteLatestPartsModalOpen(false);
                  await fetchProject();
                  await fetchPartProgress();
                } catch (e) {
                  console.error(e);
                  addToast('删除失败', 'error');
                } finally {
                  setDeletingLatestParts(false);
                }
              }}
              disabled={deletingLatestParts || maxDeletablePartCount <= 0}
            >
              {deletingLatestParts ? '删除中…' : '删除'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
            删除会从“最后一个部分”开始回退，并按“串行生成原则”级联删除对应范围的章节大纲。后端禁止删除全部部分大纲（至少保留 1 个部分）。
          </div>
          <BookInput
            label={`删除数量（1-${Math.max(1, maxDeletablePartCount)})`}
            type="number"
            min={1}
            max={Math.max(1, maxDeletablePartCount)}
            value={deleteLatestPartsCount}
            onChange={(e) => setDeleteLatestPartsCount(parseInt(e.target.value, 10) || 1)}
            disabled={deletingLatestParts || maxDeletablePartCount <= 0}
          />
        </div>
      </Modal>

      <Modal
        isOpen={isRegenerateLatestPartsModalOpen}
        onClose={() => setIsRegenerateLatestPartsModalOpen(false)}
        title="重生成最新部分大纲"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton
              variant="ghost"
              onClick={() => setIsRegenerateLatestPartsModalOpen(false)}
              disabled={regeneratingLatestParts}
            >
              取消
            </BookButton>
            <BookButton
              variant="primary"
              onClick={async () => {
                if (!id) return;
                if (!partOutlines.length) return;

                const sorted = [...partOutlines].sort(
                  (a: any, b: any) => Number(a?.part_number || 0) - Number(b?.part_number || 0),
                );
                const maxCount = sorted.length;
                const count = Math.max(1, Math.min(Number(regenerateLatestPartsCount) || 1, maxCount));
                const lastN = sorted.slice(-count);
                const start = Number(lastN[0]?.part_number || 0);
                const end = Number(lastN[lastN.length - 1]?.part_number || 0);
                if (!start || !end || end < start) {
                  addToast('部分大纲数据异常，无法重生成', 'error');
                  return;
                }

	                const ok = await confirmDialog({
	                  title: '重生成最新部分大纲',
	                  message:
	                    `将重生成最后 ${count} 个部分大纲（第${start}-${end}部分）。\n\n` +
	                    `串行生成原则：会级联删除第${start + 1}-${end}部分的大纲，以及对应章节大纲/内容/向量数据。\n\n` +
	                    `确定继续？`,
	                  confirmText: '继续',
	                  dialogType: 'danger',
	                });
	                if (!ok) return;

                setRegeneratingLatestParts(true);
                try {
                  const promptText = regenerateLatestPartsPrompt.trim() || undefined;
                  const result = await writerApi.regeneratePartOutline(
                    id,
                    start,
                    { prompt: promptText, cascadeDelete: true },
                    { timeout: 0 },
                  );
                  addToast(result?.message || `第${start}部分大纲已重生成`, 'success');
                  if (result?.cascade_deleted?.message) addToast(String(result.cascade_deleted.message), 'info');
                  setIsRegenerateLatestPartsModalOpen(false);
                  setRegenerateLatestPartsPrompt('');
                  await Promise.allSettled([fetchProject(), fetchPartProgress()]);
                } catch (e) {
                  console.error(e);
                  addToast('重生成失败', 'error');
                } finally {
                  setRegeneratingLatestParts(false);
                }
              }}
              disabled={regeneratingLatestParts || !partOutlines.length}
            >
              {regeneratingLatestParts ? '重生成中…' : '重生成'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
            说明：该操作等价于桌面端“重新生成最新 N 个部分大纲”。实现方式为：从“最后 N 个部分”中找到最早的那一部分，重生成该部分大纲，并按串行原则级联删除后续部分与对应章节大纲/内容/向量数据。
          </div>

          <BookInput
            label={`重生成数量（1-${Math.max(1, partOutlines.length)})`}
            type="number"
            min={1}
            max={Math.max(1, partOutlines.length)}
            value={regenerateLatestPartsCount}
            onChange={(e) => setRegenerateLatestPartsCount(parseInt(e.target.value, 10) || 1)}
            disabled={regeneratingLatestParts}
          />

          <BookTextarea
            label="优化提示词（可选）"
            value={regenerateLatestPartsPrompt}
            onChange={(e) => setRegenerateLatestPartsPrompt(e.target.value)}
            rows={5}
            placeholder="留空则使用默认生成策略，例如：优化节奏、强化冲突、提升转折密度…"
            disabled={regeneratingLatestParts}
          />
        </div>
      </Modal>

      <Modal
        isOpen={isRegenerateLatestModalOpen}
        onClose={() => setIsRegenerateLatestModalOpen(false)}
        title="重生成最新章节大纲"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton
              variant="ghost"
              onClick={() => setIsRegenerateLatestModalOpen(false)}
              disabled={regeneratingLatest}
            >
              取消
            </BookButton>
            <BookButton
              variant="primary"
              onClick={async () => {
                if (!id) return;
                if (!chapterOutlines.length) return;

                const sorted = [...chapterOutlines].sort((a: any, b: any) => Number(a?.chapter_number || 0) - Number(b?.chapter_number || 0));
                const maxCount = sorted.length;
                const count = Math.max(1, Math.min(Number(regenerateLatestCount) || 1, maxCount));
                const lastN = sorted.slice(-count);
                const start = Number(lastN[0]?.chapter_number || 0);
                const end = Number(sorted[sorted.length - 1]?.chapter_number || 0);
                if (!start || !end || end < start) {
                  addToast('章节大纲数据异常，无法重生成', 'error');
                  return;
                }

	                const ok = await confirmDialog({
	                  title: '重生成最新章节大纲',
	                  message:
	                    `将重生成最后 ${count} 个章节大纲（第${start}-${end}章）。\n\n` +
	                    `串行生成原则：会级联删除第${start + 1}-${end}章的大纲（以及可能存在的章节内容/向量数据）。\n\n` +
	                    `确定继续？`,
	                  confirmText: '继续',
	                  dialogType: 'danger',
	                });
	                if (!ok) return;

                setRegeneratingLatest(true);
                try {
                  const promptText = regenerateLatestPrompt.trim() || undefined;
                  const result = await writerApi.regenerateChapterOutline(
                    id,
                    start,
                    { prompt: promptText, cascadeDelete: true },
                    { timeout: 0 }
                  );
                  addToast(result?.message || `第${start}章大纲已重生成`, 'success');
                  if (result?.cascade_deleted?.message) addToast(String(result.cascade_deleted.message), 'info');
                  setIsRegenerateLatestModalOpen(false);
                  setRegenerateLatestPrompt('');
                  await fetchProject();
                } catch (e) {
                  console.error(e);
                  addToast('重生成失败', 'error');
                } finally {
                  setRegeneratingLatest(false);
                }
              }}
              disabled={regeneratingLatest || !chapterOutlines.length}
            >
              {regeneratingLatest ? '重生成中…' : '重生成'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
            说明：该操作等价于桌面端“重新生成最新 N 个章节大纲”。实现方式为：从“最后 N 个大纲”中找到最早的那一章，重生成该章大纲，并按串行原则级联删除后续大纲。删除后如需补齐，可使用“批量生成章节大纲”继续生成。
          </div>

          <BookInput
            label={`重生成数量（1-${Math.max(1, chapterOutlines.length)})`}
            type="number"
            min={1}
            max={Math.max(1, chapterOutlines.length)}
            value={regenerateLatestCount}
            onChange={(e) => setRegenerateLatestCount(parseInt(e.target.value, 10) || 1)}
            disabled={regeneratingLatest}
          />

          <BookTextarea
            label="优化提示词（可选）"
            value={regenerateLatestPrompt}
            onChange={(e) => setRegenerateLatestPrompt(e.target.value)}
            rows={5}
            placeholder="留空则使用默认生成策略，例如：加强冲突、优化节奏、强化伏笔回收…"
            disabled={regeneratingLatest}
          />
        </div>
      </Modal>

      <Modal
        isOpen={isDeleteLatestModalOpen}
        onClose={() => setIsDeleteLatestModalOpen(false)}
        title="删除最新章节大纲"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={() => setIsDeleteLatestModalOpen(false)} disabled={deletingLatest}>
              取消
            </BookButton>
            <BookButton
	              variant="primary"
	              onClick={async () => {
	                if (!id) return;
	                const count = Math.max(1, Math.min(Number(deleteLatestCount) || 1, chapterOutlines.length || 1));
	                const ok = await confirmDialog({
	                  title: '删除最新章节大纲',
	                  message:
	                    `确定要删除最新 ${count} 章章节大纲吗？\n\n` +
	                    `提示：如果这些章节已有生成内容，将级联删除章节内容与向量库数据。此操作不可恢复。`,
	                  confirmText: '删除',
	                  dialogType: 'danger',
	                });
	                if (!ok) return;
	                setDeletingLatest(true);
	                try {
	                  const result = await writerApi.deleteLatestChapterOutlines(id, count);
	                  addToast(result?.message || `已删除最新 ${count} 章大纲`, 'success');
                  if (result?.warning) addToast(String(result.warning), 'info');
                  setIsDeleteLatestModalOpen(false);
                  await fetchProject();
                } catch (e) {
                  console.error(e);
                  addToast('删除失败', 'error');
                } finally {
                  setDeletingLatest(false);
                }
              }}
              disabled={deletingLatest || !chapterOutlines.length}
            >
              {deletingLatest ? '删除中…' : '删除'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
            删除会从“最后一章”开始回退。若被删除章节已生成正文/评审/摘要/向量数据，将同时级联删除，避免后续生成引用到失效上下文。
          </div>
          <BookInput
            label={`删除数量（1-${Math.max(1, chapterOutlines.length)})`}
            type="number"
            min={1}
            max={Math.max(1, chapterOutlines.length)}
            value={deleteLatestCount}
            onChange={(e) => setDeleteLatestCount(parseInt(e.target.value) || 1)}
            disabled={deletingLatest}
          />
        </div>
      </Modal>
    </div>
  );
};
