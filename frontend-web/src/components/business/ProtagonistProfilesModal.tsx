import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Modal } from '../ui/Modal';
import { BookButton } from '../ui/BookButton';
import { useToast } from '../feedback/Toast';
import { confirmDialog } from '../feedback/ConfirmDialog';
import {
  NovelDialogIntro,
  NovelDialogMetric,
  NovelDialogMetricGrid,
  NovelDialogStack,
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
import { novelsApi } from '../../api/novels';
import { ProtagonistProfilesSidebar } from './protagonist-profiles-modal/ProtagonistProfilesSidebar';
import { ProtagonistProfilesWorkspace } from './protagonist-profiles-modal/ProtagonistProfilesWorkspace';
import {
  DetailTab,
  extractIdentityFromAttributes,
  normalizeCharacterName,
} from './protagonist-profiles-modal/shared';

interface ProtagonistProfilesModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  currentChapterNumber?: number;
}

export const ProtagonistProfilesModal: React.FC<ProtagonistProfilesModalProps> = ({
  isOpen,
  onClose,
  projectId,
  currentChapterNumber,
}) => {
  const { addToast } = useToast();

  const [profiles, setProfiles] = useState<ProtagonistProfileSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [characterIdentityByName, setCharacterIdentityByName] = useState<Record<string, string>>({});
  const [identityExpanded, setIdentityExpanded] = useState(false);

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
    if (!isOpen) {
      setIdentityExpanded(false);
    }
  }, [isOpen]);

  useEffect(() => {
    setIdentityExpanded(false);
  }, [selectedName]);

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;

    const loadCharacterIdentity = async () => {
      try {
        const project = await novelsApi.get(projectId);
        const chars = Array.isArray(project?.blueprint?.characters) ? project.blueprint.characters : [];
        const next: Record<string, string> = {};
        for (const c of chars) {
          const name = normalizeCharacterName((c as any)?.name);
          const identity = normalizeCharacterName((c as any)?.identity);
          if (name && identity) next[name] = identity;
        }
        if (!cancelled) setCharacterIdentityByName(next);
      } catch (e) {
        console.error(e);
        if (!cancelled) setCharacterIdentityByName({});
      }
    };

    void loadCharacterIdentity();
    return () => {
      cancelled = true;
    };
  }, [isOpen, projectId]);

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
      message: `确认回滚角色档案到第 ${target} 章？\n注意：会删除该章节之后的所有快照。`,
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
      addToast('角色档案已创建', 'success');
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
      title: '删除角色档案',
      message: `确定要删除角色档案「${name}」吗？`,
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
  const selectedIdentity = useMemo(() => {
    const name = selectedName.trim();
    if (!name) return null;
    const fromBlueprint = normalizeCharacterName(characterIdentityByName[name]);
    if (fromBlueprint) return fromBlueprint;
    const fromAttributes = extractIdentityFromAttributes(detail?.explicit_attributes);
    return fromAttributes;
  }, [characterIdentityByName, detail?.explicit_attributes, selectedName]);

  useEffect(() => {
    if (!selectedIdentity) {
      setIdentityExpanded(false);
    }
  }, [selectedIdentity]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="角色档案"
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
          title="角色档案工作台"
          description="这里集中管理角色的属性、行为、快照与回滚链路。建议按“同步章节 -> 检查属性 -> 审核异常”这条路径进行日常维护。"
        >
          <div className="flex flex-wrap gap-2">
            <span className="story-pill">档案数 {profiles.length}</span>
            <span className="story-pill">{selectedName ? `当前档案：${selectedName}` : '待选择档案'}</span>
            {selectedName && selectedIdentity ? (
              <span className="story-pill max-w-[14rem] overflow-hidden" title={selectedIdentity}>
                <span className="truncate">{`身份：${selectedIdentity}`}</span>
              </span>
            ) : null}
            <span className="story-pill">同步目标 第 {Math.max(1, Number(syncChapter) || 1)} 章</span>
          </div>
        </NovelDialogIntro>

        <NovelDialogMetricGrid className="xl:grid-cols-4">
          <NovelDialogMetric label="档案总数" value={profiles.length} note="左侧列表管理当前项目的所有角色档案。" />
          <NovelDialogMetric label="当前档案" value={selectedName || '未选择'} note="右侧工作区只显示当前选中角色的数据。" />
          <NovelDialogMetric label="最后同步" value={selectedLastSyncedChapter} note="表示这份档案最后一次与正文对齐到的章节。" />
          <NovelDialogMetric
            label="属性规模"
            value={`${attributeCounts.explicit}/${attributeCounts.implicit}/${attributeCounts.social}`}
            note="显性 / 隐性 / 社会属性数量。"
          />
        </NovelDialogMetricGrid>

        <div className="grid h-full min-h-0 gap-4 lg:grid-cols-[300px_minmax(0,1fr)]">
          <ProtagonistProfilesSidebar
            profiles={profiles}
            loading={loading}
            createName={createName}
            creating={creating}
            selectedName={selectedName}
            characterIdentityByName={characterIdentityByName}
            onRefreshList={loadList}
            onChangeCreateName={setCreateName}
            onCreate={handleCreate}
            onSelectName={setSelectedName}
          />

          <div className="min-h-0 overflow-auto custom-scrollbar pr-1">
            <ProtagonistProfilesWorkspace
              selectedName={selectedName}
              selectedIdentity={selectedIdentity}
              identityExpanded={identityExpanded}
              selectedLastSyncedChapter={selectedLastSyncedChapter}
              detailLoading={detailLoading}
              detail={detail}
              syncChapter={syncChapter}
              syncing={syncing}
              activeTab={activeTab}
              historyLoading={historyLoading}
              history={history}
              historyStart={historyStart}
              historyEnd={historyEnd}
              historyCategory={historyCategory}
              behaviorsLoading={behaviorsLoading}
              behaviors={behaviors}
              behaviorsChapter={behaviorsChapter}
              behaviorsLimit={behaviorsLimit}
              marksLoading={marksLoading}
              marks={marks}
              marksCategory={marksCategory}
              markActionKey={markActionKey}
              snapshotsLoading={snapshotsLoading}
              snapshots={snapshots}
              snapshotDetailLoading={snapshotDetailLoading}
              snapshotDetail={snapshotDetail}
              conflictLoading={conflictLoading}
              conflict={conflict}
              diffFrom={diffFrom}
              diffTo={diffTo}
              diffLoading={diffLoading}
              diffResult={diffResult}
              rollbackTarget={rollbackTarget}
              rollbackLoading={rollbackLoading}
              implicitKey={implicitKey}
              implicitWindow={implicitWindow}
              implicitStatsLoading={implicitStatsLoading}
              implicitStats={implicitStats}
              implicitCheckLoading={implicitCheckLoading}
              implicitCheck={implicitCheck}
              onToggleIdentityExpanded={() => setIdentityExpanded((prev) => !prev)}
              onCloseIdentityExpanded={() => setIdentityExpanded(false)}
              onDelete={handleDelete}
              onRefreshDetail={loadDetail}
              onChangeSyncChapter={setSyncChapter}
              onSync={handleSync}
              onChangeActiveTab={setActiveTab}
              onRefreshHistory={refreshHistory}
              onChangeHistoryStart={setHistoryStart}
              onChangeHistoryEnd={setHistoryEnd}
              onChangeHistoryCategory={setHistoryCategory}
              onRefreshBehaviors={refreshBehaviors}
              onChangeBehaviorsChapter={setBehaviorsChapter}
              onChangeBehaviorsLimit={setBehaviorsLimit}
              onRefreshMarks={refreshMarks}
              onChangeMarksCategory={setMarksCategory}
              onExecuteDeletion={handleExecuteDeletion}
              onResetMarks={handleResetMarks}
              onRefreshSnapshots={refreshSnapshots}
              onLoadSnapshot={loadSnapshot}
              onRefreshConflict={refreshConflict}
              onChangeDiffFrom={setDiffFrom}
              onChangeDiffTo={setDiffTo}
              onRunDiff={runDiff}
              onChangeRollbackTarget={setRollbackTarget}
              onRunRollback={runRollback}
              onChangeImplicitKey={setImplicitKey}
              onChangeImplicitWindow={setImplicitWindow}
              onFetchImplicitStats={fetchImplicitStats}
              onFetchImplicitCheck={fetchImplicitCheck}
            />
          </div>
        </div>
      </NovelDialogStack>
    </Modal>
  );
};
