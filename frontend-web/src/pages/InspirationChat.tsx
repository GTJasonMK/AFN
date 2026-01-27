import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Send, ArrowLeft, Bot, User, Sparkles, Wand2 } from 'lucide-react';
import { useSSE } from '../hooks/useSSE';
import { novelsApi } from '../api/novels';
import { codingApi } from '../api/coding';
import { BookButton } from '../components/ui/BookButton';
import { BookTextarea } from '../components/ui/BookInput';
import { Modal } from '../components/ui/Modal';
import { BookCard } from '../components/ui/BookCard';

interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  isStreaming?: boolean;
}

interface InspirationChatProps {
  mode?: 'novel' | 'coding';
}

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
  
  // Load chat history
  useEffect(() => {
    if (id) {
      const loadHistory = async () => {
        const history = mode === 'novel'
          ? await novelsApi.getChatHistory(id)
          : await codingApi.getChatHistory(id);
        setMessages(history.map((msg: any) => ({
          id: msg.id,
          role: msg.role as 'user' | 'assistant',
          content: msg.content,
        })));
        if (history.length > 2) setShowBlueprintBtn(true);
      };
      loadHistory().catch((e) => console.error(e));
    }
  }, [id, mode]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleEvent = (event: string, data: any) => {
    if (event === 'streaming_start') {
      setIsTyping(true);
      setOptions([]);
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'assistant',
        content: '',
        isStreaming: true
      }]);
    } else if (event === 'ai_message_chunk') {
      setMessages(prev => {
        const newMessages = [...prev];
        const lastMsg = newMessages[newMessages.length - 1];
        if (lastMsg && lastMsg.isStreaming) {
          lastMsg.content += data.text;
        }
        return newMessages;
      });
    } else if (event === 'option') {
      setOptions(prev => [...prev, data.option]);
    } else if (event === 'complete') {
      setIsTyping(false);
      if (data?.conversation_state) setConversationState(data.conversation_state);
      if (data?.ready_for_blueprint) setShowBlueprintBtn(true);
      setMessages(prev => {
        const newMessages = [...prev];
        const lastMsg = newMessages[newMessages.length - 1];
        if (lastMsg) {
          lastMsg.isStreaming = false;
        }
        return newMessages;
      });
    } else if (event === 'error') {
      setIsTyping(false);
      console.error("SSE Error:", data);
    }
  };

  const { connect } = useSSE(handleEvent);

  const handleSend = async () => {
    if (!inputValue.trim() || !id) return;

    const userMsg: Message = {
      id: Date.now(),
      role: 'user',
      content: inputValue
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
            const ok = confirm(`${detail || '检测到已有章节大纲/后续数据。重新生成蓝图将清理后续数据。'}\n\n是否强制重新生成？`);
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

  return (
    <div className="flex flex-col h-screen bg-book-bg relative overflow-hidden">
      <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-book-bg-paper/30 to-transparent pointer-events-none" />

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
            <div className="text-sm text-book-text-sub bg-book-bg p-3 rounded-lg border border-book-border/50">
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

      {/* Header */}
      <div className="h-16 border-b border-book-border/40 bg-book-bg-glass backdrop-blur-md flex items-center justify-between px-6 z-20 shrink-0">
        <button 
          onClick={() => navigate('/')}
          className="flex items-center text-book-text-sub hover:text-book-primary transition-colors group"
        >
          <div className="p-1.5 rounded-full bg-book-bg-paper border border-book-border group-hover:border-book-primary/50 mr-3 shadow-sm transition-colors">
            <ArrowLeft size={16} />
          </div>
          <span className="font-serif font-bold text-lg">
            {mode === 'novel' ? '灵感构思' : '需求分析'}
          </span>
        </button>

        {showBlueprintBtn && (
          <BookButton 
            variant="primary" 
            size="md" 
            onClick={generateBlueprint}
            disabled={isGeneratingBlueprint}
            className="shadow-lg shadow-book-primary/20 animate-in fade-in slide-in-from-top-4 duration-500"
          >
            <Wand2 size={16} className="mr-2 fill-current" />
            {isGeneratingBlueprint ? '生成中…' : '生成蓝图'}
          </BookButton>
        )}
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-6 md:p-10 space-y-8 custom-scrollbar z-10 scroll-smooth">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-book-text-muted opacity-60 animate-in zoom-in-95 duration-700">
            <div className="w-24 h-24 bg-book-bg-paper rounded-full flex items-center justify-center mb-6 shadow-inner border border-book-border/50">
              <Sparkles size={48} className="text-book-accent" />
            </div>
            <h2 className="text-2xl font-serif font-bold text-book-text-main mb-2">
                {mode === 'novel' ? '开启你的创作之旅' : '描述你的软件创意'}
            </h2>
            <p className="text-sm">
                {mode === 'novel' ? '告诉我关于你故事的一切想法...' : '你想构建什么样的系统？'}
            </p>
          </div>
        )}
        
        {messages.map((msg) => (
          <div 
            key={msg.id} 
            className={`flex gap-5 max-w-4xl mx-auto ${msg.role === 'user' ? 'flex-row-reverse' : ''} animate-in fade-in slide-in-from-bottom-4 duration-500`}
          >
            <div className={`
              w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-md border border-white/10
              ${msg.role === 'user' 
                ? 'bg-gradient-to-br from-book-primary to-book-primary-light text-white' 
                : 'bg-book-bg-paper text-book-primary border-book-border'}
            `}>
              {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
            </div>
            
            <div className={`
              max-w-[85%] rounded-2xl p-6 leading-relaxed text-base shadow-sm relative
              ${msg.role === 'user' 
                ? 'bg-book-primary text-white rounded-tr-sm shadow-book-primary/20' 
                : 'bg-book-bg-paper border border-book-border/60 rounded-tl-sm text-book-text-main shadow-sm'}
            `}>
              <div className="whitespace-pre-wrap font-sans text-[15px]">{msg.content}</div>
              {msg.isStreaming && (
                <span className="inline-block w-1.5 h-4 ml-1 align-middle bg-current animate-pulse rounded-full"/>
              )}
            </div>
          </div>
        ))}
        
        {/* Options Bubbles */}
        {!isTyping && options.length > 0 && (
            <div className="flex flex-wrap gap-2 max-w-4xl mx-auto pl-14 animate-in fade-in slide-in-from-bottom-2 duration-500">
              {options.map((opt, idx) => (
                <button
                  key={idx}
                  onClick={() => setInputValue(opt.label)}
                  className="px-4 py-2 rounded-full border border-book-primary/30 bg-book-bg-paper text-book-primary text-sm hover:bg-book-primary hover:text-white transition-all duration-300 shadow-sm hover:shadow-md active:scale-95"
                >
                  {opt.label}
                </button>
              ))}
            </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-6 pb-8 border-t border-book-border/40 bg-book-bg-glass backdrop-blur-xl z-20 shrink-0">
        <div className="max-w-4xl mx-auto relative group">
          <BookTextarea 
            className="pr-16 max-h-40 min-h-[72px] py-4 px-6 text-base shadow-inner border-book-border/60 focus:border-book-primary/60 bg-book-bg/50 rounded-2xl resize-none"
            placeholder="输入你的想法... (Shift + Enter 换行)"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isTyping}
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isTyping}
            className={`
              absolute right-3 bottom-3 p-2.5 rounded-xl transition-all duration-300 transform
              ${!inputValue.trim() || isTyping 
                ? 'text-book-text-muted bg-transparent cursor-not-allowed opacity-50' 
                : 'text-white bg-book-primary hover:bg-book-primary-light shadow-md hover:scale-105 hover:-translate-y-0.5 active:scale-95'}
            `}
          >
            <Send size={20} className={isTyping ? "opacity-0" : "opacity-100"} />
            {isTyping && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              </div>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
