import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Send, ArrowLeft, Bot, User, Sparkles, Wand2 } from 'lucide-react';
import { useSSE } from '../hooks/useSSE';
import { novelsApi } from '../api/novels';
import { codingApi } from '../api/coding';
import { BookButton } from '../components/ui/BookButton';
import { BookTextarea } from '../components/ui/BookInput';
import { Modal } from '../components/ui/Modal';
import { BookCard } from '../components/ui/BookCard';
import { confirmDialog } from '../components/feedback/ConfirmDialog';
import { readBootstrapCache, writeBootstrapCache } from '../utils/bootstrapCache';
import {
  NovelDialogIntro,
  NovelDialogMetric,
  NovelDialogMetricGrid,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from '../components/business/novel/NovelDialogPrimitives';
import { AppViewportFrame, AppViewportShell, SegmentPager } from '../components/layout/AppViewport';

interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  isStreaming?: boolean;
}

interface InspirationChatProps {
  mode?: 'novel' | 'coding';
}

type InspirationChatBootstrapSnapshot = {
  messages: Array<Pick<Message, 'id' | 'role' | 'content'>>;
  showBlueprintBtn: boolean;
  conversationState: any;
};

const INSPIRATION_CHAT_BOOTSTRAP_TTL_MS = 10 * 60 * 1000;
const getInspirationChatBootstrapKey = (mode: 'novel' | 'coding', projectId: string) =>
  `afn:web:inspiration-chat:${mode}:${projectId}:bootstrap:v1`;

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
  const [workspacePane, setWorkspacePane] = useState<'conversation' | 'guide'>('conversation');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const completionHintShownRef = useRef(false);
  const pendingChunkRef = useRef('');
  const chunkFlushTimerRef = useRef<number | null>(null);
  const isStreamingRef = useRef(false);
  const messageIdSeqRef = useRef(0);

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

    const cached = readBootstrapCache<InspirationChatBootstrapSnapshot>(
      getInspirationChatBootstrapKey(mode, id),
      INSPIRATION_CHAT_BOOTSTRAP_TTL_MS,
    );

    if (!cached) {
      setMessages([]);
      setShowBlueprintBtn(false);
      setConversationState({});
      return;
    }

    const safeMessages = Array.isArray(cached.messages)
      ? cached.messages
          .filter((item) => item && (item.role === 'user' || item.role === 'assistant' || item.role === 'system'))
          .map((item, idx) => ({
            id: Number(item.id) || (Date.now() + idx),
            role: item.role,
            content: String(item.content || ''),
          }))
      : [];

    setMessages(safeMessages);
    setShowBlueprintBtn(Boolean(cached.showBlueprintBtn));
    setConversationState(cached.conversationState && typeof cached.conversationState === 'object' ? cached.conversationState : {});
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
    });
  }, [conversationState, id, isTyping, messages, mode, showBlueprintBtn]);
  
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
          content: msg.content,
        }));

        // 对齐桌面端：首次进入时也显示一条欢迎语（作为对话气泡，而不是空态占位）
        if (mapped.length === 0) {
          const welcome =
            mode === 'novel'
              ? "你好！我是AFN AI助手。\n\n请告诉我你的创意想法，我会帮你创建一个完整的小说蓝图。"
              : "你好！我是AFN需求分析助手。\n\n请告诉我你想要构建什么样的系统，我会帮你分析需求并设计项目架构。";
          setMessages([
            {
              id: nextMessageId(),
              role: 'assistant',
              content: welcome,
            },
          ]);
        } else {
          setMessages(mapped);
        }

        // 避免路由切换后遗留旧状态
        setShowBlueprintBtn(history.length > 2);
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
      setOptions((prev) => [...prev, data.option]);
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
          next = [...prev];
          next[lastIdx] = { ...prev[lastIdx], isStreaming: false };
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

      setIsBlueprintConfirmOpen(true);
    } catch (e: any) {
      console.error(e);
      setBlueprintTip(String(e?.response?.data?.detail || '生成蓝图失败'));
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
    setIsBlueprintConfirmOpen(false);
    setBlueprintPreview(null);
    setBlueprintTip(null);
    if (mode === 'novel') navigate(`/novel/${id}`);
    else navigate(`/coding/detail/${id}`);
  };

  const regenerateBlueprint = async () => {
    if (!id) return;
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
	            if (!ok) return;
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
    } catch (e: any) {
      console.error(e);
      setBlueprintTip(String(e?.response?.data?.detail || '重新生成失败'));
    } finally {
      setIsGeneratingBlueprint(false);
    }
  };

  const stageTitle = mode === 'novel' ? '灵感构思' : '需求分析';
  const stageDescription = mode === 'novel'
    ? '把碎片化念头压成故事方向、人物动机与蓝图结构。'
    : '把模糊需求整理为可执行的系统边界、角色职责与架构方案。';
  const safeConversationState = conversationState && typeof conversationState === 'object' ? conversationState : {};

  const extractNextQuestion = (state: any) => {
    if (!state || typeof state !== 'object') return null;
    const raw =
      state.next_question ??
      state.nextQuestion ??
      state.next_prompt ??
      state.nextPrompt ??
      state.next_step_question ??
      state.nextStepQuestion;
    if (raw === null || raw === undefined) return null;
    const text = String(raw).trim();
    return text ? text : null;
  };

  const extractProgressSummary = (state: any) => {
    if (!state || typeof state !== 'object') return null;
    const raw = state.progress_summary ?? state.progressSummary ?? state.collected_summary ?? state.collectedSummary;
    if (raw === null || raw === undefined) return null;
    const text = String(raw).trim();
    return text ? text : null;
  };

  const nextQuestion = isTyping ? null : extractNextQuestion(safeConversationState);
  const progressSummary = isTyping ? null : extractProgressSummary(safeConversationState);
  const progressSummaryLines = progressSummary
    ? progressSummary
        .replace(/\r\n/g, '\n')
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => line.replace(/^[-•]\s*/, ''))
    : [];
  const nextQuestionPlaceholder = mode === 'novel'
    ? '模型会在每轮回答结束后给你一个「下一个问题」，用来继续收敛世界观、人物与冲突。'
    : '模型会在每轮回答结束后给你一个「下一个问题」，用来继续补齐边界、角色与核心流程。';
  const progressSummaryPlaceholder = mode === 'novel'
    ? '每轮回答后，这里会自动总结已确认的世界观、人物与冲突信息，便于你判断何时生成蓝图。'
    : '每轮回答后，这里会自动总结已确认的目标、功能与约束信息，便于你判断何时生成架构设计。';
  const progressSummaryMaxLines = isElectronRuntime ? 10 : 10;

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
  const workspacePaneItems = [
    {
      id: 'conversation',
      label: '对话区',
      hint: '继续推进灵感对话，保持上下文连续。',
    },
	    {
	      id: 'guide',
	      label: '引导区',
	      hint: '查看进度、下一个问题和已收集信息，不把它们堆到主对话下面。',
	    },
	  ] as const;

  return (
    <AppViewportShell>

      <Modal
        isOpen={isBlueprintConfirmOpen}
        onClose={() => setIsBlueprintConfirmOpen(false)}
        title="蓝图预览与确认"
        maxWidthClassName="max-w-3xl"
        footer={
          <>
            <BookButton variant="ghost" onClick={() => setIsBlueprintConfirmOpen(false)} disabled={isGeneratingBlueprint}>
              返回对话
            </BookButton>
            <BookButton variant="secondary" onClick={regenerateBlueprint} disabled={isGeneratingBlueprint}>
              {isGeneratingBlueprint ? '重新生成中…' : '重新生成'}
            </BookButton>
            <BookButton variant="primary" onClick={confirmBlueprintAndContinue}>
              确认并继续
            </BookButton>
          </>
        }
      >
        <NovelDialogStack>
          <NovelDialogIntro
            eyebrow={mode === 'novel' ? 'Story Blueprint' : 'System Blueprint'}
            title={mode === 'novel' ? '确认故事蓝图' : '确认架构蓝图'}
            description={
              mode === 'novel'
                ? '先快速判断作品名和一句话摘要是否对得上你的设想，再决定是否回到对话继续压实。'
                : '先确认系统类型和一句话摘要是否准确，再决定是否回到对话继续澄清。'
            }
          >
            <div className="flex flex-wrap gap-2">
              <span className="story-pill">{mode === 'novel' ? '对话已压缩成故事蓝图' : '对话已压缩成系统方案'}</span>
              {showBlueprintBtn ? <span className="story-pill">可继续下一阶段</span> : null}
            </div>
          </NovelDialogIntro>

          {blueprintTip ? (
            <NovelDialogSurface className="text-sm leading-relaxed text-book-text-sub">
              {blueprintTip}
            </NovelDialogSurface>
          ) : null}

          <NovelDialogMetricGrid>
            <NovelDialogMetric
              label={mode === 'novel' ? '标题 / 类型' : '系统类型'}
              value={
                mode === 'novel'
                  ? String(blueprintPreview?.title || '（未命名）')
                  : String(blueprintPreview?.project_type_desc || '（未设置项目类型）')
              }
              note={mode === 'novel' ? '先确认作品名是否贴合这轮灵感收敛结果。' : '先确认系统定位是否准确。'}
            />
            <NovelDialogMetric
              label="一句话摘要"
              value={String(
                blueprintPreview?.one_sentence_summary || blueprintPreview?.summary || '（暂无一句话概要）'
              )}
              note="这是判断是否进入下一阶段的最快速参考。"
            />
          </NovelDialogMetricGrid>

          <NovelDialogSection
            eyebrow="Summary"
            title="蓝图摘要"
            description="这里展示当前蓝图的压缩摘要，适合快速决定是确认还是重生。"
          >
            <NovelDialogSurface>
              {mode === 'novel' ? (
                <div className="space-y-2 text-sm text-book-text-main">
                  <div className="font-serif text-lg font-bold">
                    {String(blueprintPreview?.title || '（未命名）')}
                  </div>
                  <div className="italic text-book-text-sub">
                    {String(blueprintPreview?.one_sentence_summary || '（暂无一句话概要）')}
                  </div>
                </div>
              ) : (
                <div className="space-y-2 text-sm text-book-text-main">
                  <div className="font-serif text-lg font-bold">
                    {String(blueprintPreview?.project_type_desc || '（未设置项目类型）')}
                  </div>
                  <div className="italic text-book-text-sub">
                    {String(blueprintPreview?.one_sentence_summary || blueprintPreview?.summary || '（暂无一句话概要）')}
                  </div>
                </div>
              )}
            </NovelDialogSurface>
          </NovelDialogSection>

          <details className="rounded-xl border border-book-border/45 bg-book-bg-paper/80">
            <summary className="cursor-pointer select-none px-5 py-4 text-sm font-semibold text-book-text-main">
              查看完整蓝图（JSON）
            </summary>
            <div className="px-5 pb-5">
              <NovelDialogSurface className="max-h-[22rem] overflow-auto custom-scrollbar">
                <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-book-text-main">
                  {(() => {
                    try {
                      return JSON.stringify(blueprintPreview || {}, null, 2);
                    } catch {
                      return String(blueprintPreview ?? '');
                    }
                  })()}
                </pre>
              </NovelDialogSurface>
            </div>
          </details>
        </NovelDialogStack>
      </Modal>

      <AppViewportFrame size={isElectronRuntime ? 'wide' : 'default'}>
        <div
          className={
            isElectronRuntime
              ? 'min-h-0 flex-1 grid grid-cols-[minmax(320px,420px)_minmax(0,1fr)] grid-rows-[auto_minmax(0,1fr)] gap-4'
              : 'min-h-0 flex-1 flex flex-col gap-4'
          }
        >
	          <section
	            className={`relative overflow-hidden rounded-2xl border border-book-border/55 bg-book-bg-paper/95 shadow-surface-strong ${
	              isElectronRuntime ? 'px-5 py-4' : 'px-5 py-5 sm:px-7 sm:py-6'
	            }`}
	          >
	            <div
	              className={
	                isElectronRuntime
	                  ? 'relative z-[1] flex flex-col gap-3'
	                  : 'relative z-[1] flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between'
	              }
	            >
	              <div className={`${isElectronRuntime ? 'min-w-0 space-y-2' : 'space-y-4'}`}>
	                <div className="flex flex-wrap items-center justify-between gap-3">
	                  <button
	                    type="button"
	                    onClick={() => navigate('/')}
	                    className={`inline-flex ${isElectronRuntime ? 'h-10' : 'h-11'} items-center gap-2 rounded-full border border-book-border/55 bg-book-bg-paper/78 px-4 text-sm font-semibold text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/30 hover:text-book-primary`}
	                  >
	                    <ArrowLeft size={16} />
	                    返回首页
	                  </button>
	                  {isElectronRuntime ? (
	                    <div className="rounded-full border border-book-border/55 bg-book-bg/78 px-3 py-1.5 text-xs font-semibold text-book-text-main">
	                      状态：{headerCompactStatus}
	                    </div>
	                  ) : (
	                    <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-primary">
	                      {mode === 'novel' ? '灵感对话' : '需求分析'}
	                    </div>
	                  )}
	                </div>

	                <div>
	                  <h1
	                    className={
	                      isElectronRuntime
	                        ? 'font-serif text-3xl font-bold leading-[1.08] tracking-[-0.02em] text-book-text-main'
	                        : 'font-serif text-[clamp(2.4rem,6vw,4.8rem)] font-bold leading-[0.95] tracking-[-0.04em] text-book-text-main'
	                    }
	                  >
	                    {stageTitle}
	                  </h1>
		                  <p
		                    className={
		                      isElectronRuntime
		                        ? 'mt-2 text-sm leading-relaxed text-book-text-sub'
		                        : 'mt-3 max-w-3xl text-sm leading-relaxed text-book-text-sub sm:text-base'
		                    }
		                  >
		                    {stageDescription}
		                  </p>
		                  {isElectronRuntime ? (
		                    <div className="mt-2 flex flex-wrap items-center gap-2">
		                      <div className="rounded-full border border-book-border/55 bg-book-bg/78 px-3 py-1.5 text-xs font-semibold text-book-text-main">
		                        {headerProgressLabel}：{headerProgressValue}
		                      </div>
		                      <div className="rounded-full border border-book-border/55 bg-book-bg/78 px-3 py-1.5 text-xs font-semibold text-book-text-main">
		                        沉淀：{headerCollectedValue}
		                      </div>
		                    </div>
		                  ) : null}
		                  {!isElectronRuntime ? (
		                    <div className="mt-4 flex flex-wrap gap-2">
		                      <span className="story-pill">{conversationStatus}</span>
		                      <span className="story-pill">对话 {messages.length} 条</span>
	                      {mode === 'coding' && codingRequiredProgress ? (
	                        <span className="story-pill">
	                          必需信息 {codingRequiredProgress.done}/{codingRequiredProgress.total}
	                        </span>
	                      ) : null}
	                      {mode === 'novel' ? (
	                        <span className="story-pill">{chapterCount ? `篇幅：${chapterCount} 章` : '待确认篇幅'}</span>
	                      ) : null}
	                    </div>
		                  ) : null}
		                </div>
		              </div>

		              <div className={isElectronRuntime ? 'flex flex-col gap-2' : 'flex shrink-0 flex-col gap-2 items-start'}>
		                <BookButton
		                  variant={showBlueprintBtn ? 'primary' : 'secondary'}
		                  size="lg"
		                  onClick={() => void handleGenerateBlueprintClick()}
		                  disabled={isGeneratingBlueprint || isTyping}
		                  className={isElectronRuntime ? 'w-full justify-center' : 'self-start'}
		                >
		                  <Wand2 size={16} />
		                  {isGeneratingBlueprint ? '生成中…' : mode === 'coding' ? '生成架构设计' : '生成蓝图'}
		                </BookButton>
		                {!isElectronRuntime ? (
		                  <div className="text-xs leading-relaxed text-book-text-sub">
		                    {showBlueprintBtn
		                      ? '信息已足够清晰：生成后会弹出预览与确认。'
		                      : '信息可能未完整：也可以先试生成草稿，后面再补充并重生。'}
		                  </div>
		                ) : null}
		              </div>
		            </div>
		          </section>
	
	        <div className={isElectronRuntime ? 'hidden' : 'xl:hidden'}>
	          <div className="relative overflow-hidden rounded-xl border border-book-border/55 bg-book-bg-paper/95 shadow-surface px-4 py-4">
	            <div className="relative z-[1]">
	              <SegmentPager
                items={[...workspacePaneItems]}
                value={workspacePane}
                onChange={(next) => setWorkspacePane(next as 'conversation' | 'guide')}
              />
            </div>
          </div>
	        </div>
	
	        <section
	          className={`grid min-h-0 flex-1 gap-4 ${
	            isElectronRuntime ? 'contents' : 'xl:grid-cols-[320px_minmax(0,1fr)]'
	          }`}
	        >
		          <div
		            className={
		                isElectronRuntime
		                  ? 'col-start-1 row-start-2 min-h-0 h-full flex flex-col'
		                  : `${workspacePane === 'guide' ? 'min-h-0' : 'hidden'} xl:block`
		              }
		          >
		            <div className={isElectronRuntime ? 'min-h-0 h-full flex flex-col pr-2' : ''}>
			              <aside className="space-y-4 h-full">
			                <BookCard
                      className="p-6 h-full min-h-0 flex flex-col"
                      variant={isElectronRuntime ? 'default' : 'flat'}
                    >
		                  <div className="flex items-center justify-between gap-3">
		                    <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
		                      引导区
		                    </div>
	                    {!isTyping ? (
	                      <button
	                        type="button"
	                        onClick={() => {
	                          setWorkspacePane('conversation');
	                          window.setTimeout(() => inputRef.current?.focus(), 0);
	                        }}
	                        className="rounded-full border border-book-border/55 bg-book-bg-paper/78 px-3 py-1.5 text-xs font-semibold text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/35 hover:text-book-primary"
	                      >
	                        去回答
	                      </button>
	                    ) : null}
	                  </div>

	                  <div className="mt-4 rounded-xl border border-book-border/50 bg-book-bg/72 px-4 py-3">
	                    <div className="text-xs font-semibold text-book-text-muted">
	                      下一个问题
	                    </div>
	                    {nextQuestion && !isTyping ? (
	                      <div
	                        className={`mt-2 text-sm leading-relaxed text-book-text-main ${
	                          isElectronRuntime ? 'line-clamp-4' : ''
	                        }`}
	                      >
	                        {nextQuestion}
	                      </div>
	                    ) : (
	                      <div className="mt-2 text-xs leading-relaxed text-book-text-sub">
	                        {isTyping ? 'AI 正在生成下一步问题…' : nextQuestionPlaceholder}
	                      </div>
	                    )}
	                  </div>

                      <div className="mt-5 text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                        当前进度
                      </div>
                      <div className="mt-3 flex-1 min-h-0 flex flex-col">
                        {progressSummaryLines.length > 0 ? (
                          isElectronRuntime ? (
                            <>
                              <ul className="space-y-2">
                                {progressSummaryLines.slice(0, progressSummaryMaxLines).map((line, idx) => (
                                  <li key={`${idx}-${line}`} className="flex gap-2 text-sm text-book-text-main">
                                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-book-primary/70" />
                                    <span className="flex-1 leading-relaxed line-clamp-2">{line}</span>
                                  </li>
                                ))}
                              </ul>
                              <div className="mt-auto pt-4 text-xs leading-relaxed text-book-text-sub">
                                {showBlueprintBtn
                                  ? (mode === 'coding' ? '信息已足够清晰，可以开始生成架构设计。' : '信息已足够清晰，可以开始生成蓝图。')
                                  : '继续回答上面的「下一个问题」，这里会自动汇总你已经确认的信息。'}
                              </div>
                            </>
                          ) : (
                            <ul className="space-y-2">
                              {progressSummaryLines.slice(0, progressSummaryMaxLines).map((line, idx) => (
                                <li
                                  key={`${idx}-${line}`}
                                  className="flex gap-3 rounded-xl border border-book-border/45 bg-book-bg-paper/70 px-4 py-3 text-sm text-book-text-main"
                                >
                                  <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-book-primary/70" />
                                  <span className="flex-1 leading-relaxed">
                                    {line}
                                  </span>
                                </li>
                              ))}
                            </ul>
                          )
                        ) : (
                          <div className="flex-1 rounded-xl border border-dashed border-book-border/50 bg-book-bg-paper/60 px-4 py-4 text-sm leading-relaxed text-book-text-sub flex items-center">
                            <div className="w-full">
                              <div className="text-sm text-book-text-main font-semibold">
                                {isTyping ? 'AI 正在整理当前进度…' : '进度会在每轮对话后自动生成'}
                              </div>
                              <div className="mt-2 text-sm leading-relaxed text-book-text-sub">
                                {isTyping ? '请稍等片刻。' : progressSummaryPlaceholder}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>

		                  {collectedInfoItems.length > 0 ? (
                        <details className="mt-5 rounded-xl border border-book-border/45 bg-book-bg-paper/80">
                          <summary className="cursor-pointer select-none px-4 py-3 text-sm font-semibold text-book-text-main">
                            已收集信息（{collectedInfoItems.length}）
                          </summary>
                          <div className="px-4 pb-4">
                            <div className="space-y-3">
                              {collectedInfoItems.map((item) => (
                                <div
                                  key={item.label}
                                  className="rounded-xl border border-book-border/50 bg-book-bg/72 px-4 py-3"
                                >
                                  <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                                    {item.label}
                                  </div>
                                  <div className="mt-2 text-sm leading-relaxed text-book-text-main">
                                    {item.value}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        </details>
                      ) : null}
		                </BookCard>
		              </aside>
	            </div>
	          </div>

          <div
            className={
              isElectronRuntime
                ? 'col-start-2 row-start-1 row-span-2 min-h-0'
                : `${workspacePane === 'conversation' ? 'min-h-0' : 'hidden'} xl:block`
            }
          >
              <div className={`relative overflow-hidden ${isElectronRuntime ? '' : 'min-h-[30rem]'} h-full min-h-0 rounded-2xl border border-book-border/55 bg-book-bg-paper/95 shadow-surface-strong p-4 sm:p-6`}>
                <div className="relative z-[1] flex h-full min-h-0 flex-col">
                {isElectronRuntime ? (
                  <div className="flex items-center justify-between gap-3 border-b border-book-border/40 pb-3">
                    <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                      对话区
                    </div>
                    <div className="rounded-full border border-book-border/55 bg-book-bg/78 px-3 py-1.5 text-xs font-semibold text-book-text-main">
                      {isTyping ? '生成中…' : '等待输入'}
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-book-border/40 pb-4">
                    <div>
                      <h2 className="font-serif text-3xl font-bold text-book-text-main">
                        {mode === 'novel' ? '把故事说到足够具体' : '把系统边界说到足够清晰'}
                      </h2>
                    </div>
                    <div className="rounded-full border border-book-border/55 bg-book-bg/78 px-4 py-2 text-sm font-semibold text-book-text-main">
                      {isTyping ? '生成中' : '等待输入'}
                    </div>
                  </div>
                )}

                <div className={`${isElectronRuntime ? 'mt-4' : 'mt-6'} flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar ${isElectronRuntime ? '' : 'scroll-smooth'}`}>
                  {messages.length === 0 ? (
                    <div className="flex h-full min-h-[20rem] flex-col items-center justify-center rounded-2xl border border-dashed border-book-border/55 bg-book-bg-paper/60 px-6 text-center">
                      <div className="flex h-20 w-20 items-center justify-center rounded-full border border-book-border/50 bg-book-bg/75 text-book-primary">
                        <Sparkles size={36} />
                      </div>
                      <div className="mt-5 font-serif text-3xl font-bold text-book-text-main">
                        {mode === 'novel' ? '先把故事火种抛进来' : '先把系统目标抛进来'}
                      </div>
                      <p className="mt-3 max-w-xl text-sm leading-relaxed text-book-text-sub">
                        {mode === 'novel'
                          ? '说世界观、人物、冲突、情绪或任何零散念头都可以。系统会帮你压出一个可展开的长篇骨架。'
                          : '说业务目标、用户角色、核心流程或技术约束都可以。系统会帮你收束为可交付的架构起点。'}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-5">
                      {messages.map((msg) => (
                        <div
                          key={msg.id}
                          className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                          {msg.role !== 'user' ? (
                            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-book-border/50 bg-book-bg/78 text-book-primary">
                              <Bot size={18} />
                            </div>
                          ) : null}

                          <div
                            className={`
                              max-w-[88%] rounded-xl px-5 py-4 shadow-surface
                              ${msg.role === 'user'
                                ? 'bg-book-primary text-white'
                                : 'border border-book-border/55 bg-book-bg-paper/82 text-book-text-main'}
                            `}
                          >
                            <div className="mb-2 text-[0.68rem] font-bold uppercase tracking-[0.18em] opacity-80">
                              {msg.role === 'user' ? 'You' : 'AFN'}
                            </div>
                            <div className="whitespace-pre-wrap text-[15px] leading-relaxed">
                              {msg.content}
                            </div>
                            {msg.isStreaming ? (
                              <span className="mt-2 inline-block h-4 w-1.5 rounded-full bg-current align-middle animate-pulse" />
                            ) : null}
                          </div>

                          {msg.role === 'user' ? (
                            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-book-primary/30 bg-book-primary text-white">
                              <User size={18} />
                            </div>
                          ) : null}
                        </div>
                      ))}

                      {!isTyping && options.length > 0 ? (
                        <div className="flex flex-wrap gap-3 pl-0 sm:pl-16">
                          {options.map((opt, idx) => (
                            <button
                              key={idx}
                              type="button"
                              onClick={() => void sendText(`选择：${String(opt?.label || '')}`)}
                              className="rounded-full border border-book-primary/28 bg-book-bg-paper/82 px-4 py-2 text-sm font-semibold text-book-primary transition-all duration-300 hover:-translate-y-0.5 hover:bg-book-primary hover:text-white"
                            >
                              {opt.label}
                            </button>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>

                <div className={`${isElectronRuntime ? 'mt-4' : 'mt-6'} border-t border-book-border/40 pt-4`}>
                  <div
                    className={`
                      rounded-xl border border-book-border/55 backdrop-blur-xl p-3 shadow-surface
                      ${isElectronRuntime ? 'bg-book-bg-paper/92' : 'bg-book-bg-paper/72'}
                    `}
                  >
                    <div className="relative">
	                      <BookTextarea
	                        ref={inputRef}
	                        className={`${isElectronRuntime ? 'min-h-[104px]' : 'min-h-[132px]'} max-h-56 resize-none border-none bg-transparent px-4 pb-4 pr-20 pt-4 shadow-none focus:ring-0`}
	                        placeholder="输入你的想法... (Shift + Enter 换行)"
	                        value={inputValue}
	                        onChange={(e) => setInputValue(e.target.value)}
	                        onKeyDown={handleKeyDown}
                        spellCheck={false}
                        disabled={isTyping}
                      />
                      <button
                        type="button"
                        onClick={handleSend}
                        disabled={!inputValue.trim() || isTyping}
                        className={`
                          absolute bottom-4 right-4 inline-flex h-12 w-12 items-center justify-center rounded-full transition-all duration-300
                          ${!inputValue.trim() || isTyping
                            ? 'cursor-not-allowed border border-book-border/50 bg-book-bg text-book-text-muted opacity-60'
                            : 'border border-book-primary bg-book-primary text-white shadow-surface-strong hover:-translate-y-0.5 hover:bg-book-primary-light'}
                        `}
                      >
                        <Send size={18} className={isTyping ? 'opacity-0' : 'opacity-100'} />
                        {isTyping ? (
                          <div className="absolute inset-0 flex items-center justify-center">
                            <div className="h-5 w-5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                          </div>
                        ) : null}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
        </div>
      </AppViewportFrame>
    </AppViewportShell>
  );
};
