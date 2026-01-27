import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Modal } from '../ui/Modal';
import { BookButton } from '../ui/BookButton';
import { BookCard } from '../ui/BookCard';
import { BookInput } from '../ui/BookInput';
import { useToast } from '../feedback/Toast';
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
import { User, RefreshCw, Plus, Trash2, Database, ScrollText, Activity, ShieldAlert, Camera, GitCompare, Sparkles } from 'lucide-react';

interface ProtagonistProfilesModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  currentChapterNumber?: number;
}

type DetailTab = 'attributes' | 'history' | 'behaviors' | 'deletions' | 'snapshots' | 'diff' | 'implicit';

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
    if (!confirm(`确认回滚主角档案到第 ${target} 章？\n注意：会删除该章节之后的所有快照。`)) return;
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
    if (!confirm(`确定要删除主角档案「${name}」吗？`)) return;
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
      <div className="grid grid-cols-[280px_1fr] gap-4 h-[75vh]">
        <div className="space-y-3 min-w-0">
          <BookCard className="p-3">
            <div className="flex items-center justify-between gap-2">
              <div className="font-bold text-book-text-main flex items-center gap-2">
                <User size={16} className="text-book-primary" />
                档案列表
              </div>
              <BookButton variant="ghost" size="sm" onClick={loadList} disabled={loading}>
                <RefreshCw size={14} className={`mr-1 ${loading ? 'animate-spin' : ''}`} />
                刷新
              </BookButton>
            </div>

            <div className="mt-3 flex gap-2">
              <input
                className="flex-1 px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                placeholder="新建：输入角色名"
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
              />
              <BookButton variant="primary" size="sm" onClick={handleCreate} disabled={creating}>
                <Plus size={14} className="mr-1" />
                {creating ? '创建中…' : '创建'}
              </BookButton>
            </div>
          </BookCard>

          <div className="space-y-2 overflow-auto custom-scrollbar pr-1">
            {profiles.length === 0 && !loading && (
              <BookCard className="p-4 text-sm text-book-text-muted">暂无档案，可在上方创建。</BookCard>
            )}
            {profiles.map((p) => {
              const active = p.character_name === selectedName;
              return (
                <button
                  key={p.id}
                  onClick={() => setSelectedName(p.character_name)}
                  className={`w-full text-left rounded-lg border p-3 transition-all ${
                    active
                      ? 'bg-book-primary/5 border-book-primary/30'
                      : 'bg-book-bg border-book-border/40 hover:border-book-primary/20'
                  }`}
                >
                  <div className="font-bold text-book-text-main truncate">{p.character_name}</div>
                  <div className="mt-1 text-[11px] text-book-text-muted font-mono">
                    synced={p.last_synced_chapter} · exp={p.attribute_counts?.explicit ?? 0} · imp={p.attribute_counts?.implicit ?? 0} · soc={p.attribute_counts?.social ?? 0}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="min-w-0 overflow-auto custom-scrollbar pr-1 space-y-4">
          {!selectedName ? (
            <BookCard className="p-6">
              <div className="text-sm text-book-text-muted">请选择左侧档案，或新建一个。</div>
            </BookCard>
          ) : (
            <>
              <BookCard className="p-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="font-bold text-book-text-main truncate">{selectedName}</div>
                    <div className="text-xs text-book-text-muted mt-1">
                      最后同步章节：{selectedSummary?.last_synced_chapter ?? detail?.last_synced_chapter ?? 0}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <BookButton variant="ghost" size="sm" onClick={handleDelete}>
                      <Trash2 size={14} className="mr-1" />
                      删除
                    </BookButton>
                    <BookButton variant="ghost" size="sm" onClick={loadDetail} disabled={detailLoading}>
                      <RefreshCw size={14} className={`mr-1 ${detailLoading ? 'animate-spin' : ''}`} />
                      刷新
                    </BookButton>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3">
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

                <div className="mt-3 text-xs text-book-text-muted leading-relaxed">
                  说明：同步会分析指定章节正文，自动更新主角档案的显性/隐性/社会属性，并记录行为与删除候选（需 LLM 可用）。
                </div>
	              </BookCard>

	              <BookCard className="p-2">
	                <div className="flex gap-1 overflow-x-auto no-scrollbar">
	                  {([
	                    { id: 'attributes', label: '属性', icon: User },
	                    { id: 'history', label: '历史', icon: ScrollText },
	                    { id: 'behaviors', label: '行为', icon: Activity },
	                    { id: 'deletions', label: '删除', icon: Trash2 },
	                    { id: 'snapshots', label: '快照', icon: Camera },
	                    { id: 'diff', label: 'Diff/回滚', icon: GitCompare },
	                    { id: 'implicit', label: '隐性', icon: Sparkles },
	                  ] as Array<{ id: DetailTab; label: string; icon: any }>).map((tab) => {
	                    const Icon = tab.icon;
	                    const active = activeTab === tab.id;
	                    return (
	                      <button
	                        key={tab.id}
	                        onClick={() => setActiveTab(tab.id)}
	                        className={`flex-none px-3 py-2 rounded-lg border text-xs font-bold flex items-center gap-2 transition-all ${
	                          active
	                            ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
	                            : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
	                        }`}
	                      >
	                        <Icon size={14} />
	                        {tab.label}
	                      </button>
	                    );
	                  })}
	                </div>
	              </BookCard>

	              {activeTab === 'attributes' && (
	                <BookCard className="p-4">
	                  <div className="font-bold text-book-text-main mb-3">属性数据</div>
	                  {detailLoading && (
	                    <div className="text-sm text-book-text-muted">加载中…</div>
	                  )}
	                  {!detailLoading && !detail && (
	                    <div className="text-sm text-book-text-muted">暂无详情数据。</div>
	                  )}
	                  {detail && (
	                    <div className="space-y-4">
	                      <div>
	                        <div className="text-xs font-bold text-book-text-sub mb-1">显性属性</div>
	                        <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono bg-book-bg-paper p-3 rounded-lg border border-book-border/40 overflow-auto">
	                          {JSON.stringify(detail.explicit_attributes || {}, null, 2)}
	                        </pre>
	                      </div>
	                      <div>
	                        <div className="text-xs font-bold text-book-text-sub mb-1">隐性属性</div>
	                        <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono bg-book-bg-paper p-3 rounded-lg border border-book-border/40 overflow-auto">
	                          {JSON.stringify(detail.implicit_attributes || {}, null, 2)}
	                        </pre>
	                      </div>
	                      <div>
	                        <div className="text-xs font-bold text-book-text-sub mb-1">社会属性</div>
	                        <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono bg-book-bg-paper p-3 rounded-lg border border-book-border/40 overflow-auto">
	                          {JSON.stringify(detail.social_attributes || {}, null, 2)}
	                        </pre>
	                      </div>
	                    </div>
	                  )}
	                </BookCard>
	              )}

	              {activeTab === 'history' && (
	                <BookCard className="p-4 space-y-3">
	                  <div className="flex items-center justify-between gap-2">
	                    <div className="font-bold text-book-text-main">变更历史</div>
	                    <BookButton variant="ghost" size="sm" onClick={refreshHistory} disabled={historyLoading}>
	                      <RefreshCw size={14} className={`mr-1 ${historyLoading ? 'animate-spin' : ''}`} />
	                      刷新
	                    </BookButton>
	                  </div>

	                  <div className="grid grid-cols-3 gap-3">
	                    <BookInput
	                      label="起始章(可选)"
	                      type="number"
	                      min={1}
	                      value={historyStart}
	                      onChange={(e) => setHistoryStart(e.target.value ? Number(e.target.value) : '')}
	                    />
	                    <BookInput
	                      label="结束章(可选)"
	                      type="number"
	                      min={1}
	                      value={historyEnd}
	                      onChange={(e) => setHistoryEnd(e.target.value ? Number(e.target.value) : '')}
	                    />
	                    <label className="text-sm font-bold text-book-text-sub">
	                      类别(可选)
	                      <select
	                        className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
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
	                    <div className="text-sm text-book-text-muted">暂无变更记录。</div>
	                  ) : (
	                    <div className="space-y-3">
	                      {history.map((h) => (
	                        <div key={h.id} className="p-3 rounded-lg border border-book-border/40 bg-book-bg">
	                          <div className="flex items-center justify-between gap-2">
	                            <div className="font-bold text-book-text-main text-sm">
	                              第 {h.chapter_number} 章 · {h.attribute_category}.{h.attribute_key} · {h.operation}
	                            </div>
	                            <div className="text-[11px] text-book-text-muted font-mono">
	                              {new Date(h.created_at).toLocaleString()}
	                            </div>
	                          </div>
	                          {h.change_description ? (
	                            <div className="mt-2 text-sm text-book-text-main whitespace-pre-wrap leading-relaxed">
	                              {h.change_description}
	                            </div>
	                          ) : null}
	                          {h.event_cause ? (
	                            <div className="mt-2 text-xs text-book-text-muted whitespace-pre-wrap">
	                              触发：{h.event_cause}
	                            </div>
	                          ) : null}
	                          {h.evidence ? (
	                            <div className="mt-2 text-xs text-book-text-muted whitespace-pre-wrap border-l-2 border-book-border pl-2">
	                              证据：{h.evidence}
	                            </div>
	                          ) : null}
	                        </div>
	                      ))}
	                    </div>
	                  )}
	                </BookCard>
	              )}

	              {activeTab === 'behaviors' && (
	                <BookCard className="p-4 space-y-3">
	                  <div className="flex items-center justify-between gap-2">
	                    <div className="font-bold text-book-text-main">行为记录</div>
	                    <BookButton variant="ghost" size="sm" onClick={refreshBehaviors} disabled={behaviorsLoading}>
	                      <RefreshCw size={14} className={`mr-1 ${behaviorsLoading ? 'animate-spin' : ''}`} />
	                      刷新
	                    </BookButton>
	                  </div>

	                  <div className="grid grid-cols-2 gap-3">
	                    <BookInput
	                      label="指定章节(可选)"
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
	                    <div className="text-sm text-book-text-muted">暂无行为记录。</div>
	                  ) : (
	                    <div className="space-y-3">
	                      {behaviors.map((b) => (
	                        <div key={b.id} className="p-3 rounded-lg border border-book-border/40 bg-book-bg">
	                          <div className="flex items-center justify-between gap-2">
	                            <div className="font-bold text-book-text-main text-sm">第 {b.chapter_number} 章</div>
	                            <div className="text-[11px] text-book-text-muted font-mono">
	                              {new Date(b.created_at).toLocaleString()}
	                            </div>
	                          </div>
	                          <div className="mt-2 text-sm text-book-text-main whitespace-pre-wrap leading-relaxed">
	                            {b.behavior_description}
	                          </div>
	                          {Array.isArray(b.behavior_tags) && b.behavior_tags.length > 0 ? (
	                            <div className="mt-2 flex flex-wrap gap-2">
	                              {b.behavior_tags.map((t) => (
	                                <span key={`${b.id}-${t}`} className="text-[11px] px-2 py-0.5 rounded-full border border-book-border/50 bg-book-bg-paper text-book-text-sub">
	                                  {t}
	                                </span>
	                              ))}
	                            </div>
	                          ) : null}
	                          {b.original_text ? (
	                            <div className="mt-2 text-xs text-book-text-muted whitespace-pre-wrap border-l-2 border-book-border pl-2">
	                              原文：{b.original_text}
	                            </div>
	                          ) : null}
	                          {b.classification_results && Object.keys(b.classification_results).length > 0 ? (
	                            <pre className="mt-2 text-xs text-book-text-main whitespace-pre-wrap font-mono bg-book-bg-paper p-2 rounded border border-book-border/40 overflow-auto">
	                              {JSON.stringify(b.classification_results, null, 2)}
	                            </pre>
	                          ) : null}
	                        </div>
	                      ))}
	                    </div>
	                  )}
	                </BookCard>
	              )}

	              {activeTab === 'deletions' && (
	                <BookCard className="p-4 space-y-3">
	                  <div className="flex items-center justify-between gap-2">
	                    <div className="font-bold text-book-text-main">删除标记</div>
	                    <BookButton variant="ghost" size="sm" onClick={refreshMarks} disabled={marksLoading}>
	                      <RefreshCw size={14} className={`mr-1 ${marksLoading ? 'animate-spin' : ''}`} />
	                      刷新
	                    </BookButton>
	                  </div>

	                  <label className="text-sm font-bold text-book-text-sub">
	                    类别筛选
	                    <select
	                      className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
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
	                    <div className="text-sm text-book-text-muted">暂无删除标记。</div>
	                  ) : (
	                    <div className="space-y-3">
	                      {marks.map((m) => {
	                        const cat = m.attribute_category as AttributeCategory;
	                        const key = m.attribute_key;
	                        const execKey = `exec:${cat}:${key}`;
	                        const resetKey = `reset:${cat}:${key}`;
	                        const disabled = markActionKey === execKey || markActionKey === resetKey;
	                        return (
	                          <div key={m.id} className="p-3 rounded-lg border border-book-border/40 bg-book-bg">
	                            <div className="flex items-start justify-between gap-2">
	                              <div className="min-w-0">
	                                <div className="font-bold text-book-text-main text-sm truncate">
	                                  {m.attribute_category}.{m.attribute_key}
	                                </div>
	                                <div className="text-xs text-book-text-muted mt-1">
	                                  连续标记：{m.consecutive_count}/5 · 最后标记章：{m.last_marked_chapter}
	                                  {m.is_executed ? ' · 已执行' : ''}
	                                </div>
	                              </div>
	                              <div className="flex items-center gap-2">
	                                <BookButton
	                                  variant="secondary"
	                                  size="sm"
	                                  onClick={() => handleExecuteDeletion(cat, key)}
	                                  disabled={disabled || m.is_executed}
	                                  title="达到阈值后可执行删除"
	                                >
	                                  执行
	                                </BookButton>
	                                <BookButton
	                                  variant="ghost"
	                                  size="sm"
	                                  onClick={() => handleResetMarks(cat, key)}
	                                  disabled={disabled}
	                                >
	                                  重置
	                                </BookButton>
	                              </div>
	                            </div>
	                            {m.mark_reason ? (
	                              <div className="mt-2 text-xs text-book-text-muted whitespace-pre-wrap">
	                                原因：{m.mark_reason}
	                              </div>
	                            ) : null}
	                            {m.evidence ? (
	                              <div className="mt-2 text-xs text-book-text-muted whitespace-pre-wrap border-l-2 border-book-border pl-2">
	                                证据：{m.evidence}
	                              </div>
	                            ) : null}
	                          </div>
	                        );
	                      })}
	                    </div>
	                  )}
	                </BookCard>
	              )}

	              {activeTab === 'snapshots' && (
	                <BookCard className="p-4 space-y-3">
	                  <div className="flex items-center justify-between gap-2">
	                    <div className="font-bold text-book-text-main">状态快照</div>
	                    <BookButton variant="ghost" size="sm" onClick={refreshSnapshots} disabled={snapshotsLoading}>
	                      <RefreshCw size={14} className={`mr-1 ${snapshotsLoading ? 'animate-spin' : ''}`} />
	                      刷新
	                    </BookButton>
	                  </div>

	                  {snapshots?.snapshots?.length ? (
	                    <div className="grid grid-cols-1 gap-2">
	                      {snapshots.snapshots.map((s) => (
	                        <button
	                          key={`ss-${s.chapter_number}`}
	                          onClick={() => loadSnapshot(s.chapter_number)}
	                          className="text-left p-3 rounded-lg border border-book-border/40 bg-book-bg hover:border-book-primary/20 transition-all"
	                        >
	                          <div className="flex items-center justify-between gap-2">
	                            <div className="font-bold text-book-text-main text-sm">第 {s.chapter_number} 章</div>
	                            <div className="text-[11px] text-book-text-muted font-mono">
	                              Δ{s.changes_in_chapter} · 行为{ s.behaviors_in_chapter }
	                            </div>
	                          </div>
	                          <div className="mt-1 text-[11px] text-book-text-muted font-mono">
	                            exp={s.attribute_counts.explicit} · imp={s.attribute_counts.implicit} · soc={s.attribute_counts.social}
	                          </div>
	                        </button>
	                      ))}
	                    </div>
	                  ) : (
	                    <div className="text-sm text-book-text-muted">
	                      暂无快照。请先按顺序“同步”章节后生成快照。
	                    </div>
	                  )}

	                  {snapshotDetailLoading && (
	                    <div className="text-sm text-book-text-muted">快照加载中…</div>
	                  )}
	                  {snapshotDetail && (
	                    <div className="space-y-3 pt-2">
	                      <div className="font-bold text-book-text-main">快照详情（第 {snapshotDetail.chapter_number} 章）</div>
	                      <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono bg-book-bg-paper p-3 rounded-lg border border-book-border/40 overflow-auto">
	                        {JSON.stringify(snapshotDetail, null, 2)}
	                      </pre>
	                    </div>
	                  )}
	                </BookCard>
	              )}

	              {activeTab === 'diff' && (
	                <div className="space-y-4">
	                  <BookCard className="p-4">
	                    <div className="flex items-center justify-between gap-2">
	                      <div className="font-bold text-book-text-main flex items-center gap-2">
	                        <ShieldAlert size={16} className="text-book-primary" />
	                        冲突检测
	                      </div>
	                      <BookButton variant="ghost" size="sm" onClick={refreshConflict} disabled={conflictLoading}>
	                        <RefreshCw size={14} className={`mr-1 ${conflictLoading ? 'animate-spin' : ''}`} />
	                        刷新
	                      </BookButton>
	                    </div>
	                    {conflict ? (
	                      <div className="mt-2 text-sm text-book-text-main">
	                        {conflict.has_conflict ? (
	                          <div className="text-book-accent font-bold">
	                            存在冲突：last_synced_chapter={conflict.last_synced_chapter} &gt; max_chapter={conflict.max_available_chapter}
	                          </div>
	                        ) : (
	                          <div className="text-book-primary font-bold">无冲突</div>
	                        )}
	                        <div className="mt-2 text-xs text-book-text-muted">
	                          可回滚快照：{(conflict.available_snapshot_chapters || []).join(', ') || '（无）'}
	                        </div>
	                      </div>
	                    ) : (
	                      <div className="mt-2 text-sm text-book-text-muted">暂无数据。</div>
	                    )}
	                  </BookCard>

	                  <BookCard className="p-4 space-y-3">
	                    <div className="font-bold text-book-text-main">Diff（状态差异）</div>
	                    <div className="grid grid-cols-2 gap-3">
	                      <BookInput
	                        label="from_chapter（0表示空状态）"
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

	                    {diffResult && (
	                      <div className="space-y-3">
	                        <div className="text-sm text-book-text-muted">
	                          {diffResult.has_changes ? '有变化' : '无变化'} · from {diffResult.from_chapter} → to {diffResult.to_chapter}
	                        </div>
	                        <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono bg-book-bg-paper p-3 rounded-lg border border-book-border/40 overflow-auto">
	                          {JSON.stringify(diffResult.categories || {}, null, 2)}
	                        </pre>
	                      </div>
	                    )}
	                  </BookCard>

	                  <BookCard className="p-4 space-y-3">
	                    <div className="font-bold text-book-text-main">回滚（reset）</div>
	                    <div className="grid grid-cols-2 gap-3">
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
	                    <div className="text-xs text-book-text-muted leading-relaxed">
	                      注意：回滚会删除目标章节之后的所有快照，属于破坏性操作。
	                    </div>
	                  </BookCard>
	                </div>
	              )}

	              {activeTab === 'implicit' && (
	                <BookCard className="p-4 space-y-3">
	                  <div className="font-bold text-book-text-main">隐性属性分析</div>
	                  <div className="grid grid-cols-2 gap-3">
	                    <label className="text-sm font-bold text-book-text-sub">
	                      attribute_key
	                      <input
	                        className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
	                        value={implicitKey}
	                        onChange={(e) => setImplicitKey(e.target.value)}
	                        placeholder="例如：勇气 / 信念 / 道德底线"
	                      />
	                    </label>
	                    <BookInput
	                      label="window"
	                      type="number"
	                      min={1}
	                      max={50}
	                      value={implicitWindow}
	                      onChange={(e) => setImplicitWindow(Math.max(1, Math.min(50, Number(e.target.value) || 10)))}
	                    />
	                  </div>
	                  <div className="flex gap-2 justify-end">
	                    <BookButton variant="secondary" onClick={fetchImplicitStats} disabled={implicitStatsLoading}>
	                      {implicitStatsLoading ? '统计中…' : '统计'}
	                    </BookButton>
	                    <BookButton variant="primary" onClick={fetchImplicitCheck} disabled={implicitCheckLoading}>
	                      <Sparkles size={16} className={`mr-2 ${implicitCheckLoading ? 'animate-pulse' : ''}`} />
	                      {implicitCheckLoading ? '生成中…' : 'LLM建议'}
	                    </BookButton>
	                  </div>

	                  {implicitStats && (
	                    <BookCard className="p-3 bg-book-bg/50 border-book-border/50">
	                      <div className="text-xs text-book-text-muted font-mono">
	                        total={implicitStats.total} · conform={implicitStats.conform_count} · non={implicitStats.non_conform_count} · rate={Math.round((implicitStats.conform_rate || 0) * 100)}%
	                      </div>
	                      <div className="mt-1 text-xs font-bold">
	                        {implicitStats.threshold_reached ? (
	                          <span className="text-book-accent">已达到更新阈值</span>
	                        ) : (
	                          <span className="text-book-text-muted">未达到更新阈值</span>
	                        )}
	                      </div>
	                    </BookCard>
	                  )}

	                  {implicitCheck && (
	                    <BookCard className="p-3 bg-book-bg/50 border-book-border/50 space-y-2">
	                      <div className="text-xs text-book-text-muted">决策：<span className="font-bold text-book-text-main">{implicitCheck.decision}</span></div>
	                      <div className="text-xs text-book-text-muted whitespace-pre-wrap">理由：{implicitCheck.reasoning}</div>
	                      {implicitCheck.suggested_new_value !== undefined ? (
	                        <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono bg-book-bg-paper p-2 rounded border border-book-border/40 overflow-auto">
	                          {JSON.stringify(implicitCheck.suggested_new_value, null, 2)}
	                        </pre>
	                      ) : null}
	                      {implicitCheck.evidence_summary ? (
	                        <div className="text-xs text-book-text-muted whitespace-pre-wrap border-l-2 border-book-border pl-2">
	                          证据：{implicitCheck.evidence_summary}
	                        </div>
	                      ) : null}
	                    </BookCard>
	                  )}
	                </BookCard>
	              )}
            </>
          )}
        </div>
      </div>
    </Modal>
  );
};
