import React, { useEffect, useMemo, useState } from 'react';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';
import { Sparkles, FileText, User, Layers, Search, Loader2, Database, RefreshCw } from 'lucide-react';
import { CharacterPortraitGallery } from './CharacterPortraitGallery';
import { MangaPromptViewer } from './MangaPromptViewer';
import { novelsApi, RagDiagnoseResponse, RagIngestAllResponse } from '../../api/novels';
import { useToast } from '../feedback/Toast';

interface AssistantPanelProps {
  projectId: string;
  chapterNumber?: number;
  summary?: string;
  outline?: string;
}

export const AssistantPanel: React.FC<AssistantPanelProps> = ({
  projectId,
  chapterNumber,
  summary,
  outline
}) => {
  const [activeTab, setActiveTab] = useState<'outline' | 'portraits' | 'manga' | 'rag'>('outline');
  const [ragQuery, setRagQuery] = useState('');
  const [ragResults, setRagResults] = useState<any>(null);
  const [isRagLoading, setIsRagLoading] = useState(false);
  const [ragDiagnose, setRagDiagnose] = useState<RagDiagnoseResponse | null>(null);
  const [ragDiagnoseLoading, setRagDiagnoseLoading] = useState(false);
  const [ragIngesting, setRagIngesting] = useState(false);
  const [ragIngestResult, setRagIngestResult] = useState<RagIngestAllResponse | null>(null);
  const { addToast } = useToast();

  const tabs = [
    { id: 'outline', label: '大纲', icon: FileText },
    { id: 'portraits', label: '角色', icon: User },
    { id: 'manga', label: '漫画', icon: Layers },
    { id: 'rag', label: '知识库', icon: Sparkles },
  ];

  const handleRagSearch = async () => {
    if (!ragQuery.trim()) return;
    setIsRagLoading(true);
    try {
      const results = await novelsApi.queryRAG(projectId, ragQuery);
      setRagResults(results);
    } catch (e) {
      console.error(e);
    } finally {
      setIsRagLoading(false);
    }
  };

  const fetchRagDiagnose = async () => {
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
  };

  useEffect(() => {
    if (activeTab !== 'rag') return;
    fetchRagDiagnose();
  }, [activeTab, projectId]);

  const vectorStoreReady = useMemo(() => {
    return Boolean(ragDiagnose?.vector_store_enabled);
  }, [ragDiagnose]);

  // 入库（分析/摘要/向量化）依赖 LLMService；纯检索依赖 EmbeddingService（由 /rag/query 自行检查）
  const ingestReady = useMemo(() => {
    return Boolean(ragDiagnose?.vector_store_enabled && ragDiagnose?.embedding_service_enabled);
  }, [ragDiagnose]);

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

  return (
    <div className="w-96 border-l border-book-border/50 bg-book-bg-paper flex flex-col h-full transition-all duration-300 shadow-xl relative z-30">
      {/* Tabs */}
      <div className="flex border-b border-book-border/50 bg-book-bg-paper sticky top-0 z-10 p-1">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`
                flex-1 py-2.5 text-[13px] font-bold flex flex-col items-center justify-center gap-1 transition-all relative rounded-md
                ${activeTab === tab.id 
                  ? 'text-book-primary bg-book-primary/5 shadow-inner' 
                  : 'text-book-text-muted hover:text-book-text-main hover:bg-book-bg'}
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
                {outline || "暂无大纲内容"}
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="text-xs font-black text-book-text-muted uppercase tracking-widest flex items-center gap-2">
                <Sparkles size={14} /> 章节摘要
              </h3>
              <div className="text-sm text-book-text-secondary leading-loose">
                {summary || "内容生成后将在此显示摘要"}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'portraits' && (
          <div className="animate-in fade-in duration-500">
            <CharacterPortraitGallery projectId={projectId} />
          </div>
        )}

        {activeTab === 'manga' && chapterNumber && (
          <div className="animate-in fade-in duration-500">
            <MangaPromptViewer projectId={projectId} chapterNumber={chapterNumber} />
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
                  LLM：{ragDiagnoseLoading ? '检测中…' : (ragDiagnose?.embedding_service_enabled ? '已启用' : '不可用')}
                </span>
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
                  className="p-4 text-sm bg-book-bg/50 border-book-border/50 hover:border-book-primary/20 transition-all"
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
                <BookCard key={`chunk-${chunk.chapter_number ?? 'unknown'}-${i}`} className="p-4 text-sm bg-book-bg/50 border-book-primary/10 hover:border-book-primary/30 transition-all">
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
