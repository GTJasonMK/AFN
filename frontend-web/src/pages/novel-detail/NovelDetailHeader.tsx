import React from 'react';
import { ArrowLeft, Camera, Download, Orbit, PenSquare, Sparkles, Trash2, Users, Wand2, Link2, ListChecks } from 'lucide-react';
import { BookButton } from '../../components/ui/BookButton';
import { Dropdown } from '../../components/ui/Dropdown';
import { getStatusText } from '../../utils/constants';

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
  const genre = String(blueprintData?.genre || '未分类').trim() || '未分类';
  const projectStatusRaw = String(project?.status || 'draft').trim() || 'draft';
  const projectStatus = getStatusText(projectStatusRaw);
  const chapterOutlineCount = Array.isArray(blueprintData?.chapter_outline)
    ? blueprintData.chapter_outline.length
    : 0;
  const characterCount = Array.isArray(blueprintData?.characters)
    ? blueprintData.characters.length
    : 0;
  const relationshipCount = Array.isArray(blueprintData?.relationships)
    ? blueprintData.relationships.length
    : Array.isArray(blueprintData?.character_relationships)
      ? blueprintData.character_relationships.length
      : 0;
  const storyStageLabel = isBlueprintDirty ? '待保存' : '已同步';
  const storyStageHint = isBlueprintDirty ? (dirtySummary || '有未保存的修改') : '';
  const statusTone = worldSettingError
    ? 'border-red-500/25 bg-red-500/8 text-red-600 dark:text-red-300'
    : isBlueprintDirty
      ? 'border-amber-500/25 bg-amber-500/8 text-amber-700 dark:text-amber-300'
      : 'border-emerald-500/25 bg-emerald-500/8 text-emerald-700 dark:text-emerald-300';

  return (
    <section className="dramatic-surface rounded-[28px] px-4 py-2 sm:px-5 sm:py-3">
      <div className="relative z-[1] flex items-center justify-between gap-3">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <BookButton
            variant="ghost"
            size="sm"
            onClick={() => safeNavigate(`/write/${projectId}`)}
            title="返回写作台"
          >
            <ArrowLeft size={16} />
            写作台
          </BookButton>

          <button
            type="button"
            onClick={handleAvatarClick}
            disabled={avatarLoading}
            className="relative flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-[16px] border border-book-border/55 bg-book-bg-paper/82 text-book-text-main shadow-surface transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/35 disabled:cursor-not-allowed disabled:opacity-60"
            title={blueprintData?.avatar_svg ? '点击重新生成头像' : '点击生成小说头像'}
          >
            {blueprintData?.avatar_svg ? (
              <div
                className="h-full w-full avatar-svg"
                dangerouslySetInnerHTML={{ __html: String(blueprintData.avatar_svg) }}
              />
            ) : (
              <span className="font-serif text-xl font-bold uppercase text-book-primary">
                {projectTitle.slice(0, 1)}
              </span>
            )}
            <span className="absolute bottom-0.5 right-0.5 inline-flex h-5 w-5 items-center justify-center rounded-full border border-book-border/55 bg-book-bg-paper/92 text-book-primary">
              <Camera size={11} />
            </span>
          </button>

          <div className="min-w-0 flex-1">
            <div className="flex min-w-0 items-center gap-2 overflow-hidden">
              <div className="hidden xl:inline-flex eyebrow">Story Control</div>
              <h1 className="min-w-0 flex-1 truncate font-serif text-xl font-bold leading-tight tracking-[-0.03em] text-book-text-main">
                {projectTitle}
              </h1>
              <BookButton variant="ghost" size="sm" onClick={openEditTitleModal} title="编辑标题">
                <PenSquare size={14} />
              </BookButton>

              <span
                title={storyStageHint || undefined}
                className={`inline-flex items-center rounded-full border font-semibold ${statusTone} px-2.5 py-1 text-[0.7rem]`}
              >
                {storyStageLabel}
              </span>
              <span className="story-pill-compact hidden sm:inline-flex" title={genre}>
                {genre}
              </span>
              <span className="story-pill-compact hidden md:inline-flex" title={projectStatus}>
                {projectStatus}
              </span>
              {worldSettingError ? (
                <span className="story-pill-compact hidden lg:inline-flex border-red-500/25 bg-red-500/8 text-red-600 dark:text-red-300">
                  世界观 JSON 需修正
                </span>
              ) : null}

              <span className="story-pill-compact hidden xl:inline-flex" title="章节大纲数量">
                <ListChecks size={14} />
                章节 {chapterOutlineCount}
              </span>
              <span className="story-pill-compact hidden xl:inline-flex" title="角色数量">
                <Users size={14} />
                角色 {characterCount}
              </span>
              <span className="story-pill-compact hidden xl:inline-flex" title="关系数量">
                <Link2 size={14} />
                关系 {relationshipCount}
              </span>
            </div>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <BookButton
            variant={isBlueprintDirty ? 'secondary' : 'ghost'}
            size="sm"
            onClick={handleSave}
            disabled={saving || Boolean(worldSettingError)}
            title={
              worldSettingError
                ? '世界观 JSON 无效：请先修正再保存'
                : (isBlueprintDirty ? (dirtySummary || '有未保存的修改') : '当前没有未保存修改')
            }
          >
            {saving ? '保存中…' : isBlueprintDirty ? '保存蓝图' : '已保存'}
          </BookButton>

          <BookButton
            variant="primary"
            size="sm"
            onClick={() => safeNavigate(`/write/${projectId}`)}
            title="进入写作台"
          >
            <Wand2 size={16} />
            写作台
          </BookButton>

          <Dropdown
            label="更多"
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
    </section>
  );
};
