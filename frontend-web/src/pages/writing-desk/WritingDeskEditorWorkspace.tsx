import React from 'react';
import type { Chapter } from '../../api/writer';
import { WorkspaceTabs, type WorkspaceHandle } from '../../components/business/WorkspaceTabs';
import { BookButton } from '../../components/ui/BookButton';

type WritingDeskEditorWorkspaceProps = {
  projectId: string;
  currentChapter: Chapter | null;
  chaptersCount: number;
  sidebarVisible: boolean;
  assistantVisible: boolean;
  canGenerateOutlines: boolean;
  outlineDisabledReason: string | null;
  onToggleSidebar: () => void;
  onToggleAssistant: () => void;
  onOpenBatchGenerate: () => void;
  onCreateChapter: () => void;
  editorRef: React.RefObject<WorkspaceHandle | null>;
  workspaceProps: Omit<React.ComponentProps<typeof WorkspaceTabs>, 'projectId' | 'chapter'>;
};

export const WritingDeskEditorWorkspace: React.FC<WritingDeskEditorWorkspaceProps> = ({
  projectId,
  currentChapter,
  chaptersCount,
  sidebarVisible,
  assistantVisible,
  canGenerateOutlines,
  outlineDisabledReason,
  onToggleSidebar,
  onToggleAssistant,
  onOpenBatchGenerate,
  onCreateChapter,
  editorRef,
  workspaceProps,
}) => {
  if (currentChapter) {
    return (
      <WorkspaceTabs
        ref={editorRef as React.Ref<WorkspaceHandle>}
        projectId={projectId}
        chapter={currentChapter}
        {...workspaceProps}
      />
    );
  }

  return (
    <div className="flex h-full w-full items-center justify-center p-6 sm:p-8">
      <div className="w-full max-w-2xl rounded-2xl border border-book-border/55 bg-book-bg-paper/78 p-6 shadow-surface-strong sm:p-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">写作台</div>
            <h2 className="mt-3 font-serif text-[clamp(1.8rem,3vw,2.6rem)] font-bold leading-[1.02] tracking-[-0.04em] text-book-text-main">
              {chaptersCount > 0 ? '选择一个章节，继续推进故事。' : '先创建第一章，让写作台开始运转。'}
            </h2>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-book-text-sub sm:text-base">
              {chaptersCount > 0
                ? '在左侧选择章节后，正文/版本/评审都会出现在主工作区。'
                : '当前项目还没有章节。你可以先新增一章，或批量生成章节大纲后再逐章写作。'}
            </p>
          </div>

          <div className="shrink-0 rounded-[18px] border border-book-border/55 bg-book-bg/72 px-4 py-3 text-sm text-book-text-sub shadow-surface">
            <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
              提示
            </div>
            <div className="mt-2 font-semibold text-book-text-main">
              {chaptersCount > 0 ? `当前共有 ${chaptersCount} 章` : '建议从第一章开始'}
            </div>
            <div className="mt-1 text-book-text-sub">
              章节栏/助手都可以在顶部命令栏一键开关。
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap justify-end gap-2">
          {!sidebarVisible ? (
            <BookButton variant="ghost" onClick={onToggleSidebar}>
              显示章节栏
            </BookButton>
          ) : null}
          {!assistantVisible && chaptersCount > 0 ? (
            <BookButton variant="ghost" onClick={onToggleAssistant}>
              打开助手
            </BookButton>
          ) : null}
          <BookButton
            variant="ghost"
            onClick={onOpenBatchGenerate}
            disabled={!canGenerateOutlines}
            title={canGenerateOutlines ? '批量生成章节大纲' : (outlineDisabledReason || '当前不满足生成章节大纲条件')}
          >
            批量生成大纲
          </BookButton>
          <BookButton
            variant="primary"
            onClick={onCreateChapter}
            disabled={!canGenerateOutlines}
            title={canGenerateOutlines ? '生成下一章的章节大纲' : (outlineDisabledReason || '当前不满足生成章节大纲条件')}
          >
            生成下一章大纲
          </BookButton>
        </div>
      </div>
    </div>
  );
};
