import React, { lazy, Suspense, startTransition, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  codingApi,
  CodingFileDetail,
  CodingFileVersion,
  DirectoryAgentStateResponse,
} from '../api/coding';
import { BookButton } from '../components/ui/BookButton';
import { BookCard } from '../components/ui/BookCard';
import { BookInput, BookTextarea } from '../components/ui/BookInput';
import { useToast } from '../components/feedback/Toast';
import { useSSE } from '../hooks/useSSE';
import { scheduleIdleTask } from '../utils/scheduleIdleTask';
import { readBootstrapCache, writeBootstrapCache } from '../utils/bootstrapCache';
import {
  Database,
  LayoutPanelLeft,
  PauseCircle,
  PlayCircle,
  Save,
  Search,
  XCircle,
  Square,
  Wand2,
} from 'lucide-react';

type AssistantTab = 'rag' | 'agent';

type StreamLogType =
  | 'progress'
  | 'thinking'
  | 'action'
  | 'observation'
  | 'warning'
  | 'error'
  | 'structure_update'
  | 'final_state'
  | 'saved'
  | 'planning_complete'
  | 'agent_start'
  | 'iteration_start';

type StreamLog = {
  id: string;
  type: StreamLogType;
  title: string;
  content: string;
  ts: number;
  timeText: string;
};

type CodingDeskBootstrapSnapshot = {
  project: any | null;
  treeData: any | null;
};

const CODING_DESK_BOOTSTRAP_TTL_MS = 4 * 60 * 1000;
const getCodingDeskBootstrapKey = (projectId: string) => `afn:web:coding-desk:${projectId}:bootstrap:v1`;

const DirectoryTreeLazy = lazy(() =>
  import('../components/coding/DirectoryTree').then((m) => ({ default: m.DirectoryTree }))
);

const LOG_LABELS: Record<StreamLogType, { label: string; cls: string }> = {
  progress: { label: 'Progress', cls: 'text-book-text-muted' },
  thinking: { label: 'Thinking', cls: 'text-book-primary' },
  action: { label: 'Action', cls: 'text-book-accent' },
  observation: { label: 'Observation', cls: 'text-green-600' },
  warning: { label: 'Warning', cls: 'text-orange-600' },
  error: { label: 'Error', cls: 'text-red-600' },
  structure_update: { label: 'Structure', cls: 'text-book-primary' },
  final_state: { label: 'Final', cls: 'text-book-primary' },
  saved: { label: 'Saved', cls: 'text-green-600' },
  planning_complete: { label: 'Complete', cls: 'text-green-600' },
  agent_start: { label: 'Start', cls: 'text-book-text-muted' },
  iteration_start: { label: 'Iteration', cls: 'text-book-text-muted' },
};

const safeJson = (value: any): string => {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value ?? '');
  }
};

const truncateText = (text: string, maxLen: number, suffix: string): string => {
  const s = String(text ?? '');
  if (s.length <= maxLen) return s;
  return `${s.slice(0, maxLen)}\n${suffix}`;
};

const normalizePath = (raw: any): string => {
  const s = String(raw ?? '').trim().replace(/\\/g, '/');
  if (!s) return '';
  const noDup = s.replace(/\/{2,}/g, '/');
  const noDot = noDup.startsWith('./') ? noDup.slice(2) : noDup;
  return noDot.endsWith('/') ? noDot.slice(0, -1) : noDot;
};

const dirname = (p: string): string => {
  const s = normalizePath(p);
  const idx = s.lastIndexOf('/');
  if (idx <= 0) return '';
  return s.slice(0, idx);
};

const basename = (p: string): string => {
  const s = normalizePath(p);
  const idx = s.lastIndexOf('/');
  return idx >= 0 ? s.slice(idx + 1) : s;
};

const pathDepth = (p: string): number => {
  const s = normalizePath(p);
  if (!s) return 0;
  return s.split('/').filter(Boolean).length;
};

const buildAgentDirectoryTreeData = (preview: { directories?: any[]; files?: any[]; stats?: any }) => {
  const rawDirs = Array.isArray(preview?.directories) ? preview.directories : [];
  const rawFiles = Array.isArray(preview?.files) ? preview.files : [];

  const dirInfoByPath = new Map<string, any>();
  const allDirPaths = new Set<string>();

  const ensureDirPath = (rawPath: any) => {
    let cur = normalizePath(rawPath);
    if (!cur) return;
    while (cur) {
      if (!allDirPaths.has(cur)) allDirPaths.add(cur);
      const parent = dirname(cur);
      if (!parent || parent === cur) break;
      cur = parent;
    }
  };

  for (const d of rawDirs) {
    const p = normalizePath(d?.path);
    if (!p) continue;
    dirInfoByPath.set(p, { ...d, path: p });
    ensureDirPath(p);
  }

  for (const f of rawFiles) {
    const filePath = normalizePath(f?.path);
    if (!filePath) continue;
    const parentDir = dirname(filePath);
    if (parentDir) ensureDirPath(parentDir);
  }

  const sortedDirPaths = Array.from(allDirPaths).sort((a, b) => {
    const da = pathDepth(a);
    const db = pathDepth(b);
    if (da !== db) return da - db;
    return a.localeCompare(b);
  });

  const nodeByPath = new Map<string, any>();
  for (const p of sortedDirPaths) {
    const info = dirInfoByPath.get(p) || { path: p };
    nodeByPath.set(p, {
      id: `agent:dir:${p}`,
      name: basename(p) || p,
      ...info,
      children: [],
      files: [],
    });
  }

  for (const p of sortedDirPaths) {
    const parent = dirname(p);
    if (!parent) continue;
    const parentNode = nodeByPath.get(parent);
    const node = nodeByPath.get(p);
    if (!parentNode || !node) continue;
    parentNode.children.push(node);
  }

  for (const f of rawFiles) {
    const filePath = normalizePath(f?.path);
    if (!filePath) continue;
    const parent = dirname(filePath);
    const dirNode = nodeByPath.get(parent);
    if (!dirNode) continue;

    const filename = String(f?.filename || basename(filePath) || filePath);
    dirNode.files.push({
      id: `agent:file:${filePath}`,
      filename,
      file_path: filePath,
      ...f,
    });
  }

  for (const node of nodeByPath.values()) {
    node.children.sort((a: any, b: any) => String(a?.name || '').localeCompare(String(b?.name || '')));
    node.files.sort((a: any, b: any) => String(a?.filename || '').localeCompare(String(b?.filename || '')));
  }

  const rootNodes = sortedDirPaths
    .filter((p) => {
      const parent = dirname(p);
      return !parent || !nodeByPath.has(parent);
    })
    .map((p) => nodeByPath.get(p))
    .filter(Boolean);

  return {
    root_nodes: rootNodes,
    total_directories: Number(preview?.stats?.total_directories || allDirPaths.size) || 0,
    total_files: Number(preview?.stats?.total_files || rawFiles.length) || 0,
  };
};

export const CodingDesk: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { addToast } = useToast();

  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<any>(null);
  const [treeData, setTreeData] = useState<any>(null);
  const [treeLoading, setTreeLoading] = useState(false);

  const [currentFile, setCurrentFile] = useState<CodingFileDetail | null>(null);
  const [content, setContent] = useState('');
  const [reviewPrompt, setReviewPrompt] = useState('');
  const promptTokensRef = useRef<string[]>([]);
  const promptTokenFlushTimerRef = useRef<number | null>(null);
  const reviewTokensRef = useRef<string[]>([]);
  const reviewTokenFlushTimerRef = useRef<number | null>(null);

  const resetPromptTokenBuffer = useCallback(() => {
    promptTokensRef.current = [];
    if (promptTokenFlushTimerRef.current !== null) {
      window.clearTimeout(promptTokenFlushTimerRef.current);
      promptTokenFlushTimerRef.current = null;
    }
  }, []);

  const flushPromptTokens = useCallback(() => {
    if (promptTokensRef.current.length === 0) return;
    const text = promptTokensRef.current.join('');
    promptTokensRef.current = [];
    setContent((prev) => prev + text);
  }, []);

  const schedulePromptTokenFlush = useCallback(() => {
    if (promptTokenFlushTimerRef.current !== null) return;
    promptTokenFlushTimerRef.current = window.setTimeout(() => {
      promptTokenFlushTimerRef.current = null;
      flushPromptTokens();
    }, 48);
  }, [flushPromptTokens]);

  const resetReviewTokenBuffer = useCallback(() => {
    reviewTokensRef.current = [];
    if (reviewTokenFlushTimerRef.current !== null) {
      window.clearTimeout(reviewTokenFlushTimerRef.current);
      reviewTokenFlushTimerRef.current = null;
    }
  }, []);

  const flushReviewTokens = useCallback(() => {
    if (reviewTokensRef.current.length === 0) return;
    const text = reviewTokensRef.current.join('');
    reviewTokensRef.current = [];
    setReviewPrompt((prev) => prev + text);
  }, []);

  const scheduleReviewTokenFlush = useCallback(() => {
    if (reviewTokenFlushTimerRef.current !== null) return;
    reviewTokenFlushTimerRef.current = window.setTimeout(() => {
      reviewTokenFlushTimerRef.current = null;
      flushReviewTokens();
    }, 48);
  }, [flushReviewTokens]);

  const [versions, setVersions] = useState<CodingFileVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);

  const [isAssistantOpen, setIsAssistantOpen] = useState(true);
  const [activeAssistantTab, setActiveAssistantTab] = useState<AssistantTab>('agent');

  // Prompt generate/save
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [genStage, setGenStage] = useState<string | null>(null);
  const [genMessage, setGenMessage] = useState<string | null>(null);

  // Review prompt generate/save
  const [isGeneratingReview, setIsGeneratingReview] = useState(false);
  const [isSavingReview, setIsSavingReview] = useState(false);
  const [reviewNotes, setReviewNotes] = useState('');

  // RAG tab
  const [ragQuery, setRagQuery] = useState('');
  const [ragTopK, setRagTopK] = useState<number>(() => {
    try {
      const raw = localStorage.getItem(`afn:coding_rag_topk:${id || ''}`);
      const n = raw ? Number(raw) : 8;
      if (!Number.isFinite(n)) return 8;
      return Math.max(1, Math.min(30, Math.floor(n)));
    } catch {
      return 8;
    }
  });
  const [ragLoading, setRagLoading] = useState(false);
  const [ragResult, setRagResult] = useState<any | null>(null);

  // Agent tab
  const [agentState, setAgentState] = useState<DirectoryAgentStateResponse | null>(null);
  const [agentStateLoading, setAgentStateLoading] = useState(false);
  const [agentRunning, setAgentRunning] = useState(false);
  const [agentLogs, setAgentLogs] = useState<StreamLog[]>([]);
  const pendingAgentLogsRef = useRef<StreamLog[]>([]);
  const agentLogFlushTimerRef = useRef<number | null>(null);
  const [agentLogRenderLimit, setAgentLogRenderLimit] = useState(200);
  const [agentPreview, setAgentPreview] = useState<{ directories?: any[]; files?: any[]; stats?: any } | null>(null);
  const [showAgentTree, setShowAgentTree] = useState(false);
  const agentLogRef = useRef<HTMLDivElement | null>(null);
  const agentClearExistingRef = useRef<boolean>(true);
  const [agentDetailedMode, setAgentDetailedMode] = useState<boolean>(() => {
    try {
      const raw = localStorage.getItem(`afn:coding_agent_detailed:${id || ''}`);
      if (!raw) return false;
      const v = String(raw).trim().toLowerCase();
      return v === '1' || v === 'true' || v === 'yes';
    } catch {
      return false;
    }
  });
  const agentDetailedModeRef = useRef<boolean>(agentDetailedMode);
  const hasBootstrapProjectRef = useRef(false);

  useEffect(() => {
    if (!id) return;
    const cached = readBootstrapCache<CodingDeskBootstrapSnapshot>(
      getCodingDeskBootstrapKey(id),
      CODING_DESK_BOOTSTRAP_TTL_MS,
    );
    if (!cached) {
      hasBootstrapProjectRef.current = false;
      setProject(null);
      setTreeData(null);
      setLoading(true);
      return;
    }
    if (cached.project) {
      setProject(cached.project);
      setLoading(false);
      hasBootstrapProjectRef.current = true;
    } else {
      hasBootstrapProjectRef.current = false;
      setProject(null);
      setLoading(true);
    }
    if (cached.treeData) {
      setTreeData(cached.treeData);
    } else {
      setTreeData(null);
    }
  }, [id]);

  const resetAgentLogBuffer = useCallback(() => {
    pendingAgentLogsRef.current = [];
    if (agentLogFlushTimerRef.current !== null) {
      window.clearTimeout(agentLogFlushTimerRef.current);
      agentLogFlushTimerRef.current = null;
    }
  }, []);

  const flushAgentLogs = useCallback(() => {
    const pending = pendingAgentLogsRef.current;
    if (pending.length === 0) return;
    pendingAgentLogsRef.current = [];
    startTransition(() => {
      setAgentLogs((prev) => {
        const next = [...prev, ...pending];
        if (next.length > 600) next.splice(0, next.length - 600);
        return next;
      });
    });
  }, []);

  const scheduleAgentLogFlush = useCallback(() => {
    if (agentLogFlushTimerRef.current !== null) return;
    agentLogFlushTimerRef.current = window.setTimeout(() => {
      agentLogFlushTimerRef.current = null;
      flushAgentLogs();
    }, 80);
  }, [flushAgentLogs]);

  const refreshTreeData = useCallback(async () => {
    if (!id) return;
    setTreeLoading(true);
    try {
      const tree = await codingApi.getDirectoryTree(id);
      setTreeData(tree);
    } catch (e) {
      console.error(e);
      addToast('加载目录结构失败', 'error');
      setTreeData(null);
    } finally {
      setTreeLoading(false);
    }
  }, [addToast, id]);

  const refreshBasic = useCallback(async () => {
    if (!id) return;
    if (!hasBootstrapProjectRef.current) {
      setLoading(true);
    }
    try {
      const proj = await codingApi.get(id);
      setProject(proj);
      hasBootstrapProjectRef.current = true;
    } catch (e) {
      console.error(e);
      addToast('加载项目失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast, id]);

  const refreshAgentState = useCallback(async () => {
    if (!id) return;
    setAgentStateLoading(true);
    try {
      const data = await codingApi.getDirectoryAgentState(id);
      setAgentState(data);
    } catch (e) {
      console.error(e);
      setAgentState(null);
    } finally {
      setAgentStateLoading(false);
    }
  }, [id]);

  useEffect(() => {
    refreshBasic();
  }, [refreshBasic]);

  useEffect(() => {
    if (!id) return;
    if (!project && !treeData) return;
    writeBootstrapCache<CodingDeskBootstrapSnapshot>(getCodingDeskBootstrapKey(id), {
      project,
      treeData,
    });
  }, [id, project, treeData]);

  useEffect(() => {
    if (!id || loading) return;
    if (treeData !== null) return;

    const cancel = scheduleIdleTask(() => {
      void refreshTreeData();
    }, { delay: 160, timeout: 2200 });

    return cancel;
  }, [id, loading, refreshTreeData, treeData]);

  useEffect(() => {
    if (!id) return;
    try {
      localStorage.setItem(`afn:coding_rag_topk:${id}`, String(ragTopK));
    } catch {
      // ignore
    }
  }, [id, ragTopK]);

  useEffect(() => {
    agentDetailedModeRef.current = agentDetailedMode;
    if (!id) return;
    try {
      localStorage.setItem(`afn:coding_agent_detailed:${id}`, agentDetailedMode ? '1' : '0');
    } catch {
      // ignore
    }
  }, [agentDetailedMode, id]);

  const agentTreeData = useMemo(() => {
    if (!agentPreview) return null;
    return buildAgentDirectoryTreeData(agentPreview);
  }, [agentPreview]);

  const agentPreviewText = useMemo(() => (agentPreview ? safeJson(agentPreview) : ''), [agentPreview]);

  const visibleAgentLogs = useMemo(() => {
    const limit = Math.max(0, Math.floor(agentLogRenderLimit));
    if (limit <= 0) return [];
    if (agentLogs.length <= limit) return agentLogs;
    return agentLogs.slice(agentLogs.length - limit);
  }, [agentLogRenderLimit, agentLogs]);

  const hasMoreAgentLogs = visibleAgentLogs.length < agentLogs.length;
  const remainingAgentLogs = Math.max(0, agentLogs.length - visibleAgentLogs.length);

  const loadFile = useCallback(async (fileId: number) => {
    if (!id) return;
    try {
      const file = await codingApi.getFile(id, fileId);
      setCurrentFile(file);
      setContent(file.content || '');
      setReviewPrompt(file.review_prompt || '');

      const versionList = await codingApi.getFileVersions(id, fileId);
      setVersions(versionList.versions || []);
      setSelectedVersionId(versionList.selected_version_id ?? null);
    } catch (e) {
      console.error(e);
      addToast('加载文件失败', 'error');
    }
  }, [addToast, id]);

  // 支持通过 ?fileId=123 直达某个文件
  useEffect(() => {
    if (!id) return;
    const raw = searchParams.get('fileId');
    const fileId = raw ? Number(raw) : NaN;
    if (!Number.isFinite(fileId) || fileId <= 0) return;
    loadFile(fileId).catch(() => {});
  }, [id, loadFile, searchParams]);

  const isDirty = useMemo(() => {
    const base = currentFile?.content || '';
    return content !== base;
  }, [content, currentFile]);

  const isReviewDirty = useMemo(() => {
    const base = currentFile?.review_prompt || '';
    return reviewPrompt !== base;
  }, [currentFile, reviewPrompt]);

  // ========== Prompt 生成 SSE ==========
  const { connect: connectPromptStream, disconnect: disconnectPromptStream } = useSSE((event, data) => {
    if (event === 'progress') {
      setGenStage(String(data?.stage || ''));
      setGenMessage(String(data?.message || ''));
      return;
    }
    if (event === 'token' && data?.token) {
      promptTokensRef.current.push(String(data.token));
      schedulePromptTokenFlush();
      return;
    }
    if (event === 'complete') {
      flushPromptTokens();
      resetPromptTokenBuffer();
      setIsGenerating(false);
      setGenStage(null);
      setGenMessage(null);
      addToast('Prompt 生成完成', 'success');
      if (id && currentFile?.id) loadFile(currentFile.id);
      return;
    }
    if (event === 'error') {
      flushPromptTokens();
      resetPromptTokenBuffer();
      setIsGenerating(false);
      setGenStage(null);
      setGenMessage(null);
      addToast(String(data?.message || '生成失败'), 'error');
    }
  });

  // ========== Review Prompt 生成 SSE ==========
  const { connect: connectReviewStream, disconnect: disconnectReviewStream } = useSSE((event, data) => {
    if (event === 'progress') {
      setGenStage(String(data?.stage || 'review'));
      setGenMessage(String(data?.message || ''));
      return;
    }
    if (event === 'token' && data?.token) {
      reviewTokensRef.current.push(String(data.token));
      scheduleReviewTokenFlush();
      return;
    }
    if (event === 'complete') {
      flushReviewTokens();
      resetReviewTokenBuffer();
      setIsGeneratingReview(false);
      setGenStage(null);
      setGenMessage(null);
      addToast('审查 Prompt 生成完成', 'success');
      if (id && currentFile?.id) loadFile(currentFile.id);
      return;
    }
    if (event === 'error') {
      flushReviewTokens();
      resetReviewTokenBuffer();
      setIsGeneratingReview(false);
      setGenStage(null);
      setGenMessage(null);
      addToast(String(data?.message || '生成失败'), 'error');
    }
  });

  useEffect(() => {
    return () => {
      disconnectPromptStream();
      disconnectReviewStream();
      resetPromptTokenBuffer();
      resetReviewTokenBuffer();
    };
  }, [disconnectPromptStream, disconnectReviewStream, resetPromptTokenBuffer, resetReviewTokenBuffer]);

  const handleGeneratePrompt = async () => {
    if (!id || !currentFile) return;
    resetPromptTokenBuffer();
    setIsGenerating(true);
    setGenStage(null);
    setGenMessage(null);
    setContent('');
    await connectPromptStream(codingApi.generateFilePromptStream(id, currentFile.id), {});
  };

  const handleSavePrompt = async () => {
    if (!id || !currentFile) return;
    setIsSaving(true);
    try {
      await codingApi.saveFileContent(id, currentFile.id, content);
      addToast('已保存为新版本', 'success');
      await loadFile(currentFile.id);
    } catch (e) {
      console.error(e);
      addToast('保存失败', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleGenerateReview = async () => {
    if (!id || !currentFile) return;
    resetReviewTokenBuffer();
    setIsGeneratingReview(true);
    setGenStage(null);
    setGenMessage(null);
    setReviewPrompt('');
    await connectReviewStream(codingApi.generateReviewPromptStream(id, currentFile.id), {
      writing_notes: reviewNotes.trim() ? reviewNotes.trim() : undefined,
    });
  };

  const handleSaveReview = async () => {
    if (!id || !currentFile) return;
    setIsSavingReview(true);
    try {
      await codingApi.saveReviewPrompt(id, currentFile.id, reviewPrompt);
      addToast('审查 Prompt 已保存', 'success');
      await loadFile(currentFile.id);
    } catch (e) {
      console.error(e);
      addToast('保存失败', 'error');
    } finally {
      setIsSavingReview(false);
    }
  };

  const handleSelectVersion = async (v: CodingFileVersion) => {
    if (!id || !currentFile) return;
    try {
      await codingApi.selectFileVersion(id, currentFile.id, v.id);
      addToast('已切换版本', 'success');
      await loadFile(currentFile.id);
    } catch (e) {
      console.error(e);
      addToast('切换失败', 'error');
    }
  };

  // ========== RAG ==========
  const runRagQuery = useCallback(async () => {
    if (!id) return;
    const q = (ragQuery || '').trim();
    if (!q) return;
    setRagLoading(true);
    try {
      const res = await codingApi.queryRag(id, q, { topK: ragTopK });
      setRagResult(res);
    } catch (e) {
      console.error(e);
      addToast('RAG 查询失败', 'error');
      setRagResult(null);
    } finally {
      setRagLoading(false);
    }
  }, [addToast, id, ragQuery, ragTopK]);

  // ========== 目录规划 Agent ==========
  const formatAgentLogContent = useCallback((type: StreamLogType, body?: any): string => {
    const detailed = agentDetailedModeRef.current;

    if (body === null || body === undefined) return '';

    // Error 对象 JSON.stringify 会丢信息，单独处理
    if (body instanceof Error) {
      const msg = body.message || String(body);
      return detailed
        ? msg
        : truncateText(msg, 800, '…（已截断，开启“详细模式”查看完整内容）');
    }

    // 纯文本
    if (typeof body === 'string') {
      if (detailed) return body;
      const limit = type === 'thinking' ? 300 : 1200;
      return truncateText(body, limit, '…（已截断，开启“详细模式”查看完整内容）');
    }

    // 对象：按事件类型做尽量贴近桌面端的摘要/展开逻辑
    if (detailed) return safeJson(body);

    if (type === 'action') {
      // 桌面端默认只展示动作名称，参数与理由在详细模式中查看
      return '';
    }

    if (type === 'observation') {
      const tool = typeof body?.tool === 'string' ? body.tool : '';
      const result = body?.result;
      if (result === null || result === undefined) return '';
      if (typeof result === 'string') {
        const text = truncateText(result, 800, '…（已截断，开启“详细模式”查看完整内容）');
        return tool ? `工具: ${tool}\n${text}` : text;
      }
      if (Array.isArray(result)) return tool ? `工具: ${tool}\n结果: Array(${result.length})` : `结果: Array(${result.length})`;
      if (typeof result === 'object') {
        const keys = Object.keys(result);
        if (keys.length === 0) return tool ? `工具: ${tool}\n结果: {}` : '结果: {}';
        const previewKeys = keys.slice(0, 10).join(', ');
        const more = keys.length > 10 ? `, ...(+${keys.length - 10})` : '';
        return tool ? `工具: ${tool}\n结果字段: ${previewKeys}${more}` : `结果字段: ${previewKeys}${more}`;
      }
      const s = String(result ?? '');
      return tool ? `工具: ${tool}\n${s}` : s;
    }

    if (type === 'warning' || type === 'error') {
      const tool = typeof body?.tool === 'string' ? body.tool : '';
      const msg =
        (typeof body?.message === 'string' ? body.message : '') ||
        (typeof body?.error === 'string' ? body.error : '') ||
        '';
      if (msg) {
        const text = truncateText(msg, 1200, '…（已截断，开启“详细模式”查看完整内容）');
        return tool ? `工具: ${tool}\n${text}` : text;
      }
      const fallback = truncateText(safeJson(body), 1200, '…（已截断，开启“详细模式”查看完整内容）');
      return tool ? `工具: ${tool}\n${fallback}` : fallback;
    }

    return truncateText(safeJson(body), 1200, '…（已截断，开启“详细模式”查看完整内容）');
  }, []);

  const appendAgentLog = useCallback((type: StreamLogType, title: string, body?: any) => {
    const contentText = formatAgentLogContent(type, body);
    const ts = Date.now();
    const timeText = (() => {
      try {
        return new Date(ts).toLocaleTimeString();
      } catch {
        return '';
      }
    })();
    pendingAgentLogsRef.current.push({
      id: `${ts}-${Math.random().toString(16).slice(2)}`,
      type,
      title: title || type,
      content: contentText,
      ts,
      timeText,
    });
    scheduleAgentLogFlush();
  }, [formatAgentLogContent, scheduleAgentLogFlush]);

  const { connect: connectAgentStream, disconnect: disconnectAgentStream } = useSSE((event, data) => {
    // 统一记录日志，必要时做少量摘要
    const et = String(event || '') as StreamLogType;

    if (et === 'progress') {
      appendAgentLog('progress', String(data?.stage || 'progress'), String(data?.message || ''));
      return;
    }

    if (et === 'thinking') {
      appendAgentLog('thinking', String(data?.step || 'thinking'), String(data?.content || ''));
      return;
    }

    if (et === 'action') {
      appendAgentLog('action', String(data?.tool || data?.action || 'action'), data);
      return;
    }

    if (et === 'observation') {
      const ok = data?.success !== false;
      appendAgentLog(ok ? 'observation' : 'error', ok ? 'observation' : 'observation_failed', data);
      return;
    }

    if (et === 'structure_update') {
      setAgentPreview({
        directories: Array.isArray(data?.directories) ? data.directories : [],
        files: Array.isArray(data?.files) ? data.files : [],
        stats: data?.stats || null,
      });
      appendAgentLog('structure_update', 'structure_update', data?.stats || {});
      return;
    }

    if (et === 'final_state') {
      setAgentPreview({
        directories: Array.isArray(data?.directories) ? data.directories : [],
        files: Array.isArray(data?.files) ? data.files : [],
        stats: data?.stats || null,
      });
      appendAgentLog('final_state', 'final_state', { directories: (data?.directories || []).length, files: (data?.files || []).length });
      return;
    }

    if (et === 'saved') {
      appendAgentLog('saved', 'saved', data);
      flushAgentLogs();
      setShowAgentTree(false);
      void refreshBasic();
      void refreshTreeData();
      return;
    }

    if (et === 'planning_complete') {
      appendAgentLog('planning_complete', 'planning_complete', data);
      flushAgentLogs();
      setAgentRunning(false);
      if (!agentClearExistingRef.current) setShowAgentTree(false);
      void refreshBasic();
      void refreshTreeData();
      return;
    }

    if (et === 'warning') {
      appendAgentLog('warning', 'warning', data);
      return;
    }

    if (et === 'error') {
      appendAgentLog('error', 'error', data);
      flushAgentLogs();
      setAgentRunning(false);
      setShowAgentTree(false);
      return;
    }

    // 兜底
    appendAgentLog(et || 'progress', et || 'event', data);
  });

  useEffect(() => {
    if (!agentRunning) return;
    const el = agentLogRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [agentLogs.length, agentRunning]);

  useEffect(() => {
    if (!id) return;
    if (activeAssistantTab !== 'agent') return;
    refreshAgentState();
  }, [activeAssistantTab, id, refreshAgentState]);

  useEffect(() => {
    return () => {
      disconnectAgentStream();
      resetAgentLogBuffer();
    };
  }, [disconnectAgentStream, resetAgentLogBuffer]);

  const startAgentPlanning = useCallback(async (opts: { clearExisting: boolean }) => {
    if (!id) return;
    resetAgentLogBuffer();
    setAgentLogRenderLimit(200);
    agentClearExistingRef.current = Boolean(opts.clearExisting);
    setAgentRunning(true);
    setAgentLogs([]);
    setAgentPreview(null);
    setShowAgentTree(true);
    await connectAgentStream(codingApi.planDirectoryAgentStream(id), {
      clear_existing: opts.clearExisting,
    });
  }, [connectAgentStream, id, resetAgentLogBuffer]);

  const stopAgentPlanning = useCallback(async () => {
    if (!id) return;
    disconnectAgentStream();
    setAgentRunning(false);
    try {
      await codingApi.pauseDirectoryAgent(id, '用户手动停止');
      await refreshAgentState();
      addToast('已请求暂停（如后端未实现暂停，将仅断开连接）', 'info');
    } catch (e) {
      console.error(e);
      addToast('暂停失败（已断开连接）', 'info');
    }
  }, [addToast, disconnectAgentStream, id, refreshAgentState]);

  const discardAgentState = useCallback(async () => {
    if (!id) return;
    try {
      await codingApi.clearDirectoryAgentState(id);
      await refreshAgentState();
      setAgentPreview(null);
      setShowAgentTree(false);
      addToast('已清除暂停状态', 'success');
    } catch (e) {
      console.error(e);
      addToast('清除失败', 'error');
    }
  }, [addToast, id, refreshAgentState]);

  const continueAgentPlanning = useCallback(async () => {
    if (!id) return;
    // 后端的 plan-agent 是否支持 resume 取决于实现；这里复用同一路由并带上 resume 标记，保持与桌面端一致
    resetAgentLogBuffer();
    setAgentLogRenderLimit(200);
    agentClearExistingRef.current = false;
    setAgentRunning(true);
    setAgentLogs([]);
    setAgentPreview(null);
    setShowAgentTree(true);
    await connectAgentStream(codingApi.planDirectoryAgentStream(id), { resume: true });
  }, [connectAgentStream, id, resetAgentLogBuffer]);

  if (loading) {
    return <div className="flex h-screen items-center justify-center text-book-text-muted">加载中...</div>;
  }

  return (
    <div className="flex flex-col h-screen bg-book-bg overflow-hidden">
      {/* Header - 完全照抄桌面端 coding_desk/header.py */}
      <div className="h-14 border-b border-book-border bg-book-bg-paper flex items-center px-4 gap-3 shrink-0 z-30">
        {/* 返回按钮 */}
        <button
          onClick={() => navigate(`/coding/detail/${id}`)}
          className="text-book-primary hover:bg-book-primary/10 px-3 py-1.5 rounded text-sm"
        >
          &lt; 返回
        </button>

        {/* 分隔线 */}
        <div className="w-px h-6 bg-book-border" />

        {/* 项目标题 */}
        <div className="text-[15px] font-semibold text-book-text-main">
          {project?.title || '加载中...'}
        </div>

        {/* 分隔线 */}
        <div className="w-px h-6 bg-book-border" />

        {/* 当前文件路径 */}
        {currentFile?.file_path && (
          <div className="text-xs text-book-text-sub font-mono">
            {currentFile.file_path}
          </div>
        )}

        {/* stretch */}
        <div className="flex-1" />

        {/* 项目详情按钮 */}
        <button
          onClick={() => navigate(`/coding/detail/${id}`)}
          className="px-3 py-1.5 text-xs text-book-text-sub border border-book-border rounded hover:text-book-primary hover:border-book-primary hover:bg-book-primary/10 transition-colors"
        >
          项目详情
        </button>

        {/* RAG助手切换按钮 */}
        <button
          onClick={() => setIsAssistantOpen((v) => !v)}
          className={`px-3 py-1.5 text-xs border rounded transition-colors ${
            isAssistantOpen
              ? 'bg-book-primary text-white border-book-primary'
              : 'text-book-primary border-book-primary hover:bg-book-primary/10'
          }`}
        >
          RAG助手
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        {/* Sidebar */}
        <div className="w-[300px] bg-book-bg-paper border-r border-book-border/60 flex flex-col">
          <div className="p-3 border-b border-book-border/30">
            <div className="text-xs font-bold text-book-text-sub uppercase tracking-wider flex items-center gap-2">
              <LayoutPanelLeft size={14} />
              项目结构
              {showAgentTree ? (
                <span className="ml-1 text-[10px] font-bold text-book-primary bg-book-primary/10 border border-book-primary/20 px-1.5 py-0.5 rounded">
                  规划预览
                </span>
              ) : null}
            </div>
          </div>
          <div className="p-3 border-b border-book-border/30">
            <BookCard className="p-3 bg-book-bg/40 border-book-border/40">
              <div className="text-xs text-book-text-muted">状态：{String(project?.status || 'unknown')}</div>
              <div className="mt-1 text-sm font-bold text-book-text-main truncate">{String(project?.title || '未命名项目')}</div>
            </BookCard>
          </div>
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {treeLoading && !(showAgentTree && agentTreeData) && !treeData ? (
              <div className="p-4 text-xs text-book-text-muted">目录加载中…</div>
            ) : (
              <Suspense fallback={<div className="p-4 text-xs text-book-text-muted">目录组件加载中…</div>}>
                <DirectoryTreeLazy data={showAgentTree && agentTreeData ? agentTreeData : treeData} onSelectFile={loadFile} />
              </Suspense>
            )}
          </div>
        </div>

        {/* Workspace */}
        <div className="flex-1 min-w-0 bg-book-bg flex flex-col overflow-hidden">
          {!currentFile ? (
            <div className="h-full flex items-center justify-center text-book-text-muted">
              请选择一个文件开始编辑
            </div>
          ) : (
            <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-6 space-y-4">
              <BookCard className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-bold text-book-text-main">{currentFile.filename}</div>
                    <div className="text-xs text-book-text-muted mt-1 whitespace-pre-wrap">
                      {currentFile.description || currentFile.purpose || currentFile.file_path}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {isGenerating ? (
                      <BookButton
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          disconnectPromptStream();
                          setIsGenerating(false);
                          addToast('已断开生成流（后台任务可能仍在运行）', 'info');
                        }}
                        title="仅断开 SSE 连接（不保证取消后台任务）"
                      >
                        <Square size={16} className="mr-1" />
                        停止
                      </BookButton>
                    ) : (
                      <BookButton size="sm" variant="primary" onClick={handleGeneratePrompt} disabled={isGenerating || isSaving}>
                        <Wand2 size={16} className="mr-1" />
                        生成 Prompt
                      </BookButton>
                    )}
                    <BookButton
                      size="sm"
                      variant="secondary"
                      onClick={handleSavePrompt}
                      disabled={isSaving || isGenerating}
                      title="保存为新版本"
                    >
                      <Save size={16} className="mr-1" />
                      {isSaving ? '保存中…' : (isDirty ? '保存*' : '保存')}
                    </BookButton>
                  </div>
                </div>

                {(genStage || genMessage) ? (
                  <div className="mt-3 text-xs text-book-text-muted bg-book-bg p-2 rounded border border-book-border/40">
                    {genStage ? <span className="font-mono mr-2">{genStage}</span> : null}
                    {genMessage}
                  </div>
                ) : null}

                {versions.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {versions.map((v, idx) => {
                      const isSelected = selectedVersionId ? selectedVersionId === v.id : idx === 0;
                      return (
                        <button
                          key={`ver-${v.id}-${idx}`}
                          className={`px-3 py-1 rounded-lg border text-xs font-bold transition-all ${
                            isSelected
                              ? 'bg-book-primary/10 border-book-primary/30 text-book-primary'
                              : 'bg-book-bg border-book-border/40 text-book-text-muted hover:text-book-text-main'
                          }`}
                          onClick={() => handleSelectVersion(v)}
                          disabled={isGenerating || isSaving}
                          type="button"
                        >
                          {v.version_label || `v${idx + 1}`}
                        </button>
                      );
                    })}
                  </div>
                ) : null}
              </BookCard>

              <BookCard className="p-4">
                <div className="text-xs font-bold text-book-text-sub mb-2">实现 Prompt</div>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="w-full min-h-[380px] resize-y rounded-lg bg-book-bg border border-book-border/40 px-3 py-3 text-sm text-book-text-main font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-book-primary/30"
                  placeholder="选择一个文件后点击「生成 Prompt」开始生成，或直接编辑后保存。"
                  spellCheck={false}
                  readOnly={isGenerating}
                />
              </BookCard>

              <BookCard className="p-4">
                <div className="flex items-center justify-between gap-3 mb-2">
                  <div className="text-xs font-bold text-book-text-sub">审查 Prompt</div>
                  <div className="flex items-center gap-2">
                    {isGeneratingReview ? (
                      <BookButton
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          disconnectReviewStream();
                          setIsGeneratingReview(false);
                          addToast('已断开生成流（后台任务可能仍在运行）', 'info');
                        }}
                      >
                        <Square size={16} className="mr-1" />
                        停止
                      </BookButton>
                    ) : (
                      <BookButton size="sm" variant="ghost" onClick={handleGenerateReview} disabled={!content.trim()}>
                        <Wand2 size={16} className="mr-1" />
                        生成审查
                      </BookButton>
                    )}
                    <BookButton
                      size="sm"
                      variant="secondary"
                      onClick={handleSaveReview}
                      disabled={isSavingReview || isGeneratingReview}
                      title="保存审查 Prompt"
                    >
                      <Save size={16} className="mr-1" />
                      {isSavingReview ? '保存中…' : (isReviewDirty ? '保存*' : '保存')}
                    </BookButton>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                  <BookInput
                    label="审查偏好（可选）"
                    placeholder="例如：更关注安全/性能/可测试性…"
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                  />
                </div>

                <textarea
                  value={reviewPrompt}
                  onChange={(e) => setReviewPrompt(e.target.value)}
                  className="w-full min-h-[180px] resize-y rounded-lg bg-book-bg border border-book-border/40 px-3 py-3 text-sm text-book-text-main font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-book-primary/30"
                  placeholder="生成实现 Prompt 后可生成审查 Prompt…"
                  spellCheck={false}
                  readOnly={isGeneratingReview}
                />
              </BookCard>
            </div>
          )}
        </div>

        {/* Assistant */}
        {isAssistantOpen ? (
          <div className="w-[420px] bg-book-bg-paper border-l border-book-border/60 flex flex-col">
            <div className="p-2 border-b border-book-border/30 flex items-center gap-2">
              <button
                className={`flex-1 px-3 py-2 rounded-lg text-xs font-bold border transition-all ${
                  activeAssistantTab === 'agent'
                    ? 'bg-book-primary/10 border-book-primary/30 text-book-primary'
                    : 'bg-book-bg border-book-border/40 text-book-text-muted hover:text-book-text-main'
                }`}
                onClick={() => setActiveAssistantTab('agent')}
                type="button"
              >
                目录规划
              </button>
              <button
                className={`flex-1 px-3 py-2 rounded-lg text-xs font-bold border transition-all ${
                  activeAssistantTab === 'rag'
                    ? 'bg-book-primary/10 border-book-primary/30 text-book-primary'
                    : 'bg-book-bg border-book-border/40 text-book-text-muted hover:text-book-text-main'
                }`}
                onClick={() => setActiveAssistantTab('rag')}
                type="button"
              >
                RAG查询
              </button>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-4 space-y-4">
              {activeAssistantTab === 'rag' ? (
                <div className="space-y-3">
                  <BookCard className="p-4 space-y-3">
                    <div className="font-bold text-book-text-main flex items-center gap-2">
                      <Database size={16} className="text-book-primary" />
                      RAG查询
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <BookInput
                        label="TopK"
                        type="number"
                        min={1}
                        max={30}
                        value={ragTopK}
                        onChange={(e) => setRagTopK(Number(e.target.value || 8))}
                      />
                      <div className="flex items-end">
                        <BookButton
                          variant="primary"
                          size="sm"
                          onClick={runRagQuery}
                          disabled={ragLoading || !(ragQuery || '').trim()}
                          className="w-full"
                        >
                          <Search size={14} className={`mr-1 ${ragLoading ? 'animate-spin' : ''}`} />
                          查询
                        </BookButton>
                      </div>
                    </div>
                    <label className="text-xs font-bold text-book-text-sub">
                      查询内容
                      <BookTextarea
                        rows={3}
                        value={ragQuery}
                        onChange={(e) => setRagQuery(e.target.value)}
                        placeholder="输入查询，例如：鉴权、缓存、数据库迁移…"
                      />
                    </label>
                  </BookCard>

                  <BookCard className="p-4">
                    <div className="text-xs font-bold text-book-text-sub mb-2">结果</div>
                    {!ragResult ? (
                      <div className="text-xs text-book-text-muted">暂无结果</div>
                    ) : (
                      <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed">
                        {safeJson(ragResult)}
                      </pre>
                    )}
                  </BookCard>
                </div>
              ) : (
                <div className="space-y-3">
                  <BookCard className="p-4 space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="font-bold text-book-text-main">目录规划</div>
                      <div className="flex items-center gap-3">
                        <label className="flex items-center gap-2 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            className="rounded border-book-border text-book-primary focus:ring-book-primary"
                            checked={agentDetailedMode}
                            onChange={(e) => {
                              const checked = e.target.checked;
                              agentDetailedModeRef.current = checked;
                              setAgentDetailedMode(checked);
                              addToast(
                                checked ? '详细模式已开启，将显示完整输出' : '详细模式已关闭，输出将截断显示',
                                'info',
                              );
                            }}
                          />
                          <span className="text-[11px] font-bold text-book-text-sub">详细模式</span>
                        </label>
                        <div className="text-[11px] text-book-text-muted">
                          {agentStateLoading ? '状态加载中…' : (agentState?.has_paused_state ? '可恢复' : '无暂停状态')}
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <BookButton
                        variant="primary"
                        size="sm"
                        onClick={() => startAgentPlanning({ clearExisting: true })}
                        disabled={agentRunning}
                      >
                        {agentRunning ? <PauseCircle size={14} className="mr-1" /> : <PlayCircle size={14} className="mr-1" />}
                        规划全项目
                      </BookButton>
                      <BookButton
                        variant="ghost"
                        size="sm"
                        onClick={() => startAgentPlanning({ clearExisting: false })}
                        disabled={agentRunning}
                      >
                        <PlayCircle size={14} className="mr-1" />
                        优化目录
                      </BookButton>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <BookButton
                        variant="secondary"
                        size="sm"
                        onClick={continueAgentPlanning}
                        disabled={agentRunning || !agentState?.has_paused_state}
                        title="按桌面端逻辑尝试继续（取决于后端是否实现 resume）"
                      >
                        <PlayCircle size={14} className="mr-1" />
                        继续规划
                      </BookButton>
                      <BookButton
                        variant="ghost"
                        size="sm"
                        onClick={discardAgentState}
                        disabled={agentRunning || !agentState?.has_paused_state}
                      >
                        <XCircle size={14} className="mr-1" />
                        放弃进度
                      </BookButton>
                    </div>

                    <BookButton
                      variant="secondary"
                      size="sm"
                      onClick={stopAgentPlanning}
                      disabled={!agentRunning}
                      title="尽量调用后端 pause-agent；若不可用则仅断开连接"
                    >
                      <Square size={14} className="mr-1" />
                      停止
                    </BookButton>

                    {agentState?.progress_message ? (
                      <div className="text-xs text-book-text-muted bg-book-bg p-2 rounded border border-book-border/40">
                        {agentState.progress_percent ? <span className="font-mono mr-2">{agentState.progress_percent}%</span> : null}
                        {agentState.progress_message}
                      </div>
                    ) : null}
                  </BookCard>

                  {agentPreview ? (
                    <BookCard className="p-4">
                      <div className="text-xs font-bold text-book-text-sub mb-2">结构预览</div>
                      <div className="text-xs text-book-text-muted mb-2">
                        目录 {agentPreview.directories?.length || 0} · 文件 {agentPreview.files?.length || 0}
                      </div>
                      <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed max-h-56 overflow-auto custom-scrollbar">
                        {agentPreviewText}
                      </pre>
                    </BookCard>
                  ) : null}

                  <BookCard className="p-4">
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="text-xs font-bold text-book-text-sub">过程输出</div>
                      <div className="flex items-center gap-2">
                        <button
                          className="text-xs text-book-primary font-bold hover:underline"
                          type="button"
                          onClick={() => {
                            resetAgentLogBuffer();
                            setAgentLogs([]);
                            setAgentLogRenderLimit(200);
                          }}
                        >
                          清空
                        </button>
                        {hasMoreAgentLogs ? (
                          <button
                            className="text-xs text-book-text-muted hover:underline"
                            type="button"
                            onClick={() =>
                              setAgentLogRenderLimit((prev) =>
                                Math.min(agentLogs.length, Math.max(prev, 0) + 200)
                              )
                            }
                            title="为提升流式渲染性能，默认只渲染最近一部分日志"
                          >
                            显示更多（剩余 {remainingAgentLogs}）
                          </button>
                        ) : null}
                        {agentLogRenderLimit > 200 ? (
                          <button
                            className="text-xs text-book-text-muted hover:underline"
                            type="button"
                            onClick={() => setAgentLogRenderLimit(200)}
                          >
                            收起
                          </button>
                        ) : null}
                        <button
                          className="text-xs text-book-text-muted hover:underline"
                          type="button"
                          onClick={() => refreshAgentState()}
                        >
                          {agentStateLoading ? '刷新中…' : '刷新状态'}
                        </button>
                      </div>
                    </div>

                    {agentLogs.length === 0 ? (
                      <div className="text-xs text-book-text-muted">
                        {agentRunning ? '等待输出…' : '点击“规划全项目/优化目录”开始。'}
                      </div>
                    ) : (
                      <div ref={agentLogRef} className="max-h-[420px] overflow-y-auto custom-scrollbar space-y-2 pr-1">
                        {visibleAgentLogs.map((log) => {
                          const meta = LOG_LABELS[log.type] || { label: log.type, cls: 'text-book-text-muted' };
                          return (
                            <div key={log.id} className="p-2 rounded border border-book-border/40 bg-book-bg">
                              <div className="flex items-center justify-between gap-2">
                                <div className={`text-[11px] font-bold ${meta.cls}`}>
                                  {meta.label}
                                  {log.title ? <span className="text-book-text-muted font-normal ml-2">{log.title}</span> : null}
                                </div>
                                <div className="text-[10px] text-book-text-muted">
                                  {log.timeText}
                                </div>
                              </div>
                              {log.content ? (
                                <pre className="mt-1 text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed">
                                  {log.content}
                                </pre>
                              ) : null}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </BookCard>
                </div>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};
