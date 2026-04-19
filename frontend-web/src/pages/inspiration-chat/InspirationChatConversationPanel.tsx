import React from 'react';
import { Bot, Send, Sparkles, User } from 'lucide-react';
import { BookTextarea } from '../../components/ui/BookInput';
import type { Message } from './shared';

type InspirationChatConversationPanelProps = {
  isElectronRuntime: boolean;
  mode: 'novel' | 'coding';
  isTyping: boolean;
  messages: Message[];
  options: any[];
  inputValue: string;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  onChangeInputValue: (value: string) => void;
  onSend: () => void | Promise<void>;
  onKeyDown: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onOptionSelect: (label: string) => void | Promise<void>;
};

export const InspirationChatConversationPanel: React.FC<InspirationChatConversationPanelProps> = ({
  isElectronRuntime,
  mode,
  isTyping,
  messages,
  options,
  inputValue,
  messagesEndRef,
  inputRef,
  onChangeInputValue,
  onSend,
  onKeyDown,
  onOptionSelect,
}) => {
  return (
    <div
      className={`relative overflow-hidden ${isElectronRuntime ? '' : 'min-h-[30rem]'} h-full min-h-0 rounded-2xl border border-book-border/55 bg-book-bg-paper/95 p-4 shadow-surface-strong sm:p-6`}
    >
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

        <div className={`${isElectronRuntime ? 'mt-4' : 'mt-6'} custom-scrollbar flex-1 min-h-0 overflow-y-auto pr-2 ${isElectronRuntime ? '' : 'scroll-smooth'}`}>
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
                      <span className="mt-2 inline-block h-4 w-1.5 animate-pulse rounded-full bg-current align-middle" />
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
                      onClick={() => onOptionSelect(String(opt?.label || ''))}
                      className="rounded-full border border-book-primary/28 bg-book-bg-paper/82 px-4 py-2 text-sm font-semibold text-book-primary transition-all duration-300 hover:-translate-y-0.5 hover:bg-book-primary hover:text-white"
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          )}
          <div ref={messagesEndRef as React.Ref<HTMLDivElement>} />
        </div>

        <div className={`${isElectronRuntime ? 'mt-4' : 'mt-6'} border-t border-book-border/40 pt-4`}>
          <div
            className={`
              rounded-xl border border-book-border/55 p-3 shadow-surface backdrop-blur-xl
              ${isElectronRuntime ? 'bg-book-bg-paper/92' : 'bg-book-bg-paper/72'}
            `}
          >
            <div className="relative">
              <BookTextarea
                ref={inputRef as React.Ref<HTMLTextAreaElement>}
                className={`${isElectronRuntime ? 'min-h-[104px]' : 'min-h-[132px]'} max-h-56 resize-none border-none bg-transparent px-4 pb-4 pr-20 pt-4 shadow-none focus:ring-0`}
                placeholder="输入你的想法... (Shift + Enter 换行)"
                value={inputValue}
                onChange={(e) => onChangeInputValue(e.target.value)}
                onKeyDown={onKeyDown}
                spellCheck={false}
                disabled={isTyping}
              />
              <button
                type="button"
                onClick={onSend}
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
                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  </div>
                ) : null}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
