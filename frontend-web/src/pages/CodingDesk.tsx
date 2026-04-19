import React, { startTransition, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  codingApi,
  CodingFileDetail,
  CodingFileVersion,
  DirectoryAgentStateResponse,
} from '../api/coding';
import { useToast } from '../components/feedback/Toast';
import { useSSE } from '../hooks/useSSE';
import { useTokenBuffer } from '../hooks/useTokenBuffer';
import { usePersistedState } from '../hooks/usePersistedState';
import { scheduleIdleTask } from '../utils/scheduleIdleTask';
import { readBootstrapCache, writeBootstrapCache } from '../utils/bootstrapCache';
import { CodingDeskAssistantPanel } from './coding-desk/CodingDeskAssistantPanel';
import { CodingDeskEditorPanel } from './coding-desk/CodingDeskEditorPanel';
import { CodingDeskHeader } from './coding-desk/CodingDeskHeader';
import { CodingDeskSidebar } from './coding-desk/CodingDeskSidebar';
import {
  AssistantTab,
  buildAgentDirectoryTreeData,
  CODING_DESK_BOOTSTRAP_TTL_MS,
  getCodingDeskBootstrapKey,
  safeJson,
  StreamLog,
  StreamLogType,
  truncateText,
  type CodingDeskBootstrapSnapshot,
} from './coding-desk/shared';

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
  const appendPromptTokens = useCallback((text: string) => {
    setContent((prev) => prev + text);
  }, []);
  const {
    pushToken: pushPromptToken,
    flush: flushPromptTokens,
    reset: resetPromptTokenBuffer,
  } = useTokenBuffer(appendPromptTokens, 48);

  const appendReviewTokens = useCallback((text: string) => {
    setReviewPrompt((prev) => prev + text);
  }, []);
  const {
    pushToken: pushReviewToken,
    flush: flushReviewTokens,
    reset: resetReviewTokenBuffer,
  } = useTokenBuffer(appendReviewTokens, 48);

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
  const [ragTopK, setRagTopK] = usePersistedState<number>(
    id ? `afn:coding_rag_topk:${id}` : null,
    8,
    {
      parse: (raw) => {
        const n = Number(raw);
        if (!Number.isFinite(n)) return 8;
        return Math.max(1, Math.min(30, Math.floor(n)));
      },
      serialize: (value) => String(value),
    },
  );
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
  const [agentDetailedMode, setAgentDetailedMode] = usePersistedState<boolean>(
    id ? `afn:coding_agent_detailed:${id}` : null,
    false,
    {
      parse: (raw) => {
        const v = String(raw).trim().toLowerCase();
        return v === '1' || v === 'true' || v === 'yes';
      },
      serialize: (value) => (value ? '1' : '0'),
    },
  );
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
    agentDetailedModeRef.current = agentDetailedMode;
  }, [agentDetailedMode]);

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
	      pushPromptToken(String(data.token));
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
	      pushReviewToken(String(data.token));
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

  const handleStopPrompt = useCallback(() => {
    disconnectPromptStream();
    setIsGenerating(false);
    addToast('已断开生成流（后台任务可能仍在运行）', 'info');
  }, [addToast, disconnectPromptStream]);

  const handleStopReview = useCallback(() => {
    disconnectReviewStream();
    setIsGeneratingReview(false);
    addToast('已断开生成流（后台任务可能仍在运行）', 'info');
  }, [addToast, disconnectReviewStream]);

  const handleChangeAgentDetailedMode = useCallback((checked: boolean) => {
    agentDetailedModeRef.current = checked;
    setAgentDetailedMode(checked);
    addToast(
      checked ? '详细模式已开启，将显示完整输出' : '详细模式已关闭，输出将截断显示',
      'info',
    );
  }, [addToast, setAgentDetailedMode]);

  if (loading) {
    return <div className="flex h-full min-h-0 items-center justify-center text-book-text-muted">加载中...</div>;
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-book-bg overflow-hidden">
      <CodingDeskHeader
        projectTitle={String(project?.title || '')}
        currentFilePath={currentFile?.file_path ? String(currentFile.file_path) : null}
        isAssistantOpen={isAssistantOpen}
        onBack={() => navigate(`/coding/detail/${id}`)}
        onOpenProjectDetail={() => navigate(`/coding/detail/${id}`)}
        onToggleAssistant={() => setIsAssistantOpen((v) => !v)}
      />

      <div className="flex-1 min-h-0 flex overflow-hidden">
        <CodingDeskSidebar
          project={project}
          treeLoading={treeLoading}
          showAgentTree={showAgentTree}
          agentTreeData={agentTreeData}
          treeData={treeData}
          onSelectFile={loadFile}
        />

        <CodingDeskEditorPanel
          currentFile={currentFile}
          content={content}
          reviewPrompt={reviewPrompt}
          reviewNotes={reviewNotes}
          versions={versions}
          selectedVersionId={selectedVersionId}
          isGenerating={isGenerating}
          isSaving={isSaving}
          isDirty={isDirty}
          isGeneratingReview={isGeneratingReview}
          isSavingReview={isSavingReview}
          isReviewDirty={isReviewDirty}
          genStage={genStage}
          genMessage={genMessage}
          onChangeContent={setContent}
          onChangeReviewPrompt={setReviewPrompt}
          onChangeReviewNotes={setReviewNotes}
          onStopPrompt={handleStopPrompt}
          onGeneratePrompt={handleGeneratePrompt}
          onSavePrompt={handleSavePrompt}
          onSelectVersion={handleSelectVersion}
          onStopReview={handleStopReview}
          onGenerateReview={handleGenerateReview}
          onSaveReview={handleSaveReview}
        />

        {isAssistantOpen ? (
          <CodingDeskAssistantPanel
            activeAssistantTab={activeAssistantTab}
            ragTopK={ragTopK}
            ragLoading={ragLoading}
            ragQuery={ragQuery}
            ragResult={ragResult}
            agentDetailedMode={agentDetailedMode}
            agentStateLoading={agentStateLoading}
            agentState={agentState}
            agentRunning={agentRunning}
            agentPreview={agentPreview}
            agentPreviewText={agentPreviewText}
            agentLogs={agentLogs}
            visibleAgentLogs={visibleAgentLogs}
            hasMoreAgentLogs={hasMoreAgentLogs}
            remainingAgentLogs={remainingAgentLogs}
            agentLogRenderLimit={agentLogRenderLimit}
            agentLogRef={agentLogRef}
            onChangeActiveAssistantTab={setActiveAssistantTab}
            onChangeRagTopK={setRagTopK}
            onRunRagQuery={runRagQuery}
            onChangeRagQuery={setRagQuery}
            onChangeAgentDetailedMode={handleChangeAgentDetailedMode}
            onStartAgentPlanning={startAgentPlanning}
            onContinueAgentPlanning={continueAgentPlanning}
            onDiscardAgentState={discardAgentState}
            onStopAgentPlanning={stopAgentPlanning}
            onClearAgentLogs={() => {
              resetAgentLogBuffer();
              setAgentLogs([]);
              setAgentLogRenderLimit(200);
            }}
            onExpandAgentLogs={() =>
              setAgentLogRenderLimit((prev) =>
                Math.min(agentLogs.length, Math.max(prev, 0) + 200),
              )
            }
            onCollapseAgentLogs={() => setAgentLogRenderLimit(200)}
            onRefreshAgentState={refreshAgentState}
          />
        ) : null}
      </div>
    </div>
  );
};
