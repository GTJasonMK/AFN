import React from 'react';
import { ProtagonistProfileSummary } from '../../../api/protagonist';
import { BookButton } from '../../ui/BookButton';
import { BookInput } from '../../ui/BookInput';
import {
  NovelDialogSection,
  NovelDialogSurface,
} from '../novel/NovelDialogPrimitives';
import { Plus, RefreshCw } from 'lucide-react';
import { normalizeCharacterName } from './shared';

type ProtagonistProfilesSidebarProps = {
  profiles: ProtagonistProfileSummary[];
  loading: boolean;
  createName: string;
  creating: boolean;
  selectedName: string;
  characterIdentityByName: Record<string, string>;
  onRefreshList: () => void | Promise<void>;
  onChangeCreateName: (value: string) => void;
  onCreate: () => void | Promise<void>;
  onSelectName: (name: string) => void;
};

export const ProtagonistProfilesSidebar: React.FC<ProtagonistProfilesSidebarProps> = ({
  profiles,
  loading,
  createName,
  creating,
  selectedName,
  characterIdentityByName,
  onRefreshList,
  onChangeCreateName,
  onCreate,
  onSelectName,
}) => {
  return (
    <NovelDialogSection
      eyebrow="Profiles"
      title="档案列表"
      description="创建新档案后可在这里切换、刷新和检查同步边界。"
      className="min-h-0"
      actions={(
        <BookButton variant="ghost" size="sm" onClick={onRefreshList} disabled={loading}>
          <RefreshCw size={14} className={`mr-1 ${loading ? 'animate-spin' : ''}`} />
          刷新
        </BookButton>
      )}
    >
      <div className="flex h-full min-h-0 flex-col gap-4">
        <NovelDialogSurface>
          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
            <BookInput
              label="新建档案"
              placeholder="输入角色名"
              value={createName}
              onChange={(e) => onChangeCreateName(e.target.value)}
            />
            <div className="flex items-end">
              <BookButton variant="primary" size="sm" onClick={onCreate} disabled={creating}>
                <Plus size={14} className="mr-1" />
                {creating ? '创建中…' : '创建'}
              </BookButton>
            </div>
          </div>
        </NovelDialogSurface>

        <div className="custom-scrollbar min-h-0 flex-1 space-y-2 overflow-auto pr-1">
          {profiles.length === 0 && !loading ? (
            <NovelDialogSurface className="text-sm text-book-text-muted">
              暂无档案，可在上方输入角色名后创建。
            </NovelDialogSurface>
          ) : null}

          {profiles.map((profile) => {
            const active = profile.character_name === selectedName;
            const nameKey = normalizeCharacterName(profile.character_name);
            const identity = normalizeCharacterName(characterIdentityByName[nameKey]);
            return (
              <button
                key={profile.id}
                onClick={() => onSelectName(profile.character_name)}
                className={`w-full rounded-[22px] border px-4 py-3 text-left transition-all ${
                  active
                    ? 'border-book-primary/40 bg-book-primary/8 shadow-[0_18px_40px_-34px_rgba(121,84,57,0.75)]'
                    : 'border-book-border/45 bg-book-bg/70 hover:border-book-primary/25 hover:bg-book-bg-paper/72'
                }`}
                type="button"
              >
                <div className="flex min-w-0 items-center justify-between gap-2">
                  <div className="min-w-0 truncate text-sm font-semibold text-book-text-main">
                    {profile.character_name}
                  </div>
                  {identity ? (
                    <span className="story-pill-compact shrink-0 max-w-[8rem] overflow-hidden" title={identity}>
                      <span className="truncate">{identity}</span>
                    </span>
                  ) : null}
                </div>
                <div className="mt-2 text-[11px] leading-relaxed text-book-text-muted">
                  synced={profile.last_synced_chapter} · exp={profile.attribute_counts?.explicit ?? 0} · imp={profile.attribute_counts?.implicit ?? 0} · soc={profile.attribute_counts?.social ?? 0}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </NovelDialogSection>
  );
};
