import React, { lazy, Suspense, useEffect, useState, useMemo, useCallback } from 'react';
import { novelsApi, Novel } from '../api/novels';
import { codingApi, CodingProjectSummary } from '../api/coding';
import { settingsApi } from '../api/settings';
import { ProjectListItem, ProjectListItemModel } from '../components/business/ProjectListItem';
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

  return (
    <div className="flex h-screen w-full bg-book-bg overflow-hidden relative">
      {showParticleBackground ? (
        <Suspense fallback={null}>
          <ParticleBackgroundLazy />
        </Suspense>
      ) : null}

      {!isLowPowerMode ? (
        <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-30">
          <div className="absolute -top-20 -left-20 w-96 h-96 bg-book-primary/10 rounded-full blur-3xl animate-pulse" />
          <div className="absolute top-1/2 right-0 w-64 h-64 bg-book-accent/10 rounded-full blur-3xl animate-pulse delay-700" />
        </div>
      ) : null}

      <div className="w-[380px] flex flex-col justify-between px-12 py-20 z-10">
        <div className="absolute top-8 right-8">
          <button
            onClick={openSettings}
            className="text-book-text-muted hover:text-book-accent flex items-center gap-2 text-sm transition-colors"
          >
            <Settings size={16} /> 设置
          </button>
        </div>

        <div className="space-y-10 animate-in fade-in slide-in-from-left-4 duration-700 my-auto">
          <div className="space-y-4">
            <h1 className="font-serif text-6xl font-bold text-book-text-main tracking-wider">
              AFN
            </h1>
            <p className="font-sans text-lg text-book-text-sub tracking-wide">
              AI 驱动的长篇小说创作助手
            </p>
          </div>

          <div className="space-y-2 border-l-4 border-book-primary/30 pl-4 py-1">
            <p className="font-serif text-lg italic text-book-text-secondary leading-relaxed">
              {quote[0]}
            </p>
            <p className="font-serif text-xs italic text-book-text-muted">
              {quote[1]}
            </p>
          </div>

          <div className="h-4" />

          <div className="space-y-4 w-full max-w-xs">
            <button
              onClick={() => {
                setCreateDefaultType('novel');
                setIsCreateModalOpen(true);
              }}
              className="w-full py-3.5 px-6 rounded-xl bg-book-accent text-white font-medium shadow-lg shadow-book-accent/20 hover:bg-book-text-main hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300 flex items-center justify-center gap-2 group"
            >
              <Plus size={20} className="group-hover:rotate-90 transition-transform duration-300" />
              创建小说
            </button>

            {codingEnabled && (
              <button
                onClick={() => {
                  setCreateDefaultType('coding');
                  setIsCreateModalOpen(true);
                }}
                className="w-full py-3.5 px-6 rounded-xl bg-book-bg-paper border-2 border-book-accent text-book-accent font-medium hover:bg-book-accent hover:text-white transition-all duration-300 flex items-center justify-center gap-2"
              >
                <Code size={20} />
                创建Prompt工程
              </button>
            )}

            <button
              onClick={() => setActiveTab('all')}
              className="w-full py-3.5 px-6 rounded-xl bg-transparent border border-book-border text-book-text-main hover:border-book-accent hover:text-book-accent transition-all duration-300 flex items-center justify-center gap-2"
            >
              <FolderOpen size={20} />
              查看全部项目
            </button>

            <button
              onClick={() => setIsImportOpen(true)}
              className="w-full py-3.5 px-6 rounded-xl bg-book-bg-paper border border-book-border text-book-text-main hover:border-book-primary hover:text-book-primary transition-all duration-300 flex items-center justify-center gap-2"
              title="导入 TXT 小说并自动分析（桌面版同款流程）"
            >
              <Upload size={20} />
              导入 TXT 小说
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 bg-book-bg-paper border-l border-book-border/40 p-12 flex flex-col z-10">
        {codingEnabled && (
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => setProjectKind('novel')}
              className={`px-4 py-2 rounded-lg text-sm font-bold border transition-all ${
                projectKind === 'novel'
                  ? 'bg-book-bg-paper border-book-border text-book-text-main'
                  : 'bg-transparent border-book-border/40 text-book-text-muted hover:text-book-text-main hover:border-book-border'
              }`}
            >
              小说
            </button>
            <button
              onClick={() => setProjectKind('coding')}
              className={`px-4 py-2 rounded-lg text-sm font-bold border transition-all ${
                projectKind === 'coding'
                  ? 'bg-book-bg-paper border-book-border text-book-text-main'
                  : 'bg-transparent border-book-border/40 text-book-text-muted hover:text-book-text-main hover:border-book-border'
              }`}
            >
              Prompt工程
            </button>
          </div>
        )}

        <div className="flex gap-6 border-b border-book-border/30 pb-4 mb-6">
          <button
            onClick={() => setActiveTab('recent')}
            className={`text-lg font-medium transition-colors pb-1 relative ${activeTab === 'recent' ? 'text-book-accent' : 'text-book-text-muted hover:text-book-text-main'}`}
          >
            最近项目
            {activeTab === 'recent' && <div className="absolute bottom-[-17px] left-0 right-0 h-0.5 bg-book-accent" />}
          </button>

          <button
            onClick={() => setActiveTab('all')}
            className={`text-lg font-medium transition-colors pb-1 relative ${activeTab === 'all' ? 'text-book-accent' : 'text-book-text-muted hover:text-book-text-main'}`}
          >
            全部项目
            {activeTab === 'all' && <div className="absolute bottom-[-17px] left-0 right-0 h-0.5 bg-book-accent" />}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-3">
          {loading ? (
            [1, 2, 3, 4].map((i) => (
              <div key={i} className="h-20 w-full bg-book-bg-paper/40 rounded-lg animate-pulse" />
            ))
          ) : visibleProjects.length > 0 ? (
            <>
              {visibleProjects.map((project) => (
                <ProjectListItem
                  key={project.id}
                  project={project}
                  onClick={handleProjectClick}
                  onDelete={handleDelete}
                  onHover={handleProjectHover}
                />
              ))}

              {hasMoreProjects ? (
                <div className="pt-1 pb-2 flex justify-center">
                  <button
                    onClick={loadMoreProjects}
                    className="px-4 py-2 rounded-lg text-sm border border-book-border/60 text-book-text-sub hover:text-book-primary hover:border-book-primary/40 transition-colors"
                  >
                    加载更多（剩余 {remainingProjects} 项）
                  </button>
                </div>
              ) : null}
            </>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-book-text-muted opacity-60">
              <FolderOpen size={48} className="mb-4 stroke-1" />
              <p className="text-center whitespace-pre-line">
                {activeTab === 'recent'
                  ? '暂无最近项目\n点击"创建小说"开始您的创作之旅'
                  : '暂无项目\n点击"创建小说"开始您的创作之旅'}
              </p>
            </div>
          )}
        </div>
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
