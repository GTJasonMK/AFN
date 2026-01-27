import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  codingApi,
  CodingFileDetail,
  CodingFileVersion,
  DirectoryAgentStateResponse,
} from '../api/coding';
import { DirectoryTree } from '../components/coding/DirectoryTree';
import { BookButton } from '../components/ui/BookButton';
import { BookCard } from '../components/ui/BookCard';
import { BookInput, BookTextarea } from '../components/ui/BookInput';
import { useToast } from '../components/feedback/Toast';
import { useSSE } from '../hooks/useSSE';
import {
  ArrowLeft,
  Code,
  Database,
  FileCode,
  LayoutPanelLeft,
  PanelRight,
  PauseCircle,
  PlayCircle,
  RefreshCw,
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
};

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

export const CodingDesk: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { addToast } = useToast();

  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<any>(null);
  const [treeData, setTreeData] = useState<any>(null);

  const [currentFile, setCurrentFile] = useState<CodingFileDetail | null>(null);
  const [content, setContent] = useState('');
  const [reviewPrompt, setReviewPrompt] = useState('');

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
  const [agentPreview, setAgentPreview] = useState<{ directories?: any[]; files?: any[]; stats?: any } | null>(null);
  const agentLogRef = useRef<HTMLDivElement | null>(null);

  const refreshBasic = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [proj, tree] = await Promise.all([
        codingApi.get(id),
        codingApi.getDirectoryTree(id),
      ]);
      setProject(proj);
      setTreeData(tree);
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
    try {
      localStorage.setItem(`afn:coding_rag_topk:${id}`, String(ragTopK));
    } catch {
      // ignore
    }
  }, [id, ragTopK]);

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
      setContent((prev) => prev + String(data.token));
      return;
    }
    if (event === 'complete') {
      setIsGenerating(false);
      setGenStage(null);
      setGenMessage(null);
      addToast('Prompt 生成完成', 'success');
      if (id && currentFile?.id) loadFile(currentFile.id);
      return;
    }
    if (event === 'error') {
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
      setReviewPrompt((prev) => prev + String(data.token));
      return;
    }
    if (event === 'complete') {
      setIsGeneratingReview(false);
      setGenStage(null);
      setGenMessage(null);
      addToast('审查 Prompt 生成完成', 'success');
      if (id && currentFile?.id) loadFile(currentFile.id);
      return;
    }
    if (event === 'error') {
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
    };
  }, [disconnectPromptStream, disconnectReviewStream]);

  const handleGeneratePrompt = async () => {
    if (!id || !currentFile) return;
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
      setSelectedVersionId(v.id);
      setContent(v.content || '');
      addToast('已切换版本', 'success');
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
  const appendAgentLog = useCallback((type: StreamLogType, title: string, body?: any) => {
    const contentText = (() => {
      if (body === null || body === undefined) return '';
      if (typeof body === 'string') return body;
      return safeJson(body);
    })();

    setAgentLogs((prev) => {
      const next: StreamLog[] = [
        ...prev,
        {
          id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
          type,
          title: title || type,
          content: contentText,
          ts: Date.now(),
        },
      ];
      if (next.length > 600) next.splice(0, next.length - 600);
      return next;
    });
  }, []);

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
      refreshBasic();
      return;
    }

    if (et === 'planning_complete') {
      appendAgentLog('planning_complete', 'planning_complete', data);
      setAgentRunning(false);
      refreshBasic();
      return;
    }

    if (et === 'warning') {
      appendAgentLog('warning', 'warning', data);
      return;
    }

    if (et === 'error') {
      appendAgentLog('error', 'error', data);
      setAgentRunning(false);
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
    return () => disconnectAgentStream();
  }, [disconnectAgentStream]);

  const startAgentPlanning = useCallback(async (opts: { clearExisting: boolean }) => {
    if (!id) return;
    setAgentRunning(true);
    setAgentLogs([]);
    setAgentPreview(null);
    await connectAgentStream(codingApi.planDirectoryAgentStream(id), {
      clear_existing: opts.clearExisting,
    });
  }, [connectAgentStream, id]);

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
      addToast('已清除暂停状态', 'success');
    } catch (e) {
      console.error(e);
      addToast('清除失败', 'error');
    }
  }, [addToast, id, refreshAgentState]);

  const continueAgentPlanning = useCallback(async () => {
    if (!id) return;
    // 后端的 plan-agent 是否支持 resume 取决于实现；这里复用同一路由并带上 resume 标记，保持与桌面端一致
    setAgentRunning(true);
    setAgentLogs([]);
    setAgentPreview(null);
    await connectAgentStream(codingApi.planDirectoryAgentStream(id), { resume: true });
  }, [connectAgentStream, id]);

  if (loading) {
    return <div className="flex h-screen items-center justify-center text-book-text-muted">加载中...</div>;
  }

  return (
    <div className="flex flex-col h-screen bg-book-bg overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-book-border/40 bg-book-bg-paper flex items-center justify-between px-4 shrink-0 z-30 shadow-sm">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={() => navigate('/')}
            className="flex items-center text-book-text-sub hover:text-book-primary transition-colors text-sm font-medium shrink-0"
          >
            <ArrowLeft size={16} className="mr-1" />
            返回列表
          </button>

          <div className="flex items-center gap-2 min-w-0">
            <Code size={16} className="text-book-accent shrink-0" />
            <div className="font-serif font-bold text-book-text-main text-base tracking-wide truncate">
              {project?.title || 'Prompt 工程'}
            </div>
            {currentFile?.file_path ? (
              <div className="text-xs text-book-text-muted truncate">
                · {currentFile.file_path}
              </div>
            ) : null}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <BookButton size="sm" variant="ghost" onClick={() => navigate(`/coding/detail/${id}`)} title="返回项目详情页">
            <FileCode size={16} className="mr-1" />
            详情
          </BookButton>

          <BookButton size="sm" variant="ghost" onClick={refreshBasic} title="刷新目录树/项目信息">
            <RefreshCw size={16} className="mr-1" />
            刷新
          </BookButton>

          <BookButton size="sm" variant="ghost" onClick={() => setIsAssistantOpen((v) => !v)} title="切换右侧面板">
            <PanelRight size={16} className="mr-1" />
            {isAssistantOpen ? '隐藏助手' : '显示助手'}
          </BookButton>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        {/* Sidebar */}
        <div className="w-[300px] bg-book-bg-paper border-r border-book-border/60 flex flex-col">
          <div className="p-3 border-b border-book-border/30">
            <div className="text-xs font-bold text-book-text-sub uppercase tracking-wider flex items-center gap-2">
              <LayoutPanelLeft size={14} />
              Explorer
            </div>
          </div>
          <div className="p-3 border-b border-book-border/30">
            <BookCard className="p-3 bg-book-bg/40 border-book-border/40">
              <div className="text-xs text-book-text-muted">状态：{String(project?.status || 'unknown')}</div>
              <div className="mt-1 text-sm font-bold text-book-text-main truncate">{String(project?.title || '未命名项目')}</div>
            </BookCard>
          </div>
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            <DirectoryTree data={treeData} onSelectFile={loadFile} />
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
                RAG 查询
              </button>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-4 space-y-4">
              {activeAssistantTab === 'rag' ? (
                <div className="space-y-3">
                  <BookCard className="p-4 space-y-3">
                    <div className="font-bold text-book-text-main flex items-center gap-2">
                      <Database size={16} className="text-book-primary" />
                      RAG 查询
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
                      <div className="font-bold text-book-text-main">目录规划（Agent）</div>
                      <div className="text-[11px] text-book-text-muted">
                        {agentStateLoading ? '状态加载中…' : (agentState?.has_paused_state ? '可恢复' : '无暂停状态')}
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
                        {safeJson(agentPreview)}
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
                          onClick={() => setAgentLogs([])}
                        >
                          清空
                        </button>
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
                        {agentLogs.map((log) => {
                          const meta = LOG_LABELS[log.type] || { label: log.type, cls: 'text-book-text-muted' };
                          return (
                            <div key={log.id} className="p-2 rounded border border-book-border/40 bg-book-bg">
                              <div className="flex items-center justify-between gap-2">
                                <div className={`text-[11px] font-bold ${meta.cls}`}>
                                  {meta.label}
                                  {log.title ? <span className="text-book-text-muted font-normal ml-2">{log.title}</span> : null}
                                </div>
                                <div className="text-[10px] text-book-text-muted">
                                  {(() => {
                                    try {
                                      return new Date(log.ts).toLocaleTimeString();
                                    } catch {
                                      return '';
                                    }
                                  })()}
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
