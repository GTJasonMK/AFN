import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';
import { writerApi } from '../../api/writer';
import { useToast } from '../feedback/Toast';
import { Activity, RefreshCw, Clock } from 'lucide-react';

type ViewMode = 'chapter' | 'timeline';

interface CharacterStateViewProps {
  projectId: string;
  chapterNumber: number;
}

export const CharacterStateView: React.FC<CharacterStateViewProps> = ({ projectId, chapterNumber }) => {
  const { addToast } = useToast();

  const [mode, setMode] = useState<ViewMode>('chapter');
  const [characters, setCharacters] = useState<string[]>([]);
  const [selectedCharacter, setSelectedCharacter] = useState<string>('');

  const [loading, setLoading] = useState(false);
  const [states, setStates] = useState<Record<string, any> | null>(null);

  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timeline, setTimeline] = useState<any[] | null>(null);
  const [fromChapter, setFromChapter] = useState<number>(1);
  const [toChapter, setToChapter] = useState<number>(chapterNumber);

  useEffect(() => {
    setToChapter(chapterNumber);
  }, [chapterNumber]);

  const refreshCharacters = useCallback(async () => {
    try {
      const res = await writerApi.listTrackedCharacters(projectId);
      setCharacters(res.characters || []);
    } catch (e) {
      console.error(e);
      setCharacters([]);
    }
  }, [projectId]);

  const refreshChapterStates = useCallback(async () => {
    if (!chapterNumber) return;
    setLoading(true);
    try {
      const res = await writerApi.getChapterCharacterStates(
        projectId,
        chapterNumber,
        selectedCharacter ? selectedCharacter : undefined
      );
      setStates(res.character_states || {});
    } catch (e) {
      console.error(e);
      setStates(null);
      addToast('获取角色状态失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast, chapterNumber, projectId, selectedCharacter]);

  const refreshTimeline = useCallback(async () => {
    const name = selectedCharacter.trim();
    if (!name) {
      addToast('请先选择一个角色查看时间线', 'error');
      return;
    }
    setTimelineLoading(true);
    try {
      const res = await writerApi.getCharacterTimeline(projectId, name, {
        fromChapter,
        toChapter: toChapter || undefined,
      });
      setTimeline(res.timeline || []);
    } catch (e) {
      console.error(e);
      setTimeline(null);
      addToast('获取角色时间线失败', 'error');
    } finally {
      setTimelineLoading(false);
    }
  }, [addToast, fromChapter, projectId, selectedCharacter, toChapter]);

  useEffect(() => {
    refreshCharacters();
  }, [refreshCharacters]);

  useEffect(() => {
    if (mode !== 'chapter') return;
    refreshChapterStates();
  }, [mode, refreshChapterStates]);

  const stateEntries = useMemo(() => {
    const obj = states || {};
    return Object.entries(obj).sort(([a], [b]) => a.localeCompare(b, 'zh-Hans-CN'));
  }, [states]);

  const hasAnyState = stateEntries.length > 0;

  return (
    <div className="space-y-4">
      <BookCard className="p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="font-bold text-book-text-main flex items-center gap-2">
            <Activity size={16} className="text-book-primary" />
            人物状态
            <span className="text-xs text-book-text-muted font-normal">· 第 {chapterNumber} 章</span>
          </div>
          <BookButton
            variant="ghost"
            size="sm"
            onClick={() => {
              if (mode === 'chapter') refreshChapterStates();
              else refreshTimeline();
            }}
            disabled={loading || timelineLoading}
          >
            <RefreshCw size={14} className={`mr-1 ${(loading || timelineLoading) ? 'animate-spin' : ''}`} />
            刷新
          </BookButton>
        </div>
      </BookCard>

      <BookCard className="p-4 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs font-bold text-book-text-sub">
            视图
            <select
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
              value={mode}
              onChange={(e) => setMode(e.target.value as ViewMode)}
            >
              <option value="chapter">本章状态</option>
              <option value="timeline">时间线</option>
            </select>
          </label>

          <label className="text-xs font-bold text-book-text-sub">
            角色筛选
            <select
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
              value={selectedCharacter}
              onChange={(e) => setSelectedCharacter(e.target.value)}
            >
              <option value="">全部</option>
              {characters.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </label>
        </div>

        {mode === 'timeline' && (
          <div className="grid grid-cols-2 gap-3">
            <label className="text-xs font-bold text-book-text-sub">
              起始章节
              <input
                type="number"
                min={1}
                className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                value={fromChapter}
                onChange={(e) => setFromChapter(Math.max(1, Number(e.target.value) || 1))}
              />
            </label>
            <label className="text-xs font-bold text-book-text-sub">
              结束章节
              <input
                type="number"
                min={1}
                className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                value={toChapter}
                onChange={(e) => setToChapter(Math.max(1, Number(e.target.value) || 1))}
              />
            </label>
          </div>
        )}

        {mode === 'timeline' && (
          <div className="flex justify-end">
            <BookButton variant="primary" size="sm" onClick={refreshTimeline} disabled={timelineLoading || !selectedCharacter.trim()}>
              <Clock size={14} className="mr-1" />
              {timelineLoading ? '加载中…' : '加载时间线'}
            </BookButton>
          </div>
        )}
      </BookCard>

      {mode === 'chapter' && (
        <div className="space-y-3">
          {!hasAnyState && (
            <BookCard className="p-4">
              <div className="text-xs text-book-text-muted leading-relaxed">
                暂无角色状态记录。通常需要先对章节执行分析/入库（如“RAG入库”），系统才会生成可追踪的状态索引。
              </div>
            </BookCard>
          )}

          {stateEntries.map(([name, st]) => {
            const location = st?.location ? String(st.location) : '';
            const status = st?.status ? String(st.status) : '';
            const emotional = st?.emotional_state ? String(st.emotional_state) : '';
            const changes = Array.isArray(st?.changes) ? st.changes : [];

            return (
              <BookCard key={name} className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="font-bold text-book-text-main">{name}</div>
                  <div className="text-[11px] text-book-text-muted font-mono">第 {chapterNumber} 章</div>
                </div>

                <div className="mt-2 text-sm text-book-text-main space-y-1">
                  {location ? <div><span className="font-bold text-book-text-sub">位置：</span>{location}</div> : null}
                  {status ? <div><span className="font-bold text-book-text-sub">状态：</span>{status}</div> : null}
                  {emotional ? <div><span className="font-bold text-book-text-sub">情绪：</span>{emotional}</div> : null}
                </div>

                {changes.length > 0 && (
                  <div className="mt-3">
                    <div className="text-xs font-bold text-book-text-sub mb-1">本章变化</div>
                    <ul className="list-disc list-inside text-sm text-book-text-main space-y-1">
                      {changes.map((c: string, idx: number) => (
                        <li key={`${name}-c-${idx}`}>{String(c)}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </BookCard>
            );
          })}
        </div>
      )}

      {mode === 'timeline' && (
        <div className="space-y-3">
          {timelineLoading && (
            <BookCard className="p-4 text-sm text-book-text-muted">加载时间线中…</BookCard>
          )}

          {!timelineLoading && (!timeline || timeline.length === 0) && (
            <BookCard className="p-4 text-sm text-book-text-muted">
              {selectedCharacter.trim() ? '暂无时间线数据。' : '请选择一个角色查看时间线。'}
            </BookCard>
          )}

          {(timeline || []).map((it: any) => (
            <BookCard key={`tl-${it.chapter_number}`} className="p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="font-bold text-book-text-main">第 {it.chapter_number} 章</div>
                <div className="text-[11px] text-book-text-muted font-mono">{selectedCharacter}</div>
              </div>
              <div className="mt-2 text-sm text-book-text-main space-y-1">
                {it.location ? <div><span className="font-bold text-book-text-sub">位置：</span>{String(it.location)}</div> : null}
                {it.status ? <div><span className="font-bold text-book-text-sub">状态：</span>{String(it.status)}</div> : null}
              </div>
              {Array.isArray(it.changes) && it.changes.length > 0 && (
                <div className="mt-3">
                  <div className="text-xs font-bold text-book-text-sub mb-1">变化</div>
                  <ul className="list-disc list-inside text-sm text-book-text-main space-y-1">
                    {it.changes.map((c: any, idx: number) => (
                      <li key={`tl-${it.chapter_number}-${idx}`}>{String(c)}</li>
                    ))}
                  </ul>
                </div>
              )}
            </BookCard>
          ))}
        </div>
      )}
    </div>
  );
};
