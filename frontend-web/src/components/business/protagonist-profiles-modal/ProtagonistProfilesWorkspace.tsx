import React from 'react';
import {
  AttributeCategory,
  AttributeChangeResponse,
  BehaviorRecordResponse,
  DeletionMarkResponse,
  DiffResponse,
  ImplicitCheckResponse,
  ImplicitStatsResponse,
  ProfileConflictCheck,
  ProtagonistProfileResponse,
  SnapshotListResponse,
  SnapshotResponse,
} from '../../../api/protagonist';
import { BookButton } from '../../ui/BookButton';
import { BookInput } from '../../ui/BookInput';
import {
  NovelDialogIntro,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from '../novel/NovelDialogPrimitives';
import {
  ChevronDown,
  ChevronUp,
  Database,
  GitCompare,
  RefreshCw,
  Sparkles,
  Trash2,
} from 'lucide-react';
import {
  codeBlockClassName,
  DETAIL_TABS,
  DetailTab,
  formatDateTime,
  selectClassName,
} from './shared';

type ProtagonistProfilesWorkspaceProps = {
  selectedName: string;
  selectedIdentity: string | null;
  identityExpanded: boolean;
  selectedLastSyncedChapter: number;
  detailLoading: boolean;
  detail: ProtagonistProfileResponse | null;
  syncChapter: number;
  syncing: boolean;
  activeTab: DetailTab;
  historyLoading: boolean;
  history: AttributeChangeResponse[];
  historyStart: number | '';
  historyEnd: number | '';
  historyCategory: AttributeCategory | '';
  behaviorsLoading: boolean;
  behaviors: BehaviorRecordResponse[];
  behaviorsChapter: number | '';
  behaviorsLimit: number;
  marksLoading: boolean;
  marks: DeletionMarkResponse[];
  marksCategory: AttributeCategory | '';
  markActionKey: string | null;
  snapshotsLoading: boolean;
  snapshots: SnapshotListResponse | null;
  snapshotDetailLoading: boolean;
  snapshotDetail: SnapshotResponse | null;
  conflictLoading: boolean;
  conflict: ProfileConflictCheck | null;
  diffFrom: number;
  diffTo: number;
  diffLoading: boolean;
  diffResult: DiffResponse | null;
  rollbackTarget: number;
  rollbackLoading: boolean;
  implicitKey: string;
  implicitWindow: number;
  implicitStatsLoading: boolean;
  implicitStats: ImplicitStatsResponse | null;
  implicitCheckLoading: boolean;
  implicitCheck: ImplicitCheckResponse | null;
  onToggleIdentityExpanded: () => void;
  onCloseIdentityExpanded: () => void;
  onDelete: () => void | Promise<void>;
  onRefreshDetail: () => void | Promise<void>;
  onChangeSyncChapter: (value: number) => void;
  onSync: () => void | Promise<void>;
  onChangeActiveTab: (tab: DetailTab) => void;
  onRefreshHistory: () => void | Promise<void>;
  onChangeHistoryStart: (value: number | '') => void;
  onChangeHistoryEnd: (value: number | '') => void;
  onChangeHistoryCategory: (value: AttributeCategory | '') => void;
  onRefreshBehaviors: () => void | Promise<void>;
  onChangeBehaviorsChapter: (value: number | '') => void;
  onChangeBehaviorsLimit: (value: number) => void;
  onRefreshMarks: () => void | Promise<void>;
  onChangeMarksCategory: (value: AttributeCategory | '') => void;
  onExecuteDeletion: (category: AttributeCategory, key: string) => void | Promise<void>;
  onResetMarks: (category: AttributeCategory, key: string) => void | Promise<void>;
  onRefreshSnapshots: () => void | Promise<void>;
  onLoadSnapshot: (chapter: number) => void | Promise<void>;
  onRefreshConflict: () => void | Promise<void>;
  onChangeDiffFrom: (value: number) => void;
  onChangeDiffTo: (value: number) => void;
  onRunDiff: () => void | Promise<void>;
  onChangeRollbackTarget: (value: number) => void;
  onRunRollback: () => void | Promise<void>;
  onChangeImplicitKey: (value: string) => void;
  onChangeImplicitWindow: (value: number) => void;
  onFetchImplicitStats: () => void | Promise<void>;
  onFetchImplicitCheck: () => void | Promise<void>;
};

export const ProtagonistProfilesWorkspace: React.FC<ProtagonistProfilesWorkspaceProps> = ({
  selectedName,
  selectedIdentity,
  identityExpanded,
  selectedLastSyncedChapter,
  detailLoading,
  detail,
  syncChapter,
  syncing,
  activeTab,
  historyLoading,
  history,
  historyStart,
  historyEnd,
  historyCategory,
  behaviorsLoading,
  behaviors,
  behaviorsChapter,
  behaviorsLimit,
  marksLoading,
  marks,
  marksCategory,
  markActionKey,
  snapshotsLoading,
  snapshots,
  snapshotDetailLoading,
  snapshotDetail,
  conflictLoading,
  conflict,
  diffFrom,
  diffTo,
  diffLoading,
  diffResult,
  rollbackTarget,
  rollbackLoading,
  implicitKey,
  implicitWindow,
  implicitStatsLoading,
  implicitStats,
  implicitCheckLoading,
  implicitCheck,
  onToggleIdentityExpanded,
  onCloseIdentityExpanded,
  onDelete,
  onRefreshDetail,
  onChangeSyncChapter,
  onSync,
  onChangeActiveTab,
  onRefreshHistory,
  onChangeHistoryStart,
  onChangeHistoryEnd,
  onChangeHistoryCategory,
  onRefreshBehaviors,
  onChangeBehaviorsChapter,
  onChangeBehaviorsLimit,
  onRefreshMarks,
  onChangeMarksCategory,
  onExecuteDeletion,
  onResetMarks,
  onRefreshSnapshots,
  onLoadSnapshot,
  onRefreshConflict,
  onChangeDiffFrom,
  onChangeDiffTo,
  onRunDiff,
  onChangeRollbackTarget,
  onRunRollback,
  onChangeImplicitKey,
  onChangeImplicitWindow,
  onFetchImplicitStats,
  onFetchImplicitCheck,
}) => {
  const activeTabMeta = DETAIL_TABS.find((tab) => tab.id === activeTab) || DETAIL_TABS[0];

  if (!selectedName) {
    return (
      <NovelDialogIntro
        eyebrow="Profile Detail"
        title="先选择一个角色档案"
        description="右侧工作区会展示当前角色的属性、变更历史、行为记录和快照信息。若当前还没有角色，可先在左侧创建。"
      />
    );
  }

  return (
    <NovelDialogStack>
      <NovelDialogSection
        eyebrow="Profile Overview"
        title={selectedName}
        description={`最后同步章节：${selectedLastSyncedChapter}。同步会分析指定章节正文，更新属性、行为与删除候选。`}
        actions={(
          <>
            {selectedIdentity ? (
              <div className="relative shrink-0">
                <button
                  type="button"
                  onClick={onToggleIdentityExpanded}
                  className={`story-pill-compact inline-flex max-w-[12rem] items-center gap-2 overflow-hidden transition-colors ${
                    identityExpanded ? 'border-book-primary/35 bg-book-primary/10 text-book-primary' : ''
                  }`}
                  title={identityExpanded ? '收起身份' : '展开身份'}
                  aria-expanded={identityExpanded}
                  aria-label={identityExpanded ? '收起角色身份' : '展开角色身份'}
                >
                  <span className="min-w-0 flex-1 truncate">{selectedIdentity}</span>
                  {identityExpanded ? (
                    <ChevronUp size={14} className="shrink-0 opacity-80" />
                  ) : (
                    <ChevronDown size={14} className="shrink-0 opacity-80" />
                  )}
                </button>

                {identityExpanded ? (
                  <div className="absolute right-0 top-full z-20 mt-2 w-[min(56vw,28rem)] rounded-[22px] border border-book-border/55 bg-book-bg-paper/92 p-3 shadow-[0_24px_58px_-48px_rgba(34,17,7,0.94)] backdrop-blur-xl">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-[0.7rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                        角色身份
                      </div>
                      <button
                        type="button"
                        onClick={onCloseIdentityExpanded}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-book-border/55 bg-book-bg/70 text-book-text-muted transition-colors hover:border-book-primary/35 hover:text-book-primary"
                        title="收起"
                        aria-label="收起角色身份"
                      >
                        <ChevronUp size={14} />
                      </button>
                    </div>
                    <div className="custom-scrollbar mt-2 max-h-28 overflow-auto whitespace-pre-wrap break-words text-xs leading-relaxed text-book-text-main">
                      {selectedIdentity}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}
            <BookButton variant="ghost" size="sm" onClick={onDelete}>
              <Trash2 size={14} className="mr-1" />
              删除
            </BookButton>
            <BookButton variant="ghost" size="sm" onClick={onRefreshDetail} disabled={detailLoading}>
              <RefreshCw size={14} className={`mr-1 ${detailLoading ? 'animate-spin' : ''}`} />
              刷新
            </BookButton>
          </>
        )}
      >
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto]">
          <BookInput
            label="同步到章节"
            type="number"
            min={1}
            value={syncChapter}
            onChange={(e) => onChangeSyncChapter(Number(e.target.value) || 1)}
          />
          <div className="flex items-end justify-end">
            <BookButton variant="primary" onClick={onSync} disabled={syncing}>
              <Database size={16} className={`mr-2 ${syncing ? 'animate-pulse' : ''}`} />
              {syncing ? '同步中…' : '同步'}
            </BookButton>
          </div>
        </div>

        <div className="mt-4">
          <NovelDialogSurface className="text-xs leading-relaxed text-book-text-muted">
            说明：同步依赖 LLM 分析章节正文，会自动更新显性 / 隐性 / 社会属性，并记录行为与删除候选。建议按章节顺序执行，避免快照链路断层。
          </NovelDialogSurface>
        </div>
      </NovelDialogSection>

      <NovelDialogSection
        eyebrow="Workspace"
        title={activeTabMeta.label}
        description={activeTabMeta.description}
      >
        <div className="flex flex-wrap gap-2">
          {DETAIL_TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onChangeActiveTab(tab.id)}
                className={`flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold transition-all ${
                  active
                    ? 'border-book-primary/40 bg-book-primary/8 text-book-primary'
                    : 'border-book-border/45 bg-book-bg/72 text-book-text-main hover:border-book-primary/25'
                }`}
                type="button"
              >
                <Icon size={14} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </NovelDialogSection>

      {activeTab === 'attributes' ? (
        <NovelDialogSection
          eyebrow="Attributes"
          title="属性数据"
          description="当前档案的核心状态快照。显性属性偏事实，隐性属性偏倾向，社会属性偏关系和位置。"
        >
          {detailLoading ? (
            <NovelDialogSurface className="text-sm text-book-text-muted">加载中…</NovelDialogSurface>
          ) : !detail ? (
            <NovelDialogSurface className="text-sm text-book-text-muted">暂无详情数据。</NovelDialogSurface>
          ) : (
            <div className="grid gap-3 xl:grid-cols-3">
              <NovelDialogSurface>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">Explicit</div>
                <pre className={`mt-3 ${codeBlockClassName}`}>
                  {JSON.stringify(detail.explicit_attributes || {}, null, 2)}
                </pre>
              </NovelDialogSurface>
              <NovelDialogSurface>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">Implicit</div>
                <pre className={`mt-3 ${codeBlockClassName}`}>
                  {JSON.stringify(detail.implicit_attributes || {}, null, 2)}
                </pre>
              </NovelDialogSurface>
              <NovelDialogSurface>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">Social</div>
                <pre className={`mt-3 ${codeBlockClassName}`}>
                  {JSON.stringify(detail.social_attributes || {}, null, 2)}
                </pre>
              </NovelDialogSurface>
            </div>
          )}
        </NovelDialogSection>
      ) : null}

      {activeTab === 'history' ? (
        <NovelDialogSection
          eyebrow="History"
          title="变更历史"
          description="筛选某一章节范围内的属性变化，检查更新是否来自合理事件。"
          actions={(
            <BookButton variant="ghost" size="sm" onClick={onRefreshHistory} disabled={historyLoading}>
              <RefreshCw size={14} className={`mr-1 ${historyLoading ? 'animate-spin' : ''}`} />
              刷新
            </BookButton>
          )}
        >
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              <BookInput
                label="起始章（可选）"
                type="number"
                min={1}
                value={historyStart}
                onChange={(e) => onChangeHistoryStart(e.target.value ? Number(e.target.value) : '')}
              />
              <BookInput
                label="结束章（可选）"
                type="number"
                min={1}
                value={historyEnd}
                onChange={(e) => onChangeHistoryEnd(e.target.value ? Number(e.target.value) : '')}
              />
              <label className="text-sm font-bold text-book-text-sub">
                类别（可选）
                <select
                  className={selectClassName}
                  value={historyCategory}
                  onChange={(e) => onChangeHistoryCategory((e.target.value as AttributeCategory) || '')}
                >
                  <option value="">全部</option>
                  <option value="explicit">explicit</option>
                  <option value="implicit">implicit</option>
                  <option value="social">social</option>
                </select>
              </label>
            </div>

            {history.length === 0 ? (
              <NovelDialogSurface className="text-sm text-book-text-muted">
                暂无变更记录。
              </NovelDialogSurface>
            ) : (
              <div className="space-y-3">
                {history.map((item) => (
                  <NovelDialogSurface key={item.id}>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-sm font-semibold text-book-text-main">
                        第 {item.chapter_number} 章 · {item.attribute_category}.{item.attribute_key} · {item.operation}
                      </div>
                      <div className="text-[11px] text-book-text-muted">
                        {formatDateTime(item.created_at)}
                      </div>
                    </div>
                    {item.change_description ? (
                      <div className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-book-text-main">
                        {item.change_description}
                      </div>
                    ) : null}
                    {item.event_cause ? (
                      <div className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-book-text-muted">
                        触发：{item.event_cause}
                      </div>
                    ) : null}
                    {item.evidence ? (
                      <div className="mt-2 whitespace-pre-wrap border-l-2 border-book-border pl-3 text-xs leading-relaxed text-book-text-muted">
                        证据：{item.evidence}
                      </div>
                    ) : null}
                  </NovelDialogSurface>
                ))}
              </div>
            )}
          </div>
        </NovelDialogSection>
      ) : null}

      {activeTab === 'behaviors' ? (
        <NovelDialogSection
          eyebrow="Behaviors"
          title="行为记录"
          description="按章节抽样行为记录，核对标签、原文证据和分类结果是否可信。"
          actions={(
            <BookButton variant="ghost" size="sm" onClick={onRefreshBehaviors} disabled={behaviorsLoading}>
              <RefreshCw size={14} className={`mr-1 ${behaviorsLoading ? 'animate-spin' : ''}`} />
              刷新
            </BookButton>
          )}
        >
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <BookInput
                label="指定章节（可选）"
                type="number"
                min={1}
                value={behaviorsChapter}
                onChange={(e) => onChangeBehaviorsChapter(e.target.value ? Number(e.target.value) : '')}
              />
              <BookInput
                label="返回数量"
                type="number"
                min={1}
                max={100}
                value={behaviorsLimit}
                onChange={(e) => onChangeBehaviorsLimit(Math.max(1, Math.min(100, Number(e.target.value) || 20)))}
              />
            </div>

            {behaviors.length === 0 ? (
              <NovelDialogSurface className="text-sm text-book-text-muted">
                暂无行为记录。
              </NovelDialogSurface>
            ) : (
              <div className="space-y-3">
                {behaviors.map((item) => (
                  <NovelDialogSurface key={item.id}>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-sm font-semibold text-book-text-main">第 {item.chapter_number} 章</div>
                      <div className="text-[11px] text-book-text-muted">
                        {formatDateTime(item.created_at)}
                      </div>
                    </div>
                    <div className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-book-text-main">
                      {item.behavior_description}
                    </div>
                    {Array.isArray(item.behavior_tags) && item.behavior_tags.length > 0 ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {item.behavior_tags.map((tag) => (
                          <span key={`${item.id}-${tag}`} className="story-pill">
                            {tag}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    {item.original_text ? (
                      <div className="mt-2 whitespace-pre-wrap border-l-2 border-book-border pl-3 text-xs leading-relaxed text-book-text-muted">
                        原文：{item.original_text}
                      </div>
                    ) : null}
                    {item.classification_results && Object.keys(item.classification_results).length > 0 ? (
                      <pre className={`mt-3 ${codeBlockClassName}`}>
                        {JSON.stringify(item.classification_results, null, 2)}
                      </pre>
                    ) : null}
                  </NovelDialogSurface>
                ))}
              </div>
            )}
          </div>
        </NovelDialogSection>
      ) : null}

      {activeTab === 'deletions' ? (
        <NovelDialogSection
          eyebrow="Deletion Marks"
          title="删除标记"
          description="关注连续标记次数和最后标记章节，避免误删仍然有效的长期属性。"
          actions={(
            <BookButton variant="ghost" size="sm" onClick={onRefreshMarks} disabled={marksLoading}>
              <RefreshCw size={14} className={`mr-1 ${marksLoading ? 'animate-spin' : ''}`} />
              刷新
            </BookButton>
          )}
        >
          <div className="space-y-4">
            <label className="text-sm font-bold text-book-text-sub">
              类别筛选
              <select
                className={selectClassName}
                value={marksCategory}
                onChange={(e) => onChangeMarksCategory((e.target.value as AttributeCategory) || '')}
              >
                <option value="">全部</option>
                <option value="explicit">explicit</option>
                <option value="implicit">implicit</option>
                <option value="social">social</option>
              </select>
            </label>

            {marks.length === 0 ? (
              <NovelDialogSurface className="text-sm text-book-text-muted">
                暂无删除标记。
              </NovelDialogSurface>
            ) : (
              <div className="space-y-3">
                {marks.map((item) => {
                  const category = item.attribute_category as AttributeCategory;
                  const key = item.attribute_key;
                  const execKey = `exec:${category}:${key}`;
                  const resetKey = `reset:${category}:${key}`;
                  const disabled = markActionKey === execKey || markActionKey === resetKey;

                  return (
                    <NovelDialogSurface key={item.id}>
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold text-book-text-main">
                            {item.attribute_category}.{item.attribute_key}
                          </div>
                          <div className="mt-1 text-xs leading-relaxed text-book-text-muted">
                            连续标记：{item.consecutive_count}/5 · 最后标记章：{item.last_marked_chapter}
                            {item.is_executed ? ' · 已执行' : ''}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <BookButton
                            variant="secondary"
                            size="sm"
                            onClick={() => onExecuteDeletion(category, key)}
                            disabled={disabled || item.is_executed}
                            title="达到阈值后可执行删除"
                          >
                            执行
                          </BookButton>
                          <BookButton
                            variant="ghost"
                            size="sm"
                            onClick={() => onResetMarks(category, key)}
                            disabled={disabled}
                          >
                            重置
                          </BookButton>
                        </div>
                      </div>
                      {item.mark_reason ? (
                        <div className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-book-text-muted">
                          原因：{item.mark_reason}
                        </div>
                      ) : null}
                      {item.evidence ? (
                        <div className="mt-2 whitespace-pre-wrap border-l-2 border-book-border pl-3 text-xs leading-relaxed text-book-text-muted">
                          证据：{item.evidence}
                        </div>
                      ) : null}
                    </NovelDialogSurface>
                  );
                })}
              </div>
            )}
          </div>
        </NovelDialogSection>
      ) : null}

      {activeTab === 'snapshots' ? (
        <NovelDialogSection
          eyebrow="Snapshots"
          title="状态快照"
          description="快照用于复核章节同步结果，也是回滚和 diff 的基础。"
          actions={(
            <BookButton variant="ghost" size="sm" onClick={onRefreshSnapshots} disabled={snapshotsLoading}>
              <RefreshCw size={14} className={`mr-1 ${snapshotsLoading ? 'animate-spin' : ''}`} />
              刷新
            </BookButton>
          )}
        >
          <div className="space-y-4">
            {snapshots?.snapshots?.length ? (
              <div className="grid gap-2">
                {snapshots.snapshots.map((snapshot) => (
                  <button
                    key={`ss-${snapshot.chapter_number}`}
                    onClick={() => onLoadSnapshot(snapshot.chapter_number)}
                    className="rounded-[22px] border border-book-border/45 bg-book-bg/72 px-4 py-3 text-left transition-all hover:border-book-primary/25 hover:bg-book-bg-paper/72"
                    type="button"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-sm font-semibold text-book-text-main">第 {snapshot.chapter_number} 章</div>
                      <div className="text-[11px] text-book-text-muted">
                        Δ{snapshot.changes_in_chapter} · 行为 {snapshot.behaviors_in_chapter}
                      </div>
                    </div>
                    <div className="mt-2 text-[11px] leading-relaxed text-book-text-muted">
                      exp={snapshot.attribute_counts.explicit} · imp={snapshot.attribute_counts.implicit} · soc={snapshot.attribute_counts.social}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <NovelDialogSurface className="text-sm text-book-text-muted">
                暂无快照。请先按顺序同步章节后再回到这里查看。
              </NovelDialogSurface>
            )}

            {snapshotDetailLoading ? (
              <NovelDialogSurface className="text-sm text-book-text-muted">
                快照加载中…
              </NovelDialogSurface>
            ) : null}

            {snapshotDetail ? (
              <NovelDialogSurface>
                <div className="text-sm font-semibold text-book-text-main">
                  快照详情（第 {snapshotDetail.chapter_number} 章）
                </div>
                <pre className={`mt-3 ${codeBlockClassName}`}>
                  {JSON.stringify(snapshotDetail, null, 2)}
                </pre>
              </NovelDialogSurface>
            ) : null}
          </div>
        </NovelDialogSection>
      ) : null}

      {activeTab === 'diff' ? (
        <NovelDialogStack>
          <NovelDialogSection
            eyebrow="Conflict Check"
            title="冲突检测"
            description="先确认当前档案与可用章节范围是否冲突，再决定是否执行回滚。"
            actions={(
              <BookButton variant="ghost" size="sm" onClick={onRefreshConflict} disabled={conflictLoading}>
                <RefreshCw size={14} className={`mr-1 ${conflictLoading ? 'animate-spin' : ''}`} />
                刷新
              </BookButton>
            )}
          >
            {conflict ? (
              <NovelDialogSurface>
                {conflict.has_conflict ? (
                  <div className="text-sm font-semibold text-book-accent">
                    存在冲突：last_synced_chapter={conflict.last_synced_chapter} &gt; max_chapter={conflict.max_available_chapter}
                  </div>
                ) : (
                  <div className="text-sm font-semibold text-book-primary">无冲突</div>
                )}
                <div className="mt-2 text-xs leading-relaxed text-book-text-muted">
                  可回滚快照：{(conflict.available_snapshot_chapters || []).join(', ') || '（无）'}
                </div>
              </NovelDialogSurface>
            ) : (
              <NovelDialogSurface className="text-sm text-book-text-muted">
                暂无数据。
              </NovelDialogSurface>
            )}
          </NovelDialogSection>

          <NovelDialogSection
            eyebrow="Diff"
            title="状态差异"
            description="对比两个章节节点之间的属性变化，判断档案演化是否符合剧情推进。"
          >
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <BookInput
                  label="from_chapter（0 表示空状态）"
                  type="number"
                  min={0}
                  value={diffFrom}
                  onChange={(e) => onChangeDiffFrom(Math.max(0, Number(e.target.value) || 0))}
                />
                <BookInput
                  label="to_chapter"
                  type="number"
                  min={1}
                  value={diffTo}
                  onChange={(e) => onChangeDiffTo(Math.max(1, Number(e.target.value) || 1))}
                />
              </div>
              <div className="flex justify-end">
                <BookButton variant="primary" onClick={onRunDiff} disabled={diffLoading}>
                  <GitCompare size={16} className={`mr-2 ${diffLoading ? 'animate-pulse' : ''}`} />
                  {diffLoading ? '对比中…' : '生成 Diff'}
                </BookButton>
              </div>

              {diffResult ? (
                <NovelDialogSurface>
                  <div className="text-sm text-book-text-muted">
                    {diffResult.has_changes ? '有变化' : '无变化'} · from {diffResult.from_chapter} → to {diffResult.to_chapter}
                  </div>
                  <pre className={`mt-3 ${codeBlockClassName}`}>
                    {JSON.stringify(diffResult.categories || {}, null, 2)}
                  </pre>
                </NovelDialogSurface>
              ) : null}
            </div>
          </NovelDialogSection>

          <NovelDialogSection
            eyebrow="Rollback"
            title="回滚快照"
            description="这是破坏性操作，会删除目标章节之后的全部快照，只在同步链明显出错时使用。"
          >
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto]">
              <BookInput
                label="目标章节"
                type="number"
                min={1}
                value={rollbackTarget}
                onChange={(e) => onChangeRollbackTarget(Math.max(1, Number(e.target.value) || 1))}
              />
              <div className="flex items-end justify-end">
                <BookButton variant="primary" onClick={onRunRollback} disabled={rollbackLoading}>
                  <Database size={16} className={`mr-2 ${rollbackLoading ? 'animate-pulse' : ''}`} />
                  {rollbackLoading ? '回滚中…' : '回滚'}
                </BookButton>
              </div>
            </div>
          </NovelDialogSection>
        </NovelDialogStack>
      ) : null}

      {activeTab === 'implicit' ? (
        <NovelDialogSection
          eyebrow="Implicit Attributes"
          title="隐性属性分析"
          description="用于判断某个隐性属性是否达到更新阈值，并请求模型给出新的建议值。"
        >
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <BookInput
                label="attribute_key"
                value={implicitKey}
                onChange={(e) => onChangeImplicitKey(e.target.value)}
                placeholder="例如：勇气 / 信念 / 道德底线"
              />
              <BookInput
                label="window"
                type="number"
                min={1}
                max={50}
                value={implicitWindow}
                onChange={(e) => onChangeImplicitWindow(Math.max(1, Math.min(50, Number(e.target.value) || 10)))}
              />
            </div>
            <div className="flex flex-wrap justify-end gap-2">
              <BookButton variant="secondary" onClick={onFetchImplicitStats} disabled={implicitStatsLoading}>
                {implicitStatsLoading ? '统计中…' : '统计'}
              </BookButton>
              <BookButton variant="primary" onClick={onFetchImplicitCheck} disabled={implicitCheckLoading}>
                <Sparkles size={16} className={`mr-2 ${implicitCheckLoading ? 'animate-pulse' : ''}`} />
                {implicitCheckLoading ? '生成中…' : 'LLM建议'}
              </BookButton>
            </div>

            {implicitStats ? (
              <NovelDialogSurface>
                <div className="text-xs text-book-text-muted">
                  total={implicitStats.total} · conform={implicitStats.conform_count} · non={implicitStats.non_conform_count} · rate={Math.round((implicitStats.conform_rate || 0) * 100)}%
                </div>
                <div className="mt-2 text-sm font-semibold">
                  {implicitStats.threshold_reached ? (
                    <span className="text-book-accent">已达到更新阈值</span>
                  ) : (
                    <span className="text-book-text-muted">未达到更新阈值</span>
                  )}
                </div>
              </NovelDialogSurface>
            ) : null}

            {implicitCheck ? (
              <NovelDialogSurface>
                <div className="text-sm text-book-text-muted">
                  决策：<span className="font-semibold text-book-text-main">{implicitCheck.decision}</span>
                </div>
                <div className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-book-text-muted">
                  理由：{implicitCheck.reasoning}
                </div>
                {implicitCheck.suggested_new_value !== undefined ? (
                  <pre className={`mt-3 ${codeBlockClassName}`}>
                    {JSON.stringify(implicitCheck.suggested_new_value, null, 2)}
                  </pre>
                ) : null}
                {implicitCheck.evidence_summary ? (
                  <div className="mt-2 whitespace-pre-wrap border-l-2 border-book-border pl-3 text-xs leading-relaxed text-book-text-muted">
                    证据：{implicitCheck.evidence_summary}
                  </div>
                ) : null}
              </NovelDialogSurface>
            ) : null}
          </div>
        </NovelDialogSection>
      ) : null}
    </NovelDialogStack>
  );
};
