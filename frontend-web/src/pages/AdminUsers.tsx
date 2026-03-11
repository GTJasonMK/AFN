import React, { startTransition, useCallback, useDeferredValue, useEffect, useMemo, useState } from 'react';
import { Activity, Database, Download, TrendingUp, UserPlus, Users } from 'lucide-react';
import { adminUsersApi, AdminUserMonitorItem, AdminUsersMonitorSummary } from '../api/adminUsers';
import { adminDashboardApi, AdminDashboardTrendsResponse } from '../api/adminDashboard';
import { BookButton } from '../components/ui/BookButton';
import { BookCard } from '../components/ui/BookCard';
import { BookInput } from '../components/ui/BookInput';
import { useToast } from '../components/feedback/Toast';
import { confirmDialog } from '../components/feedback/ConfirmDialog';
import { AdminPanelHeader } from '../components/admin/AdminPanelHeader';
import { AdminAccessDenied } from '../components/admin/AdminAccessDenied';
import { AdminBarListChart, AdminDonutChart, AdminStackedProgress, AdminTrendChart } from '../components/admin/AdminCharts';
import { LazyRender } from '../components/admin/LazyRender';
import { isAdminUser, useAuthStore } from '../store/auth';
import { extractApiErrorMessage } from '../api/client';
import { scheduleIdleTask } from '../utils/scheduleIdleTask';
import { readBootstrapCache, writeBootstrapCache } from '../utils/bootstrapCache';
import { downloadCsv } from '../utils/csv';

type StatusFilter = 'all' | 'active' | 'inactive';
type SortMode = 'lastActivity' | 'projects' | 'username';
type FocusFilter = 'all' | 'has_projects' | 'has_configs' | 'recently_active' | 'inactive_only' | 'dormant_assets';

const formatDate = (value?: string | null): string => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
};

const toTimestamp = (value?: string | null): number => {
  if (!value) return 0;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 0;
  return date.getTime();
};

const emptySummary: AdminUsersMonitorSummary = {
  total_users: 0,
  active_users: 0,
  inactive_users: 0,
  admin_users: 0,
  recently_active_users: 0,
  total_novel_projects: 0,
  total_coding_projects: 0,
  total_projects: 0,
  total_llm_configs: 0,
  total_embedding_configs: 0,
  total_image_configs: 0,
  total_theme_configs: 0,
};

type AdminUsersBootstrapSnapshot = {
  users: AdminUserMonitorItem[];
  summary: AdminUsersMonitorSummary;
  trendData: AdminDashboardTrendsResponse | null;
};

const ADMIN_USERS_BOOTSTRAP_KEY = 'afn:web:admin:users:bootstrap:v1';
const ADMIN_USERS_BOOTSTRAP_TTL_MS = 3 * 60 * 1000;
const adminFilterSelectClassName =
  'w-full rounded-[18px] border border-book-border/45 bg-book-bg-paper/82 px-4 py-3 text-book-text-main shadow-inner focus:outline-none focus:ring-2 focus:ring-book-primary/20 focus:border-book-primary';

export const AdminUsers: React.FC = () => {
  const { addToast } = useToast();
  const { authEnabled, user } = useAuthStore();
  const initialCacheRef = React.useRef<AdminUsersBootstrapSnapshot | null>(
    readBootstrapCache<AdminUsersBootstrapSnapshot>(
      ADMIN_USERS_BOOTSTRAP_KEY,
      ADMIN_USERS_BOOTSTRAP_TTL_MS,
    ),
  );

  const isAdmin = isAdminUser(authEnabled, user);
  const [users, setUsers] = useState<AdminUserMonitorItem[]>(
    () => initialCacheRef.current?.users ?? []
  );
  const [summary, setSummary] = useState<AdminUsersMonitorSummary>(
    () => initialCacheRef.current?.summary ?? emptySummary
  );
  const [trendData, setTrendData] = useState<AdminDashboardTrendsResponse | null>(
    () => initialCacheRef.current?.trendData ?? null
  );
  const [trendMode, setTrendMode] = useState<'line' | 'bar'>('line');

  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [statusUpdatingId, setStatusUpdatingId] = useState<number | null>(null);
  const [roleUpdatingId, setRoleUpdatingId] = useState<number | null>(null);
  const [resettingUserId, setResettingUserId] = useState<number | null>(null);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [newUserActive, setNewUserActive] = useState(true);
  const [newUserAdmin, setNewUserAdmin] = useState(false);

  const [resetTarget, setResetTarget] = useState<AdminUserMonitorItem | null>(null);
  const [resetPassword, setResetPassword] = useState('');

  const [searchKeyword, setSearchKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [sortMode, setSortMode] = useState<SortMode>('lastActivity');
  const [focusFilter, setFocusFilter] = useState<FocusFilter>('all');
  const deferredSearchKeyword = useDeferredValue(searchKeyword);
  const [userRowLimit, setUserRowLimit] = useState(80);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const monitorData = await adminUsersApi.monitor();
      setUsers(Array.isArray(monitorData.users) ? monitorData.users : []);
      setSummary(monitorData.summary || emptySummary);

      scheduleIdleTask(() => {
        void adminDashboardApi
          .trends(21)
          .then((trendsRes) => startTransition(() => setTrendData(trendsRes)))
          .catch((error) => console.error(error));
      }, { delay: 160, timeout: 2400 });
    } catch (error) {
      console.error(error);
      addToast(extractApiErrorMessage(error, '加载用户监控数据失败'), 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    if (!isAdmin) return;
    fetchUsers();
  }, [fetchUsers, isAdmin]);

  useEffect(() => {
    const hasSummary = Number(summary.total_users || 0) > 0 || Number(summary.total_projects || 0) > 0;
    if (!trendData && users.length === 0 && !hasSummary) return;
    writeBootstrapCache<AdminUsersBootstrapSnapshot>(ADMIN_USERS_BOOTSTRAP_KEY, {
      users,
      summary,
      trendData,
    });
  }, [summary, trendData, users]);

  const filteredUsers = useMemo(() => {
    const keyword = deferredSearchKeyword.trim().toLowerCase();
    const rows = users.filter((item) => {
      if (statusFilter === 'active' && !item.is_active) return false;
      if (statusFilter === 'inactive' && item.is_active) return false;

      const totalConfigs =
        Number(item.metrics.llm_configs || 0) +
        Number(item.metrics.embedding_configs || 0) +
        Number(item.metrics.image_configs || 0) +
        Number(item.metrics.theme_configs || 0);

      if (focusFilter === 'has_projects' && Number(item.metrics.total_projects || 0) <= 0) return false;
      if (focusFilter === 'has_configs' && totalConfigs <= 0) return false;
      if (focusFilter === 'recently_active' && !item.metrics.recently_active) return false;
      if (focusFilter === 'inactive_only' && item.is_active) return false;
      if (focusFilter === 'dormant_assets') {
        const totalAssets = Number(item.metrics.total_projects || 0) + totalConfigs;
        const lastActivityTs = toTimestamp(item.metrics.last_activity_at);
        const dormantThreshold = Date.now() - 30 * 24 * 60 * 60 * 1000;
        if (totalAssets <= 0) return false;
        if (!lastActivityTs || lastActivityTs > dormantThreshold) return false;
      }

      if (!keyword) return true;

      const usernameText = String(item.username || '').toLowerCase();
      const idText = String(item.id || '');
      return usernameText.includes(keyword) || idText.includes(keyword);
    });

    rows.sort((a, b) => {
      if (sortMode === 'projects') {
        return (b.metrics?.total_projects || 0) - (a.metrics?.total_projects || 0);
      }
      if (sortMode === 'username') {
        return String(a.username || '').localeCompare(String(b.username || ''));
      }

      const bTs = toTimestamp(b.metrics?.last_activity_at);
      const aTs = toTimestamp(a.metrics?.last_activity_at);
      return bTs - aTs;
    });

    return rows;
  }, [users, deferredSearchKeyword, statusFilter, sortMode, focusFilter]);

  const visibleUsers = useMemo(() => filteredUsers.slice(0, userRowLimit), [filteredUsers, userRowLimit]);

  useEffect(() => {
    setUserRowLimit(80);
  }, [users.length, deferredSearchKeyword, statusFilter, sortMode, focusFilter]);

  const topProjectUsers = useMemo(() => {
    return [...users]
      .sort((a, b) => (b.metrics?.total_projects || 0) - (a.metrics?.total_projects || 0))
      .slice(0, 5);
  }, [users]);

  const riskUsers = useMemo(() => {
    const dormantThreshold = Date.now() - 30 * 24 * 60 * 60 * 1000;
    return users
      .filter((item) => {
        const totalConfigs =
          Number(item.metrics.llm_configs || 0) +
          Number(item.metrics.embedding_configs || 0) +
          Number(item.metrics.image_configs || 0) +
          Number(item.metrics.theme_configs || 0);
        const totalAssets = Number(item.metrics.total_projects || 0) + totalConfigs;
        if (totalAssets <= 0) return false;

        const lastActivityTs = toTimestamp(item.metrics.last_activity_at);
        return !lastActivityTs || lastActivityTs <= dormantThreshold;
      })
      .sort((a, b) => {
        const assetsA =
          Number(a.metrics.total_projects || 0) +
          Number(a.metrics.llm_configs || 0) +
          Number(a.metrics.embedding_configs || 0) +
          Number(a.metrics.image_configs || 0) +
          Number(a.metrics.theme_configs || 0);
        const assetsB =
          Number(b.metrics.total_projects || 0) +
          Number(b.metrics.llm_configs || 0) +
          Number(b.metrics.embedding_configs || 0) +
          Number(b.metrics.image_configs || 0) +
          Number(b.metrics.theme_configs || 0);
        return assetsB - assetsA;
      })
      .slice(0, 6);
  }, [users]);

  const activitySegments = useMemo(() => {
    let activeWithAssets = 0;
    let activeWithoutAssets = 0;
    let inactiveWithAssets = 0;
    let inactiveWithoutAssets = 0;

    users.forEach((item) => {
      const totalConfigs =
        Number(item.metrics.llm_configs || 0) +
        Number(item.metrics.embedding_configs || 0) +
        Number(item.metrics.image_configs || 0) +
        Number(item.metrics.theme_configs || 0);
      const totalAssets = Number(item.metrics.total_projects || 0) + totalConfigs;

      if (item.is_active && totalAssets > 0) activeWithAssets += 1;
      if (item.is_active && totalAssets <= 0) activeWithoutAssets += 1;
      if (!item.is_active && totalAssets > 0) inactiveWithAssets += 1;
      if (!item.is_active && totalAssets <= 0) inactiveWithoutAssets += 1;
    });

    return [
      { key: 'active_with_assets', label: '启用且有数据', count: activeWithAssets },
      { key: 'active_without_assets', label: '启用且无数据', count: activeWithoutAssets },
      { key: 'inactive_with_assets', label: '禁用且有数据', count: inactiveWithAssets },
      { key: 'inactive_without_assets', label: '禁用且无数据', count: inactiveWithoutAssets },
    ];
  }, [users]);

  const totalConfigAssets =
    Number(summary.total_llm_configs || 0) +
    Number(summary.total_embedding_configs || 0) +
    Number(summary.total_image_configs || 0) +
    Number(summary.total_theme_configs || 0);

  const dormantAssetCount = useMemo(() => {
    const dormantThreshold = Date.now() - 30 * 24 * 60 * 60 * 1000;
    return users.filter((item) => {
      const totalConfigs =
        Number(item.metrics.llm_configs || 0) +
        Number(item.metrics.embedding_configs || 0) +
        Number(item.metrics.image_configs || 0) +
        Number(item.metrics.theme_configs || 0);
      const totalAssets = Number(item.metrics.total_projects || 0) + totalConfigs;
      if (totalAssets <= 0) return false;

      const lastActivityTs = toTimestamp(item.metrics.last_activity_at);
      return !lastActivityTs || lastActivityTs <= dormantThreshold;
    }).length;
  }, [users]);

  const noAssetCount = useMemo(() => {
    return users.filter((item) => {
      const totalConfigs =
        Number(item.metrics.llm_configs || 0) +
        Number(item.metrics.embedding_configs || 0) +
        Number(item.metrics.image_configs || 0) +
        Number(item.metrics.theme_configs || 0);
      const totalAssets = Number(item.metrics.total_projects || 0) + totalConfigs;
      return totalAssets <= 0;
    }).length;
  }, [users]);

  const userStatusChartData = useMemo(() => {
    return [
      { label: '启用用户', value: summary.active_users, color: '#14B8A6' },
      { label: '禁用用户', value: summary.inactive_users, color: '#EF4444' },
    ];
  }, [summary.active_users, summary.inactive_users]);

  const assetStructureSegments = useMemo(() => {
    return [
      { label: '项目总量', value: summary.total_projects, color: '#6366F1' },
      { label: '配置总量', value: totalConfigAssets, color: '#14B8A6' },
    ];
  }, [summary.total_projects, totalConfigAssets]);

  const userLayerChartData = useMemo(() => {
    return [
      { label: '7天活跃', value: summary.recently_active_users, color: '#6366F1' },
      { label: '30天沉默但有数据', value: dormantAssetCount, color: '#F59E0B' },
      { label: '禁用用户', value: summary.inactive_users, color: '#EF4444' },
      { label: '无资产用户', value: noAssetCount, color: '#A1A1AA' },
    ];
  }, [summary.recently_active_users, dormantAssetCount, summary.inactive_users, noAssetCount]);

  const userTrendSeries = useMemo(() => {
    if (!trendData) return [];

    const seriesMap = new Map(trendData.series.map((item) => [item.key, item]));
    const toPoints = (key: string) => {
      const target = seriesMap.get(key);
      if (!target) return [];
      return target.points.map((point) => ({
        label: point.date,
        value: Number(point.value || 0),
      }));
    };

    return [
      { label: '新用户', color: '#6366F1', points: toPoints('new_users') },
      { label: '新建项目', color: '#14B8A6', points: toPoints('new_projects') },
      { label: '新建配置', color: '#F59E0B', points: toPoints('new_configs') },
    ].filter((item) => item.points.length > 0);
  }, [trendData]);

  const handleExportCsv = () => {
    if (filteredUsers.length <= 0) {
      addToast('当前没有可导出的用户记录', 'error');
      return;
    }

    const header = [
      'id',
      'username',
      'is_active',
      'is_admin',
      'novel_projects',
      'coding_projects',
      'total_projects',
      'llm_configs',
      'embedding_configs',
      'image_configs',
      'theme_configs',
      'last_activity_at',
      'recently_active',
    ];

    const rows = filteredUsers.map((item) => [
      item.id,
      item.username,
      item.is_active ? 'true' : 'false',
      item.is_admin ? 'true' : 'false',
      item.metrics.novel_projects,
      item.metrics.coding_projects,
      item.metrics.total_projects,
      item.metrics.llm_configs,
      item.metrics.embedding_configs,
      item.metrics.image_configs,
      item.metrics.theme_configs,
      item.metrics.last_activity_at || '',
      item.metrics.recently_active ? 'true' : 'false',
    ]);

    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    downloadCsv(header, rows, `admin-users-${stamp}.csv`);

    addToast(`已导出 ${filteredUsers.length} 条用户记录`, 'success');
  };

  const handleCreateUser = async () => {
    const userName = username.trim();
    if (!userName) {
      addToast('请输入用户名', 'error');
      return;
    }
    if (password.length < 6) {
      addToast('密码至少 6 位', 'error');
      return;
    }

    setCreating(true);
    try {
      await adminUsersApi.create({
        username: userName,
        password,
        is_active: newUserActive,
        is_admin: newUserAdmin,
      });
      setUsername('');
      setPassword('');
      setNewUserActive(true);
      setNewUserAdmin(false);
      addToast('用户创建成功', 'success');
      await fetchUsers();
    } catch (error) {
      console.error(error);
      addToast(extractApiErrorMessage(error, '创建用户失败'), 'error');
    } finally {
      setCreating(false);
    }
  };

  const handleToggleStatus = async (target: AdminUserMonitorItem) => {
    const nextStatus = !target.is_active;

    const ok = await confirmDialog({
      title: nextStatus ? '启用用户' : '禁用用户',
      message: `确定要${nextStatus ? '启用' : '禁用'}账号「${target.username}」吗？`,
      confirmText: nextStatus ? '启用' : '禁用',
      dialogType: nextStatus ? 'warning' : 'danger',
    });
    if (!ok) return;

    setStatusUpdatingId(target.id);
    try {
      await adminUsersApi.updateStatus(target.id, nextStatus);
      addToast(`已${nextStatus ? '启用' : '禁用'}账号`, 'success');
      await fetchUsers();
    } catch (error) {
      console.error(error);
      addToast(extractApiErrorMessage(error, '更新用户状态失败'), 'error');
    } finally {
      setStatusUpdatingId(null);
    }
  };

  const handleToggleAdminRole = async (target: AdminUserMonitorItem) => {
    const nextIsAdmin = !target.is_admin;

    const ok = await confirmDialog({
      title: nextIsAdmin ? '授予管理员' : '撤销管理员',
      message: `确定要${nextIsAdmin ? '授予' : '撤销'}账号「${target.username}」的管理员权限吗？`,
      confirmText: nextIsAdmin ? '授予' : '撤销',
      dialogType: nextIsAdmin ? 'warning' : 'danger',
    });
    if (!ok) return;

    setRoleUpdatingId(target.id);
    try {
      await adminUsersApi.updateRole(target.id, nextIsAdmin);
      addToast(`已${nextIsAdmin ? '授予' : '撤销'}管理员权限`, 'success');
      await fetchUsers();
    } catch (error) {
      console.error(error);
      addToast(extractApiErrorMessage(error, '更新管理员角色失败'), 'error');
    } finally {
      setRoleUpdatingId(null);
    }
  };

  const handleResetPassword = async () => {
    if (!resetTarget) return;
    if (resetPassword.length < 6) {
      addToast('新密码至少 6 位', 'error');
      return;
    }

    const ok = await confirmDialog({
      title: '重置密码',
      message: `确定要重置「${resetTarget.username}」的密码吗？`,
      confirmText: '重置',
      dialogType: 'warning',
    });
    if (!ok) return;

    setResettingUserId(resetTarget.id);
    try {
      await adminUsersApi.resetPassword(resetTarget.id, resetPassword);
      addToast('密码重置成功', 'success');
      setResetPassword('');
      setResetTarget(null);
      await fetchUsers();
    } catch (error) {
      console.error(error);
      addToast(extractApiErrorMessage(error, '重置用户密码失败'), 'error');
    } finally {
      setResettingUserId(null);
    }
  };

  if (!isAdmin) {
    return <AdminAccessDenied />;
  }

  return (
    <div className="page-shell min-h-screen overflow-hidden">
      <div className="ambient-orb -left-16 top-0 h-64 w-64 bg-book-primary/10" />
      <div className="ambient-orb right-[-4rem] top-28 h-72 w-72 bg-book-primary-light/10" />

      <div className="relative mx-auto flex min-h-screen w-full max-w-[1600px] flex-col gap-4 px-3 py-3 sm:px-5 sm:py-5">
        <AdminPanelHeader
          current="users"
          title="管理员用户管理"
          description="管理账号并监控用户层级数据"
          onRefresh={fetchUsers}
          refreshing={loading}
          extraActions={(
            <BookButton variant="secondary" size="sm" onClick={handleExportCsv}>
              <Download size={14} />
              导出CSV
            </BookButton>
          )}
        />

        <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="metric-tile">
            <div className="flex items-center gap-2 text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
              <Users size={14} />
              用户总数
            </div>
            <div className="mt-3 font-serif text-3xl font-bold text-book-text-main">{summary.total_users}</div>
            <div className="mt-2 text-sm text-book-text-sub">启用 {summary.active_users} / 禁用 {summary.inactive_users}</div>
          </div>
          <div className="metric-tile">
            <div className="flex items-center gap-2 text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
              <Activity size={14} />
              近 7 天活跃
            </div>
            <div className="mt-3 font-serif text-3xl font-bold text-book-text-main">{summary.recently_active_users}</div>
            <div className="mt-2 text-sm text-book-text-sub">管理员账号 {summary.admin_users}</div>
          </div>
          <div className="metric-tile">
            <div className="flex items-center gap-2 text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
              <TrendingUp size={14} />
              项目总量
            </div>
            <div className="mt-3 font-serif text-3xl font-bold text-book-text-main">{summary.total_projects}</div>
            <div className="mt-2 text-sm text-book-text-sub">
              小说 {summary.total_novel_projects} / Prompt {summary.total_coding_projects}
            </div>
          </div>
          <div className="metric-tile">
            <div className="flex items-center gap-2 text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
              <Database size={14} />
              配置总量
            </div>
            <div className="mt-3 font-serif text-3xl font-bold text-book-text-main">
              {summary.total_llm_configs + summary.total_embedding_configs + summary.total_image_configs + summary.total_theme_configs}
            </div>
            <div className="mt-2 text-sm text-book-text-sub">
              LLM {summary.total_llm_configs} · 嵌入 {summary.total_embedding_configs} · 图片 {summary.total_image_configs} · 主题 {summary.total_theme_configs}
            </div>
          </div>
        </section>

        <section className="grid gap-4 xl:grid-cols-3">
          <BookCard className="rounded-[28px] bg-book-bg-paper/82">
            <LazyRender placeholderHeight={220} rootMargin="360px 0px">
              <AdminDonutChart
                title="账号状态占比"
                data={userStatusChartData}
                centerLabel="用户总数"
                centerValue={summary.total_users}
              />
            </LazyRender>
          </BookCard>

          <BookCard className="rounded-[28px] bg-book-bg-paper/82">
            <LazyRender placeholderHeight={180} rootMargin="360px 0px">
              <AdminStackedProgress title="数据资产结构（项目 / 配置）" segments={assetStructureSegments} />
            </LazyRender>
          </BookCard>

          <BookCard className="rounded-[28px] bg-book-bg-paper/82">
            <LazyRender placeholderHeight={220} rootMargin="360px 0px">
              <AdminBarListChart title="用户活跃分层" data={userLayerChartData} totalOverride={summary.total_users} />
            </LazyRender>
          </BookCard>
        </section>

        <section className="dramatic-surface rounded-[30px]">
          <div className="relative z-[1] space-y-4 px-5 py-5 sm:px-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                  User Trend
                </div>
                <h2 className="mt-2 font-serif text-2xl font-bold text-book-text-main">
                  近 {trendData?.days || 21} 天用户趋势
                </h2>
              </div>
              <div className="inline-flex overflow-hidden rounded-full border border-book-border/50 bg-book-bg-paper/72 p-1">
                <button
                  className={`rounded-full px-4 py-2 text-sm font-semibold ${
                    trendMode === 'line'
                      ? 'bg-book-primary text-white'
                      : 'text-book-text-muted hover:text-book-text-main'
                  }`}
                  onClick={() => setTrendMode('line')}
                >
                  折线图
                </button>
                <button
                  className={`rounded-full px-4 py-2 text-sm font-semibold ${
                    trendMode === 'bar'
                      ? 'bg-book-primary text-white'
                      : 'text-book-text-muted hover:text-book-text-main'
                  }`}
                  onClick={() => setTrendMode('bar')}
                >
                  柱状图
                </button>
              </div>
            </div>
            <LazyRender placeholderHeight={280} rootMargin="420px 0px">
              <AdminTrendChart
                series={userTrendSeries}
                mode={trendMode}
                emptyText="暂无用户趋势数据"
              />
            </LazyRender>
          </div>
        </section>

        <section className="dramatic-surface sticky top-3 z-20 rounded-[30px]">
          <div className="relative z-[1] grid gap-4 px-5 py-5 lg:grid-cols-[minmax(0,1fr)_320px] sm:px-6">
            <div className="space-y-4">
              <div>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                  Filter Console
                </div>
                <h2 className="mt-2 font-serif text-2xl font-bold text-book-text-main">筛选与监控视图</h2>
                <p className="mt-2 text-sm leading-relaxed text-book-text-sub">
                  先锁定用户集，再进入表格执行启用、授权和密码重置操作。
                </p>
              </div>

              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <BookInput
                label="搜索用户"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                placeholder="用户名或用户ID"
              />
              <div>
                <label className="block text-sm font-bold text-book-text-sub mb-1.5 ml-1">状态过滤</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
                  className={adminFilterSelectClassName}
                >
                  <option value="all">全部</option>
                  <option value="active">仅启用</option>
                  <option value="inactive">仅禁用</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-bold text-book-text-sub mb-1.5 ml-1">关注视图</label>
                <select
                  value={focusFilter}
                  onChange={(e) => setFocusFilter(e.target.value as FocusFilter)}
                  className={adminFilterSelectClassName}
                >
                  <option value="all">全部用户</option>
                  <option value="has_projects">有项目用户</option>
                  <option value="has_configs">有配置用户</option>
                  <option value="recently_active">最近活跃用户</option>
                  <option value="inactive_only">禁用用户</option>
                  <option value="dormant_assets">30天沉默但有数据</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-bold text-book-text-sub mb-1.5 ml-1">排序方式</label>
                <select
                  value={sortMode}
                  onChange={(e) => setSortMode(e.target.value as SortMode)}
                  className={adminFilterSelectClassName}
                >
                  <option value="lastActivity">按最近活跃</option>
                  <option value="projects">按项目数量</option>
                  <option value="username">按用户名</option>
                </select>
              </div>
            </div>

            </div>

            <div className="rounded-[24px] border border-book-border/45 bg-book-bg-paper/72 p-4">
              <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                当前结果
              </div>
              <div className="mt-3 font-serif text-3xl font-bold text-book-text-main">
                {filteredUsers.length}
              </div>
              <div className="mt-2 text-sm text-book-text-sub">共 {users.length} 个用户命中当前筛选条件</div>

              <div className="mt-4 space-y-2">
                <div className="rounded-[18px] border border-book-border/40 px-3 py-2 text-xs text-book-text-muted">
                  最近 30 天沉默但有数据：<span className="font-semibold text-book-text-main">{riskUsers.length}</span>
                </div>
                <div className="rounded-[18px] border border-book-border/40 px-3 py-2 text-xs text-book-text-muted">
                  当前关注模式：<span className="font-semibold text-book-text-main">{focusFilter}</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
          <section className="dramatic-surface rounded-[30px]">
            <div className="relative z-[1] space-y-4 px-5 py-5 sm:px-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                    User Monitor Table
                  </div>
                  <h2 className="mt-2 font-serif text-2xl font-bold text-book-text-main">用户数据监控表</h2>
                </div>
                <span className="story-pill">已渲染 {visibleUsers.length} 条</span>
              </div>

              <div className="overflow-x-auto rounded-[24px] border border-book-border/40 bg-book-bg-paper/62 px-4">
                <table className="min-w-[1120px] w-full text-sm">
                  <thead>
                    <tr className="border-b border-book-border/50 text-book-text-muted">
                      <th className="py-3 pr-3 text-left">用户</th>
                      <th className="py-3 pr-3 text-left">状态</th>
                      <th className="py-3 pr-3 text-left">项目（小说/Prompt/总）</th>
                      <th className="py-3 pr-3 text-left">配置（LLM/嵌入/图片/主题）</th>
                      <th className="py-3 pr-3 text-left">最近活跃</th>
                      <th className="py-3 text-left">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleUsers.map((item) => (
                      <tr key={item.id} className="border-b border-book-border/30 text-book-text-main">
                        <td className="py-3 pr-3 align-top">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs">{item.username}</span>
                            {item.is_admin ? (
                              <span className="rounded-full bg-book-primary/10 px-2 py-0.5 text-[10px] font-bold text-book-primary">
                                管理员
                              </span>
                            ) : null}
                          </div>
                          <div className="mt-1 text-[11px] text-book-text-muted">ID: {item.id}</div>
                        </td>
                        <td className="py-3 pr-3 align-top">
                          <div className="flex flex-wrap gap-1">
                            <span
                              className={`rounded-full px-2 py-1 text-xs ${
                                item.is_active
                                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                                  : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                              }`}
                            >
                              {item.is_active ? '启用' : '禁用'}
                            </span>
                            {item.metrics.recently_active ? (
                              <span className="rounded-full bg-book-primary/10 px-2 py-1 text-xs text-book-primary">
                                7天活跃
                              </span>
                            ) : null}
                          </div>
                        </td>
                        <td className="py-3 pr-3 align-top text-xs">
                          {item.metrics.novel_projects} / {item.metrics.coding_projects} /{' '}
                          <span className="font-bold">{item.metrics.total_projects}</span>
                        </td>
                        <td className="py-3 pr-3 align-top text-xs">
                          {item.metrics.llm_configs} / {item.metrics.embedding_configs} / {item.metrics.image_configs} / {item.metrics.theme_configs}
                        </td>
                        <td className="py-3 pr-3 align-top text-xs text-book-text-muted">
                          {formatDate(item.metrics.last_activity_at)}
                        </td>
                        <td className="py-3 align-top">
                          <div className="flex flex-wrap gap-2">
                            <BookButton
                              variant="secondary"
                              size="sm"
                              onClick={() => handleToggleStatus(item)}
                              disabled={statusUpdatingId === item.id}
                            >
                              {statusUpdatingId === item.id ? '处理中…' : item.is_active ? '禁用' : '启用'}
                            </BookButton>
                            <BookButton
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleAdminRole(item)}
                              disabled={roleUpdatingId === item.id}
                            >
                              {roleUpdatingId === item.id ? '处理中…' : item.is_admin ? '撤销管理员' : '设为管理员'}
                            </BookButton>
                            <BookButton
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setResetTarget(item);
                                setResetPassword('');
                              }}
                            >
                              重置密码
                            </BookButton>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {!loading && filteredUsers.length === 0 ? (
                      <tr>
                        <td className="py-6 text-center text-book-text-muted" colSpan={6}>
                          暂无匹配用户
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>

              {loading ? <div className="text-xs text-book-text-muted">加载中…</div> : null}
              {!loading && visibleUsers.length < filteredUsers.length ? (
                <div className="flex items-center justify-between text-xs text-book-text-muted">
                  <span>
                    已渲染 {visibleUsers.length} / {filteredUsers.length} 条
                  </span>
                  <BookButton
                    variant="ghost"
                    size="sm"
                    onClick={() => setUserRowLimit((value) => value + 80)}
                  >
                    加载更多（剩余 {filteredUsers.length - visibleUsers.length} 条）
                  </BookButton>
                </div>
              ) : null}
            </div>
          </section>

          <div className="space-y-4">
            <section className="dramatic-surface rounded-[30px]">
              <div className="relative z-[1] space-y-4 px-5 py-5">
                <div className="flex items-center gap-2 text-book-text-main">
                  <UserPlus size={16} className="text-book-primary" />
                  <h2 className="font-serif text-2xl font-bold">创建用户</h2>
                </div>
                <div className="grid gap-3">
                  <BookInput
                    label="用户名"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="3-32位：字母数字._-"
                  />
                  <BookInput
                    label="初始密码"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="至少6位"
                  />
                  <label className="inline-flex items-center gap-2 text-sm text-book-text-sub">
                    <input
                      type="checkbox"
                      checked={newUserActive}
                      onChange={(e) => setNewUserActive(e.target.checked)}
                      className="rounded border-book-border text-book-primary focus:ring-book-primary"
                    />
                    创建后立即启用
                  </label>
                  <label className="inline-flex items-center gap-2 text-sm text-book-text-sub">
                    <input
                      type="checkbox"
                      checked={newUserAdmin}
                      onChange={(e) => setNewUserAdmin(e.target.checked)}
                      className="rounded border-book-border text-book-primary focus:ring-book-primary"
                    />
                    创建为管理员
                  </label>
                  <BookButton variant="primary" onClick={handleCreateUser} disabled={creating}>
                    {creating ? '创建中…' : '创建用户'}
                  </BookButton>
                </div>
              </div>
            </section>

            <section className="dramatic-surface rounded-[30px]">
              <div className="relative z-[1] space-y-4 px-5 py-5">
                <div>
                  <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                    User Signals
                  </div>
                  <h2 className="mt-2 font-serif text-2xl font-bold text-book-text-main">用户结构概览</h2>
                </div>

                <div className="space-y-2">
              {activitySegments.map((segment) => (
                  <div
                    key={segment.key}
                    className="flex items-center justify-between rounded-[18px] border border-book-border/40 px-3 py-2 text-xs"
                  >
                    <span className="text-book-text-muted">{segment.label}</span>
                    <span className="font-bold text-book-primary">{segment.count}</span>
                  </div>
                ))}
                </div>

                <div className="space-y-2 border-t border-book-border/40 pt-2">
                  <div className="text-xs font-bold text-book-text-main">风险用户（30天沉默但有数据）</div>
                  {riskUsers.length > 0 ? (
                    riskUsers.map((item) => {
                      const totalAssets =
                        Number(item.metrics.total_projects || 0) +
                        Number(item.metrics.llm_configs || 0) +
                        Number(item.metrics.embedding_configs || 0) +
                        Number(item.metrics.image_configs || 0) +
                        Number(item.metrics.theme_configs || 0);
                      return (
                        <div
                          key={`risk-${item.id}`}
                          className="flex items-center justify-between rounded-[18px] border border-book-border/40 px-3 py-2 text-xs"
                        >
                          <div className="min-w-0">
                            <div className="truncate font-mono text-book-text-main">{item.username}</div>
                            <div className="text-book-text-muted">最近活跃：{formatDate(item.metrics.last_activity_at)}</div>
                          </div>
                          <div className="text-right">
                            <div className="font-bold text-book-accent">{totalAssets}</div>
                            <div className="text-book-text-muted">数据量</div>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="text-xs text-book-text-muted">暂无沉默高风险用户</div>
                  )}
                </div>

                <div className="space-y-2 border-t border-book-border/40 pt-2">
                  <div className="text-xs font-bold text-book-text-main">项目数量 TOP 5</div>
                  {topProjectUsers.length > 0 ? (
                    topProjectUsers.map((item) => (
                      <div
                        key={`top-${item.id}`}
                        className="flex items-center justify-between rounded-[18px] border border-book-border/40 px-3 py-2 text-xs"
                      >
                        <div className="min-w-0">
                          <div className="truncate font-mono text-book-text-main">{item.username}</div>
                          <div className="text-book-text-muted">ID: {item.id}</div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold text-book-primary">{item.metrics.total_projects}</div>
                          <div className="text-book-text-muted">项目</div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-book-text-muted">暂无可展示数据</div>
                  )}
                </div>
              </div>
            </section>

            {resetTarget ? (
              <section className="dramatic-surface rounded-[30px]">
                <div className="relative z-[1] space-y-4 px-5 py-5">
                  <div>
                    <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                      Password Reset
                    </div>
                    <h2 className="mt-2 font-serif text-2xl font-bold text-book-text-main">重置密码</h2>
                    <p className="mt-2 text-sm text-book-text-sub">
                      当前目标用户：<span className="font-mono">{resetTarget.username}</span>
                    </p>
                  </div>
                  <BookInput
                    label="新密码"
                    type="password"
                    value={resetPassword}
                    onChange={(e) => setResetPassword(e.target.value)}
                    placeholder="至少6位"
                  />
                  <div className="flex flex-wrap justify-end gap-2">
                    <BookButton
                      variant="secondary"
                      onClick={() => {
                        setResetPassword('');
                        setResetTarget(null);
                      }}
                    >
                      取消
                    </BookButton>
                    <BookButton
                      variant="warning"
                      onClick={handleResetPassword}
                      disabled={resettingUserId === resetTarget.id}
                    >
                      {resettingUserId === resetTarget.id ? '重置中…' : '确认重置'}
                    </BookButton>
                  </div>
                </div>
              </section>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
};
