import React, { lazy, Suspense, useEffect, useState, useMemo, useCallback } from 'react';
import { novelsApi, Novel } from '../api/novels';
import { codingApi, CodingProjectSummary } from '../api/coding';
import { settingsApi } from '../api/settings';
import { ProjectListItem, ProjectListItemModel } from '../components/business/ProjectListItem';
import { BookCard } from '../components/ui/BookCard';
import { useNavigate } from 'react-router-dom';
import { Plus, Settings, Code, FolderOpen, Upload } from 'lucide-react';
import { CREATIVE_QUOTES } from '../utils/constants';
import { useUIStore } from '../store/ui';
import { confirmDialog } from '../components/feedback/ConfirmDialog';
import { scheduleIdleTask } from '../utils/scheduleIdleTask';
import { prefetchProjectRouteByStatus } from '../utils/projectRoutePrefetch';
import { readBootstrapCache, writeBootstrapCache } from '../utils/bootstrapCache';

const ParticleBackgroundLazy = lazy(() =>
  import('../components/ui/ParticleBackground').then((m) => ({ default: m.ParticleBackground }))
);
const CreateProjectModalLazy = lazy(() =>
  import('../components/business/CreateProjectModal').then((m) => ({ default: m.CreateProjectModal }))
);
const ImportModalLazy = lazy(() =>
  import('../components/business/ImportModal').then((m) => ({ default: m.ImportModal }))
);

type NavigatorConnection = Navigator & {
  connection?: {
    saveData?: boolean;
    effectiveType?: string;
  };
  hardwareConcurrency?: number;
};

const detectLowPowerMode = (): boolean => {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return false;

  try {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return true;
  } catch {
    // ignore
  }

  const nav = navigator as NavigatorConnection;
  const connection = nav.connection;
  if (connection?.saveData) return true;

  const effectiveType = String(connection?.effectiveType || '').toLowerCase();
  if (effectiveType.includes('2g') || effectiveType.includes('3g')) return true;

  const cores = Number(nav.hardwareConcurrency || 0);
  if (Number.isFinite(cores) && cores > 0 && cores <= 4) return true;

  return false;
};

const shouldEnableParticleBackground = (): boolean => !detectLowPowerMode();

const INITIAL_PROJECT_RENDER_LIMIT = 48;
const PROJECT_RENDER_BATCH_SIZE = 48;
const NOVEL_LIST_BOOTSTRAP_TTL_MS = 3 * 60 * 1000;
const NOVEL_LIST_BOOTSTRAP_KEY = 'afn:web:novel-list:bootstrap:v1';

type NovelListBootstrapSnapshot = {
  novels: Novel[];
  codingProjects: CodingProjectSummary[];
  codingEnabled: boolean;
  projectKind: 'novel' | 'coding';
};

export const NovelList: React.FC = () => {
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
  const [projectKind, setProjectKind] = useState<'novel' | 'coding'>(() => {
    const cached = initialBootstrapRef.current;
    if (cached?.codingEnabled && cached.projectKind === 'coding') return 'coding';
    return 'novel';
  });
  const [codingEnabled, setCodingEnabled] = useState(() => Boolean(initialBootstrapRef.current?.codingEnabled));
  const [showParticleBackground, setShowParticleBackground] = useState(false);
  const [isLowPowerMode] = useState<boolean>(() => detectLowPowerMode());
  const [renderLimit, setRenderLimit] = useState(INITIAL_PROJECT_RENDER_LIMIT);
  const navigate = useNavigate();
  const { openSettings } = useUIStore();

  const quote = useMemo(() => {
    return CREATIVE_QUOTES[Math.floor(Math.random() * CREATIVE_QUOTES.length)];
  }, []);

  const fetchNovels = useCallback(async () => {
    setLoading((prev) => prev && !initialBootstrapRef.current);
    try {
      const [advancedConfig, novelList] = await Promise.all([
        settingsApi.getAdvancedConfig(),
        novelsApi.list(),
      ]);

      const isCodingEnabled = advancedConfig.coding_project_enabled ?? false;
      setCodingEnabled(isCodingEnabled);
      setProjectKind((prev) => (!isCodingEnabled && prev === 'coding' ? 'novel' : prev));
      setNovels(novelList);
      setLoading(false);

      if (isCodingEnabled) {
        void codingApi
          .list()
          .then((codingList) => setCodingProjects(codingList))
          .catch((error) => {
            console.error('Failed to fetch coding projects', error);
            setCodingProjects([]);
          });
      } else {
        setCodingProjects([]);
      }
    } catch (err) {
      console.error('Failed to fetch novels', err);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    writeBootstrapCache<NovelListBootstrapSnapshot>(NOVEL_LIST_BOOTSTRAP_KEY, {
      novels,
      codingProjects,
      codingEnabled,
      projectKind: codingEnabled && projectKind === 'coding' ? 'coding' : 'novel',
    });
  }, [codingEnabled, codingProjects, novels, projectKind]);

  useEffect(() => {
    fetchNovels();
  }, [fetchNovels]);

  useEffect(() => {
    if (loading) return;
    if (isLowPowerMode || !shouldEnableParticleBackground()) return;

    const cancel = scheduleIdleTask(() => {
      setShowParticleBackground(true);
    }, { delay: 900, timeout: 2600 });

    return cancel;
  }, [isLowPowerMode, loading]);

  const handleProjectClick = useCallback((project: ProjectListItemModel) => {
    if (project.kind === 'coding') {
      const status = (project.status || '').toLowerCase();
      if (status.includes('draft')) {
        navigate(`/coding/inspiration/${project.id}`);
      } else {
        navigate(`/coding/detail/${project.id}`);
      }
      return;
    }

    const status = String(project.status || '').toLowerCase();
    if (status === 'draft' || status === 'inspiration') {
      navigate(`/inspiration/${project.id}`);
      return;
    }
    navigate(`/write/${project.id}`);
  }, [navigate]);

  const handleProjectHover = useCallback((project: ProjectListItemModel) => {
    prefetchProjectRouteByStatus({ kind: project.kind, status: project.status });
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
      fetchNovels();
    } catch (e) {
      console.error(e);
    }
  }, [fetchNovels]);

  const currentProjects = useMemo<ProjectListItemModel[]>(() => {
    if (projectKind === 'coding') {
      return codingProjects.map((p) => ({
        kind: 'coding',
        id: p.id,
        title: p.title,
        description: p.project_type_desc || 'Prompt工程',
        status: (p.status || '').toLowerCase(),
        updated_at: p.last_edited,
      }));
    }
    return novels.map((n) => ({
      kind: 'novel',
      id: n.id,
      title: n.title,
      description: n.is_imported
        ? `导入分析：${n.import_analysis_status || 'pending'}${n.genre ? ` · 类型：${n.genre}` : ''}`
        : (n.description || (n.genre ? `类型：${n.genre}` : undefined)),
      status: n.status,
      updated_at: n.last_edited || n.updated_at || n.created_at || new Date().toISOString(),
    }));
  }, [projectKind, codingProjects, novels]);

  const recentProjects = useMemo(() => {
    return [...currentProjects]
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, 10);
  }, [currentProjects]);

  const displayedProjects = useMemo(() => {
    return activeTab === 'recent' ? recentProjects : currentProjects;
  }, [activeTab, currentProjects, recentProjects]);

  useEffect(() => {
    if (loading) return;
    setRenderLimit(INITIAL_PROJECT_RENDER_LIMIT);
  }, [activeTab, loading, projectKind]);

  const visibleProjects = useMemo(() => {
    return displayedProjects.slice(0, renderLimit);
  }, [displayedProjects, renderLimit]);

  const hasMoreProjects = visibleProjects.length < displayedProjects.length;
  const remainingProjects = Math.max(0, displayedProjects.length - visibleProjects.length);

  const loadMoreProjects = useCallback(() => {
    setRenderLimit((prev) => prev + PROJECT_RENDER_BATCH_SIZE);
  }, []);

  const latestProject = recentProjects[0] || null;
  const draftProjectCount = useMemo(() => {
    return currentProjects.filter((project) => {
      const status = String(project.status || '').toLowerCase();
      return status.includes('draft') || status.includes('inspiration');
    }).length;
  }, [currentProjects]);
  const completedProjectCount = useMemo(() => {
    return currentProjects.filter((project) => {
      const status = String(project.status || '').toLowerCase();
      return status.includes('completed') || status.includes('done');
    }).length;
  }, [currentProjects]);
  const dashboardStats = useMemo(() => {
    return [
      {
        label: '小说项目',
        value: novels.length,
        hint: '长篇、世界观、角色与章节',
      },
      {
        label: 'Prompt 工程',
        value: codingEnabled ? codingProjects.length : 0,
        hint: codingEnabled ? '需求分析、架构与交付流' : '当前未启用',
      },
      {
        label: '构思中',
        value: draftProjectCount,
        hint: '仍在灵感对话或蓝图阶段',
      },
      {
        label: '已推进',
        value: completedProjectCount,
        hint: '已经进入写作或交付推进',
      },
    ];
  }, [codingEnabled, codingProjects.length, completedProjectCount, draftProjectCount, novels.length]);
  const activeKindLabel = projectKind === 'coding' ? 'Prompt 工程' : '小说项目';
  const activeKindDescription = projectKind === 'coding'
    ? '把需求访谈、架构设计与执行工作台收束成一条稳定流水线。'
    : '从灵感对话、蓝图铺陈到章节推进，维持长篇创作的叙事张力。';
  const emptyTitle = activeTab === 'recent' ? '暂无最近项目' : '当前还没有项目';
  const emptyDescription = activeTab === 'recent'
    ? '先新建一个项目，让最近动态开始滚动。'
    : '从创建小说或导入 TXT 开始，搭起你的下一个创作舞台。';

  return (
    <div className="page-shell min-h-screen overflow-hidden">
      {showParticleBackground ? (
        <Suspense fallback={null}>
          <ParticleBackgroundLazy />
        </Suspense>
      ) : null}

      {!isLowPowerMode ? (
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="ambient-orb -left-16 top-0 h-72 w-72 bg-book-primary/18" />
          <div className="ambient-orb right-[-6rem] top-24 h-64 w-64 bg-book-primary-light/16" />
          <div className="ambient-orb bottom-[-6rem] left-1/3 h-72 w-72 bg-book-primary/10" />
        </div>
      ) : null}
      <div className="relative mx-auto flex min-h-screen w-full max-w-[1600px] flex-col gap-6 px-4 py-4 sm:px-6 sm:py-6 xl:px-8">
        <section className="dramatic-surface rounded-[34px] p-6 sm:p-8 lg:p-10">
          <div className="pointer-events-none absolute inset-y-0 right-0 w-1/2 bg-gradient-to-l from-book-primary/10 via-transparent to-transparent" />
          <div className="relative z-[1] grid gap-8 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,420px)]">
            <div className="space-y-8">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-4">
                  <div className="eyebrow">AFN Creative OS</div>
                  <div className="space-y-4">
                    <h1 className="max-w-4xl font-serif text-[clamp(2.8rem,7vw,5.8rem)] font-bold leading-[0.94] tracking-[-0.04em] text-book-text-main">
                      把灵感
                      <br />
                      锻造成长篇工程
                    </h1>
                    <p className="max-w-3xl text-sm leading-relaxed text-book-text-sub sm:text-base lg:text-lg">
                      从一段模糊念头开始，推进到蓝图、章节、Prompt 工程与后台治理。
                      AFN 现在把首页改造成创作总控台，而不是一张平铺列表。
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={openSettings}
                  className="inline-flex h-12 items-center gap-2 rounded-full border border-book-border/55 bg-book-bg-paper/78 px-4 text-sm font-semibold text-book-text-main shadow-[0_22px_44px_-34px_rgba(36,18,6,0.92)] transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/30 hover:text-book-primary"
                >
                  <Settings size={16} />
                  设置
                </button>
              </div>

              <div className="flex flex-wrap gap-3">
                <span className="story-pill">叙事优先</span>
                <span className="story-pill">项目总数 {currentProjects.length}</span>
                <span className="story-pill">{projectKind === 'coding' ? '需求与架构流' : '小说与章节流'}</span>
              </div>

              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {dashboardStats.map((item) => (
                  <div key={item.label} className="metric-tile">
                    <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                      {item.label}
                    </div>
                    <div className="mt-3 font-serif text-4xl font-bold text-book-text-main">
                      {item.value}
                    </div>
                    <div className="mt-2 text-sm leading-relaxed text-book-text-sub">
                      {item.hint}
                    </div>
                  </div>
                ))}
              </div>

              <div className="story-divider" />

              <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
                <div className="rounded-[30px] border border-book-border/55 bg-book-bg-paper/72 p-6 shadow-[0_26px_60px_-42px_rgba(36,18,6,0.96)] backdrop-blur-xl">
                  <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                    今日序章
                  </div>
                  <p className="mt-4 font-serif text-xl italic leading-relaxed text-book-text-main sm:text-2xl">
                    {quote[0]}
                  </p>
                  <p className="mt-3 text-sm font-semibold text-book-text-muted">
                    {quote[1]}
                  </p>

                  <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <button
                      type="button"
                      onClick={() => {
                        setCreateDefaultType('novel');
                        setIsCreateModalOpen(true);
                      }}
                      className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full border border-book-primary bg-book-primary px-5 text-sm font-semibold text-white shadow-[0_20px_44px_-28px_rgba(87,44,17,0.96)] transition-all duration-300 hover:-translate-y-0.5 hover:bg-book-primary-light"
                    >
                      <Plus size={18} />
                      创建小说
                    </button>

                    {codingEnabled ? (
                      <button
                        type="button"
                        onClick={() => {
                          setCreateDefaultType('coding');
                          setIsCreateModalOpen(true);
                        }}
                        className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full border border-book-border/60 bg-book-bg px-5 text-sm font-semibold text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/35 hover:text-book-primary"
                      >
                        <Code size={18} />
                        创建 Prompt 工程
                      </button>
                    ) : null}

                    <button
                      type="button"
                      onClick={() => setActiveTab('all')}
                      className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full border border-book-border/60 bg-book-bg px-5 text-sm font-semibold text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/35 hover:text-book-primary"
                    >
                      <FolderOpen size={18} />
                      查看全量项目
                    </button>

                    <button
                      type="button"
                      onClick={() => setIsImportOpen(true)}
                      title="导入 TXT 小说并自动分析"
                      className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full border border-book-border/60 bg-book-bg px-5 text-sm font-semibold text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/35 hover:text-book-primary"
                    >
                      <Upload size={18} />
                      导入 TXT
                    </button>
                  </div>
                </div>

                <div className="rounded-[30px] border border-book-border/55 bg-book-bg-paper/72 p-6 shadow-[0_26px_60px_-42px_rgba(36,18,6,0.96)] backdrop-blur-xl">
                  <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                    当前场景
                  </div>
                  <div className="mt-4 font-serif text-3xl font-bold text-book-text-main">
                    {activeKindLabel}
                  </div>
                  <p className="mt-3 text-sm leading-relaxed text-book-text-sub">
                    {activeKindDescription}
                  </p>
                  <div className="mt-6 space-y-3">
                    <div className="rounded-[22px] border border-book-border/50 bg-book-bg/72 px-4 py-3">
                      <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                        最近热度
                      </div>
                      <div className="mt-2 text-lg font-semibold text-book-text-main">
                        {recentProjects.length} 个最近项目
                      </div>
                    </div>
                    <div className="rounded-[22px] border border-book-border/50 bg-book-bg/72 px-4 py-3">
                      <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                        最新更新
                      </div>
                      <div className="mt-2 text-base font-semibold text-book-text-main">
                        {latestProject ? latestProject.title : '还没有项目'}
                      </div>
                      <div className="mt-1 text-sm text-book-text-sub">
                        {latestProject ? '继续推进它，或者切换到全部项目盘点全局。' : '先创建一个项目，把创作引擎点亮。'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-[30px] border border-book-border/55 bg-book-bg-paper/72 p-6 shadow-[0_24px_56px_-42px_rgba(36,18,6,0.96)] backdrop-blur-xl">
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                  工作模式
                </div>
                {codingEnabled ? (
                  <div className="mt-4 inline-flex w-full rounded-full border border-book-border/55 bg-book-bg/75 p-1">
                    <button
                      type="button"
                      onClick={() => setProjectKind('novel')}
                      className={`flex-1 rounded-full px-4 py-2.5 text-sm font-semibold transition-all ${
                        projectKind === 'novel'
                          ? 'bg-book-primary text-white shadow-[0_18px_38px_-24px_rgba(87,44,17,0.96)]'
                          : 'text-book-text-sub hover:text-book-text-main'
                      }`}
                    >
                      小说
                    </button>
                    <button
                      type="button"
                      onClick={() => setProjectKind('coding')}
                      className={`flex-1 rounded-full px-4 py-2.5 text-sm font-semibold transition-all ${
                        projectKind === 'coding'
                          ? 'bg-book-primary text-white shadow-[0_18px_38px_-24px_rgba(87,44,17,0.96)]'
                          : 'text-book-text-sub hover:text-book-text-main'
                      }`}
                    >
                      Prompt 工程
                    </button>
                  </div>
                ) : (
                  <div className="mt-4 rounded-[24px] border border-book-border/50 bg-book-bg/75 px-4 py-4 text-sm leading-relaxed text-book-text-sub">
                    当前环境只启用了小说工作流。开启高级配置后，这里会自动扩展出 Prompt 工程入口。
                  </div>
                )}
              </div>

              <div className="rounded-[30px] border border-book-border/55 bg-book-bg-paper/72 p-6 shadow-[0_24px_56px_-42px_rgba(36,18,6,0.96)] backdrop-blur-xl">
                <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                  操作节奏
                </div>
                <div className="mt-4 space-y-4">
                  <div className="rounded-[22px] border border-book-border/50 bg-book-bg/72 px-4 py-4">
                    <div className="text-sm font-semibold text-book-text-main">1. 开始创作</div>
                    <div className="mt-1 text-sm leading-relaxed text-book-text-sub">
                      先确定是小说还是 Prompt 工程，再创建一个新项目。
                    </div>
                  </div>
                  <div className="rounded-[22px] border border-book-border/50 bg-book-bg/72 px-4 py-4">
                    <div className="text-sm font-semibold text-book-text-main">2. 盘点进度</div>
                    <div className="mt-1 text-sm leading-relaxed text-book-text-sub">
                      用最近项目看节奏，用全部项目校准全局密度与优先级。
                    </div>
                  </div>
                  <div className="rounded-[22px] border border-book-border/50 bg-book-bg/72 px-4 py-4">
                    <div className="text-sm font-semibold text-book-text-main">3. 回到工作台</div>
                    <div className="mt-1 text-sm leading-relaxed text-book-text-sub">
                      点击任一项目即可继续灵感对话、蓝图编排或章节写作。
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid min-h-0 flex-1 gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="dramatic-surface min-h-[24rem] rounded-[34px] p-4 sm:p-6">
            <div className="relative z-[1] flex h-full min-h-0 flex-col">
              <div className="flex flex-col gap-4 border-b border-book-border/40 pb-5 lg:flex-row lg:items-end lg:justify-between">
                <div className="space-y-3">
                  <div className="eyebrow">Project Board</div>
                  <div>
                    <h2 className="font-serif text-3xl font-bold text-book-text-main sm:text-4xl">
                      {activeKindLabel}总控台
                    </h2>
                    <p className="mt-2 text-sm leading-relaxed text-book-text-sub sm:text-base">
                      {activeTab === 'recent' ? '优先回到最近推进过的项目，保持连续性。' : '查看全量资产，决定接下来哪一条线该继续推进。'}
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <div className="inline-flex rounded-full border border-book-border/55 bg-book-bg/78 p-1">
                    <button
                      type="button"
                      onClick={() => setActiveTab('recent')}
                      className={`rounded-full px-4 py-2 text-sm font-semibold transition-all ${
                        activeTab === 'recent'
                          ? 'bg-book-primary text-white shadow-[0_18px_38px_-24px_rgba(87,44,17,0.96)]'
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
                          ? 'bg-book-primary text-white shadow-[0_18px_38px_-24px_rgba(87,44,17,0.96)]'
                          : 'text-book-text-sub hover:text-book-text-main'
                      }`}
                    >
                      全部项目
                    </button>
                  </div>

                  <div className="rounded-full border border-book-border/55 bg-book-bg/78 px-4 py-2 text-sm font-semibold text-book-text-main">
                    当前显示 {visibleProjects.length} / {displayedProjects.length}
                  </div>
                </div>
              </div>

              <div className="mt-6 flex-1 min-h-0 overflow-y-auto pr-1 custom-scrollbar">
                {loading ? (
                  <div className="grid gap-4">
                    {[1, 2, 3, 4].map((i) => (
                      <div key={i} className="h-36 rounded-[30px] border border-book-border/45 bg-book-bg-paper/55 animate-pulse" />
                    ))}
                  </div>
                ) : visibleProjects.length > 0 ? (
                  <>
                    <div className="grid gap-4">
                      {visibleProjects.map((project) => (
                        <ProjectListItem
                          key={project.id}
                          project={project}
                          onClick={handleProjectClick}
                          onDelete={handleDelete}
                          onHover={handleProjectHover}
                        />
                      ))}
                    </div>

                    {hasMoreProjects ? (
                      <div className="mt-6 flex justify-center">
                        <button
                          type="button"
                          onClick={loadMoreProjects}
                          className="inline-flex min-h-11 items-center justify-center rounded-full border border-book-border/60 bg-book-bg-paper/72 px-5 text-sm font-semibold text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/35 hover:text-book-primary"
                        >
                          加载更多（剩余 {remainingProjects} 项）
                        </button>
                      </div>
                    ) : null}
                  </>
                ) : (
                  <div className="flex h-full min-h-[18rem] flex-col items-center justify-center rounded-[30px] border border-dashed border-book-border/55 bg-book-bg-paper/58 px-6 text-center">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full border border-book-border/50 bg-book-bg/75 text-book-primary">
                      <FolderOpen size={28} />
                    </div>
                    <div className="mt-5 font-serif text-3xl font-bold text-book-text-main">
                      {emptyTitle}
                    </div>
                    <p className="mt-3 max-w-md text-sm leading-relaxed text-book-text-sub">
                      {emptyDescription}
                    </p>
                    <div className="mt-6 flex flex-wrap justify-center gap-3">
                      <button
                        type="button"
                        onClick={() => {
                          setCreateDefaultType('novel');
                          setIsCreateModalOpen(true);
                        }}
                        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-book-primary bg-book-primary px-5 text-sm font-semibold text-white transition-all duration-300 hover:-translate-y-0.5 hover:bg-book-primary-light"
                      >
                        <Plus size={16} />
                        创建小说
                      </button>
                      <button
                        type="button"
                        onClick={() => setIsImportOpen(true)}
                        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-book-border/60 bg-book-bg px-5 text-sm font-semibold text-book-text-main transition-all duration-300 hover:-translate-y-0.5 hover:border-book-primary/35 hover:text-book-primary"
                      >
                        <Upload size={16} />
                        导入 TXT
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <aside className="space-y-4">
            <BookCard className="p-6" variant="default">
              <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                进度快照
              </div>
              <div className="mt-4 space-y-4">
                <div className="rounded-[22px] border border-book-border/45 bg-book-bg/72 px-4 py-3">
                  <div className="text-sm font-semibold text-book-text-main">项目总览</div>
                  <div className="mt-1 text-2xl font-serif font-bold text-book-primary">
                    {currentProjects.length}
                  </div>
                  <div className="mt-1 text-sm text-book-text-sub">
                    当前模式下可继续推进的项目数
                  </div>
                </div>
                <div className="rounded-[22px] border border-book-border/45 bg-book-bg/72 px-4 py-3">
                  <div className="text-sm font-semibold text-book-text-main">最近活跃</div>
                  <div className="mt-1 text-2xl font-serif font-bold text-book-primary">
                    {recentProjects.length}
                  </div>
                  <div className="mt-1 text-sm text-book-text-sub">
                    最近编辑过的项目会优先出现在前排
                  </div>
                </div>
              </div>
            </BookCard>

            <BookCard className="p-6" variant="flat">
              <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                推荐动作
              </div>
              <div className="mt-4 space-y-3 text-sm leading-relaxed text-book-text-sub">
                <p>如果你要开新坑，直接创建项目，不要先在空白页犹豫。</p>
                <p>如果你在多个项目间切换，用“全部项目”先盘点，再回到“最近项目”保持推进节奏。</p>
                <p>导入已有 TXT 时，建议尽快进入蓝图与章节检查，减少后续结构回炉。</p>
              </div>
            </BookCard>
          </aside>
        </section>
      </div>

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
    </div>
  );
};
