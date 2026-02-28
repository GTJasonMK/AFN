import React from 'react';
import { BookButton } from '../../components/ui/BookButton';

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
  return (
    <div className="h-[100px] border-b border-book-border bg-book-bg-paper flex items-center justify-between px-6 sticky top-0 z-20">
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={handleAvatarClick}
          disabled={avatarLoading}
          className="w-16 h-16 rounded border-2 border-book-primary flex items-center justify-center shrink-0 hover:border-book-primary/70 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          title={blueprintData?.avatar_svg ? '点击重新生成头像' : '点击生成小说头像'}
        >
          {blueprintData?.avatar_svg ? (
            <div
              className="w-full h-full"
              dangerouslySetInnerHTML={{ __html: String(blueprintData.avatar_svg) }}
            />
          ) : (
            <span className="text-3xl font-bold text-book-text-main">
              {String(project?.title || 'B').trim().slice(0, 1) || 'B'}
            </span>
          )}
        </button>

        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <h1 className="font-serif font-bold text-[28px] text-book-text-main tracking-wide">{project.title}</h1>
            <button
              className="text-xs text-book-text-sub underline hover:text-book-primary"
              onClick={openEditTitleModal}
            >
              编辑
            </button>
            {blueprintData?.avatar_svg ? (
              <button
                className="text-xs text-book-text-sub underline hover:text-red-600 disabled:opacity-50"
                onClick={handleDeleteAvatar}
                disabled={avatarLoading}
                title="删除当前小说头像"
              >
                删除头像
              </button>
            ) : null}
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="px-2 py-0.5 border border-book-border rounded text-book-text-sub">
              {blueprintData.genre || '未分类'}
            </span>
            <span className="px-2 py-0.5 border border-book-border rounded text-book-text-sub italic">
              {project.status}
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <BookButton
          variant={isBlueprintDirty ? 'primary' : 'secondary'}
          size="sm"
          onClick={handleSave}
          disabled={saving || Boolean(worldSettingError)}
          title={
            worldSettingError
              ? '世界观 JSON 无效：请先修正再保存'
              : (isBlueprintDirty ? (dirtySummary || '有未保存的修改') : '保存蓝图')
          }
        >
          {saving ? '保存中...' : (isBlueprintDirty ? '保存*' : '保存')}
        </BookButton>
        <BookButton variant="secondary" size="sm" onClick={() => safeNavigate(`/write/${projectId}`)}>
          返回写作台
        </BookButton>
        <BookButton variant="secondary" size="sm" onClick={handleExport}>
          导出
        </BookButton>
        <BookButton
          variant="secondary"
          size="sm"
          onClick={handleRagSync}
          disabled={ragSyncing}
          title="同步项目到向量库"
        >
          {ragSyncing ? 'RAG同步中…' : 'RAG同步'}
        </BookButton>
        <BookButton variant="secondary" size="sm" onClick={openRefineModal}>
          优化蓝图
        </BookButton>
        <BookButton variant="primary" size="sm" onClick={() => safeNavigate(`/write/${projectId}`)}>
          开始创作
        </BookButton>
      </div>
    </div>
  );
};
