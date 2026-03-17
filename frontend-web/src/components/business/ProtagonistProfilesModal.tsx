import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Modal } from '../ui/Modal';
import { BookButton } from '../ui/BookButton';
import { BookInput } from '../ui/BookInput';
import { useToast } from '../feedback/Toast';
import { confirmDialog } from '../feedback/ConfirmDialog';
import {
  NovelDialogIntro,
  NovelDialogMetric,
  NovelDialogMetricGrid,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from './novel/NovelDialogPrimitives';
import {
  protagonistApi,
  ProtagonistProfileResponse,
  ProtagonistProfileSummary,
  AttributeCategory,
  AttributeChangeResponse,
  BehaviorRecordResponse,
  DeletionMarkResponse,
  SnapshotListResponse,
  SnapshotResponse,
  DiffResponse,
  ProfileConflictCheck,
  ImplicitStatsResponse,
  ImplicitCheckResponse,
} from '../../api/protagonist';
import {
  User,
  RefreshCw,
  Plus,
  Trash2,
  Database,
  ScrollText,
  Activity,
  Camera,
  GitCompare,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';

interface ProtagonistProfilesModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  currentChapterNumber?: number;
}

type DetailTab = 'attributes' | 'history' | 'behaviors' | 'deletions' | 'snapshots' | 'diff' | 'implicit';

const DETAIL_TABS: Array<{
  id: DetailTab;
  label: string;
  description: string;
  icon: LucideIcon;
}> = [
  {
    id: 'attributes',
    label: '属性',
    description: '查看主角当前的显性、隐性和社会属性快照。',
    icon: User,
  },
  {
    id: 'history',
    label: '历史',
    description: '筛选属性变更历史，追踪每次更新的章节来源和证据。',
    icon: ScrollText,
  },
  {
    id: 'behaviors',
    label: '行为',
    description: '回看被抽取出的行为记录、标签和原文证据。',
    icon: Activity,
  },
  {
    id: 'deletions',
    label: '删除',
    description: '核对删除候选的累计标记、执行情况和重置状态。',
    icon: Trash2,
  },
  {
    id: 'snapshots',
    label: '快照',
    description: '浏览按章节沉淀的状态快照，并对具体章节快照做抽样检查。',
    icon: Camera,
  },
  {
    id: 'diff',
    label: 'Diff/回滚',
    description: '执行冲突检测、章节间状态对比，并在必要时回滚快照。',
    icon: GitCompare,
  },
  {
    id: 'implicit',
    label: '隐性',
    description: '评估隐性属性是否达到更新阈值，并请求 LLM 给出修订建议。',
    icon: Sparkles,
  },
];

const selectClassName = `
  book-control book-select mt-1 w-full rounded-2xl border px-4 py-3
  text-sm text-book-text-main transition-all duration-200
  focus:border-book-primary/45 focus:outline-none focus:ring-2 focus:ring-book-primary/18
`;

const codeBlockClassName = `
  max-h-[20rem] overflow-auto whitespace-pre-wrap rounded-[22px] border border-book-border/45
  bg-book-bg-paper/78 p-4 font-mono text-xs text-book-text-main
  shadow-[inset_0_1px_0_rgba(255,255,255,0.24)]
`;

const formatDateTime = (value: string) => {
  if (!value) return '未知时间';
  const time = new Date(value);
  return Number.isNaN(time.getTime()) ? value : time.toLocaleString();
};

export const ProtagonistProfilesModal: React.FC<ProtagonistProfilesModalProps> = ({
  isOpen,
  onClose,
  projectId,
  currentChapterNumber,
}) => {
  const { addToast } = useToast();

  const [profiles, setProfiles] = useState<ProtagonistProfileSummary[]>([]);
  const [loading, setLoading] = useState(false);

  const [selectedName, setSelectedName] = useState<string>('');
  const [detail, setDetail] = useState<ProtagonistProfileResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [createName, setCreateName] = useState('');
  const [creating, setCreating] = useState(false);

  const [syncing, setSyncing] = useState(false);
  const [syncChapter, setSyncChapter] = useState<number>(currentChapterNumber || 1);

  const [activeTab, setActiveTab] = useState<DetailTab>('attributes');

  // 变更历史
  const [historyLoading, setHistoryLoading] = useState(false);
  const [history, setHistory] = useState<AttributeChangeResponse[]>([]);
  const [historyStart, setHistoryStart] = useState<number | ''>('');
  const [historyEnd, setHistoryEnd] = useState<number | ''>('');
  const [historyCategory, setHistoryCategory] = useState<AttributeCategory | ''>('');

  // 行为记录
  const [behaviorsLoading, setBehaviorsLoading] = useState(false);
  const [behaviors, setBehaviors] = useState<BehaviorRecordResponse[]>([]);
  const [behaviorsChapter, setBehaviorsChapter] = useState<number | ''>('');
  const [behaviorsLimit, setBehaviorsLimit] = useState<number>(20);

  // 删除标记
  const [marksLoading, setMarksLoading] = useState(false);
  const [marks, setMarks] = useState<DeletionMarkResponse[]>([]);
  const [marksCategory, setMarksCategory] = useState<AttributeCategory | ''>('');
  const [markActionKey, setMarkActionKey] = useState<string | null>(null);

  // 快照 / diff / 回滚
  const [snapshotsLoading, setSnapshotsLoading] = useState(false);
  const [snapshots, setSnapshots] = useState<SnapshotListResponse | null>(null);
  const [snapshotDetailLoading, setSnapshotDetailLoading] = useState(false);
  const [snapshotDetail, setSnapshotDetail] = useState<SnapshotResponse | null>(null);

  const [diffLoading, setDiffLoading] = useState(false);
  const [diffFrom, setDiffFrom] = useState<number>(0);
  const [diffTo, setDiffTo] = useState<number>(currentChapterNumber || 1);
  const [diffResult, setDiffResult] = useState<DiffResponse | null>(null);

  const [rollbackLoading, setRollbackLoading] = useState(false);
  const [rollbackTarget, setRollbackTarget] = useState<number>(Math.max(0, (currentChapterNumber || 1) - 1));

  // 冲突检测
  const [conflictLoading, setConflictLoading] = useState(false);
  const [conflict, setConflict] = useState<ProfileConflictCheck | null>(null);

  // 隐性属性统计/建议
  const [implicitKey, setImplicitKey] = useState('');
  const [implicitWindow, setImplicitWindow] = useState<number>(10);
  const [implicitStatsLoading, setImplicitStatsLoading] = useState(false);
  const [implicitStats, setImplicitStats] = useState<ImplicitStatsResponse | null>(null);
  const [implicitCheckLoading, setImplicitCheckLoading] = useState(false);
  const [implicitCheck, setImplicitCheck] = useState<ImplicitCheckResponse | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setSyncChapter(currentChapterNumber || 1);
    setDiffTo(currentChapterNumber || 1);
    setRollbackTarget(Math.max(1, (currentChapterNumber || 1) - 1));
  }, [currentChapterNumber, isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    setActiveTab('attributes');
    setHistory([]);
    setBehaviors([]);
    setMarks([]);
    setSnapshots(null);
    setSnapshotDetail(null);
    setDiffResult(null);
    setConflict(null);
    setImplicitStats(null);
    setImplicitCheck(null);
  }, [isOpen, selectedName]);

  const loadList = useCallback(async () => {
    setLoading(true);
    try {
      const list = await protagonistApi.listProfiles(projectId);
      setProfiles(list || []);
      if (!selectedName && list && list.length > 0) {
        setSelectedName(list[0].character_name);
      }
    } catch (e) {
      console.error(e);
      setProfiles([]);
    } finally {
      setLoading(false);
    }
  }, [projectId, selectedName]);

  useEffect(() => {
    if (!isOpen) return;
    loadList();
  }, [isOpen, loadList]);

  const loadDetail = useCallback(async () => {
    const name = selectedName.trim();
    if (!name) {
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    try {
      const data = await protagonistApi.getProfile(projectId, name);
      setDetail(data);
    } catch (e) {
      console.error(e);
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, [projectId, selectedName]);

  useEffect(() => {
    if (!isOpen) return;
    loadDetail();
  }, [isOpen, loadDetail]);

  const selectedSummary = useMemo(() => {
    return profiles.find((p) => p.character_name === selectedName) || null;
  }, [profiles, selectedName]);

  const refreshConflict = useCallback(async () => {
    const name = selectedName.trim();
    if (!name) return;
    setConflictLoading(true);
    try {
      const res = await protagonistApi.conflictCheck(projectId, name);
      setConflict(res);
    } catch (e) {
      console.error(e);
      setConflict(null);
    } finally {
      setConflictLoading(false);
    }
  }, [projectId, selectedName]);

  const refreshHistory = useCallback(async () => {
    const name = selectedName.trim();
    if (!name) return;
    setHistoryLoading(true);
    try {
      const res = await protagonistApi.getHistory(projectId, name, {
        startChapter: typeof historyStart === 'number' ? historyStart : undefined,
        endChapter: typeof historyEnd === 'number' ? historyEnd : undefined,
        category: historyCategory || undefined,
      });
      setHistory(res || []);
    } catch (e) {
      console.error(e);
      setHistory([]);
      addToast('获取变更历史失败', 'error');
    } finally {
      setHistoryLoading(false);
    }
  }, [addToast, historyCategory, historyEnd, historyStart, projectId, selectedName]);

  const refreshBehaviors = useCallback(async () => {
    const name = selectedName.trim();
    if (!name) return;
    setBehaviorsLoading(true);
    try {
      const res = await protagonistApi.getBehaviors(projectId, name, {
        chapter: typeof behaviorsChapter === 'number' ? behaviorsChapter : undefined,
        limit: behaviorsLimit,
      });
      setBehaviors(res || []);
    } catch (e) {
      console.error(e);
      setBehaviors([]);
      addToast('获取行为记录失败', 'error');
    } finally {
      setBehaviorsLoading(false);
    }
  }, [addToast, behaviorsChapter, behaviorsLimit, projectId, selectedName]);

  const refreshMarks = useCallback(async () => {
    const name = selectedName.trim();
    if (!name) return;
    setMarksLoading(true);
    try {
      const res = await protagonistApi.getDeletionMarks(projectId, name, marksCategory || undefined);
      setMarks(res || []);
    } catch (e) {
      console.error(e);
      setMarks([]);
      addToast('获取删除标记失败', 'error');
    } finally {
      setMarksLoading(false);
    }
  }, [addToast, marksCategory, projectId, selectedName]);

  const handleExecuteDeletion = useCallback(async (category: AttributeCategory, key: string) => {
    const name = selectedName.trim();
    if (!name) return;
    const actionKey = `exec:${category}:${key}`;
    setMarkActionKey(actionKey);
    try {
      const res = await protagonistApi.executeDeletion(projectId, name, category, key);
      addToast(res?.message || '已执行删除', 'success');
      await loadDetail();
      await refreshMarks();
    } catch (e: any) {
      console.error(e);
      const msg = e?.response?.data?.detail || '执行删除失败';
      addToast(String(msg), 'error');
    } finally {
      setMarkActionKey(null);
    }
  }, [addToast, loadDetail, projectId, refreshMarks, selectedName]);

  const handleResetMarks = useCallback(async (category: AttributeCategory, key: string) => {
    const name = selectedName.trim();
    if (!name) return;
    const actionKey = `reset:${category}:${key}`;
    setMarkActionKey(actionKey);
    try {
      const res = await protagonistApi.resetDeletionMarks(projectId, name, category, key);
      addToast(res?.message || '已重置删除标记', res?.success ? 'success' : 'info');
      await refreshMarks();
    } catch (e) {
      console.error(e);
      addToast('重置删除标记失败', 'error');
    } finally {
      setMarkActionKey(null);
    }
  }, [addToast, projectId, refreshMarks, selectedName]);

  const refreshSnapshots = useCallback(async () => {
    const name = selectedName.trim();
    if (!name) return;
    setSnapshotsLoading(true);
    try {
      const res = await protagonistApi.getSnapshots(projectId, name);
      setSnapshots(res);
    } catch (e) {
      console.error(e);
      setSnapshots(null);
      addToast('获取快照列表失败', 'error');
    } finally {
      setSnapshotsLoading(false);
    }
  }, [addToast, projectId, selectedName]);

  const loadSnapshot = useCallback(async (chapter: number) => {
    const name = selectedName.trim();
    if (!name) return;
    setSnapshotDetailLoading(true);
    try {
      const res = await protagonistApi.getSnapshotAtChapter(projectId, name, chapter);
      setSnapshotDetail(res);
    } catch (e) {
      console.error(e);
      setSnapshotDetail(null);
      addToast('获取快照失败', 'error');
    } finally {
      setSnapshotDetailLoading(false);
    }
  }, [addToast, projectId, selectedName]);

  const runDiff = useCallback(async () => {
    const name = selectedName.trim();
    if (!name) return;
    setDiffLoading(true);
    try {
      const res = await protagonistApi.diffBetweenChapters(projectId, name, diffFrom, diffTo);
      setDiffResult(res);
    } catch (e) {
      console.error(e);
      setDiffResult(null);
      addToast('diff 获取失败', 'error');
    } finally {
      setDiffLoading(false);
    }
  }, [addToast, diffFrom, diffTo, projectId, selectedName]);

  const runRollback = useCallback(async () => {
    const name = selectedName.trim();
    if (!name) return;
    const target = Math.max(1, Number(rollbackTarget) || 1);
    const ok = await confirmDialog({
      title: '回滚确认',
      message: `确认回滚主角档案到第 ${target} 章？\n注意：会删除该章节之后的所有快照。`,
      confirmText: '回滚',
      dialogType: 'danger',
    });
    if (!ok) return;
    setRollbackLoading(true);
    try {
      const res = await protagonistApi.rollbackToChapter(projectId, name, target);
      addToast(res.message || '回滚完成', res.success ? 'success' : 'error');
      await loadList();
      await loadDetail();
      await refreshSnapshots();
      await refreshConflict();
    } catch (e) {
      console.error(e);
      addToast('回滚失败', 'error');
    } finally {
      setRollbackLoading(false);
    }
  }, [addToast, loadDetail, loadList, projectId, refreshConflict, refreshSnapshots, rollbackTarget, selectedName]);

  const fetchImplicitStats = useCallback(async () => {
    const name = selectedName.trim();
    const key = implicitKey.trim();
    if (!name || !key) {
      addToast('请输入隐性属性键名', 'error');
      return;
    }
    setImplicitStatsLoading(true);
    try {
      const res = await protagonistApi.getImplicitStats(projectId, name, key, implicitWindow);
      setImplicitStats(res);
      addToast('统计已更新', 'success');
    } catch (e) {
      console.error(e);
      setImplicitStats(null);
      addToast('统计失败', 'error');
    } finally {
      setImplicitStatsLoading(false);
    }
  }, [addToast, implicitKey, implicitWindow, projectId, selectedName]);

  const fetchImplicitCheck = useCallback(async () => {
    const name = selectedName.trim();
    const key = implicitKey.trim();
    if (!name || !key) {
      addToast('请输入隐性属性键名', 'error');
      return;
    }
    setImplicitCheckLoading(true);
    try {
      const res = await protagonistApi.checkImplicitUpdate(projectId, name, key);
      setImplicitCheck(res);
      addToast('LLM 建议已生成', 'success');
    } catch (e: any) {
      console.error(e);
      setImplicitCheck(null);
      const msg = e?.response?.data?.detail || 'LLM 建议生成失败';
      addToast(String(msg), 'error');
    } finally {
      setImplicitCheckLoading(false);
    }
  }, [addToast, implicitKey, projectId, selectedName]);

  useEffect(() => {
    if (!isOpen) return;
    if (!selectedName.trim()) return;

    if (activeTab === 'history') refreshHistory();
    if (activeTab === 'behaviors') refreshBehaviors();
    if (activeTab === 'deletions') refreshMarks();
    if (activeTab === 'snapshots') refreshSnapshots();
    if (activeTab === 'diff') refreshConflict();
  }, [activeTab, isOpen, refreshBehaviors, refreshConflict, refreshHistory, refreshMarks, refreshSnapshots, selectedName]);

  const handleCreate = async () => {
    const name = createName.trim();
    if (!name) {
      addToast('请输入角色名', 'error');
      return;
    }
    setCreating(true);
    try {
      await protagonistApi.createProfile(projectId, name);
      addToast('主角档案已创建', 'success');
      setCreateName('');
      setSelectedName(name);
      await loadList();
      await loadDetail();
    } catch (e) {
      console.error(e);
      addToast('创建失败', 'error');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async () => {
    const name = selectedName.trim();
    if (!name) return;
    const ok = await confirmDialog({
      title: '删除主角档案',
      message: `确定要删除主角档案「${name}」吗？`,
      confirmText: '删除',
      dialogType: 'danger',
    });
    if (!ok) return;
    try {
      await protagonistApi.deleteProfile(projectId, name);
      addToast('已删除', 'success');
      setSelectedName('');
      setDetail(null);
      await loadList();
    } catch (e) {
      console.error(e);
      addToast('删除失败', 'error');
    }
  };

  const handleSync = async () => {
    const name = selectedName.trim();
    if (!name) {
      addToast('请先选择一个档案', 'error');
      return;
    }
    const ch = Math.max(1, Number(syncChapter) || 1);
    setSyncing(true);
    try {
      const res = await protagonistApi.syncProfile(projectId, name, ch);
      addToast(`同步完成：应用${res.changes_applied}条变更`, 'success');
      await loadList();
      await loadDetail();
    } catch (e) {
      console.error(e);
      addToast('同步失败（请检查 LLM 配置与后端日志）', 'error');
    } finally {
      setSyncing(false);
    }
  };

  const activeTabMeta = DETAIL_TABS.find((tab) => tab.id === activeTab) || DETAIL_TABS[0];
  const attributeCounts = useMemo(() => {
    return {
      explicit:
        selectedSummary?.attribute_counts?.explicit ?? Object.keys(detail?.explicit_attributes || {}).length,
      implicit:
        selectedSummary?.attribute_counts?.implicit ?? Object.keys(detail?.implicit_attributes || {}).length,
      social:
        selectedSummary?.attribute_counts?.social ?? Object.keys(detail?.social_attributes || {}).length,
    };
  }, [detail, selectedSummary]);
  const selectedLastSyncedChapter = selectedSummary?.last_synced_chapter ?? detail?.last_synced_chapter ?? 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="主角档案"
      maxWidthClassName="max-w-6xl"
      className="max-h-[90vh]"
      footer={
        <div className="flex justify-end">
          <BookButton variant="ghost" onClick={onClose}>关闭</BookButton>
        </div>
      }
    >
      <NovelDialogStack className="h-[75vh]">
        <NovelDialogIntro
          eyebrow="Profile Workspace"
          title="主角档案工作台"
          description="这里集中管理主角的属性、行为、快照与回滚链路。建议按“同步章节 -> 检查属性 -> 审核异常”这条路径进行日常维护。"
        >
          <div className="flex flex-wrap gap-2">
            <span className="story-pill">档案数 {profiles.length}</span>
            <span className="story-pill">{selectedName ? `当前档案：${selectedName}` : '待选择档案'}</span>
            <span className="story-pill">同步目标 第 {Math.max(1, Number(syncChapter) || 1)} 章</span>
          </div>
        </NovelDialogIntro>

        <NovelDialogMetricGrid className="xl:grid-cols-4">
          <NovelDialogMetric label="档案总数" value={profiles.length} note="左侧列表管理当前项目的所有主角档案。" />
          <NovelDialogMetric label="当前档案" value={selectedName || '未选择'} note="右侧工作区只显示当前选中角色的数据。" />
          <NovelDialogMetric label="最后同步" value={selectedLastSyncedChapter} note="表示这份档案最后一次与正文对齐到的章节。" />
          <NovelDialogMetric
            label="属性规模"
            value={`${attributeCounts.explicit}/${attributeCounts.implicit}/${attributeCounts.social}`}
            note="显性 / 隐性 / 社会属性数量。"
          />
        </NovelDialogMetricGrid>

        <div className="grid h-full min-h-0 gap-4 lg:grid-cols-[300px_minmax(0,1fr)]">
          <NovelDialogSection
            eyebrow="Profiles"
            title="档案列表"
            description="创建新档案后可在这里切换、刷新和检查同步边界。"
            className="min-h-0"
            actions={(
              <BookButton variant="ghost" size="sm" onClick={loadList} disabled={loading}>
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
                    onChange={(e) => setCreateName(e.target.value)}
                  />
                  <div className="flex items-end">
                    <BookButton variant="primary" size="sm" onClick={handleCreate} disabled={creating}>
                      <Plus size={14} className="mr-1" />
                      {creating ? '创建中…' : '创建'}
                    </BookButton>
                  </div>
                </div>
              </NovelDialogSurface>

              <div className="min-h-0 flex-1 space-y-2 overflow-auto custom-scrollbar pr-1">
                {profiles.length === 0 && !loading ? (
                  <NovelDialogSurface className="text-sm text-book-text-muted">
                    暂无档案，可在上方输入角色名后创建。
                  </NovelDialogSurface>
                ) : null}

                {profiles.map((profile) => {
                  const active = profile.character_name === selectedName;
                  return (
                    <button
                      key={profile.id}
                      onClick={() => setSelectedName(profile.character_name)}
                      className={`w-full rounded-[22px] border px-4 py-3 text-left transition-all ${
                        active
                          ? 'border-book-primary/40 bg-book-primary/8 shadow-[0_18px_40px_-34px_rgba(121,84,57,0.75)]'
                          : 'border-book-border/45 bg-book-bg/70 hover:border-book-primary/25 hover:bg-book-bg-paper/72'
                      }`}
                    >
                      <div className="truncate text-sm font-semibold text-book-text-main">
                        {profile.character_name}
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

          <div className="min-h-0 overflow-auto custom-scrollbar pr-1">
            {!selectedName ? (
              <NovelDialogIntro
                eyebrow="Profile Detail"
                title="先选择一个主角档案"
                description="右侧工作区会展示当前角色的属性、变更历史、行为记录和快照信息。若当前还没有角色，可先在左侧创建。"
              />
            ) : (
              <NovelDialogStack>
                <NovelDialogSection
                  eyebrow="Profile Overview"
                  title={selectedName}
                  description={`最后同步章节：${selectedLastSyncedChapter}。同步会分析指定章节正文，更新属性、行为与删除候选。`}
                  actions={(
                    <>
                      <BookButton variant="ghost" size="sm" onClick={handleDelete}>
                        <Trash2 size={14} className="mr-1" />
                        删除
                      </BookButton>
                      <BookButton variant="ghost" size="sm" onClick={loadDetail} disabled={detailLoading}>
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
                      onChange={(e) => setSyncChapter(Number(e.target.value) || 1)}
                    />
                    <div className="flex items-end justify-end">
                      <BookButton variant="primary" onClick={handleSync} disabled={syncing}>
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
                          onClick={() => setActiveTab(tab.id)}
                          className={`flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold transition-all ${
                            active
                              ? 'border-book-primary/40 bg-book-primary/8 text-book-primary'
                              : 'border-book-border/45 bg-book-bg/72 text-book-text-main hover:border-book-primary/25'
                          }`}
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
                      <BookButton variant="ghost" size="sm" onClick={refreshHistory} disabled={historyLoading}>
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
                          onChange={(e) => setHistoryStart(e.target.value ? Number(e.target.value) : '')}
                        />
                        <BookInput
                          label="结束章（可选）"
                          type="number"
                          min={1}
                          value={historyEnd}
                          onChange={(e) => setHistoryEnd(e.target.value ? Number(e.target.value) : '')}
                        />
                        <label className="text-sm font-bold text-book-text-sub">
                          类别（可选）
                          <select
                            className={selectClassName}
                            value={historyCategory}
                            onChange={(e) => setHistoryCategory((e.target.value as AttributeCategory) || '')}
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
                      <BookButton variant="ghost" size="sm" onClick={refreshBehaviors} disabled={behaviorsLoading}>
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
                          onChange={(e) => setBehaviorsChapter(e.target.value ? Number(e.target.value) : '')}
                        />
                        <BookInput
                          label="返回数量"
                          type="number"
                          min={1}
                          max={100}
                          value={behaviorsLimit}
                          onChange={(e) => setBehaviorsLimit(Math.max(1, Math.min(100, Number(e.target.value) || 20)))}
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
                      <BookButton variant="ghost" size="sm" onClick={refreshMarks} disabled={marksLoading}>
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
                          onChange={(e) => setMarksCategory((e.target.value as AttributeCategory) || '')}
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
                                      onClick={() => handleExecuteDeletion(category, key)}
                                      disabled={disabled || item.is_executed}
                                      title="达到阈值后可执行删除"
                                    >
                                      执行
                                    </BookButton>
                                    <BookButton
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => handleResetMarks(category, key)}
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
                      <BookButton variant="ghost" size="sm" onClick={refreshSnapshots} disabled={snapshotsLoading}>
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
                              onClick={() => loadSnapshot(snapshot.chapter_number)}
                              className="rounded-[22px] border border-book-border/45 bg-book-bg/72 px-4 py-3 text-left transition-all hover:border-book-primary/25 hover:bg-book-bg-paper/72"
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
                        <BookButton variant="ghost" size="sm" onClick={refreshConflict} disabled={conflictLoading}>
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
                            onChange={(e) => setDiffFrom(Math.max(0, Number(e.target.value) || 0))}
                          />
                          <BookInput
                            label="to_chapter"
                            type="number"
                            min={1}
                            value={diffTo}
                            onChange={(e) => setDiffTo(Math.max(1, Number(e.target.value) || 1))}
                          />
                        </div>
                        <div className="flex justify-end">
                          <BookButton variant="primary" onClick={runDiff} disabled={diffLoading}>
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
                          onChange={(e) => setRollbackTarget(Math.max(1, Number(e.target.value) || 1))}
                        />
                        <div className="flex items-end justify-end">
                          <BookButton variant="primary" onClick={runRollback} disabled={rollbackLoading}>
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
                          onChange={(e) => setImplicitKey(e.target.value)}
                          placeholder="例如：勇气 / 信念 / 道德底线"
                        />
                        <BookInput
                          label="window"
                          type="number"
                          min={1}
                          max={50}
                          value={implicitWindow}
                          onChange={(e) => setImplicitWindow(Math.max(1, Math.min(50, Number(e.target.value) || 10)))}
                        />
                      </div>
                      <div className="flex flex-wrap justify-end gap-2">
                        <BookButton variant="secondary" onClick={fetchImplicitStats} disabled={implicitStatsLoading}>
                          {implicitStatsLoading ? '统计中…' : '统计'}
                        </BookButton>
                        <BookButton variant="primary" onClick={fetchImplicitCheck} disabled={implicitCheckLoading}>
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
            )}
          </div>
        </div>
      </NovelDialogStack>
    </Modal>
  );
};
