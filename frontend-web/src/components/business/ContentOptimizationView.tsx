import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';
import { useToast } from '../feedback/Toast';
import { confirmDialog } from '../feedback/ConfirmDialog';
import { useSSE } from '../../hooks/useSSE';
import { apiClient } from '../../api/client';
import { Wand2, PauseCircle, PlayCircle, XCircle, ListChecks, CheckCircle2, Copy, Undo2, Eye, Search } from 'lucide-react';
import { Modal } from '../ui/Modal';

type OptimizationMode = 'auto' | 'review' | 'plan';
type AnalysisScope = 'full' | 'selected';

type ParagraphPreview = {
  index: number;
  preview: string;
  length: number;
};

type ParagraphPreviewResponse = {
  total_paragraphs: number;
  paragraphs: ParagraphPreview[];
};

type Suggestion = {
  paragraph_index: number;
  original_text: string;
  suggested_text: string;
  reason: string;
  category: string;
  priority: string;
};

type UndoSnapshot = {
  content: string;
  key: string;
  label: string;
};

type ThinkingEventType = 'thinking' | 'action' | 'observation' | 'progress' | 'error';

type ThinkingEvent = {
  id: string;
  type: ThinkingEventType;
  title: string;
  content: string;
  ts: number;
};

type InlineDiffSeg = { type: 'same' | 'remove' | 'add'; text: string };

type InlinePreviewState = {
  suggestion: Suggestion;
  key: string;
  beforeContent: string;
  afterContent: string;
  label: string;
  range: { start: number; end: number } | null;
};

const DIMENSIONS: Array<{ id: string; label: string }> = [
  { id: 'coherence', label: '逻辑连贯性' },
  { id: 'character', label: '角色一致性' },
  { id: 'foreshadow', label: '伏笔呼应' },
  { id: 'timeline', label: '时间线一致性' },
  { id: 'style', label: '风格一致性' },
  { id: 'scene', label: '场景描写' },
];

const priorityColor: Record<string, string> = {
  high: 'text-red-600',
  medium: 'text-orange-600',
  low: 'text-book-text-muted',
};

const THINKING_LABELS: Record<ThinkingEventType, { label: string; cls: string }> = {
  thinking: { label: 'Thinking', cls: 'text-book-primary' },
  action: { label: 'Action', cls: 'text-book-accent' },
  observation: { label: 'Observation', cls: 'text-green-600' },
  progress: { label: 'Progress', cls: 'text-book-text-muted' },
  error: { label: 'Error', cls: 'text-red-600' },
};

interface ContentOptimizationViewProps {
  projectId: string;
  chapterNumber: number;
  content: string;
  onChangeContent?: (value: string) => void;
  onLocateText?: (text: string) => void;
  onSelectRange?: (start: number, end: number) => void;
}

export const ContentOptimizationView: React.FC<ContentOptimizationViewProps> = ({
  projectId,
  chapterNumber,
  content,
  onChangeContent,
  onLocateText,
  onSelectRange,
}) => {
  const { addToast } = useToast();

  const [mode, setMode] = useState<OptimizationMode>('plan');
  const [scope, setScope] = useState<AnalysisScope>('full');
  const [dimensions, setDimensions] = useState<string[]>(DIMENSIONS.map((d) => d.id));

  const [preview, setPreview] = useState<ParagraphPreviewResponse | null>(null);
  const [selectedParagraphs, setSelectedParagraphs] = useState<number[]>([]);
  const [rangeInput, setRangeInput] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);

  const [running, setRunning] = useState(false);
  const [paused, setPaused] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [totalParagraphs, setTotalParagraphs] = useState<number | null>(null);
  const [currentParagraph, setCurrentParagraph] = useState<number | null>(null);

  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [appliedKeys, setAppliedKeys] = useState<string[]>([]);
  const [undoStack, setUndoStack] = useState<UndoSnapshot[]>([]);
  const [previewSuggestion, setPreviewSuggestion] = useState<Suggestion | null>(null);
  const [inlinePreview, setInlinePreview] = useState<InlinePreviewState | null>(null);

  const [thinkingEvents, setThinkingEvents] = useState<ThinkingEvent[]>([]);
  const [thinkingExpanded, setThinkingExpanded] = useState(false);
  const thinkingScrollRef = useRef<HTMLDivElement | null>(null);

  const appliedSet = useMemo(() => new Set(appliedKeys), [appliedKeys]);

  const getSuggestionKey = useCallback((s: Suggestion) => {
    return `${s.paragraph_index}:${s.category}:${s.priority}:${(s.original_text || '').length}`;
  }, []);

  const splitParagraphs = useCallback((text: string) => {
    const parts: Array<{ start: number; end: number; text: string }> = [];
    const re = /\n{2,}/g; // 两个及以上换行视为段落分隔（textarea 输入通常为 \n）
    let last = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      const end = m.index;
      parts.push({ start: last, end, text: text.slice(last, end) });
      last = m.index + m[0].length;
    }
    parts.push({ start: last, end: text.length, text: text.slice(last) });
    return parts;
  }, []);

  const buildUpdatedContent = useCallback((s: Suggestion, current: string): { content: string; range: { start: number; end: number } } | null => {
    const target = s.original_text || '';
    const replacement = s.suggested_text || '';
    if (!target.trim()) return null;

    const paraIdx = typeof s.paragraph_index === 'number' ? s.paragraph_index : -1;
    const paras = splitParagraphs(current);
    const para = paraIdx >= 0 && paraIdx < paras.length ? paras[paraIdx] : null;
    if (para && para.text.includes(target)) {
      const localIdx = para.text.indexOf(target);
      const replacedPara = para.text.slice(0, localIdx) + replacement + para.text.slice(localIdx + target.length);
      const updated = current.slice(0, para.start) + replacedPara + current.slice(para.end);
      const start = para.start + localIdx;
      return { content: updated, range: { start, end: start + replacement.length } };
    }

    const idx = current.indexOf(target);
    if (idx < 0) return null;
    const updated = current.slice(0, idx) + replacement + current.slice(idx + target.length);
    return { content: updated, range: { start: idx, end: idx + replacement.length } };
  }, [splitParagraphs]);

  const applySuggestion = useCallback((s: Suggestion) => {
    if (!onChangeContent) {
      addToast('当前页面未绑定编辑器内容，无法自动应用建议', 'error');
      return;
    }
    const result = buildUpdatedContent(s, content);
    if (result === null) {
      addToast('未能在当前正文中定位原文片段，建议手动参考修改', 'error');
      return;
    }

    const key = getSuggestionKey(s);
    const snapshot: UndoSnapshot = { content, key, label: `段落 ${s.paragraph_index + 1} · ${s.category}` };
    setUndoStack((prev) => {
      const next = [...prev, snapshot];
      // 控制撤销栈长度，避免长期占用内存
      if (next.length > 30) next.shift();
      return next;
    });

    onChangeContent(result.content);
    if (onSelectRange) onSelectRange(result.range.start, result.range.end);
    setAppliedKeys((prev) => (prev.includes(key) ? prev : [...prev, key]));
    addToast('已应用该条建议（仅修改本地编辑器内容）', 'success');
  }, [addToast, buildUpdatedContent, content, getSuggestionKey, onChangeContent, onSelectRange]);

  const buildSimpleInlineDiff = useCallback((original: string, suggested: string): InlineDiffSeg[] => {
    const a = String(original || '');
    const b = String(suggested || '');
    if (!a && !b) return [];
    if (a === b) return [{ type: 'same', text: a }];

    const maxPrefix = Math.min(a.length, b.length);
    let prefix = 0;
    while (prefix < maxPrefix && a[prefix] === b[prefix]) prefix += 1;

    const maxSuffix = maxPrefix - prefix;
    let suffix = 0;
    while (
      suffix < maxSuffix &&
      a[a.length - 1 - suffix] === b[b.length - 1 - suffix]
    ) {
      suffix += 1;
    }

    const aMid = a.slice(prefix, a.length - suffix);
    const bMid = b.slice(prefix, b.length - suffix);
    const segs: InlineDiffSeg[] = [];
    const head = a.slice(0, prefix);
    const tail = suffix ? a.slice(a.length - suffix) : '';
    if (head) segs.push({ type: 'same', text: head });
    if (aMid) segs.push({ type: 'remove', text: aMid });
    if (bMid) segs.push({ type: 'add', text: bMid });
    if (tail) segs.push({ type: 'same', text: tail });
    return segs;
  }, []);

  const startInlinePreview = useCallback((s: Suggestion) => {
    if (!onChangeContent) {
      addToast('当前页面未绑定编辑器内容，无法预览建议', 'error');
      return;
    }
    const key = getSuggestionKey(s);
    if (inlinePreview) {
      if (inlinePreview.key === key) {
        if (onSelectRange && inlinePreview.range) onSelectRange(inlinePreview.range.start, inlinePreview.range.end);
        addToast('该条建议正在预览中，请确认或撤销', 'info');
        return;
      }
      addToast('当前有正在预览的建议，请先确认或撤销，再预览下一条', 'info');
      return;
    }

    const result = buildUpdatedContent(s, content);
    if (!result) {
      addToast('未能在当前正文中定位原文片段，已打开对比预览供参考', 'info');
      setPreviewSuggestion(s);
      return;
    }

    const label = `段落 ${s.paragraph_index + 1} · ${s.category}`;
    setInlinePreview({
      suggestion: s,
      key,
      beforeContent: content,
      afterContent: result.content,
      label,
      range: result.range,
    });
    onChangeContent(result.content);
    if (onSelectRange) onSelectRange(result.range.start, result.range.end);
    addToast(`已在编辑器中预览：${label}（请确认或撤销）`, 'success');
  }, [addToast, buildUpdatedContent, content, getSuggestionKey, inlinePreview, onChangeContent, onSelectRange]);

  const confirmInlinePreview = useCallback(() => {
    if (!inlinePreview) return;
    const snapshot: UndoSnapshot = { content: inlinePreview.beforeContent, key: inlinePreview.key, label: inlinePreview.label };
    setUndoStack((prev) => {
      const next = [...prev, snapshot];
      if (next.length > 30) next.shift();
      return next;
    });
    setAppliedKeys((prev) => (prev.includes(inlinePreview.key) ? prev : [...prev, inlinePreview.key]));
    setInlinePreview(null);
    addToast(`已确认并应用：${inlinePreview.label}`, 'success');
  }, [addToast, inlinePreview]);

  const revertInlinePreview = useCallback(async () => {
    if (!inlinePreview) return;
    if (!onChangeContent) return;
    if (content !== inlinePreview.afterContent) {
      const ok = await confirmDialog({
        title: '撤销预览',
        message: '正文已被修改。\n撤销预览将覆盖当前编辑器内容，是否继续？',
        confirmText: '继续撤销',
        dialogType: 'warning',
      });
      if (!ok) return;
    }
    onChangeContent(inlinePreview.beforeContent);
    setInlinePreview(null);
    addToast(`已撤销预览：${inlinePreview.label}`, 'success');
  }, [addToast, content, inlinePreview, onChangeContent]);

  useEffect(() => {
    // 切章/切项目时，强制清理预览态，避免误操作覆盖正文
    setInlinePreview(null);
  }, [chapterNumber, projectId]);

  const lastUndo = useMemo(() => (undoStack.length ? undoStack[undoStack.length - 1] : null), [undoStack]);

  const undoLastApply = useCallback(() => {
    if (!lastUndo) return;
    if (!onChangeContent) return;
    onChangeContent(lastUndo.content);
    setAppliedKeys((prev) => prev.filter((k) => k !== lastUndo.key));
    setUndoStack((prev) => prev.slice(0, -1));
    addToast(`已撤销：${lastUndo.label}`, 'success');
  }, [addToast, lastUndo, onChangeContent]);

  const fetchPreview = useCallback(async () => {
    if (!content.trim()) {
      addToast('正文为空，无法预览段落', 'error');
      return;
    }
    setPreviewLoading(true);
    try {
      const res = await apiClient.post<ParagraphPreviewResponse>(
        `/writer/novels/${projectId}/chapters/preview-paragraphs`,
        { content }
      );
      setPreview(res.data);
      setSelectedParagraphs([]);
    } catch (e) {
      console.error(e);
      addToast('段落预览失败', 'error');
      setPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  }, [addToast, content, projectId]);

  const appendThinking = useCallback((type: ThinkingEventType, title: string, body?: any) => {
    const contentText = (() => {
      if (body === null || body === undefined) return '';
      if (typeof body === 'string') return body;
      try {
        return JSON.stringify(body, null, 2);
      } catch {
        return String(body);
      }
    })();

    const item: ThinkingEvent = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      type,
      title: title || THINKING_LABELS[type]?.label || type,
      content: contentText,
      ts: Date.now(),
    };

    setThinkingEvents((prev) => {
      const next = [...prev, item];
      // 上限：避免长时间运行导致内存膨胀
      if (next.length > 400) next.splice(0, next.length - 400);
      return next;
    });
  }, []);

  useEffect(() => {
    if (!thinkingExpanded) return;
    const el = thinkingScrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [thinkingExpanded, thinkingEvents.length]);

  const parseRangeInput = useCallback((text: string, maxCount: number): number[] => {
    const raw = (text || '').trim();
    if (!raw) return [];
    const maxIndex = Math.max(0, Math.floor(maxCount));

    const result = new Set<number>();
    const parts = raw
      .split(/[,\s]+/g)
      .map((p) => p.trim())
      .filter(Boolean);

    for (const part of parts) {
      if (!part) continue;
      if (part.includes('-')) {
        const seg = part.split('-').map((s) => s.trim()).filter(Boolean);
        if (seg.length !== 2) continue;
        const start = Number(seg[0]);
        const end = Number(seg[1]);
        if (!Number.isFinite(start) || !Number.isFinite(end)) continue;
        const a = Math.max(1, Math.floor(Math.min(start, end)));
        const b = Math.max(1, Math.floor(Math.max(start, end)));
        for (let i = a; i <= b; i += 1) {
          const idx = i - 1;
          if (idx >= 0 && idx < maxIndex) result.add(idx);
        }
      } else {
        const n = Number(part);
        if (!Number.isFinite(n)) continue;
        const idx = Math.floor(n) - 1;
        if (idx >= 0 && idx < maxIndex) result.add(idx);
      }
    }

    return Array.from(result).sort((a, b) => a - b);
  }, []);

  const applyRangeSelection = useCallback(() => {
    if (!preview) {
      addToast('请先获取段落预览', 'info');
      return;
    }
    const indices = parseRangeInput(rangeInput, preview.total_paragraphs);
    setSelectedParagraphs(indices);
    if (indices.length === 0 && rangeInput.trim()) {
      addToast('范围解析为空，请输入如：1-5, 9-18, 20', 'info');
    }
  }, [addToast, parseRangeInput, preview, rangeInput]);

  const copyThinkingStream = useCallback(async () => {
    if (!thinkingEvents.length) return;
    const text = thinkingEvents
      .map((e) => {
        const time = (() => {
          try {
            return new Date(e.ts).toLocaleTimeString();
          } catch {
            return String(e.ts);
          }
        })();
        const header = `[${time}] ${e.type.toUpperCase()} · ${e.title}`;
        const body = (e.content || '').trim();
        return body ? `${header}\n${body}` : header;
      })
      .join('\n\n');

    try {
      await navigator.clipboard.writeText(text);
      addToast('已复制思考流', 'success');
    } catch (e) {
      console.error(e);
      addToast('复制失败（浏览器权限/非 HTTPS 环境）', 'error');
    }
  }, [addToast, thinkingEvents]);

  const handleEvent = useCallback((event: string, data: any) => {
    if (event === 'workflow_start') {
      setRunning(true);
      setPaused(false);
      setSessionId(String(data.session_id || ''));
      setTotalParagraphs(Number(data.total_paragraphs || 0));
      setCurrentParagraph(null);
      appendThinking('progress', 'Workflow Start', {
        total_paragraphs: data?.total_paragraphs,
        dimensions: data?.dimensions,
        mode: data?.mode,
      });
      return;
    }
    if (event === 'paragraph_start') {
      setCurrentParagraph(Number(data.index));
      appendThinking('progress', `Paragraph ${Number(data.index) + 1} Start`, String(data?.text_preview || '').trim());
      return;
    }
    if (event === 'thinking') {
      appendThinking('thinking', String(data?.step || 'Thinking'), String(data?.content || ''));
      return;
    }
    if (event === 'action') {
      const header = String(data?.action || 'Action');
      const desc = String(data?.description || '').trim();
      appendThinking('action', header, desc);
      return;
    }
    if (event === 'observation') {
      const ok = data?.success !== false;
      const text = String(data?.result ?? '').trim();
      appendThinking(ok ? 'observation' : 'error', ok ? 'Observation' : 'Observation Failed', text);
      return;
    }
    if (event === 'suggestion') {
      const s: Suggestion = {
        paragraph_index: Number(data.paragraph_index ?? data.index ?? 0),
        original_text: String(data.original_text ?? ''),
        suggested_text: String(data.suggested_text ?? ''),
        reason: String(data.reason ?? ''),
        category: String(data.category ?? ''),
        priority: String(data.priority ?? 'medium'),
      };
      setSuggestions((prev) => [...prev, s]);
      return;
    }
    if (event === 'paragraph_complete') {
      const idx = Number(data?.index ?? 0);
      const count = Number(data?.suggestions_count ?? 0);
      appendThinking('progress', `Paragraph ${idx + 1} Complete`, `发现 ${count} 条建议`);
      return;
    }
    if (event === 'plan_ready') {
      setPaused(true);
      setRunning(true);
      setSessionId(String(data.session_id || ''));
      if (Array.isArray(data.suggestions)) {
        setSuggestions(data.suggestions as Suggestion[]);
      }
      appendThinking('progress', 'Plan Ready', `共 ${Array.isArray(data.suggestions) ? data.suggestions.length : 0} 条建议`);
      addToast('分析完成（Plan模式）：请选择要应用的建议', 'success');
      return;
    }
    if (event === 'workflow_paused') {
      setPaused(true);
      setRunning(true);
      setSessionId(String(data.session_id || ''));
      appendThinking('progress', 'Workflow Paused', '');
      return;
    }
    if (event === 'workflow_resumed') {
      setPaused(false);
      appendThinking('progress', 'Workflow Resumed', '');
      return;
    }
    if (event === 'workflow_complete') {
      setRunning(false);
      setPaused(false);
      appendThinking('progress', 'Workflow Complete', {
        total_suggestions: data?.total_suggestions,
        summary: data?.summary,
      });
      addToast('优化流程已完成', 'success');
      return;
    }
    if (event === 'error') {
      setRunning(false);
      setPaused(false);
      const msg = String(data?.message || data?.detail || '优化失败');
      appendThinking('error', 'Error', msg);
      addToast(msg, 'error');
      return;
    }
  }, [addToast, appendThinking]);

  const { connect, disconnect } = useSSE(handleEvent);

  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  // 切换章节时：停止流并清理当前面板状态，避免把旧章节的建议带到新章节
  useEffect(() => {
    disconnect();
    setRunning(false);
    setPaused(false);
    setSessionId(null);
    setTotalParagraphs(null);
    setCurrentParagraph(null);
    setPreview(null);
    setSelectedParagraphs([]);
    setRangeInput('');
    setSuggestions([]);
    setAppliedKeys([]);
    setUndoStack([]);
    setPreviewSuggestion(null);
    setThinkingEvents([]);
    setThinkingExpanded(false);
  }, [chapterNumber, disconnect, projectId]);

  const startOptimization = useCallback(async () => {
    if (!content.trim()) {
      addToast('正文为空，无法优化', 'error');
      return;
    }
    if (!chapterNumber) return;
    if (scope === 'selected' && selectedParagraphs.length === 0) {
      addToast('选择段落模式下，请先勾选要分析的段落', 'error');
      return;
    }

    setThinkingEvents([]);
    setThinkingExpanded(true);
    setSuggestions([]);
    setAppliedKeys([]);
    setRunning(true);
    setPaused(false);
    setSessionId(null);
    setTotalParagraphs(null);
    setCurrentParagraph(null);

    await connect(`/writer/novels/${projectId}/chapters/${chapterNumber}/optimize`, {
      content,
      scope,
      selected_paragraphs: scope === 'selected' ? selectedParagraphs : undefined,
      dimensions,
      mode,
    });
  }, [addToast, chapterNumber, connect, content, dimensions, mode, projectId, scope, selectedParagraphs]);

  const continueSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      await apiClient.post(`/writer/optimization-sessions/${sessionId}/continue`, { content });
      setPaused(false);
      addToast('已继续会话', 'success');
    } catch (e) {
      console.error(e);
      addToast('继续会话失败', 'error');
    }
  }, [addToast, content, sessionId]);

  const cancelSession = useCallback(async () => {
    disconnect();
    if (!sessionId) {
      setRunning(false);
      setPaused(false);
      return;
    }
    try {
      await apiClient.post(`/writer/optimization-sessions/${sessionId}/cancel`);
      addToast('已取消优化会话', 'success');
    } catch (e) {
      console.error(e);
      addToast('取消会话失败', 'error');
    } finally {
      setRunning(false);
      setPaused(false);
      setSessionId(null);
    }
  }, [addToast, disconnect, sessionId]);

  const stopStream = useCallback(() => {
    disconnect();
    setRunning(false);
    setPaused(false);
    addToast('已停止流式连接（如需中止后台任务请点“取消”）', 'success');
  }, [addToast, disconnect]);

  const toggleDimension = (id: string) => {
    setDimensions((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      return [...prev, id];
    });
  };

  const selectAllPreview = () => {
    const all = (preview?.paragraphs || []).map((p) => p.index);
    setSelectedParagraphs(all);
  };

  const clearPreviewSelection = () => setSelectedParagraphs([]);

  const statusText = useMemo(() => {
    if (!running) return '未开始';
    if (paused) return '已暂停';
    return '运行中';
  }, [paused, running]);

  const previewKey = useMemo(() => {
    if (!previewSuggestion) return '';
    return getSuggestionKey(previewSuggestion);
  }, [getSuggestionKey, previewSuggestion]);

  const previewApplied = useMemo(() => {
    if (!previewKey) return false;
    return appliedSet.has(previewKey);
  }, [appliedSet, previewKey]);

  return (
    <div className="space-y-4">
      <BookCard className="p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="font-bold text-book-text-main flex items-center gap-2">
            <Wand2 size={16} className="text-book-primary" />
            正文优化
          </div>
          <div className="text-xs text-book-text-muted">
            状态：{statusText}
            {typeof currentParagraph === 'number' && typeof totalParagraphs === 'number'
              ? ` · 段落 ${currentParagraph + 1}/${totalParagraphs}`
              : null}
          </div>
        </div>
      </BookCard>

      {inlinePreview ? (
        <BookCard className="p-4 border border-book-accent/30 bg-book-bg-paper">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="text-sm font-bold text-book-text-main">正在预览：{inlinePreview.label}</div>
              <div className="mt-1 text-xs text-book-text-muted leading-relaxed">
                预览会直接修改编辑器内容；请尽快“确认/撤销”。如需手动编辑，建议先确认后再改，避免撤销覆盖。
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {onSelectRange && inlinePreview.range ? (
                <BookButton
                  variant="ghost"
                  size="sm"
                  onClick={() => onSelectRange(inlinePreview.range!.start, inlinePreview.range!.end)}
                  title="重新定位到修改位置"
                >
                  <Search size={14} className="mr-1" />
                  定位
                </BookButton>
              ) : null}
              <BookButton variant="ghost" size="sm" onClick={revertInlinePreview}>
                <Undo2 size={14} className="mr-1" />
                撤销预览
              </BookButton>
              <BookButton variant="primary" size="sm" onClick={confirmInlinePreview}>
                <CheckCircle2 size={14} className="mr-1" />
                确认应用
              </BookButton>
            </div>
          </div>

          <div className="mt-3 text-xs">
            <div className="text-[11px] text-book-text-muted mb-1">差异高亮</div>
            <div className="p-3 rounded-lg border border-book-border/40 bg-book-bg whitespace-pre-wrap font-mono leading-relaxed text-book-text-main">
              {buildSimpleInlineDiff(inlinePreview.suggestion.original_text, inlinePreview.suggestion.suggested_text).map((seg, idx) => (
                <span
                  key={`d-${idx}`}
                  className={
                    seg.type === 'remove'
                      ? 'bg-red-500/10 text-red-700 line-through'
                      : seg.type === 'add'
                        ? 'bg-green-500/10 text-green-700'
                        : ''
                  }
                >
                  {seg.text}
                </span>
              ))}
            </div>
          </div>
        </BookCard>
      ) : null}

      <BookCard className="p-4 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs font-bold text-book-text-sub">
            模式
            <select
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
              value={mode}
              onChange={(e) => setMode(e.target.value as OptimizationMode)}
              disabled={running}
            >
              <option value="plan">计划（先分析后选择）</option>
              <option value="review">审核（逐条暂停确认）</option>
              <option value="auto">自动（不中断）</option>
            </select>
          </label>

          <label className="text-xs font-bold text-book-text-sub">
            范围
            <select
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
              value={scope}
              onChange={(e) => setScope(e.target.value as AnalysisScope)}
              disabled={running}
            >
              <option value="full">全章</option>
              <option value="selected">选中段落</option>
            </select>
          </label>
        </div>

        <div className="space-y-2">
          <div className="text-xs font-bold text-book-text-sub flex items-center justify-between gap-2">
            <span>检查维度</span>
            <span className="text-[11px] text-book-text-muted">{dimensions.length}/{DIMENSIONS.length}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {DIMENSIONS.map((d) => (
              <label key={d.id} className="flex items-center gap-2 text-xs text-book-text-main bg-book-bg px-2 py-1 rounded border border-book-border/50">
                <input
                  type="checkbox"
                  checked={dimensions.includes(d.id)}
                  onChange={() => toggleDimension(d.id)}
                  disabled={running}
                />
                {d.label}
              </label>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <BookButton
            variant="ghost"
            size="sm"
            onClick={fetchPreview}
            disabled={previewLoading || running}
            title="调用后端段落切分预览（用于选择段落）"
          >
            <ListChecks size={14} className={`mr-1 ${previewLoading ? 'animate-spin' : ''}`} />
            {previewLoading ? '预览中…' : '段落预览'}
          </BookButton>

          <div className="flex-1" />

          {!running ? (
            <BookButton variant="primary" size="sm" onClick={startOptimization}>
              <PlayCircle size={14} className="mr-1" />
              开始
            </BookButton>
          ) : paused ? (
            <BookButton variant="primary" size="sm" onClick={continueSession} disabled={!sessionId}>
              <PlayCircle size={14} className="mr-1" />
              继续
            </BookButton>
          ) : (
            <BookButton variant="secondary" size="sm" onClick={stopStream}>
              <PauseCircle size={14} className="mr-1" />
              停止流
            </BookButton>
          )}

          <BookButton variant="secondary" size="sm" onClick={cancelSession} disabled={!running && !sessionId}>
            <XCircle size={14} className="mr-1" />
            取消
          </BookButton>
        </div>

        {scope === 'selected' && preview && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-xs text-book-text-muted">
                已识别 {preview.total_paragraphs} 段，已选择 {selectedParagraphs.length} 段
              </div>
              <div className="flex items-center gap-2">
                <button className="text-xs text-book-primary font-bold hover:underline" onClick={selectAllPreview} type="button">
                  全选
                </button>
                <button className="text-xs text-book-text-muted hover:underline" onClick={clearPreviewSelection} type="button">
                  清空
                </button>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input
                className="flex-1 px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                placeholder="范围：1-5, 9-18, 20（回车应用）"
                value={rangeInput}
                onChange={(e) => setRangeInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') applyRangeSelection();
                }}
                disabled={running}
              />
              <BookButton variant="ghost" size="sm" onClick={applyRangeSelection} disabled={running}>
                应用
              </BookButton>
            </div>
            <div className="max-h-64 overflow-y-auto custom-scrollbar space-y-2 pr-1">
              {preview.paragraphs.map((p) => (
                <label key={p.index} className="flex items-start gap-2 p-2 rounded border border-book-border/40 bg-book-bg">
                  <input
                    type="checkbox"
                    checked={selectedParagraphs.includes(p.index)}
                    onChange={() => {
                      setSelectedParagraphs((prev) => {
                        if (prev.includes(p.index)) return prev.filter((x) => x !== p.index);
                        return [...prev, p.index].sort((a, b) => a - b);
                      });
                    }}
                    disabled={running}
                  />
                  <div className="min-w-0">
                    <div className="text-[11px] text-book-text-muted">段落 {p.index + 1} · {p.length}</div>
                    <div className="text-xs text-book-text-main leading-relaxed">{p.preview}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}

        {sessionId && (
          <div className="text-[11px] text-book-text-muted">
            session_id：<span className="font-mono">{sessionId}</span>
          </div>
        )}
      </BookCard>

      <BookCard className="p-4">
        <div className="flex items-center justify-between mb-3 gap-2">
          <div className="font-bold text-book-text-main flex items-center gap-2">
            <Search size={16} className="text-book-primary" />
            思考流
          </div>
          <div className="flex items-center gap-2">
            {thinkingEvents.length > 0 ? (
              <BookButton variant="ghost" size="sm" onClick={copyThinkingStream} title="复制完整思考流">
                <Copy size={14} className="mr-1" />
                复制
              </BookButton>
            ) : null}
            {thinkingEvents.length > 0 ? (
              <BookButton variant="ghost" size="sm" onClick={() => setThinkingEvents([])} title="清空思考流">
                <XCircle size={14} className="mr-1" />
                清空
              </BookButton>
            ) : null}
            <BookButton variant="ghost" size="sm" onClick={() => setThinkingExpanded((v) => !v)}>
              {thinkingExpanded ? '收起' : '展开'}
            </BookButton>
          </div>
        </div>

        {thinkingEvents.length === 0 ? (
          <div className="text-xs text-book-text-muted leading-relaxed">
            {running ? '思考流等待输出…' : '开始优化后，这里会显示 Agent 的 Thinking / Action / Observation 过程。'}
          </div>
        ) : thinkingExpanded ? (
          <div ref={thinkingScrollRef} className="max-h-56 overflow-y-auto custom-scrollbar space-y-2 pr-1">
            {thinkingEvents.map((e) => {
              const meta = THINKING_LABELS[e.type] || { label: e.type, cls: 'text-book-text-muted' };
              return (
                <div key={e.id} className="p-2 rounded border border-book-border/40 bg-book-bg">
                  <div className="flex items-center justify-between gap-2">
                    <div className={`text-[11px] font-bold ${meta.cls}`}>
                      {meta.label}
                      {e.title ? <span className="text-book-text-muted font-normal ml-2">{e.title}</span> : null}
                    </div>
                    <div className="text-[10px] text-book-text-muted">
                      {(() => {
                        try {
                          return new Date(e.ts).toLocaleTimeString();
                        } catch {
                          return '';
                        }
                      })()}
                    </div>
                  </div>
                  {e.content ? (
                    <pre className="mt-1 text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed">
                      {e.content}
                    </pre>
                  ) : null}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-xs text-book-text-muted leading-relaxed">
            最近：{(() => {
              const last = thinkingEvents[thinkingEvents.length - 1];
              const meta = THINKING_LABELS[last.type] || { label: last.type, cls: '' };
              const title = last.title ? ` · ${last.title}` : '';
              return `${meta.label}${title}`;
            })()}
          </div>
        )}
      </BookCard>

      <BookCard className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="font-bold text-book-text-main">建议列表</div>
          <div className="flex items-center gap-2">
            {lastUndo && onChangeContent ? (
              <BookButton
                variant="ghost"
                size="sm"
                onClick={undoLastApply}
                title={`撤销上次应用：${lastUndo.label}`}
              >
                <Undo2 size={14} className="mr-1" />
                撤销{undoStack.length > 1 ? `（${undoStack.length}）` : ''}
              </BookButton>
            ) : null}
            <div className="text-xs text-book-text-muted">共 {suggestions.length} 条</div>
          </div>
        </div>

        {suggestions.length === 0 ? (
          <div className="text-xs text-book-text-muted leading-relaxed">
            {running ? '等待建议输出…' : '开始优化后，这里会显示修改建议。'}
          </div>
        ) : (
          <div className="space-y-3">
            {suggestions.map((s, idx) => {
              const key = getSuggestionKey(s);
              const applied = appliedSet.has(key);
              const previewing = inlinePreview?.key === key;
              return (
                <div key={`s-${key}-${idx}`} className="border border-book-border/40 rounded-lg p-3 bg-book-bg">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-xs font-bold text-book-text-main">
                      段落 {s.paragraph_index + 1} · {s.category}
                      <span className={`ml-2 ${priorityColor[s.priority] || 'text-book-text-muted'}`}>
                        {s.priority}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <BookButton
                        variant="ghost"
                        size="sm"
                        onClick={() => startInlinePreview(s)}
                        disabled={previewing}
                        title="在编辑器中预览（确认/撤销）"
                      >
                        <Eye size={14} className="mr-1" />
                        {previewing ? '预览中' : '预览'}
                      </BookButton>
                      <BookButton
                        variant="ghost"
                        size="sm"
                        onClick={() => setPreviewSuggestion(s)}
                        title="打开对比预览"
                      >
                        <ListChecks size={14} className="mr-1" />
                        对比
                      </BookButton>
                      {onLocateText && (s.original_text || '').trim() ? (
                        <BookButton
                          variant="ghost"
                          size="sm"
                          onClick={() => onLocateText(s.original_text)}
                          title="在编辑器中定位原文片段"
                        >
                          <Search size={14} className="mr-1" />
                          定位
                        </BookButton>
                      ) : null}
                      <BookButton
                        variant="secondary"
                        size="sm"
                        onClick={() => (previewing ? confirmInlinePreview() : applySuggestion(s))}
                        disabled={(!previewing && applied) || !onChangeContent}
                      >
                        <CheckCircle2 size={14} className="mr-1" />
                        {previewing ? '确认' : (applied ? '已应用' : '应用')}
                      </BookButton>
                      <BookButton
                        variant="ghost"
                        size="sm"
                        onClick={async () => {
                          try {
                            await navigator.clipboard.writeText(s.suggested_text || '');
                            addToast('已复制建议文本', 'success');
                          } catch (e) {
                            console.error(e);
                            addToast('复制失败（可能缺少剪贴板权限）', 'error');
                          }
                        }}
                        title="复制建议文本"
                      >
                        <Copy size={14} className="mr-1" />
                        复制
                      </BookButton>
                    </div>
                  </div>

                  {s.reason ? (
                    <div className="text-xs text-book-text-muted mt-2 whitespace-pre-wrap leading-relaxed">
                      理由：{s.reason}
                    </div>
                  ) : null}

                  <div className="grid grid-cols-1 gap-2 mt-3">
                    <div className="text-xs">
                      <div className="text-[11px] text-book-text-muted mb-1">原文</div>
                      <div className="p-2 rounded border border-book-border/40 bg-book-bg-paper text-book-text-main whitespace-pre-wrap leading-relaxed">
                        {s.original_text}
                      </div>
                    </div>
                    <div className="text-xs">
                      <div className="text-[11px] text-book-text-muted mb-1">建议</div>
                      <div className="p-2 rounded border border-book-border/40 bg-book-bg-paper text-book-text-main whitespace-pre-wrap leading-relaxed">
                        {s.suggested_text}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </BookCard>

      <Modal
        isOpen={Boolean(previewSuggestion)}
        onClose={() => setPreviewSuggestion(null)}
        title={previewSuggestion ? `预览建议：段落 ${previewSuggestion.paragraph_index + 1} · ${previewSuggestion.category}` : '预览建议'}
        maxWidthClassName="max-w-4xl"
        footer={
          <div className="flex justify-end gap-2">
            {previewSuggestion && onLocateText && (previewSuggestion.original_text || '').trim() ? (
              <BookButton
                variant="secondary"
                onClick={() => onLocateText(previewSuggestion.original_text)}
                title="在编辑器中定位原文片段"
              >
                <Search size={14} className="mr-1" />
                定位原文
              </BookButton>
            ) : null}
            {previewSuggestion && onChangeContent ? (
              <BookButton
                variant="secondary"
                onClick={() => {
                  if (!previewSuggestion) return;
                  startInlinePreview(previewSuggestion);
                  setPreviewSuggestion(null);
                }}
                title="在编辑器中预览（确认/撤销）"
              >
                <Eye size={14} className="mr-1" />
                预览到编辑器
              </BookButton>
            ) : null}
            <BookButton variant="ghost" onClick={() => setPreviewSuggestion(null)}>
              关闭
            </BookButton>
            <BookButton
              variant="primary"
              onClick={() => {
                if (!previewSuggestion) return;
                applySuggestion(previewSuggestion);
                setPreviewSuggestion(null);
              }}
              disabled={!previewSuggestion || !onChangeContent || previewApplied}
            >
              {previewApplied ? '已应用' : '应用到编辑器'}
            </BookButton>
          </div>
        }
      >
        {previewSuggestion ? (
          <div className="space-y-4">
            {previewSuggestion.reason ? (
              <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 leading-relaxed whitespace-pre-wrap">
                理由：{previewSuggestion.reason}
              </div>
            ) : null}

            <div className="space-y-2">
              <div className="text-xs font-bold text-book-text-sub">差异高亮</div>
              <div className="text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed bg-book-bg-paper p-3 rounded-lg border border-book-border/40 overflow-auto max-h-[30vh]">
                {buildSimpleInlineDiff(previewSuggestion.original_text, previewSuggestion.suggested_text).map((seg, idx) => (
                  <span
                    key={`pd-${idx}`}
                    className={
                      seg.type === 'remove'
                        ? 'bg-red-500/10 text-red-700 line-through'
                        : seg.type === 'add'
                          ? 'bg-green-500/10 text-green-700'
                          : ''
                    }
                  >
                    {seg.text}
                  </span>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="text-xs font-bold text-book-text-sub">原文</div>
                <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed bg-book-bg-paper p-3 rounded-lg border border-book-border/40 overflow-auto max-h-[60vh]">
                  {previewSuggestion.original_text}
                </pre>
              </div>
              <div className="space-y-2">
                <div className="text-xs font-bold text-book-text-sub">建议</div>
                <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed bg-book-bg-paper p-3 rounded-lg border border-book-border/40 overflow-auto max-h-[60vh]">
                  {previewSuggestion.suggested_text}
                </pre>
              </div>
            </div>

            <div className="text-xs text-book-text-muted">
              提示：应用后可在面板顶部点击“撤销”恢复上一次应用前的正文。
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
};
