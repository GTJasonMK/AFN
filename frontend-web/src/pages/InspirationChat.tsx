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
  const [showBlueprintBtn, setShowBlueprintBtn] = useState(false);
  const [isGeneratingBlueprint, setIsGeneratingBlueprint] = useState(false);
  const [isBlueprintConfirmOpen, setIsBlueprintConfirmOpen] = useState(false);
  const [blueprintPreview, setBlueprintPreview] = useState<any | null>(null);
  const [blueprintTip, setBlueprintTip] = useState<string | null>(null);
  const [options, setOptions] = useState<any[]>([]);
  const [conversationState, setConversationState] = useState<any>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
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

    node.scrollIntoView({
      behavior: isStreamingRef.current ? "auto" : "smooth",
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
      if (data?.conversation_state) setConversationState(data.conversation_state);

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
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const generateBlueprint = async () => {
    if (!id) return;
    try {
      setIsGeneratingBlueprint(true);
      setBlueprintTip(null);

      if (mode === 'novel') {
        const res = await novelsApi.generateBlueprint(id);
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
  const starterPrompts = mode === 'novel'
    ? [
        '我想写一个“文明崩塌后重建秩序”的长篇故事。',
        '主角是一名曾经的历史学者，现在被迫成为战争谈判者。',
        '希望整体气质是冷峻、克制，但在关键处突然爆发。',
      ]
    : [
        '我要做一个面向小团队的知识库协作系统。',
        '核心需求是任务跟踪、文档沉淀和权限分层。',
        '希望先帮我厘清 MVP 范围，再拆出后续扩展阶段。',
      ];
  const conversationStatus = isTyping
    ? 'AI 正在接续你的上下文'
    : showBlueprintBtn
      ? (mode === 'novel' ? '已具备生成蓝图条件' : '已具备生成架构设计条件')
      : '继续补充信息，让结构更扎实';

  return (
    <div className="page-shell min-h-screen overflow-hidden">
      <div className="ambient-orb -left-16 top-20 h-72 w-72 bg-book-primary/16" />
      <div className="ambient-orb right-[-5rem] top-8 h-64 w-64 bg-book-primary-light/14" />

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
        <div className="space-y-4">
          {blueprintTip ? (
            <div className="rounded-[22px] border border-book-border/50 bg-book-bg/72 p-4 text-sm leading-relaxed text-book-text-sub">
              {blueprintTip}
            </div>
          ) : null}

          <BookCard className="p-4">
            <div className="font-bold text-book-text-main mb-2">摘要</div>
            {mode === 'novel' ? (
              <div className="space-y-2 text-sm text-book-text-main">
                <div className="font-serif text-lg font-bold">
                  {String(blueprintPreview?.title || '（未命名）')}
                </div>
                <div className="text-book-text-sub italic">
                  {String(blueprintPreview?.one_sentence_summary || '（暂无一句话概要）')}
                </div>
              </div>
            ) : (
              <div className="space-y-2 text-sm text-book-text-main">
                <div className="font-serif text-lg font-bold">
                  {String(blueprintPreview?.project_type_desc || '（未设置项目类型）')}
                </div>
                <div className="text-book-text-sub italic">
                  {String(blueprintPreview?.one_sentence_summary || blueprintPreview?.summary || '（暂无一句话概要）')}
                </div>
              </div>
            )}
          </BookCard>

          <details className="rounded-lg border border-book-border/40 bg-book-bg-paper">
            <summary className="cursor-pointer select-none px-4 py-3 font-bold text-book-text-main">
              查看完整蓝图（JSON）
            </summary>
            <pre className="px-4 pb-4 text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed">
              {(() => {
                try {
                  return JSON.stringify(blueprintPreview || {}, null, 2);
                } catch {
                  return String(blueprintPreview ?? '');
                }
              })()}
            </pre>
          </details>
        </div>
      </Modal>

      <div className="relative mx-auto flex min-h-screen w-full max-w-[1600px] flex-col gap-4 px-3 py-3 sm:px-5 sm:py-5">
        <section className="dramatic-surface rounded-[32px] px-5 py-5 sm:px-7 sm:py-6">
          <div className="relative z-[1] flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={() => navigate('/')}
                  className="inline-flex h-11 items-center gap-2 rounded-full border border-book-border/55 bg-book-bg-paper/78 px-4 text-sm font-semibold text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/30 hover:text-book-primary"
                >
                  <ArrowLeft size={16} />
                  返回首页
                </button>
                <div className="eyebrow">{mode === 'novel' ? 'Story Forge' : 'System Forge'}</div>
              </div>

              <div>
                <h1 className="font-serif text-[clamp(2.4rem,6vw,4.8rem)] font-bold leading-[0.95] tracking-[-0.04em] text-book-text-main">
                  {stageTitle}
                </h1>
                <p className="mt-3 max-w-3xl text-sm leading-relaxed text-book-text-sub sm:text-base">
                  {stageDescription}
                </p>
              </div>
            </div>

            {showBlueprintBtn ? (
              <BookButton
                variant="primary"
                size="lg"
                onClick={generateBlueprint}
                disabled={isGeneratingBlueprint}
                className="self-start"
              >
                <Wand2 size={16} />
                {isGeneratingBlueprint ? '生成中…' : (mode === 'coding' ? '生成架构设计' : '生成蓝图')}
              </BookButton>
            ) : (
              <div className="rounded-full border border-book-border/55 bg-book-bg-paper/78 px-4 py-3 text-sm font-semibold text-book-text-sub">
                继续补全上下文，按钮会在结构足够清晰后解锁
              </div>
            )}
          </div>
        </section>

        <section className="grid min-h-0 flex-1 gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="space-y-4">
            <BookCard className="p-6">
              <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                当前状态
              </div>
              <div className="mt-4 font-serif text-3xl font-bold text-book-text-main">
                {conversationStatus}
              </div>
              <div className="mt-3 text-sm leading-relaxed text-book-text-sub">
                已收集 {messages.length} 条对话。{showBlueprintBtn ? '现在可以进入下一阶段。' : '先把背景、目标、冲突与约束说清楚。'}
              </div>
            </BookCard>

            <BookCard className="p-6" variant="flat">
              <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                起手建议
              </div>
              <div className="mt-4 space-y-3">
                {starterPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => void sendText(prompt)}
                    className="w-full rounded-[22px] border border-book-border/50 bg-book-bg/72 px-4 py-3 text-left text-sm leading-relaxed text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/28 hover:text-book-primary"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </BookCard>
          </aside>

          <div className="dramatic-surface min-h-[30rem] rounded-[32px] p-4 sm:p-6">
            <div className="relative z-[1] flex h-full min-h-0 flex-col">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-book-border/40 pb-4">
                <div>
                  <div className="eyebrow">Conversation Stage</div>
                  <h2 className="mt-3 font-serif text-3xl font-bold text-book-text-main">
                    {mode === 'novel' ? '把故事说到足够具体' : '把系统边界说到足够清晰'}
                  </h2>
                </div>
                <div className="rounded-full border border-book-border/55 bg-book-bg/78 px-4 py-2 text-sm font-semibold text-book-text-main">
                  {isTyping ? '生成中' : '等待输入'}
                </div>
              </div>

              <div className="mt-6 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar scroll-smooth">
                {messages.length === 0 ? (
                  <div className="flex h-full min-h-[20rem] flex-col items-center justify-center rounded-[30px] border border-dashed border-book-border/55 bg-book-bg-paper/60 px-6 text-center">
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
                            max-w-[88%] rounded-[28px] px-5 py-4 shadow-[0_24px_56px_-42px_rgba(36,18,6,0.96)]
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

              <div className="mt-6 border-t border-book-border/40 pt-4">
                <div className="rounded-[28px] border border-book-border/55 bg-book-bg-paper/72 p-3 shadow-[0_20px_44px_-34px_rgba(36,18,6,0.96)]">
                  <div className="relative">
                    <BookTextarea
                      className="min-h-[132px] max-h-56 resize-none border-none bg-transparent px-4 pb-4 pr-20 pt-4 shadow-none focus:ring-0"
                      placeholder="输入你的想法... (Shift + Enter 换行)"
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyDown={handleKeyDown}
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
                          : 'border border-book-primary bg-book-primary text-white shadow-[0_22px_44px_-28px_rgba(87,44,17,0.96)] hover:-translate-y-0.5 hover:bg-book-primary-light'}
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
        </section>
      </div>
    </div>
  );
};
