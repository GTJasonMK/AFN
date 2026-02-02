import React, { useMemo, useState, useEffect, useCallback } from 'react';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';
import { BarChart3, Database, Loader2, RefreshCw } from 'lucide-react';
import { InsightCard } from './chapter/components/InsightCard';
import { writerApi } from '../../api/writer';
import { useToast } from '../feedback/Toast';

type AnyObj = Record<string, any>;

const asArray = (v: any): any[] => (Array.isArray(v) ? v : []);

const Chip: React.FC<{ children: React.ReactNode; className?: string; title?: string }> = ({ children, className = '', title }) => (
  <span
    title={title}
    className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] border border-book-border/50 bg-book-bg ${className}`}
  >
    {children}
  </span>
);

interface ChapterAnalysisViewProps {
  projectId: string;
  chapterNumber: number;
}

export const ChapterAnalysisView: React.FC<ChapterAnalysisViewProps> = ({
  projectId,
  chapterNumber,
}) => {
  const { addToast } = useToast();
  const [analysisData, setAnalysisData] = useState<AnyObj | null>(null);
  const [loading, setLoading] = useState(true);
  const [isIngestingRag, setIsIngestingRag] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const chapter = await writerApi.getChapter(projectId, chapterNumber);
      setAnalysisData(chapter.analysis_data || null);
    } catch (e) {
      console.error(e);
      addToast('获取分析数据失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast, chapterNumber, projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleIngestRag = async () => {
    setIsIngestingRag(true);
    try {
      // 获取当前章节内容
      const chapter = await writerApi.getChapter(projectId, chapterNumber);
      const content = chapter.content || '';
      // 触发RAG处理
      await writerApi.updateChapter(projectId, chapterNumber, content, { triggerRag: true });
      addToast('RAG处理完成', 'success');
      await fetchData();
    } catch (e) {
      console.error(e);
      addToast('RAG处理失败', 'error');
    } finally {
      setIsIngestingRag(false);
    }
  };

  const hasData = Boolean(analysisData && Object.keys(analysisData || {}).length > 0);

  const metadata = useMemo(() => (analysisData?.metadata || null) as AnyObj | null, [analysisData]);
  const summaries = useMemo(() => (analysisData?.summaries || null) as AnyObj | null, [analysisData]);
  const characterStates = useMemo(() => (analysisData?.character_states || {}) as Record<string, AnyObj>, [analysisData]);
  const keyEvents = useMemo(() => asArray(analysisData?.key_events), [analysisData]);
  const foreshadowing = useMemo(() => (analysisData?.foreshadowing || null) as AnyObj | null, [analysisData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 size={24} className="animate-spin text-book-primary" />
      </div>
    );
  }

  if (!hasData) {
    return (
      <div className="space-y-4">
        <InsightCard
          icon={<BarChart3 size={16} className="text-book-primary" />}
          title="暂无章节分析"
          description="章节分析会在执行 RAG 处理后自动生成（角色状态、伏笔、关键事件等），用于保证后续章节连贯性。"
          actions={
            <BookButton
              variant="secondary"
              size="sm"
              onClick={handleIngestRag}
              disabled={Boolean(isIngestingRag)}
            >
              <Database size={14} className="mr-1" />
              {isIngestingRag ? '入库中...' : '生成分析'}
            </BookButton>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <InsightCard
        icon={<BarChart3 size={16} className="text-book-primary" />}
        title="章节分析"
        description="结构化信息：角色状态 / 伏笔 / 关键事件 / 元数据"
        descriptionClassName="text-xs text-book-text-muted mt-1"
        actions={
          <div className="flex items-center gap-2">
            <BookButton variant="ghost" size="sm" onClick={fetchData}>
              <RefreshCw size={14} />
            </BookButton>
            <BookButton
              variant="ghost"
              size="sm"
              onClick={handleIngestRag}
              disabled={Boolean(isIngestingRag)}
              title="重新执行RAG处理（会刷新摘要/分析/索引/向量库）"
            >
              <Database size={14} className="mr-1" />
              {isIngestingRag ? '入库中...' : '重新入库'}
            </BookButton>
          </div>
        }
      />

      {summaries && (
        <BookCard className="p-4 space-y-3">
          <div className="text-xs font-black text-book-text-muted uppercase tracking-widest">分级摘要</div>
          {summaries.one_line && (
            <div className="text-sm text-book-text-main">
              <span className="font-bold text-book-primary mr-2">一句话</span>
              <span className="italic">{String(summaries.one_line)}</span>
            </div>
          )}
          {summaries.compressed && (
            <div className="text-sm text-book-text-main leading-relaxed">
              <span className="font-bold text-book-primary mr-2">压缩</span>
              <span className="italic">{String(summaries.compressed)}</span>
            </div>
          )}
          {asArray(summaries.keywords).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {asArray(summaries.keywords).map((k, idx) => (
                <Chip key={`kw-${idx}`} className="text-book-primary">
                  {String(k)}
                </Chip>
              ))}
            </div>
          )}
        </BookCard>
      )}

      {metadata && (
        <BookCard className="p-4 space-y-3">
          <div className="text-xs font-black text-book-text-muted uppercase tracking-widest">元数据</div>

          {asArray(metadata.characters).length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-bold text-book-text-sub">角色</div>
              <div className="flex flex-wrap gap-2">
                {asArray(metadata.characters).map((v, idx) => (
                  <Chip key={`c-${idx}`} className="text-green-700 dark:text-green-200">
                    {String(v)}
                  </Chip>
                ))}
              </div>
            </div>
          )}

          {asArray(metadata.locations).length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-bold text-book-text-sub">地点</div>
              <div className="flex flex-wrap gap-2">
                {asArray(metadata.locations).map((v, idx) => (
                  <Chip key={`l-${idx}`} className="text-blue-700 dark:text-blue-200">
                    {String(v)}
                  </Chip>
                ))}
              </div>
            </div>
          )}

          {asArray(metadata.items).length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-bold text-book-text-sub">物品</div>
              <div className="flex flex-wrap gap-2">
                {asArray(metadata.items).map((v, idx) => (
                  <Chip key={`i-${idx}`} className="text-orange-700 dark:text-orange-200">
                    {String(v)}
                  </Chip>
                ))}
              </div>
            </div>
          )}

          {asArray(metadata.tags).length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-bold text-book-text-sub">标签</div>
              <div className="flex flex-wrap gap-2">
                {asArray(metadata.tags).map((v, idx) => (
                  <Chip key={`t-${idx}`} className="text-book-text-main">
                    {String(v)}
                  </Chip>
                ))}
              </div>
            </div>
          )}
        </BookCard>
      )}

      {Object.keys(characterStates || {}).length > 0 && (
        <BookCard className="p-4 space-y-3">
          <div className="text-xs font-black text-book-text-muted uppercase tracking-widest">角色状态</div>
          <div className="space-y-3">
            {Object.entries(characterStates).map(([name, state]) => (
              <div key={name} className="border border-book-border/40 rounded-lg p-3 bg-book-bg">
                <div className="font-bold text-book-primary">{name}</div>
                <div className="text-xs text-book-text-muted mt-1 space-y-1">
                  {state.location ? <div>地点：{String(state.location)}</div> : null}
                  {state.status ? <div>状态：{String(state.status)}</div> : null}
                  {state.emotional_state ? <div>情绪：{String(state.emotional_state)}</div> : null}
                </div>
                {asArray(state.changes).length > 0 && (
                  <ul className="mt-2 list-disc list-inside text-xs text-book-text-main space-y-1">
                    {asArray(state.changes).map((c, idx) => (
                      <li key={`${name}-chg-${idx}`}>{String(c)}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </BookCard>
      )}

      {keyEvents.length > 0 && (
        <BookCard className="p-4 space-y-3">
          <div className="text-xs font-black text-book-text-muted uppercase tracking-widest">关键事件</div>
          <div className="space-y-3">
            {keyEvents.map((evt, idx) => (
              <div key={`evt-${idx}`} className="border border-book-border/40 rounded-lg p-3 bg-book-bg">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-bold text-book-text-main">{String(evt.type || 'event')}</div>
                  <Chip className="text-book-text-muted">{String(evt.importance || 'medium')}</Chip>
                </div>
                <div className="text-sm text-book-text-main mt-2 leading-relaxed">
                  {String(evt.description || '')}
                </div>
                {asArray(evt.involved_characters).length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {asArray(evt.involved_characters).map((n, i) => (
                      <Chip key={`evt-${idx}-c-${i}`} className="text-green-700 dark:text-green-200">
                        {String(n)}
                      </Chip>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </BookCard>
      )}

      {foreshadowing && (
        <BookCard className="p-4 space-y-3">
          <div className="text-xs font-black text-book-text-muted uppercase tracking-widest">伏笔追踪</div>

          {asArray(foreshadowing.planted).length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-bold text-book-text-sub">已埋下</div>
              <div className="space-y-2">
                {asArray(foreshadowing.planted).map((it, idx) => (
                  <div key={`planted-${idx}`} className="border border-book-border/40 rounded-lg p-3 bg-book-bg">
                    <div className="font-bold text-book-text-main">{String(it.hint || it.title || `伏笔${idx + 1}`)}</div>
                    {it.detail ? (
                      <div className="text-xs text-book-text-muted mt-1 whitespace-pre-wrap">{String(it.detail)}</div>
                    ) : null}
                    {it.expected_payoff ? (
                      <div className="text-xs text-book-text-muted mt-1">预期回收：{String(it.expected_payoff)}</div>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          )}

          {asArray(foreshadowing.resolved).length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-bold text-book-text-sub">已回收</div>
              <div className="space-y-2">
                {asArray(foreshadowing.resolved).map((it, idx) => (
                  <div key={`resolved-${idx}`} className="border border-book-border/40 rounded-lg p-3 bg-book-bg">
                    <div className="font-bold text-book-text-main">{String(it.hint || it.title || `回收${idx + 1}`)}</div>
                    {it.payoff ? (
                      <div className="text-xs text-book-text-muted mt-1 whitespace-pre-wrap">{String(it.payoff)}</div>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          )}

          {asArray(foreshadowing.tensions).length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-bold text-book-text-sub">未解悬念</div>
              <div className="flex flex-wrap gap-2">
                {asArray(foreshadowing.tensions).map((t, idx) => (
                  <Chip key={`ten-${idx}`} className="text-book-text-main">
                    {String(t)}
                  </Chip>
                ))}
              </div>
            </div>
          )}
        </BookCard>
      )}
    </div>
  );
};
