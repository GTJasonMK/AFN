/**
 * 写作台助手面板 - 照抄桌面端 writing_desk/assistant_panel.py
 *
 * 支持两种模式：
 * 1. RAG查询 - 检索向量库内容
 * 2. 正文优化 - Agent分析正文并提供修改建议
 */

import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';
import { Search, Loader2, Database, RefreshCw } from 'lucide-react';
import { novelsApi, RagDiagnoseResponse, RagIngestAllResponse } from '../../api/novels';
import { useToast } from '../feedback/Toast';
import { ErrorBoundary } from '../feedback/ErrorBoundary';
import { ContentOptimizationView } from './ContentOptimizationView';
import { usePersistedState } from '../../hooks/usePersistedState';

// 只保留两种模式，照抄桌面端
export type AssistantMode = 'rag' | 'optimize';

const ASSISTANT_MODE_STORAGE_KEY = (projectId: string) => `afn:assistant_mode:${projectId}`;

interface AssistantPanelProps {
  projectId: string;
  chapterNumber?: number;
  content?: string;
  onChangeContent?: (value: string) => void;
  onJumpToChapter?: (chapterNumber: number) => void | Promise<void>;
  onLocateText?: (text: string) => void;
  onSelectRange?: (start: number, end: number) => void;
}

export const AssistantPanel: React.FC<AssistantPanelProps> = ({
  projectId,
  chapterNumber,
  content,
  onChangeContent,
  onJumpToChapter,
  onLocateText,
  onSelectRange,
}) => {
  // 当前模式：rag 或 optimize，照抄桌面端默认 rag
  const [currentMode, setCurrentMode] = usePersistedState<AssistantMode>(
    ASSISTANT_MODE_STORAGE_KEY(projectId),
    'rag',
    {
      parse: (raw) => {
        if (raw === 'optimize' || raw === 'rag') return raw;
        return 'rag';
      },
      serialize: (value) => value,
    },
  );

  // RAG 相关状态
  const [ragQuery, setRagQuery] = useState('');
  const [ragTopK, setRagTopK] = usePersistedState<number>(
    `afn:rag_topk:${projectId}`,
    10,
    {
      parse: (raw) => {
        const n = Number(raw);
        if (!Number.isFinite(n)) return 10;
        return Math.max(1, Math.min(50, n));
      },
      serialize: (value) => String(value),
    },
  );
  const [ragResults, setRagResults] = useState<any>(null);
  const [isRagLoading, setIsRagLoading] = useState(false);
  const [ragDiagnose, setRagDiagnose] = useState<RagDiagnoseResponse | null>(null);
  const [ragDiagnoseLoading, setRagDiagnoseLoading] = useState(false);
  const [ragIngesting, setRagIngesting] = useState(false);
  const [ragIngestResult, setRagIngestResult] = useState<RagIngestAllResponse | null>(null);

  // 正文优化模式是否已挂载（keep-alive）
  const [optimizeMounted, setOptimizeMounted] = useState(currentMode === 'optimize');

  const { addToast } = useToast();

  // 切换到优化模式时挂载组件
  useEffect(() => {
    if (currentMode === 'optimize') setOptimizeMounted(true);
  }, [currentMode]);

  // 切换模式
  const switchMode = (mode: AssistantMode) => {
    if (mode === currentMode) return;
    setCurrentMode(mode);
  };

  // RAG 诊断
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
    if (currentMode !== 'rag') return;
    fetchRagDiagnose();
  }, [currentMode, fetchRagDiagnose]);

  const vectorStoreReady = useMemo(() => {
    return Boolean(ragDiagnose?.vector_store_enabled);
  }, [ragDiagnose]);

  const ingestReady = useMemo(() => {
    return Boolean(ragDiagnose?.vector_store_enabled && ragDiagnose?.embedding_service_enabled);
  }, [ragDiagnose]);

  // RAG 查询
  const handleRagSearch = async () => {
    if (!ragQuery.trim()) return;
    if (ragDiagnose && ragDiagnose.vector_store_enabled === false) {
      addToast('向量库未启用，无法检索', 'error');
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

  // RAG 入库
  const handleIngestAll = async (force: boolean) => {
    setRagIngesting(true);
    try {
      const result = await novelsApi.ingestAllRagData(projectId, force);
      setRagIngestResult(result);
      if (result.success) {
        addToast('RAG 入库完成', 'success');
      } else {
        addToast('RAG 入库失败', 'error');
      }
      await fetchRagDiagnose();
    } catch (e) {
      console.error(e);
    } finally {
      setRagIngesting(false);
    }
  };

  const ragTypeRows = useMemo(() => {
    const rawInfos = ragDiagnose?.data_type_list;
    const infos = Array.isArray(rawInfos) ? rawInfos : [];
    const rawTypes = ragDiagnose?.completeness?.types;
    const types = Array.isArray(rawTypes) ? rawTypes : [];
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

  return (
    <div className="w-full border-l border-book-border/50 bg-book-bg-paper flex flex-col h-full">
      {/* 模式切换按钮 - 照抄桌面端 assistant_panel.py */}
      <div className="h-12 border-b border-book-border/50 flex items-center px-4 gap-2 shrink-0">
        <button
          onClick={() => switchMode('rag')}
          className={`px-4 py-1.5 rounded text-sm font-bold transition-all ${
            currentMode === 'rag'
              ? 'bg-book-primary text-white'
              : 'bg-transparent border border-book-border text-book-text-muted hover:text-book-primary hover:border-book-primary/50'
          }`}
        >
          RAG查询
        </button>
        <button
          onClick={() => switchMode('optimize')}
          className={`px-4 py-1.5 rounded text-sm font-bold transition-all ${
            currentMode === 'optimize'
              ? 'bg-book-primary text-white'
              : 'bg-transparent border border-book-border text-book-text-muted hover:text-book-primary hover:border-book-primary/50'
          }`}
        >
          正文优化
        </button>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {/* RAG查询模式 */}
        {currentMode === 'rag' && (
          <div className="p-4 space-y-4 animate-in fade-in duration-300">
            {/* RAG 头部：top_k 选择器 */}
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-xs text-book-text-muted">
                <Database size={14} className="text-book-primary" />
                <span>
                  向量库：{ragDiagnoseLoading ? '检测中...' : (ragDiagnose?.vector_store_enabled ? '已启用' : '不可用')}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1 text-[11px] text-book-text-muted">
                  <span className="font-bold">返回数量:</span>
                  <input
                    type="number"
                    min={1}
                    max={30}
                    value={ragTopK}
                    onChange={(e) => setRagTopK(Math.max(1, Math.min(30, Number(e.target.value) || 10)))}
                    className="w-14 px-2 py-1 rounded bg-book-bg border border-book-border/60 text-book-text-main outline-none focus:border-book-primary/60"
                    disabled={!vectorStoreReady}
                  />
                </div>
                <BookButton
                  variant="ghost"
                  size="sm"
                  onClick={fetchRagDiagnose}
                  disabled={ragDiagnoseLoading}
                >
                  <RefreshCw size={14} className={ragDiagnoseLoading ? 'animate-spin' : ''} />
                </BookButton>
              </div>
            </div>

            {/* 入库按钮 */}
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

            {/* 入库结果 */}
            {ragIngestResult && (
              <BookCard className="p-3 text-xs bg-book-bg/50 border-book-border/50">
                <div className="flex items-center justify-between mb-2">
                  <div className="font-bold text-book-text-main">入库结果</div>
                  <div className={`font-bold ${ragIngestResult.success ? 'text-book-primary' : 'text-book-accent'}`}>
                    {ragIngestResult.success ? '成功' : '失败'}
                  </div>
                </div>
                <div className="text-book-text-muted">
                  新增 {ragIngestResult.total_added}，更新 {ragIngestResult.total_updated}，跳过 {ragIngestResult.total_skipped}
                </div>
              </BookCard>
            )}

            {/* 向量库完整性 */}
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
                          </div>
                          {ingest && (
                            <div className="mt-1 text-[11px] text-book-text-muted">
                              入库：<span className={ingest.success ? 'text-book-primary font-bold' : 'text-book-accent font-bold'}>
                                {ingest.success ? '成功' : '失败'}
                              </span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </BookCard>
            )}

            {/* 不可用提示 */}
            {!vectorStoreReady && (
              <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 leading-relaxed">
                RAG 目前不可用：向量库未启用或初始化失败。
              </div>
            )}

            {/* 查询输入框 */}
            <div className="relative group">
              <input
                type="text"
                placeholder="输入查询内容，检索项目相关上下文..."
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleRagSearch()}
                className="w-full pl-10 pr-10 py-3 text-sm bg-book-bg rounded-lg border border-book-border/60 focus:border-book-primary/60 outline-none transition-all"
                disabled={!vectorStoreReady}
              />
              <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-book-text-muted" />
              {isRagLoading && <Loader2 size={16} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-book-primary animate-spin" />}
            </div>

            {/* 查询结果 */}
            <div className="space-y-3">
              {ragResults?.message && (
                <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50">
                  {ragResults.message}
                </div>
              )}

              {ragResults?.summaries?.map((s: any, i: number) => (
                <BookCard
                  key={`summary-${s.chapter_number ?? 'unknown'}-${i}`}
                  className={`p-3 text-sm bg-book-bg/50 border-book-border/50 hover:border-book-primary/20 transition-all ${
                    onJumpToChapter && s?.chapter_number ? 'cursor-pointer' : ''
                  }`}
                  onClick={() => {
                    const n = Number(s?.chapter_number || 0);
                    if (onJumpToChapter && n) onJumpToChapter(n);
                  }}
                >
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[10px] font-bold text-book-primary uppercase">
                      摘要 · 第 {s.chapter_number} 章
                    </span>
                    <span className="text-[10px] text-book-text-muted">{Math.round((1 - s.score) * 100)}% 相关</span>
                  </div>
                  <div className="text-xs font-bold text-book-text-main mb-1">{s.title}</div>
                  <p className="text-book-text-main text-xs leading-relaxed line-clamp-4">{s.summary}</p>
                </BookCard>
              ))}

              {ragResults?.chunks?.map((chunk: any, i: number) => (
                <BookCard
                  key={`chunk-${chunk.chapter_number ?? 'unknown'}-${i}`}
                  className={`p-3 text-sm bg-book-bg/50 border-book-primary/10 hover:border-book-primary/30 transition-all ${
                    onJumpToChapter && chunk?.chapter_number ? 'cursor-pointer' : ''
                  }`}
                  onClick={async () => {
                    const n = Number(chunk?.chapter_number || 0);
                    if (onJumpToChapter && n) {
                      await onJumpToChapter(n);
                      if (onLocateText && chunk?.content) {
                        onLocateText(String(chunk.content));
                      }
                    }
                  }}
                >
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[10px] font-bold text-book-primary uppercase">第 {chunk.chapter_number} 章</span>
                    <span className="text-[10px] text-book-text-muted">{Math.round((1 - chunk.score) * 100)}% 相关</span>
                  </div>
                  <p className="text-book-text-main text-xs leading-relaxed line-clamp-4">{chunk.content}</p>
                </BookCard>
              ))}

              {!ragResults && !isRagLoading && (
                <div className="py-12 text-center text-book-text-muted opacity-60">
                  <Database size={32} className="mx-auto mb-3 opacity-40" />
                  <p className="text-xs">输入查询内容，检索项目相关上下文</p>
                  <p className="text-[11px] mt-2 opacity-70">
                    可查询内容包括：世界观、角色设定、剧情伏笔等
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 正文优化模式 */}
        {chapterNumber && optimizeMounted && (
          <div className={currentMode === 'optimize' ? 'animate-in fade-in duration-300' : 'hidden'}>
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

        {/* 正文优化模式 - 未选择章节提示 */}
        {currentMode === 'optimize' && !chapterNumber && (
          <div className="p-4">
            <div className="py-12 text-center text-book-text-muted opacity-60">
              <p className="text-xs">请先选择一个章节</p>
              <p className="text-[11px] mt-2 opacity-70">
                正文优化功能需要选择具体章节后才能使用
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
