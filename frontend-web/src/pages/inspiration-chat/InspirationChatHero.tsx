import React from 'react';
import { ArrowLeft, Wand2 } from 'lucide-react';
import { BookButton } from '../../components/ui/BookButton';

type InspirationChatHeroProps = {
  isElectronRuntime: boolean;
  mode: 'novel' | 'coding';
  stageTitle: string;
  stageDescription: string;
  headerCompactStatus: string;
  headerProgressLabel: string;
  headerProgressValue: string;
  headerCollectedValue: string;
  conversationStatus: string;
  messagesCount: number;
  chapterCount: number | null;
  codingRequiredProgress: { done: number; total: number } | null;
  showBlueprintBtn: boolean;
  isGeneratingBlueprint: boolean;
  isTyping: boolean;
  onBackHome: () => void;
  onGenerateBlueprint: () => void | Promise<void>;
};

export const InspirationChatHero: React.FC<InspirationChatHeroProps> = ({
  isElectronRuntime,
  mode,
  stageTitle,
  stageDescription,
  headerCompactStatus,
  headerProgressLabel,
  headerProgressValue,
  headerCollectedValue,
  conversationStatus,
  messagesCount,
  chapterCount,
  codingRequiredProgress,
  showBlueprintBtn,
  isGeneratingBlueprint,
  isTyping,
  onBackHome,
  onGenerateBlueprint,
}) => {
  return (
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
              onClick={onBackHome}
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
                <span className="story-pill">对话 {messagesCount} 条</span>
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

        <div className={isElectronRuntime ? 'flex flex-col gap-2' : 'flex shrink-0 flex-col items-start gap-2'}>
          <BookButton
            variant={showBlueprintBtn ? 'primary' : 'secondary'}
            size="lg"
            onClick={onGenerateBlueprint}
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
  );
};
