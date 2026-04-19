import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSSE } from '../hooks/useSSE';
import { novelsApi } from '../api/novels';
import { codingApi } from '../api/coding';
import { confirmDialog } from '../components/feedback/ConfirmDialog';
import { readBootstrapCache, writeBootstrapCache } from '../utils/bootstrapCache';
import {
  clearBlueprintGenerationPending,
  hasRecentBlueprintGenerationPending,
  markBlueprintGenerationPending,
} from '../utils/blueprintPending';
import {
  AppViewportFrame,
  AppViewportShell,
} from '../components/layout/AppViewport';
import { BlueprintPreviewModal } from './inspiration-chat/BlueprintPreviewModal';
import { InspirationChatConversationPanel } from './inspiration-chat/InspirationChatConversationPanel';
import { InspirationChatGuidePanel } from './inspiration-chat/InspirationChatGuidePanel';
import { InspirationChatHero } from './inspiration-chat/InspirationChatHero';
import { InspirationChatWorkspace } from './inspiration-chat/InspirationChatWorkspace';
import {
  getInspirationChatBootstrapKey,
  getInspirationChatPersistKey,
  INSPIRATION_CHAT_BOOTSTRAP_TTL_MS,
  isPlainObject,
  Message,
  normalizeMessageContentForDisplay,
  normalizeTextNewlines,
  pickFirstNonEmptyString,
  readPersistedInspirationChatState,
  tryParseJsonFromText,
  writePersistedInspirationChatState,
  type InspirationChatBootstrapSnapshot,
  type WorkspacePane,
} from './inspiration-chat/shared';

interface InspirationChatProps {
  mode?: 'novel' | 'coding';
}

export const InspirationChat: React.FC<InspirationChatProps> = ({ mode = 'novel' }) => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isElectronRuntime] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    const runtime = typeof document !== 'undefined' ? document.documentElement.dataset?.runtime : undefined;
    if (runtime === 'electron') return true;
    return Boolean((window as any)?.electronAPI?.isElectron);
  });
  const [showBlueprintBtn, setShowBlueprintBtn] = useState(false);
  const [isGeneratingBlueprint, setIsGeneratingBlueprint] = useState(false);
  const [isBlueprintConfirmOpen, setIsBlueprintConfirmOpen] = useState(false);
  const [blueprintPreview, setBlueprintPreview] = useState<any | null>(null);
  const [blueprintTip, setBlueprintTip] = useState<string | null>(null);
  const [options, setOptions] = useState<any[]>([]);
  const [conversationState, setConversationState] = useState<any>({});
  const [workspacePane, setWorkspacePane] = useState<WorkspacePane>('conversation');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const completionHintShownRef = useRef(false);
  const pendingChunkRef = useRef('');
  const chunkFlushTimerRef = useRef<number | null>(null);
  const isStreamingRef = useRef(false);
  const messageIdSeqRef = useRef(0);
  const blueprintResumeCheckedRef = useRef(false);

  useEffect(() => {
    completionHintShownRef.current = false;
    pendingChunkRef.current = '';
    if (chunkFlushTimerRef.current !== null) {
      window.clearTimeout(chunkFlushTimerRef.current);
      chunkFlushTimerRef.current = null;
    }
    isStreamingRef.current = false;
    setIsTyping(false);
    setOptions([]);
    setInputValue('');
    setBlueprintTip(null);
    setBlueprintPreview(null);
    setIsBlueprintConfirmOpen(false);

    if (!id) {
      setMessages([]);
      setShowBlueprintBtn(false);
      setConversationState({});
      return;
    }

    const persisted = readPersistedInspirationChatState(getInspirationChatPersistKey(mode, id));
    const cached = readBootstrapCache<InspirationChatBootstrapSnapshot>(
      getInspirationChatBootstrapKey(mode, id),
      INSPIRATION_CHAT_BOOTSTRAP_TTL_MS,
    );

    if (!cached) {
      setMessages([]);
      setShowBlueprintBtn(Boolean(persisted?.showBlueprintBtn));
      setConversationState(persisted?.conversationState && typeof persisted.conversationState === 'object' ? persisted.conversationState : {});
      return;
    }

    const safeMessages = Array.isArray(cached.messages)
      ? cached.messages
          .filter((item) => item && (item.role === 'user' || item.role === 'assistant' || item.role === 'system'))
          .map((item, idx) => ({
            id: Number(item.id) || (Date.now() + idx),
            role: item.role,
            content: normalizeMessageContentForDisplay(item.role, item.content),
          }))
      : [];

    setMessages(safeMessages);
    setShowBlueprintBtn(Boolean(cached.showBlueprintBtn ?? persisted?.showBlueprintBtn));
    const cachedState = cached.conversationState && typeof cached.conversationState === 'object' ? cached.conversationState : {};
    const persistedState = persisted?.conversationState && typeof persisted.conversationState === 'object' ? persisted.conversationState : {};
    setConversationState({ ...persistedState, ...cachedState });
    setOptions(Array.isArray(cached.options) ? cached.options : []);
  }, [id, mode]);

  const nextMessageId = useCallback(() => {
    messageIdSeqRef.current = (messageIdSeqRef.current + 1) % 1000;
    return Date.now() * 1000 + messageIdSeqRef.current;
  }, []);

  const flushPendingChunks = useCallback(() => {
    const chunk = pendingChunkRef.current;
    if (!chunk) return;

    pendingChunkRef.current = '';
    setMessages((prev) => {
      const lastIdx = prev.length - 1;
      if (lastIdx < 0) return prev;
      const last = prev[lastIdx];
      if (!last?.isStreaming) return prev;

      const next = [...prev];
      next[lastIdx] = { ...last, content: String(last.content || "") + chunk };
      return next;
    });
  }, []);

  const scheduleChunkFlush = useCallback(() => {
    if (chunkFlushTimerRef.current !== null) return;

    chunkFlushTimerRef.current = window.setTimeout(() => {
      chunkFlushTimerRef.current = null;
      flushPendingChunks();
    }, 48);
  }, [flushPendingChunks]);

  useEffect(() => {
    return () => {
      pendingChunkRef.current = "";
      if (chunkFlushTimerRef.current !== null) {
        window.clearTimeout(chunkFlushTimerRef.current);
        chunkFlushTimerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!id) return;
    if (isTyping) return;
    if (messages.some((item) => Boolean(item.isStreaming))) return;

    const compactMessages = messages
      .map((item, idx) => ({
        id: Number(item.id) || (Date.now() + idx),
        role: item.role,
        content: String(item.content || ''),
      }))
      .slice(-200);

    writeBootstrapCache<InspirationChatBootstrapSnapshot>(getInspirationChatBootstrapKey(mode, id), {
      messages: compactMessages,
      showBlueprintBtn: Boolean(showBlueprintBtn),
      conversationState: conversationState && typeof conversationState === 'object' ? conversationState : {},
      options: Array.isArray(options) ? options : [],
    });

    writePersistedInspirationChatState(getInspirationChatPersistKey(mode, id), {
      showBlueprintBtn: Boolean(showBlueprintBtn),
      conversationState: conversationState && typeof conversationState === 'object' ? conversationState : {},
    });
  }, [conversationState, id, isTyping, messages, mode, options, showBlueprintBtn]);
  
  // Load chat history
  useEffect(() => {
    completionHintShownRef.current = false;
    if (id) {
      const loadHistory = async () => {
        const history = mode === 'novel'
          ? await novelsApi.getChatHistory(id)
          : await codingApi.getChatHistory(id);
        const mapped: Message[] = history.map((msg: any) => ({
          id: msg.id,
          role: msg.role as 'user' | 'assistant',
          content: normalizeMessageContentForDisplay(msg.role, msg.content),
        }));

        // 对齐桌面端：首次进入时也显示一条欢迎语（作为对话气泡，而不是空态占位）
        if (mapped.length === 0) {
          const welcome =
            mode === 'novel'
              ? "你好！我是AFN AI助手。\n\n请告诉我你的创意想法，我会帮你创建一个完整的小说蓝图。"
              : "你好！我是AFN需求分析助手。\n\n请告诉我你想要构建什么样的系统，我会帮你分析需求并设计项目架构。";
          setOptions([]);
          setMessages([
            {
              id: nextMessageId(),
              role: 'assistant',
              content: welcome,
            },
          ]);
        } else {
          setOptions([]);
          setMessages(mapped);
        }

        // 基于最后一条 assistant 的结构化记录，恢复 conversation_state / ready_for_blueprint / progress_summary
        for (let i = history.length - 1; i >= 0; i -= 1) {
          const record = history[i];
          if (!record || record.role !== 'assistant') continue;
          const parsed = tryParseJsonFromText(String(record.content || ''));
          if (!isPlainObject(parsed)) continue;

          const nextState: Record<string, unknown> = isPlainObject(parsed.conversation_state)
            ? { ...parsed.conversation_state }
            : {};

          if (pickFirstNonEmptyString(parsed.next_question) && !pickFirstNonEmptyString(nextState.next_question)) {
            nextState.next_question = parsed.next_question;
          }
          if (Array.isArray(parsed.next_question_points) && !Array.isArray(nextState.next_question_points)) {
            nextState.next_question_points = parsed.next_question_points;
          }
          if (pickFirstNonEmptyString(parsed.progress_summary) && !pickFirstNonEmptyString(nextState.progress_summary)) {
            nextState.progress_summary = parsed.progress_summary;
          }

          if (Object.keys(nextState).length > 0) {
            setConversationState(nextState);
          }

          const uiControl = isPlainObject(parsed.ui_control) ? parsed.ui_control : null;
          const uiOptions = uiControl && Array.isArray(uiControl.options) ? uiControl.options : [];
          setOptions(uiOptions);

          const ready = parsed.ready_for_blueprint;
          const complete = parsed.is_complete;
          if (typeof ready === 'boolean') {
            setShowBlueprintBtn(ready);
          } else if (typeof complete === 'boolean') {
            setShowBlueprintBtn(complete);
          } else {
            // 如果拿不到明确状态，尽量沿用已有状态；最后再兜底使用条数阈值
            setShowBlueprintBtn((prev) => prev || history.length > 2);
          }
          break;
        }
      };
      loadHistory().catch((e) => console.error(e));
    }
  }, [id, mode, nextMessageId]);

  // Scroll to bottom（流式输出时使用 auto，降低滚动抖动）
  useEffect(() => {
    const node = messagesEndRef.current;
    if (!node) return;

    const prefersReducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;

    node.scrollIntoView({
      behavior: (prefersReducedMotion || isStreamingRef.current) ? "auto" : "smooth",
      block: "end",
    });
  }, [messages]);

  const handleEvent = useCallback((event: string, data: any) => {
    if (event === 'streaming_start') {
      isStreamingRef.current = true;
      pendingChunkRef.current = '';
      if (chunkFlushTimerRef.current !== null) {
        window.clearTimeout(chunkFlushTimerRef.current);
        chunkFlushTimerRef.current = null;
      }

      setIsTyping(true);
      setOptions([]);
      setMessages((prev) => [
        ...prev,
        {
          id: nextMessageId(),
          role: 'assistant',
          content: '',
          isStreaming: true,
        },
      ]);
      return;
    }

    if (event === 'ai_message_chunk') {
      const chunk = String(data?.text || '');
      if (!chunk) return;
      pendingChunkRef.current += chunk;
      scheduleChunkFlush();
      return;
    }

    if (event === 'option') {
      const optionPayload = data?.option ?? data;
      if (optionPayload !== null && optionPayload !== undefined) {
        setOptions((prev) => [...prev, optionPayload]);
      }
      return;
    }

    if (event === 'complete') {
      if (chunkFlushTimerRef.current !== null) {
        window.clearTimeout(chunkFlushTimerRef.current);
        chunkFlushTimerRef.current = null;
      }
      flushPendingChunks();

      isStreamingRef.current = false;
      setIsTyping(false);
      const finalAiMessage = typeof data?.ai_message === 'string' ? String(data.ai_message) : null;
      if (Array.isArray(data?.options)) {
        setOptions(data.options);
      }
      if (data?.conversation_state && typeof data.conversation_state === 'object') {
        const nextState = { ...(data.conversation_state || {}) } as any;
        if (data?.next_question && !nextState.next_question) {
          nextState.next_question = data.next_question;
        }
        if (Array.isArray(data?.next_question_points) && !nextState.next_question_points) {
          nextState.next_question_points = data.next_question_points;
        }
        if (data?.progress_summary && !nextState.progress_summary) {
          nextState.progress_summary = data.progress_summary;
        }
        setConversationState(nextState);
      }

      const readyForBlueprint = Boolean(data?.ready_for_blueprint);
      if (readyForBlueprint) setShowBlueprintBtn(true);
      const shouldAddHint = mode === 'coding' && readyForBlueprint && !completionHintShownRef.current;
      if (shouldAddHint) completionHintShownRef.current = true;

      setMessages((prev) => {
        const lastIdx = prev.length - 1;
        let next = prev;

        if (lastIdx >= 0 && prev[lastIdx]?.isStreaming) {
          const resolvedContent = finalAiMessage ?? prev[lastIdx].content;
          next = [...prev];
          next[lastIdx] = {
            ...prev[lastIdx],
            isStreaming: false,
            content: normalizeMessageContentForDisplay(prev[lastIdx].role, resolvedContent),
          };
        }

        if (shouldAddHint) {
          return [
            ...next,
            {
              id: nextMessageId(),
              role: 'assistant',
              content: '需求分析已完成！点击右上角「生成架构设计」按钮，开始生成项目架构。',
            },
          ];
        }

        return next;
      });
      return;
    }

    if (event === 'error') {
      if (chunkFlushTimerRef.current !== null) {
        window.clearTimeout(chunkFlushTimerRef.current);
        chunkFlushTimerRef.current = null;
      }
      flushPendingChunks();

      isStreamingRef.current = false;
      setIsTyping(false);
      setMessages((prev) => {
        const lastIdx = prev.length - 1;
        if (lastIdx < 0 || !prev[lastIdx]?.isStreaming) return prev;
        const next = [...prev];
        next[lastIdx] = { ...prev[lastIdx], isStreaming: false };
        return next;
      });

      console.error("SSE Error:", data);
    }
  }, [flushPendingChunks, mode, nextMessageId, scheduleChunkFlush]);

  const { connect } = useSSE(handleEvent);

  useEffect(() => {
    if (!id) return;
    if (blueprintResumeCheckedRef.current) return;
    if (!hasRecentBlueprintGenerationPending(mode, id)) return;
    blueprintResumeCheckedRef.current = true;

    void (async () => {
      try {
        if (mode !== 'novel') return;

        const project = await novelsApi.get(id, { silent: true });
        const status = String(project?.status || '').trim().toLowerCase();
        const blueprint = project?.blueprint;
        const hasBlueprint = Boolean(blueprint && typeof blueprint === 'object');

        if (status === 'draft' || status === 'inspiration' || !hasBlueprint) {
          return;
        }

        clearBlueprintGenerationPending(mode, id);
        setBlueprintPreview(blueprint);
        setBlueprintTip('检测到上次蓝图生成可能已完成（自动恢复）。');
        setIsBlueprintConfirmOpen(true);
      } catch {
        // ignore
      }
    })();
  }, [id, mode]);

  const sendText = async (text: string) => {
    if (!id) return;
    const trimmed = String(text || '').trim();
    if (!trimmed) return;

    const userMsg: Message = {
      id: nextMessageId(),
      role: 'user',
      content: trimmed
    };

    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setIsTyping(true);

    const endpoint = mode === 'novel'
      ? `/novels/${id}/inspiration/converse-stream`
      : codingApi.converseStream(id);

    await connect(endpoint, {
      user_input: { text: userMsg.content },
      conversation_state: conversationState || {}
    });
  };

  const handleSend = async () => {
    await sendText(inputValue);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Electron/部分浏览器在中文输入法组合阶段按回车，会触发 keydown；
    // 这里避免误把“确认输入法候选词”当成“发送消息”。
    const composing = (e.nativeEvent as any)?.isComposing === true || (e.nativeEvent as any)?.keyCode === 229;
    if (composing) return;

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const generateBlueprint = async (opts?: { allowIncomplete?: boolean }) => {
    if (!id) return;
    markBlueprintGenerationPending(mode, id);
    try {
      setIsGeneratingBlueprint(true);
      setBlueprintTip(null);

      if (mode === 'novel') {
        const res = await novelsApi.generateBlueprint(id, { allowIncomplete: Boolean(opts?.allowIncomplete) });
        setBlueprintPreview(res?.blueprint || null);
        setBlueprintTip(String(res?.ai_message || '蓝图已生成'));
      } else {
        const res = await codingApi.generateBlueprint(id);
        setBlueprintPreview(res?.blueprint || null);
        setBlueprintTip('架构蓝图已生成');
      }

      clearBlueprintGenerationPending(mode, id);
      setIsBlueprintConfirmOpen(true);
    } catch (e: any) {
      console.error(e);
      const msg = String(e?.response?.data?.detail || e?.message || '生成蓝图失败').trim() || '生成蓝图失败';
      const status = Number(e?.response?.status || 0);
      const isTimeout =
        String(e?.code || '') === 'ECONNABORTED' ||
        msg.toLowerCase().includes('timeout') ||
        msg.includes('超时');
      const isNetworkLike = !status;
      const shouldKeepPending = isTimeout || isNetworkLike || status >= 500;
      if (!shouldKeepPending) {
        clearBlueprintGenerationPending(mode, id);
      }
      setBlueprintTip(
        isTimeout
          ? '蓝图生成耗时较长，前端等待已结束。\n后端可能仍在继续生成：建议稍后从项目列表重新进入。\n如果你重新进入后直接进入工作台/项目详情，说明蓝图其实已经生成成功（只是本次前端超时/断连未收到响应）。'
          : msg,
      );
      setIsBlueprintConfirmOpen(true);
    } finally {
      setIsGeneratingBlueprint(false);
    }
  };

  const handleGenerateBlueprintClick = async () => {
    if (!id) return;
    if (isTyping || isGeneratingBlueprint) return;

    const allowIncomplete = !showBlueprintBtn;
    if (allowIncomplete) {
      const ok = await confirmDialog({
        title: mode === 'coding' ? '试生成架构设计' : '试生成蓝图',
        message:
          mode === 'coding'
            ? '当前信息可能还不完整。\n\n你可以继续对话把目标、核心功能与规模说清楚；也可以先生成一版草稿架构设计，再回来补充并重新生成。\n\n是否继续试生成？'
            : '当前信息可能还不完整。\n\n你可以继续对话把世界观、人物动机与冲突说清楚；也可以先生成一版草稿蓝图，再回来补充并重新生成。\n\n是否继续试生成？',
        confirmText: '继续试生成',
        dialogType: 'warning',
      });
      if (!ok) return;
    }

    await generateBlueprint({ allowIncomplete });
  };

  const confirmBlueprintAndContinue = () => {
    if (!id) return;
    if (!blueprintPreview || typeof blueprintPreview !== 'object') {
      setIsBlueprintConfirmOpen(false);
      return;
    }
    setIsBlueprintConfirmOpen(false);
    setBlueprintPreview(null);
    setBlueprintTip(null);
    clearBlueprintGenerationPending(mode, id);
    if (mode === 'novel') navigate(`/novel/${id}`);
    else navigate(`/coding/detail/${id}`);
  };

  const regenerateBlueprint = async () => {
    if (!id) return;
    markBlueprintGenerationPending(mode, id);
    setIsGeneratingBlueprint(true);
    setBlueprintTip(null);
    try {
      if (mode === 'novel') {
        try {
          const res = await novelsApi.generateBlueprint(id);
          setBlueprintPreview(res?.blueprint || null);
          setBlueprintTip(String(res?.ai_message || '蓝图已重新生成'));
        } catch (e: any) {
          const status = Number(e?.response?.status || 0);
	          const detail = String(e?.response?.data?.detail || '');
	          if (status === 409) {
	            const ok = await confirmDialog({
	              title: '强制重新生成蓝图',
	              message: `${detail || '检测到已有章节大纲/后续数据。重新生成蓝图将清理后续数据。'}\n\n是否强制重新生成？`,
	              confirmText: '强制重生成',
	              dialogType: 'danger',
	            });
	            if (!ok) {
                clearBlueprintGenerationPending(mode, id);
                return;
              }
	            const res = await novelsApi.generateBlueprint(id, { forceRegenerate: true });
	            setBlueprintPreview(res?.blueprint || null);
	            setBlueprintTip(String(res?.ai_message || '蓝图已强制重新生成'));
	          } else {
            throw e;
          }
        }
      } else {
        const res = await codingApi.generateBlueprint(id);
        setBlueprintPreview(res?.blueprint || null);
        setBlueprintTip('架构蓝图已重新生成');
      }
      clearBlueprintGenerationPending(mode, id);
    } catch (e: any) {
      console.error(e);
      const msg = String(e?.response?.data?.detail || e?.message || '重新生成失败').trim() || '重新生成失败';
      const status = Number(e?.response?.status || 0);
      const isTimeout =
        String(e?.code || '') === 'ECONNABORTED' ||
        msg.toLowerCase().includes('timeout') ||
        msg.includes('超时');
      const isNetworkLike = !status;
      const shouldKeepPending = isTimeout || isNetworkLike || status >= 500;
      if (!shouldKeepPending) {
        clearBlueprintGenerationPending(mode, id);
      }
      setBlueprintTip(
        isTimeout
          ? '重新生成耗时较长，前端等待已结束。\n后端可能仍在继续生成：建议稍后从项目列表重新进入。\n如果你重新进入后直接进入工作台/项目详情，说明蓝图其实已经生成成功（只是本次前端超时/断连未收到响应）。'
          : String(e?.response?.data?.detail || msg || '重新生成失败'),
      );
    } finally {
      setIsGeneratingBlueprint(false);
    }
  };

  const stageTitle = mode === 'novel' ? '灵感构思' : '需求分析';
  const stageDescription = mode === 'novel'
    ? '把碎片化念头压成故事方向、人物动机与蓝图结构。'
    : '把模糊需求整理为可执行的系统边界、角色职责与架构方案。';
  const safeConversationState = conversationState && typeof conversationState === 'object' ? conversationState : {};

  const extractProgressSummary = (state: any) => {
    if (!state || typeof state !== 'object') return null;
    const raw = state.progress_summary ?? state.progressSummary ?? state.collected_summary ?? state.collectedSummary;
    if (raw === null || raw === undefined) return null;
    const text = normalizeTextNewlines(String(raw)).trim();
    return text ? text : null;
  };

  const progressSummary = isTyping ? null : extractProgressSummary(safeConversationState);
  const progressSummaryLines = progressSummary
    ? progressSummary
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => line.replace(/^[-•]\s*/, ''))
    : [];
  const progressSummaryPlaceholder = mode === 'novel'
    ? '每轮回答后，这里会自动总结已确认的世界观、人物与冲突信息，便于你判断何时生成蓝图。'
    : '每轮回答后，这里会自动总结已确认的目标、功能与约束信息，便于你判断何时生成架构设计。';
  const progressSummaryMaxLines = isElectronRuntime ? 16 : 10;

  const chapterCount = Number((safeConversationState as any)?.chapter_count ?? (safeConversationState as any)?.chapterCount ?? 0) || null;

  const getScaleLabel = (scale: string) => {
    const normalized = String(scale || '').trim().toLowerCase();
    if (normalized === 'small') return '小型';
    if (normalized === 'medium') return '中型';
    if (normalized === 'large') return '大型';
    if (normalized === 'enterprise') return '企业级';
    return scale || '（未设置）';
  };

  const collectedInfoItems: Array<{ label: string; value: string }> = (() => {
    const items: Array<{ label: string; value: string }> = [];

    if (mode === 'coding') {
      const projectGoal = String((safeConversationState as any)?.project_goal ?? (safeConversationState as any)?.projectGoal ?? '').trim();
      const coreFeaturesRaw = (safeConversationState as any)?.core_features ?? (safeConversationState as any)?.coreFeatures;
      const coreFeatures = Array.isArray(coreFeaturesRaw)
        ? coreFeaturesRaw.map((item) => String(item || '').trim()).filter(Boolean)
        : [];
      const scale = String((safeConversationState as any)?.scale ?? '').trim();
      const targetUsers = String((safeConversationState as any)?.target_users ?? (safeConversationState as any)?.targetUsers ?? '').trim();
      const techPreferences = String((safeConversationState as any)?.tech_preferences ?? (safeConversationState as any)?.techPreferences ?? '').trim();

      if (projectGoal) items.push({ label: '项目目标', value: projectGoal });
      if (coreFeatures.length > 0) items.push({ label: '核心功能', value: coreFeatures.slice(0, 6).join('、') });
      if (scale) items.push({ label: '项目规模', value: getScaleLabel(scale) });
      if (targetUsers) items.push({ label: '目标用户', value: targetUsers });
      if (techPreferences) items.push({ label: '技术偏好', value: techPreferences });
      return items;
    }

    if (chapterCount) items.push({ label: '预期篇幅', value: `${chapterCount} 章` });
    const round = Number((safeConversationState as any)?.round ?? 0) || null;
    if (round) items.push({ label: '对话轮次', value: `${round}` });
    return items;
  })();

  const codingRequiredProgress = mode === 'coding'
    ? (() => {
        const projectGoal = String((safeConversationState as any)?.project_goal ?? (safeConversationState as any)?.projectGoal ?? '').trim();
        const coreFeaturesRaw = (safeConversationState as any)?.core_features ?? (safeConversationState as any)?.coreFeatures;
        const coreFeatures = Array.isArray(coreFeaturesRaw)
          ? coreFeaturesRaw.map((item) => String(item || '').trim()).filter(Boolean)
          : [];
        const scale = String((safeConversationState as any)?.scale ?? '').trim();
        const done =
          (projectGoal ? 1 : 0) +
          (coreFeatures.length > 0 ? 1 : 0) +
          (scale ? 1 : 0);
        return { done, total: 3 };
      })()
    : null;

	  const headerCompactStatus = isTyping
	    ? '生成中'
	    : showBlueprintBtn
	      ? '可生成'
	      : '进行中';
	  const headerProgressLabel = mode === 'coding' ? '必需' : '篇幅';
	  const headerProgressValue = mode === 'coding'
	    ? (codingRequiredProgress ? `${codingRequiredProgress.done}/${codingRequiredProgress.total}` : '—')
	    : (chapterCount ? `${chapterCount}章` : '未定');
	  const headerCollectedValue = `${Math.max(0, collectedInfoItems.length)}项`;

	  const conversationStatus = isTyping
	    ? 'AI 正在接续你的上下文'
	    : showBlueprintBtn
      ? (mode === 'novel' ? '已具备生成蓝图条件' : '已具备生成架构设计条件')
      : '继续补充信息，让结构更扎实';
  return (
    <AppViewportShell>
      <BlueprintPreviewModal
        isOpen={isBlueprintConfirmOpen}
        mode={mode}
        showBlueprintBtn={showBlueprintBtn}
        blueprintPreview={blueprintPreview}
        blueprintTip={blueprintTip}
        isGeneratingBlueprint={isGeneratingBlueprint}
        onClose={() => setIsBlueprintConfirmOpen(false)}
        onRegenerate={regenerateBlueprint}
        onConfirm={confirmBlueprintAndContinue}
      />

      <AppViewportFrame size={isElectronRuntime ? 'wide' : 'default'}>
        <div
          className={
            isElectronRuntime
              ? 'min-h-0 flex-1 grid grid-cols-[minmax(320px,420px)_minmax(0,1fr)] grid-rows-[auto_minmax(0,1fr)] gap-4'
              : 'min-h-0 flex-1 flex flex-col gap-4'
          }
        >
          <InspirationChatHero
            isElectronRuntime={isElectronRuntime}
            mode={mode}
            stageTitle={stageTitle}
            stageDescription={stageDescription}
            headerCompactStatus={headerCompactStatus}
            headerProgressLabel={headerProgressLabel}
            headerProgressValue={headerProgressValue}
            headerCollectedValue={headerCollectedValue}
            conversationStatus={conversationStatus}
            messagesCount={messages.length}
            chapterCount={chapterCount}
            codingRequiredProgress={codingRequiredProgress}
            showBlueprintBtn={showBlueprintBtn}
            isGeneratingBlueprint={isGeneratingBlueprint}
            isTyping={isTyping}
            onBackHome={() => navigate('/')}
            onGenerateBlueprint={() => void handleGenerateBlueprintClick()}
          />

          <InspirationChatWorkspace
            isElectronRuntime={isElectronRuntime}
            workspacePane={workspacePane}
            onWorkspacePaneChange={setWorkspacePane}
            guidePanel={
              <InspirationChatGuidePanel
                isElectronRuntime={isElectronRuntime}
                isTyping={isTyping}
                mode={mode}
                showBlueprintBtn={showBlueprintBtn}
                progressSummaryLines={progressSummaryLines}
                progressSummaryMaxLines={progressSummaryMaxLines}
                progressSummaryPlaceholder={progressSummaryPlaceholder}
                onFocusConversation={() => {
                  setWorkspacePane('conversation');
                  window.setTimeout(() => inputRef.current?.focus(), 0);
                }}
              />
            }
            conversationPanel={
              <InspirationChatConversationPanel
                isElectronRuntime={isElectronRuntime}
                mode={mode}
                isTyping={isTyping}
                messages={messages}
                options={options}
                inputValue={inputValue}
                messagesEndRef={messagesEndRef}
                inputRef={inputRef}
                onChangeInputValue={setInputValue}
                onSend={handleSend}
                onKeyDown={handleKeyDown}
                onOptionSelect={(label) => void sendText(`选择：${label}`)}
              />
            }
          />
        </div>
      </AppViewportFrame>
    </AppViewportShell>
  );
};
