import React from 'react';
import { Camera, Download, Orbit, PenSquare, Sparkles, Trash2, Wand2 } from 'lucide-react';
import { BookButton } from '../../components/ui/BookButton';
import { Dropdown } from '../../components/ui/Dropdown';

type NovelDetailHeaderProps = {
  project: any;
  projectId: string;
  blueprintData: any;
  avatarLoading: boolean;
  handleAvatarClick: () => void | Promise<void>;
  handleDeleteAvatar: () => void | Promise<void>;
  openEditTitleModal: () => void | Promise<void>;
  isBlueprintDirty: boolean;
  dirtySummary: string;
  saving: boolean;
  worldSettingError: string;
  handleSave: () => void | Promise<void>;
  safeNavigate: (to: string) => void | Promise<void>;
  handleExport: () => void | Promise<void>;
  ragSyncing: boolean;
  handleRagSync: () => void | Promise<void>;
  openRefineModal: () => void | Promise<void>;
};

export const NovelDetailHeader: React.FC<NovelDetailHeaderProps> = ({
  project,
  projectId,
  blueprintData,
  avatarLoading,
  handleAvatarClick,
  handleDeleteAvatar,
  openEditTitleModal,
  isBlueprintDirty,
  dirtySummary,
  saving,
  worldSettingError,
  handleSave,
  safeNavigate,
  handleExport,
  ragSyncing,
  handleRagSync,
  openRefineModal,
}) => {
  const projectTitle = String(project?.title || '未命名项目').trim() || '未命名项目';
  const oneSentenceSummary = String(
    blueprintData?.one_sentence_summary || project?.description || '继续补全一句话简介，让页面先有清晰的故事锚点。',
  ).trim();
  const genre = String(blueprintData?.genre || '未分类').trim() || '未分类';
  const projectStatus = String(project?.status || 'draft').trim() || 'draft';
  const chapterOutlineCount = Array.isArray(blueprintData?.chapter_outline)
    ? blueprintData.chapter_outline.length
    : 0;
  const characterCount = Array.isArray(blueprintData?.characters)
    ? blueprintData.characters.length
    : 0;
  const relationshipCount = Array.isArray(blueprintData?.character_relationships)
    ? blueprintData.character_relationships.length
    : 0;
  const storyStageLabel = isBlueprintDirty ? '待保存草稿' : '蓝图已同步';

  return (
    <section className="dramatic-surface rounded-[32px] px-5 py-6 sm:px-7 sm:py-7">
      <div className="relative z-[1] space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="eyebrow">Story Control</div>
              <span className="story-pill">{storyStageLabel}</span>
              <span className="story-pill">{genre}</span>
              <span className="story-pill">{projectStatus}</span>
            </div>

            <div className="flex items-start gap-4 sm:gap-5">
              <button
                type="button"
                onClick={handleAvatarClick}
                disabled={avatarLoading}
                className="relative flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-[26px] border border-book-primary/35 bg-book-bg-paper/82 text-book-text-main shadow-[0_24px_52px_-36px_rgba(36,18,6,0.92)] transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/55 disabled:cursor-not-allowed disabled:opacity-60 sm:h-24 sm:w-24"
                title={blueprintData?.avatar_svg ? '点击重新生成头像' : '点击生成小说头像'}
              >
                {blueprintData?.avatar_svg ? (
                  <div
                    className="h-full w-full avatar-svg"
                    dangerouslySetInnerHTML={{ __html: String(blueprintData.avatar_svg) }}
                  />
                ) : (
                  <span className="font-serif text-4xl font-bold uppercase text-book-primary">
                    {projectTitle.slice(0, 1)}
                  </span>
                )}
                <span className="absolute bottom-2 right-2 inline-flex h-8 w-8 items-center justify-center rounded-full border border-book-border/50 bg-book-bg-paper/88 text-book-primary">
                  <Camera size={14} />
                </span>
              </button>

              <div className="min-w-0 space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                  <h1 className="font-serif text-[clamp(2rem,4vw,3.8rem)] font-bold leading-[0.94] tracking-[-0.04em] text-book-text-main">
                    {projectTitle}
                  </h1>
                  <button
                    type="button"
                    className="inline-flex items-center gap-2 rounded-full border border-book-border/55 bg-book-bg-paper/78 px-3 py-2 text-sm font-semibold text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/30 hover:text-book-primary"
                    onClick={openEditTitleModal}
                  >
                    <PenSquare size={14} />
                    编辑标题
                  </button>
                </div>

                <p className="max-w-4xl text-sm leading-relaxed text-book-text-sub sm:text-base">
                  {oneSentenceSummary}
                </p>

                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="metric-tile">
                    <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                      章节规划
                    </div>
                    <div className="mt-3 font-serif text-3xl font-bold text-book-text-main">
                      {chapterOutlineCount}
                    </div>
                    <div className="mt-2 text-sm text-book-text-sub">已铺开的章节大纲数量</div>
                  </div>
                  <div className="metric-tile">
                    <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                      角色密度
                    </div>
                    <div className="mt-3 font-serif text-3xl font-bold text-book-text-main">
                      {characterCount}
                    </div>
                    <div className="mt-2 text-sm text-book-text-sub">已录入角色</div>
                  </div>
                  <div className="metric-tile">
                    <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                      关系网络
                    </div>
                    <div className="mt-3 font-serif text-3xl font-bold text-book-text-main">
                      {relationshipCount}
                    </div>
                    <div className="mt-2 text-sm text-book-text-sub">人物之间的结构连接</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="flex w-full flex-col gap-3 lg:w-auto lg:min-w-[18rem]">
            <BookButton
              variant="primary"
              size="lg"
              onClick={() => safeNavigate(`/write/${projectId}`)}
              className="w-full"
            >
              <Wand2 size={16} />
              开始创作
            </BookButton>

            <BookButton
              variant={isBlueprintDirty ? 'secondary' : 'ghost'}
              size="md"
              onClick={handleSave}
              disabled={saving || Boolean(worldSettingError)}
              className="w-full"
              title={
                worldSettingError
                  ? '世界观 JSON 无效：请先修正再保存'
                  : (isBlueprintDirty ? (dirtySummary || '有未保存的修改') : '当前没有未保存修改')
              }
            >
              {saving ? '保存中…' : isBlueprintDirty ? '保存蓝图' : '蓝图已保存'}
            </BookButton>

            <div className="flex items-center gap-2">
              <Dropdown
                label="更多动作"
                items={[
                  { label: '导出项目', icon: <Download size={14} />, onClick: () => void handleExport() },
                  {
                    label: ragSyncing ? 'RAG同步中…' : '同步到向量库',
                    icon: <Orbit size={14} />,
                    onClick: () => {
                      if (!ragSyncing) void handleRagSync();
                    },
                  },
                  { label: '优化蓝图', icon: <Sparkles size={14} />, onClick: () => void openRefineModal() },
                  { label: '重新生成头像', icon: <Camera size={14} />, onClick: () => void handleAvatarClick() },
                  ...(blueprintData?.avatar_svg
                    ? [{ label: '删除头像', icon: <Trash2 size={14} />, onClick: () => void handleDeleteAvatar(), danger: true }]
                    : []),
                ]}
              />
            </div>
          </div>
        </div>

        <div className="story-divider" />

        <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(260px,320px)]">
          <div className="rounded-[28px] border border-book-border/55 bg-book-bg-paper/76 px-4 py-4 text-sm leading-relaxed text-book-text-sub shadow-[0_20px_44px_-34px_rgba(36,18,6,0.92)]">
            先在左侧章节间切换世界观、角色、关系与大纲，再进入写作台。高频动作只保留保存与开始创作，低频动作统一进入 overflow。
          </div>
          <div className="rounded-[28px] border border-book-border/55 bg-book-bg-paper/76 px-4 py-4 text-sm shadow-[0_20px_44px_-34px_rgba(36,18,6,0.92)]">
            <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
              当前状态
            </div>
            <div className="mt-2 font-semibold text-book-text-main">
              {worldSettingError ? '存在需要修正的世界观内容' : dirtySummary || '结构状态正常，可继续推进创作'}
            </div>
            <div className="mt-2 text-book-text-sub">
              {worldSettingError ? '修正后再保存，避免把非法 JSON 带入后续流程。' : '继续补全蓝图，或直接进入写作台开始产出正文。'}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
