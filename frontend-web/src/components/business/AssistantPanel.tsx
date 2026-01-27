import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';
import { Sparkles, FileText, User, Layers, Search, Loader2, Database, RefreshCw, Files, BadgeCheck, ScrollText, BarChart3, Wand2, Eye, Activity } from 'lucide-react';
import { CharacterPortraitGallery } from './CharacterPortraitGallery';
import { MangaPromptViewer } from './MangaPromptViewer';
import { novelsApi, RagDiagnoseResponse, RagIngestAllResponse } from '../../api/novels';
import { useToast } from '../feedback/Toast';
import { ErrorBoundary } from '../feedback/ErrorBoundary';
import type { Chapter } from '../../api/writer';
import { ChapterVersionsView } from './ChapterVersionsView';
import { ChapterReviewView } from './ChapterReviewView';
import { ChapterSummaryView } from './ChapterSummaryView';
import { ChapterAnalysisView } from './ChapterAnalysisView';
import { ContentOptimizationView } from './ContentOptimizationView';
import { ChapterPromptPreviewView } from './ChapterPromptPreviewView';
import { CharacterStateView } from './CharacterStateView';

export type AssistantTabId =
  | 'outline'
  | 'prompt'
  | 'versions'
  | 'review'
  | 'summary'
  | 'analysis'
  | 'optimize'
  | 'portraits'
  | 'state'
  | 'manga'
  | 'rag';

const ASSISTANT_TAB_STORAGE_KEY = (projectId: string) => `afn:assistant_tab:${projectId}`;

interface AssistantPanelProps {
  projectId: string;
  chapterNumber?: number;
  chapter?: Chapter | null;
  content?: string;
  characterNames?: string[];
  characterProfiles?: Record<string, string>;
  requestedTab?: AssistantTabId | null;
  onChangeContent?: (value: string) => void;
  writingNotes?: string;
  onChangeWritingNotes?: (value: string) => void;
  onIngestRag?: () => void | Promise<void>;
  isIngestingRag?: boolean;
  onSelectVersion?: (index: number) => void | Promise<void>;
  onRetryVersion?: (index: number, customPrompt?: string) => void | Promise<void>;
  onEvaluateChapter?: () => void | Promise<void>;
  onJumpToChapter?: (chapterNumber: number) => void | Promise<void>;
  onLocateText?: (text: string) => void;
  onSelectRange?: (start: number, end: number) => void;
}

export const AssistantPanel: React.FC<AssistantPanelProps> = ({
  projectId,
  chapterNumber,
  chapter,
  content,
  characterNames,
  characterProfiles,
  requestedTab,
  onChangeContent,
  writingNotes,
  onChangeWritingNotes,
  onIngestRag,
  isIngestingRag,
  onSelectVersion,
  onRetryVersion,
  onEvaluateChapter,
  onJumpToChapter,
  onLocateText,
  onSelectRange,
}) => {
  const [activeTab, setActiveTab] = useState<AssistantTabId>(() => {
    try {
      const raw = localStorage.getItem(ASSISTANT_TAB_STORAGE_KEY(projectId));
      const candidate = String(raw || '') as AssistantTabId;
      const allowed: AssistantTabId[] = [
        'outline',
        'prompt',
        'versions',
        'review',
        'summary',
        'analysis',
        'optimize',
        'portraits',
        'state',
        'manga',
        'rag',
      ];
      if (allowed.includes(candidate)) return candidate;
    } catch {
      // ignore
    }
    return 'outline';
  });
  // keep-alive（避免切换 Tab 时中断 SSE/丢失“预览→确认/撤销”等关键状态）
  const [optimizeMounted, setOptimizeMounted] = useState(activeTab === 'optimize');
  const [mangaMounted, setMangaMounted] = useState(activeTab === 'manga');
  const [ragQuery, setRagQuery] = useState('');
  const [ragTopK, setRagTopK] = useState<number>(() => {
    try {
      const raw = localStorage.getItem(`afn:rag_topk:${projectId}`);
      const n = raw ? Number(raw) : 10;
      if (!Number.isFinite(n)) return 10;
      return Math.max(1, Math.min(50, n));
    } catch {
      return 10;
    }
  });
  const [ragResults, setRagResults] = useState<any>(null);
  const [isRagLoading, setIsRagLoading] = useState(false);
  const [ragDiagnose, setRagDiagnose] = useState<RagDiagnoseResponse | null>(null);
  const [ragDiagnoseLoading, setRagDiagnoseLoading] = useState(false);
  const [ragIngesting, setRagIngesting] = useState(false);
  const [ragIngestResult, setRagIngestResult] = useState<RagIngestAllResponse | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const { addToast } = useToast();

  const chapterReady = Boolean(chapterNumber);

  // 外部请求切换 Tab（用于写作台 Header 快捷入口）
  useEffect(() => {
    if (!requestedTab) return;
    const allowed: AssistantTabId[] = [
      'outline',
      'prompt',
      'versions',
      'review',
      'summary',
      'analysis',
      'optimize',
      'portraits',
      'state',
      'manga',
      'rag',
    ];
    if (!allowed.includes(requestedTab)) return;
    const disabled = !chapterReady && requestedTab !== 'portraits' && requestedTab !== 'rag';
    setActiveTab(disabled ? 'portraits' : requestedTab);
  }, [chapterReady, requestedTab]);

  useEffect(() => {
    if (activeTab === 'optimize') setOptimizeMounted(true);
    if (activeTab === 'manga') setMangaMounted(true);
  }, [activeTab]);

  useEffect(() => {
    try {
      localStorage.setItem(ASSISTANT_TAB_STORAGE_KEY(projectId), activeTab);
    } catch {
      // ignore
    }
  }, [activeTab, projectId]);

  useEffect(() => {
    try {
      localStorage.setItem(`afn:rag_topk:${projectId}`, String(ragTopK));
    } catch {
      // ignore
    }
  }, [projectId, ragTopK]);

  const tabs = [
    { id: 'outline', label: '大纲', icon: FileText, disabled: !chapterReady },
    { id: 'prompt', label: '提示词', icon: Eye, disabled: !chapterReady },
    { id: 'versions', label: '版本', icon: Files, disabled: !chapterReady },
    { id: 'review', label: '评审', icon: BadgeCheck, disabled: !chapterReady },
    { id: 'summary', label: '摘要', icon: ScrollText, disabled: !chapterReady },
    { id: 'analysis', label: '分析', icon: BarChart3, disabled: !chapterReady },
    { id: 'optimize', label: '优化', icon: Wand2, disabled: !chapterReady },
    { id: 'portraits', label: '角色', icon: User, disabled: false },
    { id: 'state', label: '状态', icon: Activity, disabled: !chapterReady },
    { id: 'manga', label: '漫画', icon: Layers, disabled: !chapterReady },
    { id: 'rag', label: '知识库', icon: Sparkles, disabled: false },
  ] as const;

  const handleRagSearch = async () => {
    if (!ragQuery.trim()) return;
    if (ragDiagnose && ragDiagnose.vector_store_enabled === false) {
      addToast('向量库未启用，无法检索（请先在设置中启用/初始化）', 'error');
      return;
    }
    setIsRagLoading(true);
    try {
      const results = await novelsApi.queryRAG(projectId, ragQuery, ragTopK);
      setRagResults(results);
    } catch (e) {
      console.error(e);
      addToast('RAG 查询失败', 'error');
    } finally {
      setIsRagLoading(false);
    }
  };

  const fetchRagDiagnose = useCallback(async () => {
    setRagDiagnoseLoading(true);
    try {
      const data = await novelsApi.getRagDiagnose(projectId);
      setRagDiagnose(data);
    } catch (e) {
      console.error(e);
      setRagDiagnose(null);
    } finally {
      setRagDiagnoseLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (activeTab !== 'rag') return;
    fetchRagDiagnose();
  }, [activeTab, fetchRagDiagnose]);

  useEffect(() => {
    if (chapterReady) return;
    if (activeTab !== 'portraits' && activeTab !== 'rag') {
      setActiveTab('portraits');
    }
  }, [chapterReady, activeTab]);

  const vectorStoreReady = useMemo(() => {
    return Boolean(ragDiagnose?.vector_store_enabled);
  }, [ragDiagnose]);

  // 入库（分析/摘要/向量化）依赖 LLMService；纯检索依赖 EmbeddingService（由 /rag/query 自行检查）
  const ingestReady = useMemo(() => {
    return Boolean(ragDiagnose?.vector_store_enabled && ragDiagnose?.embedding_service_enabled);
  }, [ragDiagnose]);

  const ragTypeRows = useMemo(() => {
    const infos = ragDiagnose?.data_type_list || [];
    const types = ragDiagnose?.completeness?.types || [];
    const typeMap = new Map(types.map((t) => [t.data_type, t]));
    if (infos.length === 0 && types.length > 0) {
      return types.map((t) => {
        const ingest = ragIngestResult?.results?.[t.data_type];
        return {
          info: { value: t.data_type, display_name: t.display_name, weight: '', source_table: '' },
          completeness: t,
          ingest,
        };
      });
    }
    return infos.map((info) => {
      const completeness = typeMap.get(info.value);
      const ingest = ragIngestResult?.results?.[info.value];
      return { info, completeness, ingest };
    });
  }, [ragDiagnose, ragIngestResult]);

  const handleIngestAll = async (force: boolean) => {
    setRagIngesting(true);
    try {
      const result = await novelsApi.ingestAllRagData(projectId, force);
      setRagIngestResult(result);
      if (result.success) {
        addToast('RAG 入库完成', 'success');
      } else {
        addToast('RAG 入库失败，请查看结果详情', 'error');
      }
      await fetchRagDiagnose();
    } catch (e) {
      console.error(e);
    } finally {
      setRagIngesting(false);
    }
  };

  const handleEvaluate = async () => {
    if (!onEvaluateChapter) return;
    setIsEvaluating(true);
    try {
      await onEvaluateChapter();
    } finally {
      setIsEvaluating(false);
    }
  };

  return (
    <div className="w-full border-l border-book-border/50 bg-book-bg-paper flex flex-col h-full transition-all duration-300 shadow-xl relative z-30">
      {/* Tabs */}
      <div className="flex gap-1 overflow-x-auto no-scrollbar border-b border-book-border/50 bg-book-bg-paper sticky top-0 z-10 p-1">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => !tab.disabled && setActiveTab(tab.id as any)}
              disabled={tab.disabled}
              className={`
                flex-none min-w-[70px] px-2 py-2 text-[12px] font-bold flex flex-col items-center justify-center gap-1 transition-all relative rounded-md
                ${activeTab === tab.id 
                  ? 'text-book-primary bg-book-primary/5 shadow-inner' 
                  : 'text-book-text-muted hover:text-book-text-main hover:bg-book-bg'}
                ${tab.disabled ? 'opacity-40 cursor-not-allowed hover:bg-transparent hover:text-book-text-muted' : ''}
              `}
            >
              <Icon size={16} />
              {tab.label}
              {activeTab === tab.id && (
                <div className="absolute bottom-0 left-1/4 right-1/4 h-0.5 bg-book-primary rounded-full" />
              )}
            </button>
          );
        })}
      </div>

      <div className="flex-1 overflow-y-auto p-5 custom-scrollbar">
        {activeTab === 'outline' && (
          <div className="space-y-8 animate-in fade-in duration-500">
            <div className="space-y-3">
              <h3 className="text-xs font-black text-book-text-muted uppercase tracking-widest flex items-center gap-2">
                <FileText size={14} /> 本章大纲
              </h3>
              <div className="text-[15px] text-book-text-main leading-relaxed bg-book-bg p-4 rounded-xl border border-book-border/40 shadow-inner italic font-serif">
                {chapter?.summary || "暂无大纲内容"}
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="text-xs font-black text-book-text-muted uppercase tracking-widest flex items-center gap-2">
                <Sparkles size={14} /> 章节信息
              </h3>
              <BookCard className="p-4 text-sm bg-book-bg/50 border-book-border/50">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-bold text-book-text-main truncate">
                    {chapter?.title ? `${chapter.title}` : (chapterNumber ? `第${chapterNumber}章` : '未选择章节')}
                  </div>
                  <div className="text-xs text-book-text-muted font-mono">
                    {chapter?.word_count || 0}
                  </div>
                </div>
                <div className="text-xs text-book-text-muted mt-2">
                  状态：{chapter?.generation_status || '—'}
                </div>
                <div className="text-xs text-book-text-muted mt-1">
                  已选版本：{typeof chapter?.selected_version === 'number' ? `版本 ${chapter.selected_version + 1}` : '未选择'}
                </div>
                {onIngestRag && (
                  <div className="mt-3">
                    <BookButton
                      variant="secondary"
                      size="sm"
                      onClick={() => onIngestRag()}
                      disabled={Boolean(isIngestingRag)}
                    >
                      <Database size={14} className="mr-1" />
                      {isIngestingRag ? '入库中…' : '执行RAG处理'}
                    </BookButton>
                  </div>
                )}
              </BookCard>
            </div>
          </div>
        )}

        {activeTab === 'versions' && (
          <div className="animate-in fade-in duration-500">
            <ChapterVersionsView
              versions={Array.isArray(chapter?.versions) ? chapter!.versions! : []}
              selectedIndex={typeof chapter?.selected_version === 'number' ? chapter!.selected_version! : null}
              onSelectVersion={(idx) => onSelectVersion && onSelectVersion(idx)}
              onRetryVersion={(idx, prompt) => onRetryVersion && onRetryVersion(idx, prompt)}
              onUseContent={onChangeContent ? (text) => onChangeContent(text) : undefined}
            />
          </div>
        )}

        {activeTab === 'prompt' && chapterNumber && (
          <div className="animate-in fade-in duration-500">
            <ChapterPromptPreviewView
              projectId={projectId}
              chapterNumber={chapterNumber}
              writingNotes={writingNotes}
              onChangeWritingNotes={onChangeWritingNotes}
            />
          </div>
        )}

        {activeTab === 'review' && (
          <div className="animate-in fade-in duration-500">
            <ChapterReviewView
              evaluation={chapter?.evaluation || null}
              versionCount={Array.isArray(chapter?.versions) ? chapter!.versions!.length : 0}
              onEvaluate={handleEvaluate}
              isEvaluating={isEvaluating}
              onSelectVersion={(idx) => onSelectVersion && onSelectVersion(idx)}
            />
          </div>
        )}

        {activeTab === 'summary' && (
          <div className="animate-in fade-in duration-500">
            <ChapterSummaryView
              realSummary={chapter?.real_summary || null}
              onIngestRag={onIngestRag}
              isIngestingRag={isIngestingRag}
            />
          </div>
        )}

        {activeTab === 'analysis' && (
          <div className="animate-in fade-in duration-500">
            <ChapterAnalysisView
              analysisData={chapter?.analysis_data || null}
              onIngestRag={onIngestRag}
              isIngestingRag={isIngestingRag}
            />
          </div>
        )}

        {chapterNumber && optimizeMounted && (
          <div className={activeTab === 'optimize' ? 'animate-in fade-in duration-500' : 'hidden'}>
            <ErrorBoundary key={`optimize:${projectId}:${chapterNumber}`}>
              <ContentOptimizationView
                projectId={projectId}
                chapterNumber={chapterNumber}
                content={content || ''}
                onChangeContent={onChangeContent}
                onLocateText={onLocateText}
                onSelectRange={onSelectRange}
              />
            </ErrorBoundary>
          </div>
        )}

        {activeTab === 'portraits' && (
          <div className="animate-in fade-in duration-500">
            <CharacterPortraitGallery projectId={projectId} characterNames={characterNames} characterProfiles={characterProfiles} />
          </div>
        )}

        {activeTab === 'state' && chapterNumber && (
          <div className="animate-in fade-in duration-500">
            <CharacterStateView projectId={projectId} chapterNumber={chapterNumber} />
          </div>
        )}

        {chapterNumber && mangaMounted && (
          <div className={activeTab === 'manga' ? 'animate-in fade-in duration-500' : 'hidden'}>
            <ErrorBoundary key={`manga:${projectId}:${chapterNumber}`}>
              <MangaPromptViewer projectId={projectId} chapterNumber={chapterNumber} />
            </ErrorBoundary>
          </div>
        )}

	        {activeTab === 'rag' && (
	          <div className="space-y-6 animate-in fade-in duration-500">
	            <div className="flex items-center justify-between gap-2">
	              <div className="flex items-center gap-2 text-xs text-book-text-muted">
	                <Database size={14} className="text-book-primary" />
	                <span>
	                  向量库：{ragDiagnoseLoading ? '检测中…' : (ragDiagnose?.vector_store_enabled ? '已启用' : '不可用')}
	                </span>
	                <span className="opacity-40">|</span>
	                <span>
	                  嵌入：{ragDiagnoseLoading ? '检测中…' : (ragDiagnose?.embedding_service_enabled ? '已启用' : '不可用')}
	                </span>
	              </div>
		              <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1 text-[11px] text-book-text-muted">
                      <span className="font-bold">top_k</span>
                      <input
                        type="number"
                        min={1}
                        max={50}
                        value={ragTopK}
                        onChange={(e) => setRagTopK(Math.max(1, Math.min(50, Number(e.target.value) || 1)))}
                        className="w-14 px-2 py-1 rounded bg-book-bg border border-book-border/60 text-book-text-main outline-none focus:border-book-primary/60"
                        disabled={!vectorStoreReady}
                        title="RAG 检索返回数量（1-50）"
                      />
                    </div>
		                <BookButton
		                  variant="ghost"
		                  size="sm"
                      onClick={fetchRagDiagnose}
                      disabled={ragDiagnoseLoading}
                    >
                      <RefreshCw size={14} className={`mr-1 ${ragDiagnoseLoading ? 'animate-spin' : ''}`} />
		                  刷新
		                </BookButton>
                  </div>
		            </div>

	            {vectorStoreReady && ragDiagnose?.completeness && (
	              <BookCard className="p-3 text-xs bg-book-bg/50 border-book-border/50 space-y-2">
	                <div className="flex items-center justify-between gap-2">
	                  <div className="font-bold text-book-text-main">向量库完整性</div>
	                  <div className={`font-bold ${ragDiagnose.completeness.complete ? 'text-book-primary' : 'text-book-accent'}`}>
	                    {ragDiagnose.completeness.complete ? '已完成' : '未完成'}
	                  </div>
	                </div>
	                <div className="text-book-text-muted leading-relaxed">
	                  DB：{ragDiagnose.completeness.total_db_count} · 向量：{ragDiagnose.completeness.total_vector_count}
	                  · 新增：{ragDiagnose.completeness.total_new}
	                  · 修改：{ragDiagnose.completeness.total_modified}
	                  · 删除：{ragDiagnose.completeness.total_deleted}
	                </div>

	                {ragTypeRows.length > 0 && (
	                  <div className="grid grid-cols-1 gap-2 pt-1">
	                    {ragTypeRows.map(({ info, completeness, ingest }) => {
	                      const complete = Boolean(completeness?.complete);
	                      const title = info.display_name || info.value;
	                      return (
	                        <div
	                          key={`rag-type-${info.value}`}
	                          className="rounded-lg border border-book-border/40 bg-book-bg p-2"
	                        >
	                          <div className="flex items-center justify-between gap-2">
	                            <div className="font-bold text-book-text-main truncate">{title}</div>
	                            <div className={`text-[11px] font-bold ${complete ? 'text-book-primary' : 'text-book-text-muted'}`}>
	                              {complete ? '完成' : '待入库'}
	                            </div>
	                          </div>
	                          <div className="mt-1 text-[11px] text-book-text-muted font-mono">
	                            db={completeness?.db_count ?? '-'} · vec={completeness?.vector_count ?? '-'}
	                            · +{completeness?.new_count ?? 0} · ~{completeness?.modified_count ?? 0} · -{completeness?.deleted_count ?? 0}
	                          </div>
	                          {ingest && (
	                            <div className="mt-1 text-[11px] text-book-text-muted">
	                              入库：<span className={ingest.success ? 'text-book-primary font-bold' : 'text-book-accent font-bold'}>
	                                {ingest.success ? '成功' : '失败'}
	                              </span>
	                              <span className="ml-2 font-mono">+{ingest.added_count ?? 0} · ~{ingest.updated_count ?? 0}</span>
	                              {ingest.error_message ? (
	                                <div className="mt-1 text-book-accent whitespace-pre-wrap">{ingest.error_message}</div>
	                              ) : null}
	                            </div>
	                          )}
	                        </div>
	                      );
	                    })}
	                  </div>
	                )}
	              </BookCard>
	            )}

	            {!vectorStoreReady && (
	              <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 leading-relaxed">
	                RAG 目前不可用：向量库未启用或初始化失败。
                <div className="mt-2 opacity-80">
                  向量库默认使用 `storage/vectors.db`。如仍不可用请检查后端依赖（libsql-client）与启动日志。
                </div>
              </div>
            )}

            <div className="flex gap-2">
              <BookButton
                variant="primary"
                size="sm"
                onClick={() => handleIngestAll(false)}
                disabled={!ingestReady || ragIngesting}
                className="flex-1"
              >
                {ragIngesting ? <Loader2 size={14} className="mr-2 animate-spin" /> : <Database size={14} className="mr-2" />}
                智能入库
              </BookButton>
              <BookButton
                variant="ghost"
                size="sm"
                onClick={() => handleIngestAll(true)}
                disabled={!ingestReady || ragIngesting}
                className="flex-1"
              >
                强制重建
              </BookButton>
            </div>

            {vectorStoreReady && !ingestReady && (
              <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 leading-relaxed">
                提示：入库功能需要 LLM 服务可用（用于分析/摘要与向量化）。你可以在“全局设置 → LLM / 嵌入”中完成配置与测试。
              </div>
            )}

            {ragIngestResult && (
              <BookCard className="p-3 text-xs bg-book-bg/50 border-book-border/50">
                <div className="flex items-center justify-between mb-2">
                  <div className="font-bold text-book-text-main">入库结果</div>
                  <div className={`font-bold ${ragIngestResult.success ? 'text-book-primary' : 'text-book-accent'}`}>
                    {ragIngestResult.success ? '成功' : '失败'}
                  </div>
                </div>
                <div className="text-book-text-muted leading-relaxed">
                  新增 {ragIngestResult.total_added}，更新 {ragIngestResult.total_updated}，跳过 {ragIngestResult.total_skipped}
                </div>
              </BookCard>
            )}

            <div className="relative group">
              <input 
                type="text"
                placeholder="检索世界观、设定、伏笔..."
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleRagSearch()}
                className="w-full pl-10 pr-10 py-3 text-sm bg-book-bg rounded-xl border border-book-border/60 focus:border-book-primary/60 focus:ring-2 focus:ring-book-primary/10 outline-none transition-all shadow-inner"
                disabled={!vectorStoreReady}
              />
              <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-book-text-muted group-focus-within:text-book-primary transition-colors" />
              {isRagLoading && <Loader2 size={16} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-book-primary animate-spin" />}
            </div>

            <div className="space-y-4">
              {ragResults?.message && (
                <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50">
                  {ragResults.message}
                </div>
              )}

              {ragResults?.summaries?.map((s: any, i: number) => (
                <BookCard
                  key={`summary-${s.chapter_number ?? 'unknown'}-${i}`}
                  className={`
                    p-4 text-sm bg-book-bg/50 border-book-border/50 hover:border-book-primary/20 transition-all
                    ${onJumpToChapter && s?.chapter_number ? 'cursor-pointer hover:shadow-sm' : ''}
                  `}
                  onClick={() => {
                    const n = Number(s?.chapter_number || 0);
                    if (!onJumpToChapter || !n) return;
                    onJumpToChapter(n);
                  }}
                  title={onJumpToChapter && s?.chapter_number ? '点击跳转到该章节' : undefined}
                >
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[10px] font-bold text-book-primary uppercase tracking-tighter">
                      摘要 · 第 {s.chapter_number} 章
                    </span>
                    <span className="text-[10px] text-book-text-muted">{Math.round((1 - s.score) * 100)}% 相关</span>
                  </div>
                  <div className="text-xs font-bold text-book-text-main mb-1">{s.title}</div>
                  <p className="text-book-text-main leading-relaxed line-clamp-4 italic">{s.summary}</p>
                </BookCard>
              ))}

              {ragResults?.chunks?.map((chunk: any, i: number) => (
                <BookCard
                  key={`chunk-${chunk.chapter_number ?? 'unknown'}-${i}`}
                  className={`
                    p-4 text-sm bg-book-bg/50 border-book-primary/10 hover:border-book-primary/30 transition-all
                    ${onJumpToChapter && chunk?.chapter_number ? 'cursor-pointer hover:shadow-sm' : ''}
                  `}
                  onClick={async () => {
                    const n = Number(chunk?.chapter_number || 0);
                    if (!onJumpToChapter || !n) return;
                    try {
                      await onJumpToChapter(n);
                    } catch {
                      // ignore
                    }
                    if (onLocateText && chunk?.content) {
                      onLocateText(String(chunk.content));
                    }
                  }}
                  title={onJumpToChapter && chunk?.chapter_number ? '点击跳转到该章节' : undefined}
                >
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[10px] font-bold text-book-primary uppercase tracking-tighter">第 {chunk.chapter_number} 章</span>
                    <span className="text-[10px] text-book-text-muted">{Math.round((1 - chunk.score) * 100)}% 相关</span>
                  </div>
                  <p className="text-book-text-main leading-relaxed line-clamp-4 italic">{chunk.content}</p>
                </BookCard>
              ))}
              
              {!ragResults && !isRagLoading && (
                <div className="py-20 text-center text-book-text-muted opacity-40">
                  <Sparkles size={40} className="mx-auto mb-4" />
                  <p className="text-xs tracking-widest font-bold">在此检索你的宏大世界</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
