import React, { startTransition, useCallback, useDeferredValue, useEffect, useMemo, useState } from 'react';
import { Download, FolderKanban, RefreshCw } from 'lucide-react';
import { adminDashboardApi, AdminDashboardTrendsResponse, AdminProjectsResponse, AdminRecentProjectItem, AdminStatusCount } from '../api/adminDashboard';
import { BookButton } from '../components/ui/BookButton';
import { BookCard } from '../components/ui/BookCard';
import { BookInput } from '../components/ui/BookInput';
import { useToast } from '../components/feedback/Toast';
import { AdminPanelHeader } from '../components/admin/AdminPanelHeader';
import { AdminAccessDenied } from '../components/admin/AdminAccessDenied';
import { AdminBarListChart, AdminDonutChart, AdminStackedProgress, AdminTrendChart } from '../components/admin/AdminCharts';
import { LazyRender } from '../components/admin/LazyRender';
import { isAdminUser, useAuthStore } from '../store/auth';
import { scheduleIdleTask } from '../utils/scheduleIdleTask';
import { readBootstrapCache, writeBootstrapCache } from '../utils/bootstrapCache';
import { downloadCsv } from '../utils/csv';

type KindFilter = 'all' | 'novel' | 'coding';
type SortMode = 'updated_desc' | 'updated_asc' | 'title' | 'username';

const emptyData: AdminProjectsResponse = {
  summary: {
    total_novel_projects: 0,
    total_coding_projects: 0,
    total_projects: 0,
  },
  recent_projects: [],
  top_users: [],
  novel_status_distribution: [],
  coding_status_distribution: [],
  generated_at: '',
};

type AdminProjectsBootstrapSnapshot = {
  data: AdminProjectsResponse;
  trendData: AdminDashboardTrendsResponse | null;
};

const ADMIN_PROJECTS_BOOTSTRAP_KEY = 'afn:web:admin:projects:bootstrap:v1';
const ADMIN_PROJECTS_BOOTSTRAP_TTL_MS = 3 * 60 * 1000;
const adminProjectSelectClassName =
  'w-full rounded-[18px] border border-book-border/45 bg-book-bg-paper/82 px-4 py-3 text-book-text-main shadow-inner focus:outline-none focus:ring-2 focus:ring-book-primary/20 focus:border-book-primary';

const formatDate = (value?: string | null): string => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
};

const normalizeKind = (value: string): 'novel' | 'coding' => {
  return value === 'coding' ? 'coding' : 'novel';
};

const getProjectTimestamp = (item: AdminRecentProjectItem): number => {
  const raw = item.updated_at || item.created_at;
  if (!raw) return 0;
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return 0;
  return date.getTime();
};

const sumStatusCount = (rows: AdminStatusCount[]) => rows.reduce((total, item) => total + Number(item.count || 0), 0);

const formatPercent = (numerator: number, denominator: number): number => {
  if (denominator <= 0) return 0;
  return Math.round((numerator / denominator) * 1000) / 10;
};

export const AdminProjects: React.FC = () => {
  const { addToast } = useToast();
  const { authEnabled, user } = useAuthStore();
  const initialCacheRef = React.useRef<AdminProjectsBootstrapSnapshot | null>(
    readBootstrapCache<AdminProjectsBootstrapSnapshot>(
      ADMIN_PROJECTS_BOOTSTRAP_KEY,
      ADMIN_PROJECTS_BOOTSTRAP_TTL_MS,
    ),
  );
  const isAdmin = isAdminUser(authEnabled, user);

  const [data, setData] = useState<AdminProjectsResponse>(() => initialCacheRef.current?.data ?? emptyData);
  const [trendData, setTrendData] = useState<AdminDashboardTrendsResponse | null>(
    () => initialCacheRef.current?.trendData ?? null
  );
  const [trendMode, setTrendMode] = useState<'line' | 'bar'>('line');
  const [loading, setLoading] = useState(false);
  const [kindFilter, setKindFilter] = useState<KindFilter>('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [keyword, setKeyword] = useState('');
  const deferredKeyword = useDeferredValue(keyword);
  const [projectRowLimit, setProjectRowLimit] = useState(80);
  const [sortMode, setSortMode] = useState<SortMode>('updated_desc');
  const [staleOnly, setStaleOnly] = useState(false);
  const [staleDays, setStaleDays] = useState(30);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const projectsRes = await adminDashboardApi.projects(120);
      setData(projectsRes);

      scheduleIdleTask(() => {
        void adminDashboardApi
          .trends(21)
          .then((trendsRes) => startTransition(() => setTrendData(trendsRes)))
          .catch((error) => console.error(error));
      }, { delay: 160, timeout: 2400 });
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAdmin) return;
    fetchData();
  }, [fetchData, isAdmin]);

  useEffect(() => {
    if (!data.generated_at && !trendData) return;
    writeBootstrapCache<AdminProjectsBootstrapSnapshot>(ADMIN_PROJECTS_BOOTSTRAP_KEY, {
      data,
      trendData,
    });
  }, [data, trendData]);

  const statusOptions = useMemo(() => {
    const set = new Set<string>();

    data.novel_status_distribution.forEach((item) => {
      const value = String(item.status || 'UNKNOWN').trim();
      if (value) set.add(value);
    });

    data.coding_status_distribution.forEach((item) => {
      const value = String(item.status || 'UNKNOWN').trim();
      if (value) set.add(value);
    });

    data.recent_projects.forEach((item) => {
      const value = String(item.status || 'UNKNOWN').trim();
      if (value) set.add(value);
    });

    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [data.novel_status_distribution, data.coding_status_distribution, data.recent_projects]);

  const staleThresholdMs = useMemo(() => {
    const safeDays = Math.max(1, Math.min(365, Number(staleDays) || 30));
    return safeDays * 24 * 60 * 60 * 1000;
  }, [staleDays]);

  const staleCount = useMemo(() => {
    const nowTs = Date.now();
    return data.recent_projects.filter((item) => {
      const ts = getProjectTimestamp(item);
      if (!ts) return false;
      return nowTs - ts >= staleThresholdMs;
    }).length;
  }, [data.recent_projects, staleThresholdMs]);

  const freshCount = useMemo(() => {
    return Math.max(data.recent_projects.length - staleCount, 0);
  }, [data.recent_projects.length, staleCount]);

  const filteredProjects = useMemo(() => {
    const key = deferredKeyword.trim().toLowerCase();
    const nowTs = Date.now();

    const rows = data.recent_projects.filter((item: AdminRecentProjectItem) => {
      const kind = normalizeKind(item.kind);
      if (kindFilter !== 'all' && kind !== kindFilter) {
        return false;
      }

      const status = String(item.status || 'UNKNOWN');
      if (statusFilter !== 'all' && status !== statusFilter) {
        return false;
      }

      if (staleOnly) {
        const ts = getProjectTimestamp(item);
        if (!ts || nowTs - ts < staleThresholdMs) {
          return false;
        }
      }

      if (!key) return true;

      return (
        String(item.title || '').toLowerCase().includes(key) ||
        String(item.username || '').toLowerCase().includes(key) ||
        String(item.project_id || '').toLowerCase().includes(key)
      );
    });

    rows.sort((a, b) => {
      if (sortMode === 'title') {
        return String(a.title || '').localeCompare(String(b.title || ''));
      }
      if (sortMode === 'username') {
        return String(a.username || '').localeCompare(String(b.username || ''));
      }

      const delta = getProjectTimestamp(b) - getProjectTimestamp(a);
      return sortMode === 'updated_desc' ? delta : -delta;
    });

    return rows;
  }, [data.recent_projects, kindFilter, statusFilter, staleOnly, staleThresholdMs, deferredKeyword, sortMode]);

  const visibleProjects = useMemo(() => filteredProjects.slice(0, projectRowLimit), [filteredProjects, projectRowLimit]);

  useEffect(() => {
    setProjectRowLimit(80);
  }, [data.recent_projects.length, deferredKeyword, kindFilter, statusFilter, sortMode, staleOnly, staleThresholdMs]);

  const statusDistributionRows = useMemo(() => {
    const novelTotal = Math.max(data.summary.total_novel_projects, sumStatusCount(data.novel_status_distribution));
    const codingTotal = Math.max(data.summary.total_coding_projects, sumStatusCount(data.coding_status_distribution));

    return [
      {
        kind: 'novel' as const,
        label: '小说项目',
        total: novelTotal,
        rows: data.novel_status_distribution,
        barClass: 'bg-book-primary',
      },
      {
        kind: 'coding' as const,
        label: 'Prompt 项目',
        total: codingTotal,
        rows: data.coding_status_distribution,
        barClass: 'bg-book-accent',
      },
    ];
  }, [
    data.summary.total_novel_projects,
    data.summary.total_coding_projects,
    data.novel_status_distribution,
    data.coding_status_distribution,
  ]);

  const topStatusRows = useMemo(() => {
    const rows: Array<{ label: string; value: number; color: string }> = [];

    data.novel_status_distribution.forEach((item) => {
      rows.push({ label: `小说 · ${item.status}`, value: Number(item.count || 0), color: '#6366F1' });
    });
    data.coding_status_distribution.forEach((item) => {
      rows.push({ label: `Prompt · ${item.status}`, value: Number(item.count || 0), color: '#14B8A6' });
    });

    return rows.sort((a, b) => b.value - a.value).slice(0, 8);
  }, [data.novel_status_distribution, data.coding_status_distribution]);

  const projectMixData = useMemo(() => {
    return [
      { label: '小说项目', value: data.summary.total_novel_projects, color: '#6366F1' },
      { label: 'Prompt 项目', value: data.summary.total_coding_projects, color: '#14B8A6' },
    ];
  }, [data.summary.total_novel_projects, data.summary.total_coding_projects]);

  const freshnessSegments = useMemo(() => {
    return [
      { label: '最近更新', value: freshCount, color: '#14B8A6' },
      { label: `陈旧（>${Math.max(1, staleDays)}天）`, value: staleCount, color: '#F59E0B' },
    ];
  }, [freshCount, staleCount, staleDays]);

  const projectTrendSeries = useMemo(() => {
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
      { label: '新建小说项目', color: '#6366F1', points: toPoints('new_novel_projects') },
      { label: '新建Prompt项目', color: '#14B8A6', points: toPoints('new_coding_projects') },
      { label: '新建项目总量', color: '#F59E0B', points: toPoints('new_projects') },
    ].filter((item) => item.points.length > 0);
  }, [trendData]);

  const riskHints = useMemo(() => {
    const hints: string[] = [];
    const staleRate = formatPercent(staleCount, data.recent_projects.length);

    if (data.recent_projects.length > 0 && staleRate >= 40) {
      hints.push(`最近样本中陈旧项目占比 ${staleRate}%（建议优先梳理长期未维护项目）。`);
    }

    const codingShare = formatPercent(data.summary.total_coding_projects, data.summary.total_projects);
    if (data.summary.total_projects > 0 && codingShare >= 65) {
      hints.push(`Prompt 项目占比 ${codingShare}%（建议重点关注代码生成链路负载）。`);
    }

    if (data.top_users.length > 0) {
      const first = data.top_users[0];
      const topLoadRate = formatPercent(first.total_projects, data.summary.total_projects);
      if (topLoadRate >= 35) {
        hints.push(`用户 ${first.username} 持有 ${topLoadRate}% 项目，存在集中风险。`);
      }
    }

    if (hints.length === 0) {
      hints.push('当前项目分布相对健康，暂无显著风险信号。');
    }

    return hints;
  }, [staleCount, data.recent_projects.length, data.summary, data.top_users]);

  const handleExportCsv = useCallback(() => {
    if (filteredProjects.length <= 0) {
      addToast('当前没有可导出的项目记录', 'error');
      return;
    }

    const header = ['kind', 'project_id', 'title', 'status', 'username', 'updated_at', 'is_stale'];
    const rows = filteredProjects.map((item) => {
      const kind = normalizeKind(item.kind);
      const ts = getProjectTimestamp(item);
      const isStale = ts > 0 && Date.now() - ts >= staleThresholdMs;
      return [
        kind,
        item.project_id,
        item.title || '未命名项目',
        item.status || 'UNKNOWN',
        item.username,
        item.updated_at || item.created_at || '',
        isStale ? 'true' : 'false',
      ];
    });

    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    downloadCsv(header, rows, `admin-projects-${stamp}.csv`);

    addToast(`已导出 ${filteredProjects.length} 条项目记录`, 'success');
  }, [addToast, filteredProjects, staleThresholdMs]);

  if (!isAdmin) {
    return <AdminAccessDenied />;
  }

  return (
    <div className="page-shell min-h-screen overflow-hidden">
      <div className="ambient-orb -left-14 top-6 h-64 w-64 bg-book-primary/9" />
      <div className="ambient-orb right-[-5rem] top-20 h-72 w-72 bg-book-primary-light/10" />

      <div className="relative mx-auto flex min-h-screen w-full max-w-[1600px] flex-col gap-4 px-3 py-3 sm:px-5 sm:py-5">
        <AdminPanelHeader
          current="projects"
          title="管理员项目监控"
          description="查看项目规模、状态分布、陈旧风险和高活跃用户"
          onRefresh={fetchData}
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
              <FolderKanban size={14} />
              项目总数
            </div>
            <div className="mt-3 font-serif text-3xl font-bold text-book-text-main">{data.summary.total_projects}</div>
            <div className="mt-2 text-sm text-book-text-sub">小说 + Prompt 项目总和</div>
          </div>
          <div className="metric-tile">
            <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">小说项目</div>
            <div className="mt-3 font-serif text-3xl font-bold text-book-text-main">{data.summary.total_novel_projects}</div>
            <div className="mt-2 text-sm text-book-text-sub">全量聚合统计</div>
          </div>
          <div className="metric-tile">
            <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">Prompt 项目</div>
            <div className="mt-3 font-serif text-3xl font-bold text-book-text-main">{data.summary.total_coding_projects}</div>
            <div className="mt-2 text-sm text-book-text-sub">更新时间：{formatDate(data.generated_at)}</div>
          </div>
          <div className="metric-tile">
            <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
              陈旧项目（&gt;{Math.max(1, staleDays)}天）
            </div>
            <div className="mt-3 font-serif text-3xl font-bold text-book-text-main">{staleCount}</div>
            <div className="mt-2 text-sm text-book-text-sub">基于最近项目样本识别</div>
          </div>
        </section>

        <section className="grid gap-4 xl:grid-cols-3">
          <BookCard className="rounded-[28px] bg-book-bg-paper/82">
            <LazyRender placeholderHeight={220} rootMargin="360px 0px">
              <AdminDonutChart
                title="项目类型占比"
                data={projectMixData}
                centerLabel="项目总量"
                centerValue={data.summary.total_projects}
              />
            </LazyRender>
          </BookCard>

          <BookCard className="rounded-[28px] bg-book-bg-paper/82">
            <LazyRender placeholderHeight={180} rootMargin="360px 0px">
              <AdminStackedProgress title="样本新鲜度" segments={freshnessSegments} />
            </LazyRender>
          </BookCard>

          <BookCard className="rounded-[28px] bg-book-bg-paper/82">
            <LazyRender placeholderHeight={220} rootMargin="360px 0px">
              <AdminBarListChart title="高频状态排行" data={topStatusRows} />
            </LazyRender>
          </BookCard>
        </section>

        <section className="dramatic-surface rounded-[30px]">
          <div className="relative z-[1] space-y-4 px-5 py-5 sm:px-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                  Project Trend
                </div>
                <h2 className="mt-2 font-serif text-2xl font-bold text-book-text-main">
                  近 {trendData?.days || 21} 天新增趋势
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
                series={projectTrendSeries}
                mode={trendMode}
                emptyText="暂无项目趋势数据"
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
                <h2 className="mt-2 font-serif text-2xl font-bold text-book-text-main">筛选最近项目</h2>
                <p className="mt-2 text-sm leading-relaxed text-book-text-sub">
                  通过类型、状态、陈旧阈值和关键词快速锁定需要处理的项目集合。
                </p>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
              <BookInput
                label="关键词"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="标题 / 用户名 / 项目ID"
              />

              <div>
                <label className="block text-sm font-bold text-book-text-sub mb-1.5 ml-1">项目类型</label>
                <select
                  value={kindFilter}
                  onChange={(e) => setKindFilter(e.target.value as KindFilter)}
                  className={adminProjectSelectClassName}
                >
                  <option value="all">全部</option>
                  <option value="novel">小说</option>
                  <option value="coding">Prompt</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-bold text-book-text-sub mb-1.5 ml-1">项目状态</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className={adminProjectSelectClassName}
                >
                  <option value="all">全部</option>
                  {statusOptions.map((status) => (
                    <option value={status} key={status}>{status}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="block text-sm font-bold text-book-text-sub mb-1.5 ml-1">排序方式</label>
                <select
                  value={sortMode}
                  onChange={(e) => setSortMode(e.target.value as SortMode)}
                  className={adminProjectSelectClassName}
                >
                  <option value="updated_desc">最近更新优先</option>
                  <option value="updated_asc">最久未更新优先</option>
                  <option value="title">按标题</option>
                  <option value="username">按用户</option>
                </select>
              </div>

              <BookInput
                label="陈旧阈值（天）"
                type="number"
                min={1}
                max={365}
                value={staleDays}
                onChange={(e) => setStaleDays(Number(e.target.value) || 30)}
              />

              <div className="flex items-end">
                <label className="inline-flex items-center gap-2 text-sm text-book-text-sub">
                  <input
                    type="checkbox"
                    checked={staleOnly}
                    onChange={(e) => setStaleOnly(e.target.checked)}
                    className="rounded border-book-border text-book-primary focus:ring-book-primary"
                  />
                  仅看陈旧项目
                </label>
              </div>
            </div>

            </div>

            <div className="rounded-[24px] border border-book-border/45 bg-book-bg-paper/72 p-4">
              <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                当前结果
              </div>
              <div className="mt-3 font-serif text-3xl font-bold text-book-text-main">{filteredProjects.length}</div>
              <div className="mt-2 text-sm text-book-text-sub">命中记录 / 最近样本 {data.recent_projects.length}</div>

              <div className="mt-4 space-y-2">
                <div className="rounded-[18px] border border-book-border/40 px-3 py-2 text-xs text-book-text-muted">
                  新鲜项目：<span className="font-semibold text-book-text-main">{freshCount}</span>
                </div>
                <div className="rounded-[18px] border border-book-border/40 px-3 py-2 text-xs text-book-text-muted">
                  陈旧项目：<span className="font-semibold text-book-text-main">{staleCount}</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="space-y-4">
            <section className="dramatic-surface rounded-[30px]">
              <div className="relative z-[1] space-y-4 px-5 py-5 sm:px-6">
                <div>
                  <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                    Status Map
                  </div>
                  <h2 className="mt-2 font-serif text-2xl font-bold text-book-text-main">全量状态分布</h2>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
              {statusDistributionRows.map((section) => (
                  <div key={section.kind} className="space-y-2 rounded-[24px] border border-book-border/40 p-4">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-book-text-main">{section.label}</span>
                      <span className="text-book-text-muted">总计 {section.total}</span>
                    </div>
                    {section.rows.length > 0 ? section.rows.map((item) => {
                      const percent = formatPercent(item.count, section.total);
                      return (
                        <div key={`${section.kind}-${item.status}`} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-mono text-book-text-main">{item.status}</span>
                            <span className="text-book-text-muted">{item.count} · {percent}%</span>
                          </div>
                          <div className="h-1.5 rounded bg-book-bg">
                            <div className={`h-1.5 rounded ${section.barClass}`} style={{ width: `${Math.min(percent, 100)}%` }} />
                          </div>
                        </div>
                      );
                    }) : <div className="text-xs text-book-text-muted">暂无状态数据</div>}
                  </div>
                ))}
                </div>
              </div>
            </section>

            <section className="dramatic-surface rounded-[30px]">
              <div className="relative z-[1] space-y-4 px-5 py-5 sm:px-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                      Recent Projects
                    </div>
                    <h2 className="mt-2 font-serif text-2xl font-bold text-book-text-main">最近项目列表</h2>
                  </div>
                  <span className="story-pill">显示 {visibleProjects.length} / {filteredProjects.length}</span>
                </div>

                <div className="overflow-x-auto rounded-[24px] border border-book-border/40 bg-book-bg-paper/62 px-4">
                  <table className="min-w-[1020px] w-full text-sm">
                    <thead>
                      <tr className="border-b border-book-border/50 text-book-text-muted">
                        <th className="py-3 pr-3 text-left">类型</th>
                        <th className="py-3 pr-3 text-left">项目标题</th>
                        <th className="py-3 pr-3 text-left">状态</th>
                        <th className="py-3 pr-3 text-left">所属用户</th>
                        <th className="py-3 pr-3 text-left">项目ID</th>
                        <th className="py-3 text-left">更新时间</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleProjects.map((item) => {
                        const kind = normalizeKind(item.kind);
                        const updatedAt = item.updated_at || item.created_at;
                        const ageMs = Date.now() - getProjectTimestamp(item);
                        const isStale = ageMs >= staleThresholdMs;

                        return (
                          <tr key={`${kind}-${item.project_id}`} className="border-b border-book-border/30 text-book-text-main">
                            <td className="py-3 pr-3 align-top">
                              <span className={`rounded-full px-2 py-1 text-xs ${kind === 'novel' ? 'bg-book-primary/10 text-book-primary' : 'bg-book-accent/10 text-book-accent'}`}>
                                {kind === 'novel' ? '小说' : 'Prompt'}
                              </span>
                            </td>
                            <td className="py-3 pr-3 align-top">
                              <div className="font-medium">{item.title || '未命名项目'}</div>
                            </td>
                            <td className="py-3 pr-3 align-top">
                              <div className="flex flex-wrap gap-1">
                                <span className="font-mono text-xs">{item.status || 'UNKNOWN'}</span>
                                {isStale ? (
                                  <span className="rounded-full bg-yellow-500/15 px-2 py-0.5 text-[10px] text-yellow-700 dark:text-yellow-300">
                                    陈旧
                                  </span>
                                ) : null}
                              </div>
                            </td>
                            <td className="py-3 pr-3 align-top">
                              <span className="font-mono text-xs">{item.username}</span>
                            </td>
                            <td className="py-3 pr-3 align-top">
                              <span className="font-mono text-[11px] text-book-text-muted">{item.project_id}</span>
                            </td>
                            <td className="py-3 align-top text-xs text-book-text-muted">{formatDate(updatedAt)}</td>
                          </tr>
                        );
                      })}
                      {!loading && filteredProjects.length === 0 ? (
                        <tr>
                          <td className="py-6 text-center text-book-text-muted" colSpan={6}>暂无匹配项目</td>
                        </tr>
                      ) : null}
                    </tbody>
                  </table>
                </div>

                {loading ? (
                  <div className="flex items-center gap-2 text-xs text-book-text-muted">
                    <RefreshCw size={12} className="animate-spin" />
                    加载中…
                  </div>
                ) : null}
                {!loading && visibleProjects.length < filteredProjects.length ? (
                  <div className="flex items-center justify-between text-xs text-book-text-muted">
                    <span>已渲染 {visibleProjects.length} / {filteredProjects.length} 条</span>
                    <BookButton
                      variant="ghost"
                      size="sm"
                      onClick={() => setProjectRowLimit((value) => value + 80)}
                    >
                      加载更多（剩余 {filteredProjects.length - visibleProjects.length} 条）
                    </BookButton>
                  </div>
                ) : null}
              </div>
            </section>
          </div>

          <div className="space-y-4">
            <section className="dramatic-surface rounded-[30px]">
              <div className="relative z-[1] space-y-4 px-5 py-5">
                <div>
                  <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                    Top Owners
                  </div>
                  <h2 className="mt-2 font-serif text-2xl font-bold text-book-text-main">项目最多用户 TOP</h2>
                </div>
                {data.top_users.length > 0 ? (
                  <div className="space-y-2">
                    {data.top_users.slice(0, 8).map((item) => (
                      <div key={`top-project-user-${item.user_id}`} className="rounded-[18px] border border-book-border/40 px-3 py-3 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-book-text-main">{item.username}</span>
                          <span className="font-bold text-book-primary">{item.total_projects}</span>
                        </div>
                        <div className="mt-1 text-book-text-muted">小说 {item.novel_projects} · Prompt {item.coding_projects}</div>
                        <div className="mt-1 text-book-text-muted">最近更新：{formatDate(item.last_project_updated_at)}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-book-text-muted">暂无排行数据</div>
                )}
              </div>
            </section>

            <section className="dramatic-surface rounded-[30px]">
              <div className="relative z-[1] space-y-4 px-5 py-5">
                <div>
                  <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                    Risk Hints
                  </div>
                  <h2 className="mt-2 font-serif text-2xl font-bold text-book-text-main">风险提示</h2>
                </div>
                <div className="space-y-2">
                  {riskHints.map((hint) => (
                    <div key={hint} className="rounded-[18px] border border-book-border/40 px-3 py-3 text-xs leading-relaxed text-book-text-muted">
                      {hint}
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
};
