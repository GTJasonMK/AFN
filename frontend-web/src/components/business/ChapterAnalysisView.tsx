import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Database, Loader2, RefreshCw } from 'lucide-react';
import { BookButton } from '../ui/BookButton';
import { writerApi } from '../../api/writer';
import { useToast } from '../feedback/Toast';
import {
  NovelDialogIntro,
  NovelDialogMetric,
  NovelDialogMetricGrid,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from './novel/NovelDialogPrimitives';

type AnyObj = Record<string, any>;

const asArray = (v: any): any[] => (Array.isArray(v) ? v : []);

const Chip: React.FC<{ children: React.ReactNode; className?: string; title?: string }> = ({
  children,
  className = '',
  title,
}) => (
  <span
    title={title}
    className={`inline-flex items-center rounded-full border border-book-border/45 bg-book-bg px-3 py-1 text-[11px] ${className}`}
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
      const chapter = await writerApi.getChapter(projectId, chapterNumber);
      const content = chapter.content || '';
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
  const summaryKeywords = useMemo(() => asArray(summaries?.keywords), [summaries]);
  const plantedForeshadowing = useMemo(() => asArray(foreshadowing?.planted), [foreshadowing]);
  const resolvedForeshadowing = useMemo(() => asArray(foreshadowing?.resolved), [foreshadowing]);
  const tensionForeshadowing = useMemo(() => asArray(foreshadowing?.tensions), [foreshadowing]);

  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-[28px] border border-book-border/45 bg-book-bg-paper/72 p-10">
        <Loader2 size={24} className="animate-spin text-book-primary" />
      </div>
    );
  }

  if (!hasData) {
    return (
      <NovelDialogStack>
        <NovelDialogIntro
          eyebrow="Analysis Empty"
          title="章节分析还没有生成"
          description="分析数据会在执行 RAG 处理后自动生成，包括角色状态、关键事件、伏笔线索与元数据。"
          tone="warning"
        >
          <div className="flex flex-wrap gap-2">
            <span className="story-pill">第 {chapterNumber} 章</span>
            <span className="story-pill">等待结构化分析</span>
          </div>
        </NovelDialogIntro>

        <NovelDialogMetricGrid>
          <NovelDialogMetric label="输出范围" value="角色 / 事件 / 伏笔" note="结果会帮助你判断章节是否具备继续生成的条件。" />
          <NovelDialogMetric label="触发方式" value="RAG 入库" note="摘要、分析、索引与向量库会在同一次处理里刷新。" />
        </NovelDialogMetricGrid>

        <NovelDialogSection
          eyebrow="Next Action"
          title="生成章节分析"
          description="建议在大纲调整或正文大改后重新执行，保证人物与事件状态准确。"
          actions={(
            <BookButton
              variant="secondary"
              size="sm"
              onClick={handleIngestRag}
              disabled={Boolean(isIngestingRag)}
            >
              <Database size={14} />
              {isIngestingRag ? '入库中…' : '生成分析'}
            </BookButton>
          )}
        >
          <NovelDialogSurface className="text-sm leading-relaxed text-book-text-sub">
            当前还没有生成可供回看的结构化分析。完成入库后，这里会自动显示角色状态、关键事件和伏笔追踪。
          </NovelDialogSurface>
        </NovelDialogSection>
      </NovelDialogStack>
    );
  }

  return (
    <NovelDialogStack>
      <NovelDialogSection
        eyebrow="Analysis Stage"
        title="章节分析"
        description="把章节的关键事件、角色变化和伏笔状态收束为结构化视图，便于继续推进故事。"
        actions={(
          <>
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
              <Database size={14} />
              {isIngestingRag ? '入库中…' : '重新入库'}
            </BookButton>
          </>
        )}
      >
        <NovelDialogMetricGrid className="xl:grid-cols-4">
          <NovelDialogMetric label="关键事件" value={keyEvents.length} note="用于判断章节推进与冲突密度。" />
          <NovelDialogMetric label="角色状态" value={Object.keys(characterStates || {}).length} note="角色位置、情绪与状态变化。" />
          <NovelDialogMetric label="摘要关键词" value={summaryKeywords.length} note="压缩后的高频语义标签。" />
          <NovelDialogMetric label="未解悬念" value={tensionForeshadowing.length} note="可继续回收或放大的伏笔张力。" />
        </NovelDialogMetricGrid>
      </NovelDialogSection>

      {summaries ? (
        <NovelDialogSection
          eyebrow="Compressed Summary"
          title="分级摘要"
          description="优先确认一句话摘要和压缩摘要是否准确覆盖章节主推进。"
        >
          <div className="space-y-4">
            {summaries.one_line ? (
              <NovelDialogSurface>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">一句话摘要</div>
                <div className="mt-3 text-sm italic leading-relaxed text-book-text-main">{String(summaries.one_line)}</div>
              </NovelDialogSurface>
            ) : null}
            {summaries.compressed ? (
              <NovelDialogSurface>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">压缩摘要</div>
                <div className="mt-3 text-sm leading-relaxed text-book-text-main">{String(summaries.compressed)}</div>
              </NovelDialogSurface>
            ) : null}
            {summaryKeywords.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {summaryKeywords.map((keyword, idx) => (
                  <Chip key={`kw-${idx}`} className="text-book-primary">
                    {String(keyword)}
                  </Chip>
                ))}
              </div>
            ) : null}
          </div>
        </NovelDialogSection>
      ) : null}

      {metadata ? (
        <NovelDialogSection
          eyebrow="Metadata"
          title="章节元数据"
          description="检查角色、地点、物品和标签是否已经被正确提取。"
        >
          <div className="grid gap-4 lg:grid-cols-2">
            {asArray(metadata.characters).length > 0 ? (
              <NovelDialogSurface>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">角色</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {asArray(metadata.characters).map((value, idx) => (
                    <Chip key={`c-${idx}`} className="text-green-700 dark:text-green-200">
                      {String(value)}
                    </Chip>
                  ))}
                </div>
              </NovelDialogSurface>
            ) : null}

            {asArray(metadata.locations).length > 0 ? (
              <NovelDialogSurface>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">地点</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {asArray(metadata.locations).map((value, idx) => (
                    <Chip key={`l-${idx}`} className="text-blue-700 dark:text-blue-200">
                      {String(value)}
                    </Chip>
                  ))}
                </div>
              </NovelDialogSurface>
            ) : null}

            {asArray(metadata.items).length > 0 ? (
              <NovelDialogSurface>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">物品</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {asArray(metadata.items).map((value, idx) => (
                    <Chip key={`i-${idx}`} className="text-orange-700 dark:text-orange-200">
                      {String(value)}
                    </Chip>
                  ))}
                </div>
              </NovelDialogSurface>
            ) : null}

            {asArray(metadata.tags).length > 0 ? (
              <NovelDialogSurface>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">标签</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {asArray(metadata.tags).map((value, idx) => (
                    <Chip key={`t-${idx}`}>{String(value)}</Chip>
                  ))}
                </div>
              </NovelDialogSurface>
            ) : null}
          </div>
        </NovelDialogSection>
      ) : null}

      {Object.keys(characterStates || {}).length > 0 ? (
        <NovelDialogSection
          eyebrow="Character State"
          title="角色状态"
          description="回看角色的地点、情绪和状态变化，判断人物线是否连续。"
        >
          <div className="space-y-3">
            {Object.entries(characterStates).map(([name, state]) => (
              <NovelDialogSurface key={name}>
                <div className="font-semibold text-book-primary">{name}</div>
                <div className="mt-2 space-y-1 text-xs text-book-text-muted">
                  {state.location ? <div>地点：{String(state.location)}</div> : null}
                  {state.status ? <div>状态：{String(state.status)}</div> : null}
                  {state.emotional_state ? <div>情绪：{String(state.emotional_state)}</div> : null}
                </div>
                {asArray(state.changes).length > 0 ? (
                  <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-book-text-main">
                    {asArray(state.changes).map((change, idx) => (
                      <li key={`${name}-chg-${idx}`}>{String(change)}</li>
                    ))}
                  </ul>
                ) : null}
              </NovelDialogSurface>
            ))}
          </div>
        </NovelDialogSection>
      ) : null}

      {keyEvents.length > 0 ? (
        <NovelDialogSection
          eyebrow="Key Events"
          title="关键事件"
          description="确认本章主要推进点、事件强度和涉及角色是否已经被准确抽取。"
        >
          <div className="space-y-3">
            {keyEvents.map((evt, idx) => (
              <NovelDialogSurface key={`evt-${idx}`}>
                <div className="flex items-center justify-between gap-2">
                  <div className="font-semibold text-book-text-main">{String(evt.type || 'event')}</div>
                  <Chip className="text-book-text-muted">{String(evt.importance || 'medium')}</Chip>
                </div>
                <div className="mt-3 text-sm leading-relaxed text-book-text-main">
                  {String(evt.description || '')}
                </div>
                {asArray(evt.involved_characters).length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {asArray(evt.involved_characters).map((name, charIdx) => (
                      <Chip key={`evt-${idx}-c-${charIdx}`} className="text-green-700 dark:text-green-200">
                        {String(name)}
                      </Chip>
                    ))}
                  </div>
                ) : null}
              </NovelDialogSurface>
            ))}
          </div>
        </NovelDialogSection>
      ) : null}

      {foreshadowing ? (
        <NovelDialogSection
          eyebrow="Foreshadowing"
          title="伏笔追踪"
          description="检查已埋下、已回收和未解悬念，避免后续生成遗漏关键线索。"
        >
          <div className="space-y-4">
            {plantedForeshadowing.length > 0 ? (
              <NovelDialogSurface>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">已埋下</div>
                <div className="mt-3 space-y-2">
                  {plantedForeshadowing.map((item, idx) => (
                    <div key={`planted-${idx}`} className="rounded-[18px] border border-book-border/40 bg-book-bg px-3 py-3">
                      <div className="font-semibold text-book-text-main">
                        {String(item.hint || item.title || `伏笔${idx + 1}`)}
                      </div>
                      {item.detail ? (
                        <div className="mt-1 text-xs whitespace-pre-wrap text-book-text-muted">{String(item.detail)}</div>
                      ) : null}
                      {item.expected_payoff ? (
                        <div className="mt-1 text-xs text-book-text-muted">预期回收：{String(item.expected_payoff)}</div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </NovelDialogSurface>
            ) : null}

            {resolvedForeshadowing.length > 0 ? (
              <NovelDialogSurface>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">已回收</div>
                <div className="mt-3 space-y-2">
                  {resolvedForeshadowing.map((item, idx) => (
                    <div key={`resolved-${idx}`} className="rounded-[18px] border border-book-border/40 bg-book-bg px-3 py-3">
                      <div className="font-semibold text-book-text-main">
                        {String(item.hint || item.title || `回收${idx + 1}`)}
                      </div>
                      {item.payoff ? (
                        <div className="mt-1 text-xs whitespace-pre-wrap text-book-text-muted">{String(item.payoff)}</div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </NovelDialogSurface>
            ) : null}

            {tensionForeshadowing.length > 0 ? (
              <NovelDialogSurface>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">未解悬念</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {tensionForeshadowing.map((tension, idx) => (
                    <Chip key={`ten-${idx}`}>{String(tension)}</Chip>
                  ))}
                </div>
              </NovelDialogSurface>
            ) : null}
          </div>
        </NovelDialogSection>
      ) : null}
    </NovelDialogStack>
  );
};
