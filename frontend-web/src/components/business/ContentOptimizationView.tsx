import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useToast } from '../feedback/Toast';
import { confirmDialog } from '../feedback/ConfirmDialog';
import { useSSE } from '../../hooks/useSSE';
import { apiClient } from '../../api/client';
import {
  DIMENSIONS,
  THINKING_LABELS,
  buildUpdatedContent,
  getSuggestionKey,
  parseRangeInput,
} from './content-optimization/shared';
import type {
  AnalysisScope,
  InlinePreviewState,
  OptimizationMode,
  ParagraphPreviewResponse,
  Suggestion,
  ThinkingEvent,
  ThinkingEventType,
  UndoSnapshot,
} from './content-optimization/shared';
import { ContentOptimizationControlsCard } from './content-optimization/ContentOptimizationControlsCard';
import { ContentOptimizationInlinePreviewCard } from './content-optimization/ContentOptimizationInlinePreviewCard';
import { ContentOptimizationStatusCard } from './content-optimization/ContentOptimizationStatusCard';
import { ContentOptimizationSuggestionsPanel } from './content-optimization/ContentOptimizationSuggestionsPanel';
import { ContentOptimizationThinkingPanel } from './content-optimization/ContentOptimizationThinkingPanel';
import { OptimizationSuggestionPreviewModal } from './content-optimization/OptimizationSuggestionPreviewModal';

const MAX_UNDO_STACK_SIZE = 30;
const MAX_THINKING_EVENTS = 400;

const clampUndoStack = (stack: UndoSnapshot[]): UndoSnapshot[] => {
  if (stack.length <= MAX_UNDO_STACK_SIZE) {
    return stack;
  }
  return stack.slice(stack.length - MAX_UNDO_STACK_SIZE);
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
  const thinkingScrollRef = useRef<HTMLDivElement>(null);

  const appliedSet = useMemo(() => new Set(appliedKeys), [appliedKeys]);

  const pushUndoSnapshot = useCallback((snapshot: UndoSnapshot) => {
    setUndoStack((prev) => clampUndoStack([...prev, snapshot]));
  }, []);

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
    pushUndoSnapshot(snapshot);

    onChangeContent(result.content);
    if (onSelectRange) onSelectRange(result.range.start, result.range.end);
    setAppliedKeys((prev) => (prev.includes(key) ? prev : [...prev, key]));
    addToast('已应用该条建议（仅修改本地编辑器内容）', 'success');
  }, [addToast, content, onChangeContent, onSelectRange, pushUndoSnapshot]);

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
  }, [addToast, content, inlinePreview, onChangeContent, onSelectRange]);

  const confirmInlinePreview = useCallback(() => {
    if (!inlinePreview) return;
    const snapshot: UndoSnapshot = { content: inlinePreview.beforeContent, key: inlinePreview.key, label: inlinePreview.label };
    pushUndoSnapshot(snapshot);
    setAppliedKeys((prev) => (prev.includes(inlinePreview.key) ? prev : [...prev, inlinePreview.key]));
    setInlinePreview(null);
    addToast(`已确认并应用：${inlinePreview.label}`, 'success');
  }, [addToast, inlinePreview, pushUndoSnapshot]);

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
      if (next.length > MAX_THINKING_EVENTS) {
        next.splice(0, next.length - MAX_THINKING_EVENTS);
      }
      return next;
    });
  }, []);

  useEffect(() => {
    if (!thinkingExpanded) return;
    const el = thinkingScrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [thinkingExpanded, thinkingEvents.length]);

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
  }, [addToast, preview, rangeInput]);

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

  const copySuggestionText = useCallback(async (suggestion: Suggestion) => {
    try {
      await navigator.clipboard.writeText(suggestion.suggested_text || '');
      addToast('已复制建议文本', 'success');
    } catch (e) {
      console.error(e);
      addToast('复制失败（可能缺少剪贴板权限）', 'error');
    }
  }, [addToast]);

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
  }, [previewSuggestion]);

  const previewApplied = useMemo(() => {
    if (!previewKey) return false;
    return appliedSet.has(previewKey);
  }, [appliedSet, previewKey]);

  const canEdit = Boolean(onChangeContent);

  const toggleParagraphSelection = useCallback((index: number) => {
    setSelectedParagraphs((prev) => {
      if (prev.includes(index)) {
        return prev.filter((item) => item !== index);
      }
      return [...prev, index].sort((left, right) => left - right);
    });
  }, []);

  const previewSuggestionInEditor = useCallback(() => {
    if (!previewSuggestion) return;
    startInlinePreview(previewSuggestion);
    setPreviewSuggestion(null);
  }, [previewSuggestion, startInlinePreview]);

  const applyPreviewSuggestion = useCallback(() => {
    if (!previewSuggestion) return;
    applySuggestion(previewSuggestion);
    setPreviewSuggestion(null);
  }, [applySuggestion, previewSuggestion]);

  return (
    <div className="space-y-4">
      <ContentOptimizationStatusCard
        statusText={statusText}
        currentParagraph={currentParagraph}
        totalParagraphs={totalParagraphs}
      />

      {inlinePreview ? (
        <ContentOptimizationInlinePreviewCard
          inlinePreview={inlinePreview}
          onSelectRange={onSelectRange}
          onRevert={revertInlinePreview}
          onConfirm={confirmInlinePreview}
        />
      ) : null}

      <ContentOptimizationControlsCard
        mode={mode}
        scope={scope}
        dimensions={dimensions}
        preview={preview}
        selectedParagraphs={selectedParagraphs}
        rangeInput={rangeInput}
        previewLoading={previewLoading}
        running={running}
        paused={paused}
        sessionId={sessionId}
        onModeChange={setMode}
        onScopeChange={setScope}
        onToggleDimension={toggleDimension}
        onFetchPreview={fetchPreview}
        onStartOptimization={startOptimization}
        onContinueSession={continueSession}
        onStopStream={stopStream}
        onCancelSession={cancelSession}
        onRangeInputChange={setRangeInput}
        onApplyRangeSelection={applyRangeSelection}
        onSelectAllPreview={selectAllPreview}
        onClearPreviewSelection={clearPreviewSelection}
        onToggleParagraphSelection={toggleParagraphSelection}
      />

      <ContentOptimizationThinkingPanel
        thinkingEvents={thinkingEvents}
        thinkingExpanded={thinkingExpanded}
        thinkingScrollRef={thinkingScrollRef}
        running={running}
        onCopy={copyThinkingStream}
        onClear={() => setThinkingEvents([])}
        onToggleExpanded={() => setThinkingExpanded((value) => !value)}
      />

      <ContentOptimizationSuggestionsPanel
        suggestions={suggestions}
        appliedSet={appliedSet}
        inlinePreviewKey={inlinePreview?.key ?? null}
        lastUndo={lastUndo}
        undoStackLength={undoStack.length}
        canEdit={canEdit}
        onUndoLastApply={undoLastApply}
        onStartInlinePreview={startInlinePreview}
        onOpenPreview={setPreviewSuggestion}
        onApplySuggestion={applySuggestion}
        onConfirmInlinePreview={confirmInlinePreview}
        onCopySuggestion={copySuggestionText}
        onLocateText={onLocateText}
      />

      <OptimizationSuggestionPreviewModal
        previewSuggestion={previewSuggestion}
        previewApplied={previewApplied}
        canEdit={canEdit}
        onClose={() => setPreviewSuggestion(null)}
        onPreviewToEditor={previewSuggestionInEditor}
        onApplyToEditor={applyPreviewSuggestion}
        onLocateText={onLocateText}
      />
    </div>
  );
};
