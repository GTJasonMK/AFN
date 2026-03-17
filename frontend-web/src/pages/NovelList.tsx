import React, { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Code,
  FolderOpen,
  Plus,
  Settings,
  Upload,
} from 'lucide-react';
import { novelsApi, Novel } from '../api/novels';
import { codingApi, CodingProjectSummary } from '../api/coding';
import { settingsApi } from '../api/settings';
import { ProjectLauncherRow } from '../components/business/ProjectLauncherRow';
import { ProjectListItemModel } from '../components/business/ProjectListItem';
import { useUIStore } from '../store/ui';
import { confirmDialog } from '../components/feedback/ConfirmDialog';
import { scheduleIdleTask } from '../utils/scheduleIdleTask';
import { prefetchProjectRouteByStatus } from '../utils/projectRoutePrefetch';
import { readBootstrapCache, writeBootstrapCache } from '../utils/bootstrapCache';
import { getProjectHomeEntryRoute, getProjectHomeEntryLabel, getProjectKindLabel } from '../utils/projectRouting';
import { getStatusText, CREATIVE_QUOTES } from '../utils/constants';
import { AppViewportFrame, AppViewportScrollArea, AppViewportShell } from '../components/layout/AppViewport';

const ParticleBackgroundLazy = lazy(() =>
  import('../components/ui/ParticleBackground').then((m) => ({ default: m.ParticleBackground }))
);
const CreateProjectModalLazy = lazy(() =>
  import('../components/business/CreateProjectModal').then((m) => ({ default: m.CreateProjectModal }))
);
const ImportModalLazy = lazy(() =>
  import('../components/business/ImportModal').then((m) => ({ default: m.ImportModal }))
);

const NOVEL_LIST_BOOTSTRAP_TTL_MS = 3 * 60 * 1000;
const NOVEL_LIST_BOOTSTRAP_KEY = 'afn:web:novel-list:bootstrap:v1';

type NovelListBootstrapSnapshot = {
  novels: Novel[];
  codingProjects: CodingProjectSummary[];
  codingEnabled: boolean;
};

const formatProjectTimestamp = (value?: string): string => {
  if (!value) return '时间未知';

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '时间未知';

  return parsed.toLocaleString([], {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

type NovelListProps = {
  isDark?: boolean;
};

const projectTitleCollator = new Intl.Collator('zh-Hans-CN', {
  numeric: true,
  sensitivity: 'base',
});

export const NovelList: React.FC<NovelListProps> = ({ isDark = false }) => {
  const initialBootstrapRef = React.useRef<NovelListBootstrapSnapshot | null>(
    readBootstrapCache<NovelListBootstrapSnapshot>(NOVEL_LIST_BOOTSTRAP_KEY, NOVEL_LIST_BOOTSTRAP_TTL_MS)
  );
  const [novels, setNovels] = useState<Novel[]>(() =>
    Array.isArray(initialBootstrapRef.current?.novels) ? initialBootstrapRef.current!.novels : []
  );
  const [codingProjects, setCodingProjects] = useState<CodingProjectSummary[]>(() =>
    Array.isArray(initialBootstrapRef.current?.codingProjects) ? initialBootstrapRef.current!.codingProjects : []
  );
  const [loading, setLoading] = useState(() => !initialBootstrapRef.current);
  const [activeTab, setActiveTab] = useState<'recent' | 'all'>('recent');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createDefaultType, setCreateDefaultType] = useState<'novel' | 'coding'>('novel');
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [codingEnabled, setCodingEnabled] = useState(() => Boolean(initialBootstrapRef.current?.codingEnabled));
  const [showParticleBackground, setShowParticleBackground] = useState(false);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [projectsNotice, setProjectsNotice] = useState<string | null>(null);
  const [isElectronRuntime] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return Boolean((window as any)?.electronAPI?.isElectron);
  });
  const navigate = useNavigate();
  const { openSettings } = useUIStore();

  const quote = useMemo(() => CREATIVE_QUOTES[Math.floor(Math.random() * CREATIVE_QUOTES.length)], []);

  const fetchNovels = useCallback(async () => {
    setLoading((prev) => prev && !initialBootstrapRef.current);
    setProjectsError(null);
    setProjectsNotice(null);

    const bootstrapCodingEnabled = Boolean(initialBootstrapRef.current?.codingEnabled);
    const [advancedConfigResult, novelListResult] = await Promise.allSettled([
      settingsApi.getAdvancedConfig(),
      novelsApi.list(),
    ]);

    const nextCodingEnabled = advancedConfigResult.status === 'fulfilled'
      ? Boolean(advancedConfigResult.value.coding_project_enabled)
      : bootstrapCodingEnabled;

    if (advancedConfigResult.status !== 'fulfilled') {
      console.error('Failed to fetch advanced config', advancedConfigResult.reason);
      setProjectsNotice('高级配置读取失败，首页已退回安全模式展示。');
    }

    setCodingEnabled(nextCodingEnabled);

    if (novelListResult.status === 'fulfilled') {
      setNovels(novelListResult.value);
    } else {
      console.error('Failed to fetch novels', novelListResult.reason);
      if (!initialBootstrapRef.current) {
        setNovels([]);
      }
      setProjectsError('项目列表加载失败，请重试。');
    }

    if (nextCodingEnabled) {
      try {
        const codingList = await codingApi.list();
        setCodingProjects(codingList);
      } catch (error) {
        console.error('Failed to fetch coding projects', error);
        setCodingProjects([]);
        setProjectsNotice((prev) => prev ?? 'Prompt 工程列表读取失败，已先展示小说项目。');
      }
    } else {
      setCodingProjects([]);
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    writeBootstrapCache<NovelListBootstrapSnapshot>(NOVEL_LIST_BOOTSTRAP_KEY, {
      novels,
      codingProjects,
      codingEnabled,
    });
  }, [codingEnabled, codingProjects, novels]);

  useEffect(() => {
    void fetchNovels();
  }, [fetchNovels]);

  useEffect(() => {
    if (loading) return;

    const cancel = scheduleIdleTask(() => {
      setShowParticleBackground(true);
    }, { delay: 1800, timeout: 3600 });

    return cancel;
  }, [loading]);

  const handleProjectLaunch = useCallback((project: ProjectListItemModel) => {
    navigate(getProjectHomeEntryRoute(project));
  }, [navigate]);

  const handleProjectPrefetch = useCallback((project: ProjectListItemModel, trigger: 'hover' | 'commit') => {
    return prefetchProjectRouteByStatus(
      { kind: project.kind, status: project.status },
      { immediate: trigger === 'commit' },
    );
  }, []);

  const handleDelete = useCallback(async (project: ProjectListItemModel) => {
    const ok = await confirmDialog({
      title: '删除项目',
      message: `确定要删除项目「${project.title}」吗？`,
      confirmText: '删除',
      dialogType: 'danger',
    });
    if (!ok) return;
    try {
      if (project.kind === 'coding') {
        await codingApi.deleteProject(project.id);
      } else {
        await novelsApi.delete([project.id]);
      }
      void fetchNovels();
    } catch (error) {
      console.error(error);
    }
  }, [fetchNovels]);

  const currentProjects = useMemo<ProjectListItemModel[]>(() => {
    const mergedNovels = novels.map((novel) => ({
      kind: 'novel' as const,
      id: novel.id,
      title: novel.title,
      description: novel.is_imported
        ? `导入分析：${novel.import_analysis_status || 'pending'}${novel.genre ? ` · 类型：${novel.genre}` : ''}`
        : (novel.description || (novel.genre ? `类型：${novel.genre}` : undefined)),
      status: novel.status,
      updated_at: novel.last_edited || novel.updated_at || novel.created_at || new Date().toISOString(),
    }));

    const mergedCoding = codingEnabled
      ? codingProjects.map((project) => ({
          kind: 'coding' as const,
          id: project.id,
          title: project.title,
          description: project.project_type_desc || 'Prompt工程',
          status: (project.status || '').toLowerCase(),
          updated_at: project.last_edited,
        }))
      : [];

    return [...mergedNovels, ...mergedCoding];
  }, [codingEnabled, codingProjects, novels]);

  const recentProjects = useMemo(() => {
    return [...currentProjects]
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, 10);
  }, [currentProjects]);

  const allProjects = useMemo(() => {
    return [...currentProjects].sort((a, b) =>
      projectTitleCollator.compare(a.title || '未命名项目', b.title || '未命名项目')
    );
  }, [currentProjects]);

  const displayedProjects = useMemo(() => {
    return activeTab === 'recent' ? recentProjects : allProjects;
  }, [activeTab, allProjects, recentProjects]);

  const latestProject = recentProjects[0] || null;
  const listSkeletonCount = activeTab === 'recent' ? 5 : 8;
  const emptyTitle = projectsError
    ? '项目暂时没有加载出来'
    : activeTab === 'recent'
      ? '暂无最近项目'
      : '当前还没有项目';
  const emptyDescription = projectsError
    ? '后端或首页数据请求失败了。你可以直接重试，不需要刷新整个应用。'
    : activeTab === 'recent'
      ? '最近项目列表会按更新时间自动形成入口。先新建一个项目，首页就会开始工作。'
      : '全部项目会按标题排序显示。先创建小说或导入 TXT，让右侧列表形成可选择状态。';
  const pickerTitle = activeTab === 'recent' ? '最近项目' : '全部项目';
  const pickerHint = activeTab === 'recent'
    ? '按更新时间排序，只保留最近 10 个项目。'
    : '按标题排序，像桌面端首页一样直接找项目。';
  const pickerSummaryLabel = activeTab === 'recent'
    ? `显示 ${displayedProjects.length} / 10`
    : `共 ${displayedProjects.length} 个项目`;

  return (
    <AppViewportShell>
      {showParticleBackground ? (
        <Suspense fallback={null}>
          <ParticleBackgroundLazy isDark={isDark} enableConstellations={!isElectronRuntime} />
        </Suspense>
      ) : null}

      <AppViewportFrame className="px-3 py-3 sm:px-4 sm:py-4 lg:px-5">
        <section className="dramatic-surface min-h-0 flex-1 rounded-2xl p-4 sm:p-5">
          <div className="relative z-[1] grid h-full min-h-0 gap-4 lg:grid-cols-[minmax(340px,400px)_minmax(0,1fr)]">
            <aside className="flex min-h-0 flex-col rounded-xl border border-book-border/45 bg-book-bg-paper/72 backdrop-blur-xl p-5 shadow-book-card sm:p-6">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h1 className="font-serif text-[clamp(2.4rem,4vw,4.8rem)] font-bold tracking-[0.04em] text-book-text-main">
                    AFN
                  </h1>
                  <p className="mt-2 max-w-md text-sm leading-relaxed text-book-text-sub">
                    AI 驱动的长篇小说创作助手
                  </p>
                </div>

                <button
                  type="button"
                  onClick={openSettings}
                  className="inline-flex shrink-0 items-center gap-2 whitespace-nowrap rounded-full border border-book-border/60 bg-book-bg-paper/86 h-10 px-4 text-sm font-semibold text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/30 hover:text-book-primary"
                >
                  <Settings size={16} />
                  设置
                </button>
              </div>

              {latestProject ? (
                <button
                  type="button"
                  onClick={() => navigate(getProjectHomeEntryRoute(latestProject))}
                  className="mt-5 flex w-full cursor-pointer items-start gap-4 rounded-lg border border-book-border/40 bg-book-bg/60 p-4 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-book-primary/30 hover:shadow-book-card"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-semibold text-book-text-muted">{getProjectKindLabel(latestProject)}</span>
                      <span className="text-xs text-book-text-muted">·</span>
                      <span className="text-xs text-book-text-muted">{getStatusText(latestProject.status)}</span>
                    </div>
                    <div className="mt-1.5 truncate font-serif text-lg font-bold text-book-text-main">
                      {latestProject.title}
                    </div>
                    <div className="mt-1 text-xs text-book-primary font-semibold">
                      {getProjectHomeEntryLabel(latestProject)}
                    </div>
                  </div>
                  <ArrowRight size={18} className="mt-1 shrink-0 text-book-text-muted" />
                </button>
              ) : (
                <div className="mt-5 rounded-lg border border-dashed border-book-border/40 bg-book-bg/40 px-4 py-4 text-center text-sm leading-relaxed text-book-text-muted">
                  创建第一个项目后，这里会显示最近活跃入口。
                </div>
              )}

              <div className="mt-5 grid gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setCreateDefaultType('novel');
                    setIsCreateModalOpen(true);
                  }}
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-book-primary bg-book-primary min-h-12 text-[0.95rem] font-semibold text-white transition-all duration-300 hover:-translate-y-0.5 hover:bg-book-primary-light"
                >
                  <Plus size={16} />
                  创建小说
                </button>

                {codingEnabled ? (
                  <button
                    type="button"
                    onClick={() => {
                      setCreateDefaultType('coding');
                      setIsCreateModalOpen(true);
                    }}
                    className="inline-flex items-center justify-center gap-2 rounded-lg border border-book-border/60 bg-book-bg-paper/86 min-h-12 text-[0.95rem] font-semibold text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/35 hover:text-book-primary"
                  >
                    <Code size={16} />
                    创建 Prompt 工程
                  </button>
                ) : null}

                <button
                  type="button"
                  onClick={() => setIsImportOpen(true)}
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-book-border/60 bg-book-bg-paper/86 min-h-12 text-[0.95rem] font-semibold text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/35 hover:text-book-primary"
                >
                  <Upload size={16} />
                  导入 TXT
                </button>
              </div>

              <div className="mt-5 rounded-lg border border-book-border/30 bg-book-bg/50 px-4 py-4">
                <p className="font-serif text-[0.95rem] italic leading-relaxed text-book-text-main">
                  「{quote[0]}」
                </p>
                <p className="mt-2 text-right text-xs font-medium text-book-text-muted">
                  {quote[1]}
                </p>
              </div>

              <div className="mt-auto pt-4 text-xs leading-relaxed text-book-text-muted">
                共 {currentProjects.length} 个项目{latestProject ? `，最近更新 ${formatProjectTimestamp(latestProject.updated_at)}` : ''}
              </div>
            </aside>

            <section className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-book-border/45 bg-book-bg-paper/72 backdrop-blur-xl shadow-book-card">
              <div className="flex-none border-b border-book-border/35 p-4 sm:p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-serif text-[1.9rem] font-bold text-book-text-main">
                        {pickerTitle}
                      </h2>
                      <span className="story-pill">{pickerSummaryLabel}</span>
                    </div>
                    <p className="mt-2 text-sm leading-relaxed text-book-text-sub">
                      {pickerHint}
                    </p>
                  </div>

                  <div className="text-right text-xs font-semibold text-book-text-muted">
                    {latestProject ? `最新更新 ${formatProjectTimestamp(latestProject.updated_at)}` : '创建项目后，这里会自动形成最近项目入口'}
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="inline-flex rounded-full border border-book-border/55 bg-book-bg-paper/82 p-1">
                      <button
                        type="button"
                        onClick={() => setActiveTab('recent')}
                        className={`rounded-full px-4 py-2 text-sm font-semibold transition-all ${
                          activeTab === 'recent'
                            ? 'bg-book-primary text-white shadow-lg'
                            : 'text-book-text-sub hover:text-book-text-main'
                        }`}
                      >
                        最近项目
                      </button>
                      <button
                        type="button"
                        onClick={() => setActiveTab('all')}
                        className={`rounded-full px-4 py-2 text-sm font-semibold transition-all ${
                          activeTab === 'all'
                            ? 'bg-book-primary text-white shadow-lg'
                            : 'text-book-text-sub hover:text-book-text-main'
                        }`}
                      >
                        全部项目
                      </button>
                    </div>
                  </div>

                  {codingEnabled ? (
                    <div className="rounded-full border border-book-border/45 bg-book-bg/72 px-3 py-2 text-xs font-semibold text-book-text-muted">
                      列表已合并显示小说与 Prompt 工程
                    </div>
                  ) : (
                    <div className="rounded-full border border-book-border/45 bg-book-bg/72 px-3 py-2 text-xs font-semibold text-book-text-muted">
                      当前环境只启用了小说工作流。
                    </div>
                  )}
                </div>

                {projectsError ? (
                  <div className="mt-4 rounded-lg border border-amber-500/25 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-200">
                    <div className="font-semibold">首页项目列表暂时没有加载出来。</div>
                    <div className="mt-1 leading-relaxed">你可以直接重试，不需要重启整个应用。</div>
                    <button
                      type="button"
                      onClick={() => {
                        setLoading(true);
                        void fetchNovels();
                      }}
                      className="mt-3 inline-flex min-h-9 items-center justify-center rounded-full border border-amber-600/25 bg-book-bg-paper/72 px-4 text-sm font-semibold text-book-text-main transition-all duration-200 hover:-translate-y-0.5 hover:border-book-primary/35 hover:text-book-primary"
                    >
                      重新加载项目
                    </button>
                  </div>
                ) : null}

                {projectsNotice ? (
                  <div className="mt-4 rounded-lg border border-book-border/45 bg-book-bg-paper/62 px-4 py-3 text-sm leading-relaxed text-book-text-sub">
                    {projectsNotice}
                  </div>
                ) : null}
              </div>

              <div className="min-h-0 flex-1 p-4">
                {loading ? (
                  <AppViewportScrollArea className="pr-2">
                    <div className="space-y-2.5 pr-1">
                      {Array.from({ length: listSkeletonCount }).map((_, index) => (
                        <div
                          key={index}
                          className="h-[82px] rounded-lg border border-book-border/45 bg-book-bg-paper/55 animate-pulse"
                        />
                      ))}
                    </div>
                  </AppViewportScrollArea>
                ) : displayedProjects.length > 0 ? (
                  <AppViewportScrollArea className="pr-2">
                    <div className="perf-scroll-stack space-y-2.5 pr-1">
                      {displayedProjects.map((project) => (
                        <ProjectLauncherRow
                          key={project.id}
                          project={project}
                          onLaunch={handleProjectLaunch}
                          onDelete={handleDelete}
                          onPrefetch={handleProjectPrefetch}
                          showDelete={activeTab === 'all'}
                          compact={false}
                        />
                      ))}
                    </div>
                  </AppViewportScrollArea>
                ) : (
                  <div className="flex h-full flex-col items-center justify-center rounded-xl border border-dashed border-book-border/55 bg-book-bg-paper/58 px-6 text-center">
                    <div className="flex h-14 w-14 items-center justify-center rounded-full border border-book-border/50 bg-book-bg/75 text-book-primary">
                      <FolderOpen size={24} />
                    </div>
                    <div className="mt-4 font-serif text-3xl font-bold text-book-text-main">
                      {emptyTitle}
                    </div>
                    <p className="mt-3 max-w-md text-sm leading-relaxed text-book-text-sub">
                      {emptyDescription}
                    </p>
                    <div className="mt-5 flex flex-wrap justify-center gap-3">
                      {projectsError ? (
                        <button
                          type="button"
                          onClick={() => {
                            setLoading(true);
                            void fetchNovels();
                          }}
                          className="inline-flex min-h-11 items-center justify-center gap-2 whitespace-nowrap rounded-full border border-book-primary bg-book-primary px-5 text-sm font-semibold text-white transition-all duration-300 hover:-translate-y-0.5 hover:bg-book-primary-light"
                        >
                          重新加载
                        </button>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() => {
                              setCreateDefaultType('novel');
                              setIsCreateModalOpen(true);
                            }}
                            className="inline-flex min-h-11 items-center justify-center gap-2 whitespace-nowrap rounded-full border border-book-primary bg-book-primary px-5 text-sm font-semibold text-white transition-all duration-300 hover:-translate-y-0.5 hover:bg-book-primary-light"
                          >
                            <Plus size={16} />
                            创建小说
                          </button>
                          <button
                            type="button"
                            onClick={() => setIsImportOpen(true)}
                            className="inline-flex min-h-11 items-center justify-center gap-2 whitespace-nowrap rounded-full border border-book-border/60 bg-book-bg px-5 text-sm font-semibold text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/35 hover:text-book-primary"
                          >
                            <Upload size={16} />
                            导入 TXT
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </section>
          </div>
        </section>
      </AppViewportFrame>

      {isCreateModalOpen ? (
        <Suspense fallback={null}>
          <CreateProjectModalLazy
            isOpen={isCreateModalOpen}
            onClose={() => setIsCreateModalOpen(false)}
            onSuccess={fetchNovels}
            defaultType={createDefaultType}
            codingEnabled={codingEnabled}
          />
        </Suspense>
      ) : null}

      {isImportOpen ? (
        <Suspense fallback={null}>
          <ImportModalLazy
            isOpen={isImportOpen}
            onClose={() => setIsImportOpen(false)}
            onSuccess={fetchNovels}
          />
        </Suspense>
      ) : null}
    </AppViewportShell>
  );
};
