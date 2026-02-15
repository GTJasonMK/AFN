import React, { startTransition, useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, AlertTriangle, Boxes, FolderKanban, Gauge, Users } from 'lucide-react';
import { adminDashboardApi, AdminDashboardTrendsResponse, AdminOverviewResponse, AdminStatusCount } from '../api/adminDashboard';
import { BookCard } from '../components/ui/BookCard';
import { AdminPanelHeader } from '../components/admin/AdminPanelHeader';
import { AdminAccessDenied } from '../components/admin/AdminAccessDenied';
import { AdminBarListChart, AdminDonutChart, AdminStackedProgress, AdminTrendChart } from '../components/admin/AdminCharts';
import { LazyRender } from '../components/admin/LazyRender';
import { isAdminUser, useAuthStore } from '../store/auth';
import { scheduleIdleTask } from '../utils/scheduleIdleTask';
import { readBootstrapCache, writeBootstrapCache } from '../utils/bootstrapCache';

const emptyData: AdminOverviewResponse = {
  summary: {
    total_users: 0,
    active_users: 0,
    recently_active_users: 0,
    total_novel_projects: 0,
    total_coding_projects: 0,
    total_projects: 0,
    total_llm_configs: 0,
    total_embedding_configs: 0,
    total_image_configs: 0,
    total_theme_configs: 0,
  },
  novel_status_distribution: [],
  coding_status_distribution: [],
  generated_at: '',
};

type AdminOverviewBootstrapSnapshot = {
  data: AdminOverviewResponse;
  trendData: AdminDashboardTrendsResponse | null;
};

const ADMIN_OVERVIEW_BOOTSTRAP_KEY = 'afn:web:admin:overview:bootstrap:v1';
const ADMIN_OVERVIEW_BOOTSTRAP_TTL_MS = 3 * 60 * 1000;

const formatDate = (value?: string | null): string => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
};

const sumCounts = (rows: AdminStatusCount[]) => rows.reduce((total, item) => total + Number(item.count || 0), 0);

const ratePercent = (numerator: number, denominator: number): number => {
  if (denominator <= 0) return 0;
  return Math.round((numerator / denominator) * 1000) / 10;
};

export const AdminOverview: React.FC = () => {
  const { authEnabled, user } = useAuthStore();
  const isAdmin = isAdminUser(authEnabled, user);
  const initialCacheRef = React.useRef<AdminOverviewBootstrapSnapshot | null>(
    readBootstrapCache<AdminOverviewBootstrapSnapshot>(
      ADMIN_OVERVIEW_BOOTSTRAP_KEY,
      ADMIN_OVERVIEW_BOOTSTRAP_TTL_MS,
    ),
  );

  const [data, setData] = useState<AdminOverviewResponse>(() => initialCacheRef.current?.data ?? emptyData);
  const [trendData, setTrendData] = useState<AdminDashboardTrendsResponse | null>(
    () => initialCacheRef.current?.trendData ?? null
  );
  const [trendMode, setTrendMode] = useState<'line' | 'bar'>('line');
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const overviewRes = await adminDashboardApi.overview();
      setData(overviewRes);

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
    writeBootstrapCache<AdminOverviewBootstrapSnapshot>(ADMIN_OVERVIEW_BOOTSTRAP_KEY, {
      data,
      trendData,
    });
  }, [data, trendData]);

  const configTotal =
    data.summary.total_llm_configs +
    data.summary.total_embedding_configs +
    data.summary.total_image_configs +
    data.summary.total_theme_configs;

  const ratioCards = useMemo(() => {
    const totalUsers = data.summary.total_users;
    const totalProjects = data.summary.total_projects;

    return [
      {
        key: 'activeRate',
        label: '启用用户率',
        value: ratePercent(data.summary.active_users, totalUsers),
        suffix: '%',
        description: `启用 ${data.summary.active_users} / 总计 ${totalUsers}`,
      },
      {
        key: 'recentRate',
        label: '7天活跃率',
        value: ratePercent(data.summary.recently_active_users, totalUsers),
        suffix: '%',
        description: `活跃 ${data.summary.recently_active_users} / 总计 ${totalUsers}`,
      },
      {
        key: 'projectsPerUser',
        label: '人均项目数',
        value: Number((totalProjects / Math.max(totalUsers, 1)).toFixed(2)),
        suffix: '',
        description: `项目 ${totalProjects} / 用户 ${totalUsers}`,
      },
      {
        key: 'configsPerUser',
        label: '人均配置数',
        value: Number((configTotal / Math.max(totalUsers, 1)).toFixed(2)),
        suffix: '',
        description: `配置 ${configTotal} / 用户 ${totalUsers}`,
      },
    ];
  }, [
    data.summary.total_users,
    data.summary.active_users,
    data.summary.recently_active_users,
    data.summary.total_projects,
    configTotal,
  ]);

  const userSegments = useMemo(() => {
    const recent = Math.min(data.summary.recently_active_users, data.summary.active_users);
    const activeNotRecent = Math.max(data.summary.active_users - recent, 0);
    const inactive = Math.max(data.summary.total_users - data.summary.active_users, 0);

    return [
      { label: '7天活跃', value: recent, color: '#6366F1' },
      { label: '启用未活跃', value: activeNotRecent, color: '#14B8A6' },
      { label: '禁用用户', value: inactive, color: '#EF4444' },
    ];
  }, [data.summary.recently_active_users, data.summary.active_users, data.summary.total_users]);

  const projectMixData = useMemo(() => {
    return [
      { label: '小说项目', value: data.summary.total_novel_projects, color: '#6366F1' },
      { label: 'Prompt 项目', value: data.summary.total_coding_projects, color: '#14B8A6' },
    ];
  }, [data.summary.total_novel_projects, data.summary.total_coding_projects]);

  const configMixData = useMemo(() => {
    return [
      { label: 'LLM', value: data.summary.total_llm_configs, color: '#6366F1' },
      { label: '嵌入', value: data.summary.total_embedding_configs, color: '#14B8A6' },
      { label: '图片', value: data.summary.total_image_configs, color: '#F59E0B' },
      { label: '主题', value: data.summary.total_theme_configs, color: '#8B5CF6' },
    ];
  }, [
    data.summary.total_llm_configs,
    data.summary.total_embedding_configs,
    data.summary.total_image_configs,
    data.summary.total_theme_configs,
  ]);

  const overviewTrendSeries = useMemo(() => {
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

  const healthHints = useMemo(() => {
    const hints: string[] = [];

    const inactiveUsers = Math.max(data.summary.total_users - data.summary.active_users, 0);
    const inactiveRate = ratePercent(inactiveUsers, data.summary.total_users);
    if (inactiveUsers > 0 && inactiveRate >= 40) {
      hints.push(`当前禁用用户比例为 ${inactiveRate}%（建议排查账号策略）。`);
    }

    const activeRate = ratePercent(data.summary.recently_active_users, data.summary.total_users);
    if (data.summary.total_users > 0 && activeRate < 30) {
      hints.push(`最近活跃率仅 ${activeRate}%（建议关注留存和任务完成率）。`);
    }

    const codingShare = ratePercent(data.summary.total_coding_projects, data.summary.total_projects);
    if (data.summary.total_projects > 0 && codingShare >= 60) {
      hints.push(`Prompt 项目占比 ${codingShare}%（可重点关注代码工作流负载）。`);
    }

    const configPerUser = Number((configTotal / Math.max(data.summary.total_users, 1)).toFixed(2));
    if (data.summary.total_users > 0 && configPerUser >= 8) {
      hints.push(`人均配置数达到 ${configPerUser}（建议清理历史配置，降低维护成本）。`);
    }

    if (hints.length === 0) {
      hints.push('暂无明显风险指标，整体运行状态良好。');
    }

    return hints;
  }, [data.summary, configTotal]);

  const statusAlertData = useMemo(() => {
    const rows: Array<{ label: string; value: number; color: string }> = [];

    data.novel_status_distribution.forEach((item) => {
      rows.push({
        label: `小说 · ${item.status}`,
        value: Number(item.count || 0),
        color: '#6366F1',
      });
    });

    data.coding_status_distribution.forEach((item) => {
      rows.push({
        label: `Prompt · ${item.status}`,
        value: Number(item.count || 0),
        color: '#14B8A6',
      });
    });

    return rows.sort((a, b) => b.value - a.value).slice(0, 8);
  }, [data.coding_status_distribution, data.novel_status_distribution]);

  if (!isAdmin) {
    return <AdminAccessDenied />;
  }

  const novelTotal = sumCounts(data.novel_status_distribution);
  const codingTotal = sumCounts(data.coding_status_distribution);

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="max-w-7xl mx-auto space-y-4">
        <AdminPanelHeader
          current="overview"
          title="管理员总览"
          description="查看用户、项目、配置的全局运行情况"
          onRefresh={fetchData}
          refreshing={loading}
        />

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
          <BookCard className="space-y-1">
            <div className="text-xs text-book-text-muted flex items-center gap-1"><Users size={14} /> 用户概况</div>
            <div className="text-2xl font-bold text-book-text-main">{data.summary.total_users}</div>
            <div className="text-xs text-book-text-muted">
              启用 {data.summary.active_users} · 7天活跃 {data.summary.recently_active_users}
            </div>
          </BookCard>

          <BookCard className="space-y-1">
            <div className="text-xs text-book-text-muted flex items-center gap-1"><FolderKanban size={14} /> 项目总量</div>
            <div className="text-2xl font-bold text-book-text-main">{data.summary.total_projects}</div>
            <div className="text-xs text-book-text-muted">
              小说 {data.summary.total_novel_projects} · Prompt {data.summary.total_coding_projects}
            </div>
          </BookCard>

          <BookCard className="space-y-1">
            <div className="text-xs text-book-text-muted flex items-center gap-1"><Boxes size={14} /> 配置总量</div>
            <div className="text-2xl font-bold text-book-text-main">{configTotal}</div>
            <div className="text-xs text-book-text-muted">
              LLM {data.summary.total_llm_configs} · 嵌入 {data.summary.total_embedding_configs}
            </div>
          </BookCard>

          <BookCard className="space-y-1">
            <div className="text-xs text-book-text-muted flex items-center gap-1"><Activity size={14} /> 统计时间</div>
            <div className="text-sm font-bold text-book-text-main">{formatDate(data.generated_at)}</div>
            <div className="text-xs text-book-text-muted">数据实时聚合返回</div>
          </BookCard>
        </div>

        <BookCard className="space-y-3">
          <h2 className="font-bold text-sm text-book-text-main flex items-center gap-2">
            <Gauge size={14} className="text-book-primary" />
            关键比率
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            {ratioCards.map((item) => (
              <div key={item.key} className="space-y-1 border border-book-border/40 rounded-lg px-3 py-2">
                <div className="text-xs text-book-text-muted">{item.label}</div>
                <div className="text-2xl font-bold text-book-text-main">{item.value}{item.suffix}</div>
                <div className="text-[11px] text-book-text-muted">{item.description}</div>
              </div>
            ))}
          </div>
        </BookCard>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <BookCard>
            <LazyRender placeholderHeight={220} rootMargin="360px 0px">
              <AdminDonutChart
                title="项目结构占比"
                data={projectMixData}
                centerLabel="项目总量"
                centerValue={data.summary.total_projects}
              />
            </LazyRender>
          </BookCard>

          <BookCard>
            <LazyRender placeholderHeight={180} rootMargin="360px 0px">
              <AdminStackedProgress title="用户活跃结构" segments={userSegments} />
            </LazyRender>
          </BookCard>

          <BookCard>
            <LazyRender placeholderHeight={220} rootMargin="360px 0px">
              <AdminBarListChart title="配置类型规模" data={configMixData} totalOverride={configTotal} />
            </LazyRender>
          </BookCard>
        </div>

        <BookCard className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-bold text-sm text-book-text-main">近{trendData?.days || 21}天增长趋势</h2>
            <div className="inline-flex rounded-lg border border-book-border/50 overflow-hidden">
              <button
                className={`px-3 py-1 text-xs ${trendMode === 'line' ? 'bg-book-primary/15 text-book-primary' : 'bg-book-bg-paper text-book-text-muted'}`}
                onClick={() => setTrendMode('line')}
              >
                折线图
              </button>
              <button
                className={`px-3 py-1 text-xs ${trendMode === 'bar' ? 'bg-book-primary/15 text-book-primary' : 'bg-book-bg-paper text-book-text-muted'}`}
                onClick={() => setTrendMode('bar')}
              >
                柱状图
              </button>
            </div>
          </div>
          <LazyRender placeholderHeight={280} rootMargin="420px 0px">
            <AdminTrendChart
              series={overviewTrendSeries}
              mode={trendMode}
              emptyText="暂无趋势数据"
            />
          </LazyRender>
        </BookCard>

        <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-4">
          <BookCard className="space-y-3">
            <h2 className="font-bold text-sm text-book-text-main">快捷跳转</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <Link to="/admin/users" className="text-xs border border-book-border/40 rounded-lg px-3 py-2 hover:border-book-primary/40 transition-colors">
                <div className="font-bold text-book-text-main">用户面板</div>
                <div className="text-book-text-muted mt-1">账号管理、活跃监控、用户操作</div>
              </Link>
              <Link to="/admin/projects" className="text-xs border border-book-border/40 rounded-lg px-3 py-2 hover:border-book-primary/40 transition-colors">
                <div className="font-bold text-book-text-main">项目面板</div>
                <div className="text-book-text-muted mt-1">状态分布、陈旧检测、排行</div>
              </Link>
              <Link to="/admin/configs" className="text-xs border border-book-border/40 rounded-lg px-3 py-2 hover:border-book-primary/40 transition-colors">
                <div className="font-bold text-book-text-main">配置面板</div>
                <div className="text-book-text-muted mt-1">测试状态、激活比例、异常配置</div>
              </Link>
            </div>
          </BookCard>

          <BookCard className="space-y-3">
            <h2 className="font-bold text-sm text-book-text-main flex items-center gap-2">
              <AlertTriangle size={14} className="text-book-accent" />
              监控提示
            </h2>
            <div className="space-y-2">
              {healthHints.map((hint) => (
                <div key={hint} className="text-xs border border-book-border/40 rounded-lg px-3 py-2 text-book-text-muted leading-relaxed">
                  {hint}
                </div>
              ))}
            </div>
          </BookCard>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <BookCard className="space-y-3">
            <h2 className="font-bold text-sm text-book-text-main">小说项目状态分布</h2>
            <div className="space-y-2">
              {data.novel_status_distribution.length > 0 ? (
                data.novel_status_distribution.map((item) => {
                  const percent = ratePercent(item.count, novelTotal);
                  return (
                    <div key={`novel-${item.status}`} className="space-y-1 border border-book-border/40 rounded-lg px-3 py-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-mono text-xs text-book-text-main">{item.status}</span>
                        <span className="font-bold text-book-primary">{item.count}</span>
                      </div>
                      <div className="h-1.5 rounded bg-book-bg">
                        <div className="h-1.5 rounded bg-book-primary" style={{ width: `${Math.min(percent, 100)}%` }} />
                      </div>
                      <div className="text-[11px] text-book-text-muted">占比 {percent}%</div>
                    </div>
                  );
                })
              ) : (
                <div className="text-xs text-book-text-muted">暂无小说项目数据</div>
              )}
            </div>
          </BookCard>

          <BookCard className="space-y-3">
            <h2 className="font-bold text-sm text-book-text-main">Prompt 项目状态分布</h2>
            <div className="space-y-2">
              {data.coding_status_distribution.length > 0 ? (
                data.coding_status_distribution.map((item) => {
                  const percent = ratePercent(item.count, codingTotal);
                  return (
                    <div key={`coding-${item.status}`} className="space-y-1 border border-book-border/40 rounded-lg px-3 py-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-mono text-xs text-book-text-main">{item.status}</span>
                        <span className="font-bold text-book-primary">{item.count}</span>
                      </div>
                      <div className="h-1.5 rounded bg-book-bg">
                        <div className="h-1.5 rounded bg-book-accent" style={{ width: `${Math.min(percent, 100)}%` }} />
                      </div>
                      <div className="text-[11px] text-book-text-muted">占比 {percent}%</div>
                    </div>
                  );
                })
              ) : (
                <div className="text-xs text-book-text-muted">暂无 Prompt 项目数据</div>
              )}
            </div>
          </BookCard>
        </div>

        <BookCard>
          <LazyRender placeholderHeight={220} rootMargin="520px 0px">
            <AdminBarListChart title="高频状态排行（小说 + Prompt）" data={statusAlertData} />
          </LazyRender>
        </BookCard>
      </div>
    </div>
  );
};
