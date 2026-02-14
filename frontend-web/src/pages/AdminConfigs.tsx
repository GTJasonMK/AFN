import React, { startTransition, useCallback, useDeferredValue, useEffect, useMemo, useState } from 'react';
import { Boxes, Download, RefreshCw, SlidersHorizontal, Users } from 'lucide-react';
import { adminDashboardApi, AdminActiveConfigItem, AdminConfigsResponse, AdminDashboardTrendsResponse } from '../api/adminDashboard';
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

type ConfigTypeFilter = 'all' | 'llm' | 'embedding' | 'image' | 'theme';
type TestStatusFilter = 'all' | 'success' | 'failed' | 'pending' | 'untested';

const emptyData: AdminConfigsResponse = {
  summary: {
    total_configs: 0,
    total_active_configs: 0,
    by_type: [],
  },
  top_users: [],
  active_configs: [],
  test_status_distribution: [],
  generated_at: '',
};

const formatDate = (value?: string | null): string => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
};

const typeLabelMap: Record<string, string> = {
  llm: 'LLM',
  embedding: '嵌入',
  image: '图片',
  theme: '主题',
};

const normalizeTestStatus = (value?: string | null): TestStatusFilter => {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized === 'success') return 'success';
  if (normalized === 'failed') return 'failed';
  if (normalized === 'pending') return 'pending';
  return 'untested';
};

const testStatusLabel: Record<TestStatusFilter, string> = {
  all: '全部',
  success: '成功',
  failed: '失败',
  pending: '进行中',
  untested: '未测试',
};

const testStatusClassMap: Record<TestStatusFilter, string> = {
  all: 'bg-book-bg text-book-text-main',
  success: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
  untested: 'bg-book-primary/10 text-book-primary',
};

const formatPercent = (numerator: number, denominator: number): number => {
  if (denominator <= 0) return 0;
  return Math.round((numerator / denominator) * 1000) / 10;
};

export const AdminConfigs: React.FC = () => {
  const { addToast } = useToast();
  const { authEnabled, user } = useAuthStore();
  const isAdmin = isAdminUser(authEnabled, user);

  const [data, setData] = useState<AdminConfigsResponse>(emptyData);
  const [trendData, setTrendData] = useState<AdminDashboardTrendsResponse | null>(null);
  const [trendMode, setTrendMode] = useState<'line' | 'bar'>('line');
  const [loading, setLoading] = useState(false);
  const [typeFilter, setTypeFilter] = useState<ConfigTypeFilter>('all');
  const [testFilter, setTestFilter] = useState<TestStatusFilter>('all');
  const [keyword, setKeyword] = useState('');
  const deferredKeyword = useDeferredValue(keyword);
  const [configRowLimit, setConfigRowLimit] = useState(100);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const configsRes = await adminDashboardApi.configs(200);
      setData(configsRes);

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

  const statusStats = useMemo(() => {
    const stats: Record<TestStatusFilter, number> = {
      all: 0,
      success: 0,
      failed: 0,
      pending: 0,
      untested: 0,
    };

    if (data.test_status_distribution.length > 0) {
      data.test_status_distribution.forEach((item) => {
        const key = normalizeTestStatus(item.status);
        stats[key] += Number(item.count || 0);
      });
      stats.all = stats.success + stats.failed + stats.pending + stats.untested;
      return stats;
    }

    stats.all = data.active_configs.length;
    data.active_configs.forEach((item) => {
      const key = normalizeTestStatus(item.test_status);
      stats[key] += 1;
    });

    return stats;
  }, [data.active_configs, data.test_status_distribution]);

  const filteredActiveConfigs = useMemo(() => {
    const key = deferredKeyword.trim().toLowerCase();

    return data.active_configs.filter((item: AdminActiveConfigItem) => {
      const configType = String(item.config_type || '').toLowerCase();
      if (typeFilter !== 'all' && configType !== typeFilter) {
        return false;
      }

      const testStatus = normalizeTestStatus(item.test_status);
      if (testFilter !== 'all' && testStatus !== testFilter) {
        return false;
      }

      if (!key) return true;

      return (
        String(item.config_name || '').toLowerCase().includes(key) ||
        String(item.username || '').toLowerCase().includes(key) ||
        String(item.config_id || '').toLowerCase().includes(key)
      );
    });
  }, [data.active_configs, typeFilter, testFilter, deferredKeyword]);

  const visibleActiveConfigs = useMemo(
    () => filteredActiveConfigs.slice(0, configRowLimit),
    [filteredActiveConfigs, configRowLimit]
  );

  useEffect(() => {
    setConfigRowLimit(100);
  }, [data.active_configs.length, deferredKeyword, typeFilter, testFilter]);

  const problemConfigs = useMemo(() => {
    return data.active_configs
      .filter((item) => {
        const status = normalizeTestStatus(item.test_status);
        return status === 'failed' || status === 'pending';
      })
      .slice(0, 8);
  }, [data.active_configs]);

  const activeConfigUsers = useMemo(() => {
    const buckets = new Map<string, { username: string; count: number }>();

    data.active_configs.forEach((item) => {
      const key = String(item.username || 'unknown');
      const existing = buckets.get(key);
      if (existing) {
        existing.count += 1;
        return;
      }
      buckets.set(key, { username: key, count: 1 });
    });

    return Array.from(buckets.values())
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);
  }, [data.active_configs]);

  const configTypeDonutData = useMemo(() => {
    return data.summary.by_type.map((item) => ({
      label: typeLabelMap[item.config_type] || item.config_type,
      value: Number(item.total || 0),
    }));
  }, [data.summary.by_type]);

  const testStatusChartData = useMemo(() => {
    return [
      { label: '成功', value: statusStats.success, color: '#14B8A6' },
      { label: '失败', value: statusStats.failed, color: '#EF4444' },
      { label: '进行中', value: statusStats.pending, color: '#F59E0B' },
      { label: '未测试', value: statusStats.untested, color: '#6366F1' },
    ];
  }, [statusStats]);

  const activationSegments = useMemo(() => {
    const active = Number(data.summary.total_active_configs || 0);
    const inactive = Math.max(Number(data.summary.total_configs || 0) - active, 0);
    return [
      { label: '激活配置', value: active, color: '#14B8A6' },
      { label: '未激活配置', value: inactive, color: '#A1A1AA' },
    ];
  }, [data.summary.total_active_configs, data.summary.total_configs]);

  const problemByTypeRows = useMemo(() => {
    const counts = new Map<string, number>();
    problemConfigs.forEach((item) => {
      const key = String(item.config_type || 'unknown');
      counts.set(key, (counts.get(key) || 0) + 1);
    });

    return Array.from(counts.entries()).map(([type, value]) => ({
      label: `${typeLabelMap[type] || type} 异常`,
      value,
    }));
  }, [problemConfigs]);

  const configTrendSeries = useMemo(() => {
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
      { label: '新建LLM配置', color: '#6366F1', points: toPoints('new_llm_configs') },
      { label: '新建嵌入配置', color: '#14B8A6', points: toPoints('new_embedding_configs') },
      { label: '新建图片配置', color: '#F59E0B', points: toPoints('new_image_configs') },
      { label: '新建主题配置', color: '#8B5CF6', points: toPoints('new_theme_configs') },
      { label: '新建配置总量', color: '#EF4444', points: toPoints('new_configs') },
    ].filter((item) => item.points.length > 0);
  }, [trendData]);

  const healthHints = useMemo(() => {
    const hints: string[] = [];

    const activeRate = formatPercent(data.summary.total_active_configs, data.summary.total_configs);
    if (data.summary.total_configs > 0 && activeRate < 20) {
      hints.push(`激活配置率仅 ${activeRate}%（建议清理历史配置并设置默认激活策略）。`);
    }

    const failedRate = formatPercent(statusStats.failed, statusStats.all);
    if (statusStats.all > 0 && failedRate >= 20) {
      hints.push(`测试失败占比 ${failedRate}%（建议优先排查失败配置连接参数）。`);
    }

    const pendingRate = formatPercent(statusStats.pending, statusStats.all);
    if (statusStats.all > 0 && pendingRate >= 30) {
      hints.push(`测试中配置占比 ${pendingRate}%（可能存在队列堆积）。`);
    }

    if (hints.length === 0) {
      hints.push('当前配置健康度良好，未发现明显异常分布。');
    }

    return hints;
  }, [data.summary.total_active_configs, data.summary.total_configs, statusStats]);

  const handleExportCsv = useCallback(() => {
    if (filteredActiveConfigs.length <= 0) {
      addToast('当前没有可导出的配置记录', 'error');
      return;
    }

    const csvEscape = (value: unknown) => {
      const text = String(value ?? '');
      return `"${text.replace(/"/g, '""')}"`;
    };

    const header = ['config_type', 'config_id', 'config_name', 'username', 'test_status', 'updated_at'];
    const rows = filteredActiveConfigs.map((item) => [
      item.config_type,
      item.config_id,
      item.config_name || '未命名配置',
      item.username,
      normalizeTestStatus(item.test_status),
      item.updated_at || '',
    ]);

    const csv = [header, ...rows].map((line) => line.map(csvEscape).join(',')).join('\n');
    const blob = new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `admin-configs-${stamp}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);

    addToast(`已导出 ${filteredActiveConfigs.length} 条配置记录`, 'success');
  }, [addToast, filteredActiveConfigs]);

  if (!isAdmin) {
    return <AdminAccessDenied />;
  }

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="max-w-7xl mx-auto space-y-4">
        <AdminPanelHeader
          current="configs"
          title="管理员配置监控"
          description="跟踪配置规模、测试状态、异常项和高负载用户"
          onRefresh={fetchData}
          refreshing={loading}
          extraActions={(
            <BookButton variant="secondary" size="sm" onClick={handleExportCsv}>
              <Download size={14} />
              导出CSV
            </BookButton>
          )}
        />

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <BookCard className="space-y-1">
            <div className="text-xs text-book-text-muted flex items-center gap-1"><Boxes size={14} /> 配置总数</div>
            <div className="text-2xl font-bold text-book-text-main">{data.summary.total_configs}</div>
            <div className="text-xs text-book-text-muted">所有用户累计</div>
          </BookCard>
          <BookCard className="space-y-1">
            <div className="text-xs text-book-text-muted flex items-center gap-1"><SlidersHorizontal size={14} /> 激活配置</div>
            <div className="text-2xl font-bold text-book-text-main">{data.summary.total_active_configs}</div>
            <div className="text-xs text-book-text-muted">当前生效配置</div>
          </BookCard>
          <BookCard className="space-y-1">
            <div className="text-xs text-book-text-muted">测试失败</div>
            <div className="text-2xl font-bold text-book-text-main">{statusStats.failed}</div>
            <div className="text-xs text-book-text-muted">失败率 {formatPercent(statusStats.failed, statusStats.all)}%</div>
          </BookCard>
          <BookCard className="space-y-1">
            <div className="text-xs text-book-text-muted flex items-center gap-1"><Users size={14} /> 统计时间</div>
            <div className="text-sm font-bold text-book-text-main">{formatDate(data.generated_at)}</div>
            <div className="text-xs text-book-text-muted">数据库实时聚合</div>
          </BookCard>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <BookCard>
            <LazyRender placeholderHeight={220} rootMargin="360px 0px">
              <AdminDonutChart
                title="配置类型占比"
                data={configTypeDonutData}
                centerLabel="配置总量"
                centerValue={data.summary.total_configs}
              />
            </LazyRender>
          </BookCard>

          <BookCard>
            <LazyRender placeholderHeight={220} rootMargin="360px 0px">
              <AdminDonutChart
                title="测试状态占比"
                data={testStatusChartData}
                centerLabel="测试样本"
                centerValue={statusStats.all}
              />
            </LazyRender>
          </BookCard>

          <BookCard>
            <LazyRender placeholderHeight={180} rootMargin="360px 0px">
              <AdminStackedProgress title="配置激活结构" segments={activationSegments} />
            </LazyRender>
          </BookCard>
        </div>

        <BookCard className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-bold text-sm text-book-text-main">近{trendData?.days || 21}天配置新增趋势</h2>
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
          <LazyRender placeholderHeight={300} rootMargin="420px 0px">
            <AdminTrendChart
              series={configTrendSeries}
              mode={trendMode}
              emptyText="暂无配置趋势数据"
            />
          </LazyRender>
        </BookCard>

        <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-4">
          <BookCard className="space-y-3">
            <h2 className="font-bold text-sm text-book-text-main">配置类型分布</h2>
            <div className="space-y-2">
              {data.summary.by_type.length > 0 ? (
                data.summary.by_type.map((item) => {
                  const label = typeLabelMap[item.config_type] || item.config_type;
                  const activeRate = formatPercent(item.active, item.total);
                  return (
                    <div key={`type-${item.config_type}`} className="space-y-1 border border-book-border/40 rounded-lg px-3 py-2 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs text-book-text-main">{label}</span>
                        <span className="text-book-text-muted">总计 {item.total} · 激活 {item.active}</span>
                      </div>
                      <div className="h-1.5 rounded bg-book-bg">
                        <div className="h-1.5 rounded bg-book-primary" style={{ width: `${Math.min(activeRate, 100)}%` }} />
                      </div>
                      <div className="text-[11px] text-book-text-muted">激活率 {activeRate}%</div>
                    </div>
                  );
                })
              ) : (
                <div className="text-xs text-book-text-muted">暂无配置分布数据</div>
              )}
            </div>
          </BookCard>

          <BookCard className="space-y-3">
            <h2 className="font-bold text-sm text-book-text-main">监控提示</h2>
            <div className="space-y-2">
              {healthHints.map((hint) => (
                <div key={hint} className="text-xs border border-book-border/40 rounded-lg px-3 py-2 text-book-text-muted leading-relaxed">
                  {hint}
                </div>
              ))}
            </div>
          </BookCard>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-4">
          <BookCard className="space-y-3">
            <h2 className="font-bold text-sm text-book-text-main">筛选激活配置</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <BookInput
                label="关键词"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="配置名 / 用户 / 配置ID"
              />

              <div>
                <label className="block text-sm font-bold text-book-text-sub mb-1.5 ml-1">配置类型</label>
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value as ConfigTypeFilter)}
                  className="w-full px-4 py-2 rounded-lg bg-book-bg-paper text-book-text-main border border-book-border"
                >
                  <option value="all">全部类型</option>
                  <option value="llm">LLM</option>
                  <option value="embedding">嵌入</option>
                  <option value="image">图片</option>
                  <option value="theme">主题</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-bold text-book-text-sub mb-1.5 ml-1">测试状态</label>
                <select
                  value={testFilter}
                  onChange={(e) => setTestFilter(e.target.value as TestStatusFilter)}
                  className="w-full px-4 py-2 rounded-lg bg-book-bg-paper text-book-text-main border border-book-border"
                >
                  <option value="all">全部</option>
                  <option value="success">成功</option>
                  <option value="failed">失败</option>
                  <option value="pending">进行中</option>
                  <option value="untested">未测试</option>
                </select>
              </div>
            </div>
            <div className="text-xs text-book-text-muted">当前显示 {filteredActiveConfigs.length} 条激活配置</div>
          </BookCard>

          <BookCard className="space-y-3">
            <h2 className="font-bold text-sm text-book-text-main">活跃配置用户 TOP</h2>
            {activeConfigUsers.length > 0 ? (
              <div className="space-y-2">
                {activeConfigUsers.map((item) => (
                  <div key={`active-user-${item.username}`} className="flex items-center justify-between text-xs border border-book-border/40 rounded-lg px-3 py-2">
                    <span className="font-mono text-book-text-main">{item.username}</span>
                    <span className="font-bold text-book-primary">{item.count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-book-text-muted">暂无排行数据</div>
            )}
          </BookCard>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-4">
          <BookCard>
            <LazyRender placeholderHeight={220} rootMargin="520px 0px">
              <AdminBarListChart
                title="测试状态分布（全量）"
                data={testStatusChartData}
                totalOverride={statusStats.all}
              />
            </LazyRender>
          </BookCard>

          <BookCard className="space-y-3">
            <h2 className="font-bold text-sm text-book-text-main">异常配置</h2>
            {problemConfigs.length > 0 ? (
              <div className="space-y-2">
                {problemConfigs.map((item) => {
                  const statusKey = normalizeTestStatus(item.test_status);
                  return (
                    <div key={`problem-${item.config_type}-${item.config_id}`} className="border border-book-border/40 rounded-lg px-3 py-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-book-text-main">{item.config_name || '未命名配置'}</span>
                        <span className={`px-2 py-0.5 rounded ${testStatusClassMap[statusKey]}`}>{testStatusLabel[statusKey]}</span>
                      </div>
                      <div className="text-book-text-muted mt-1">
                        {typeLabelMap[item.config_type] || item.config_type} · {item.username}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-xs text-book-text-muted">暂无失败或进行中的配置</div>
            )}

            <div className="pt-2 border-t border-book-border/40">
              <LazyRender placeholderHeight={180} rootMargin="620px 0px">
                <AdminBarListChart title="异常类型分布" data={problemByTypeRows} />
              </LazyRender>
            </div>
          </BookCard>
        </div>

        <BookCard className="space-y-3">
          <h2 className="font-bold text-sm text-book-text-main">激活配置明细</h2>

          <div className="overflow-x-auto">
            <table className="min-w-[980px] w-full text-sm">
              <thead>
                <tr className="border-b border-book-border/50 text-book-text-muted">
                  <th className="text-left py-2 pr-3">类型</th>
                  <th className="text-left py-2 pr-3">配置名</th>
                  <th className="text-left py-2 pr-3">所属用户</th>
                  <th className="text-left py-2 pr-3">测试状态</th>
                  <th className="text-left py-2">更新时间</th>
                </tr>
              </thead>
              <tbody>
                {visibleActiveConfigs.map((item) => {
                  const typeLabel = typeLabelMap[item.config_type] || item.config_type;
                  const statusKey = normalizeTestStatus(item.test_status);
                  return (
                    <tr key={`${item.config_type}-${item.config_id}`} className="border-b border-book-border/30 text-book-text-main">
                      <td className="py-3 pr-3 align-top"><span className="font-mono text-xs">{typeLabel}</span></td>
                      <td className="py-3 pr-3 align-top">
                        <div className="font-medium">{item.config_name || '未命名配置'}</div>
                        <div className="text-[11px] text-book-text-muted mt-1">ID: {item.config_id}</div>
                      </td>
                      <td className="py-3 pr-3 align-top"><span className="font-mono text-xs">{item.username}</span></td>
                      <td className="py-3 pr-3 align-top text-xs">
                        <span className={`px-2 py-1 rounded ${testStatusClassMap[statusKey]}`}>{testStatusLabel[statusKey]}</span>
                      </td>
                      <td className="py-3 align-top text-xs text-book-text-muted">{formatDate(item.updated_at)}</td>
                    </tr>
                  );
                })}
                {!loading && filteredActiveConfigs.length === 0 ? (
                  <tr>
                    <td className="py-6 text-center text-book-text-muted" colSpan={5}>暂无匹配配置</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>

          {loading ? (
            <div className="text-xs text-book-text-muted flex items-center gap-2">
              <RefreshCw size={12} className="animate-spin" />
              加载中…
            </div>
          ) : null}
          {!loading && visibleActiveConfigs.length < filteredActiveConfigs.length ? (
            <div className="flex items-center justify-between text-xs text-book-text-muted">
              <span>已渲染 {visibleActiveConfigs.length} / {filteredActiveConfigs.length} 条</span>
              <BookButton
                variant="ghost"
                size="sm"
                onClick={() => setConfigRowLimit((value) => value + 100)}
              >
                加载更多（剩余 {filteredActiveConfigs.length - visibleActiveConfigs.length} 条）
              </BookButton>
            </div>
          ) : null}
        </BookCard>
      </div>
    </div>
  );
};
