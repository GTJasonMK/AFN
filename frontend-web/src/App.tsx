import { useState, useEffect, lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from './components/feedback/Toast';
import { ErrorBoundary } from './components/feedback/ErrorBoundary';
import { ConfirmDialogHost } from './components/feedback/ConfirmDialog';
import { Settings, Moon, Sun, Loader2 } from 'lucide-react';
import { useUIStore } from './store/ui';
import { themeConfigsApi } from './api/themeConfigs';
import { adminDashboardApi } from './api/adminDashboard';
import { applyThemeFromUnifiedConfig, clearThemeVariables } from './theme/applyTheme';
import { readWebAppearanceConfig, WEB_APPEARANCE_CHANGED_EVENT, WEB_APPEARANCE_STORAGE_KEY } from './theme/webAppearance';
import { AuthGate } from './components/auth/AuthGate';
import { isAdminUser, useAuthStore } from './store/auth';
import { scheduleIdleTask } from './utils/scheduleIdleTask';

// Route-level code splitting：降低首屏 JS 体积，避免把写作台/漫画等重组件打进同一个 chunk
const loadNovelList = () => import('./pages/NovelList').then((m) => ({ default: m.NovelList }));
const loadInspirationChat = () => import('./pages/InspirationChat').then((m) => ({ default: m.InspirationChat }));
const loadWritingDesk = () => import('./pages/WritingDesk').then((m) => ({ default: m.WritingDesk }));
const loadNovelDetail = () => import('./pages/NovelDetail').then((m) => ({ default: m.NovelDetail }));
const loadBlueprintPreview = () => import('./pages/BlueprintPreview').then((m) => ({ default: m.BlueprintPreview }));
const loadCodingDetail = () => import('./pages/CodingDetail').then((m) => ({ default: m.CodingDetail }));
const loadCodingDesk = () => import('./pages/CodingDesk').then((m) => ({ default: m.CodingDesk }));
const loadAdminOverview = () => import('./pages/AdminOverview').then((m) => ({ default: m.AdminOverview }));
const loadAdminUsers = () => import('./pages/AdminUsers').then((m) => ({ default: m.AdminUsers }));
const loadAdminProjects = () => import('./pages/AdminProjects').then((m) => ({ default: m.AdminProjects }));
const loadAdminConfigs = () => import('./pages/AdminConfigs').then((m) => ({ default: m.AdminConfigs }));
const loadSettingsModal = () => import('./components/business/SettingsModal').then((m) => ({ default: m.SettingsModal }));

const primeInitialRouteChunk = () => {
  if (typeof window === 'undefined') return;
  const path = String(window.location.pathname || '/');

  if (path.startsWith('/inspiration/')) {
    void loadInspirationChat();
    return;
  }
  if (path.startsWith('/blueprint/')) {
    void loadBlueprintPreview();
    return;
  }
  if (path.startsWith('/novel/')) {
    void loadNovelDetail();
    return;
  }
  if (path.startsWith('/write/')) {
    void loadWritingDesk();
    return;
  }
  if (path.startsWith('/coding/inspiration/')) {
    void loadInspirationChat();
    return;
  }
  if (path.startsWith('/coding/detail/')) {
    void loadCodingDetail();
    return;
  }
  if (path.startsWith('/coding/desk/')) {
    void loadCodingDesk();
    return;
  }
  if (path.startsWith('/admin/users')) {
    void loadAdminUsers();
    return;
  }
  if (path.startsWith('/admin/projects')) {
    void loadAdminProjects();
    return;
  }
  if (path.startsWith('/admin/configs')) {
    void loadAdminConfigs();
    return;
  }
  if (path.startsWith('/admin/')) {
    void loadAdminOverview();
    return;
  }
  void loadNovelList();
};

primeInitialRouteChunk();

const NovelList = lazy(loadNovelList);
const InspirationChat = lazy(loadInspirationChat);
const WritingDesk = lazy(loadWritingDesk);
const NovelDetail = lazy(loadNovelDetail);
const BlueprintPreview = lazy(loadBlueprintPreview);
const CodingDetail = lazy(loadCodingDetail);
const CodingDesk = lazy(loadCodingDesk);
const AdminOverview = lazy(loadAdminOverview);
const AdminUsers = lazy(loadAdminUsers);
const AdminProjects = lazy(loadAdminProjects);
const AdminConfigs = lazy(loadAdminConfigs);
const SettingsModalLazy = lazy(loadSettingsModal);

const preloadAdminRoutes = () =>
  Promise.allSettled([loadAdminOverview(), loadAdminUsers(), loadAdminProjects(), loadAdminConfigs()]);

const preloadCoreWorkflowRoutes = () =>
  Promise.allSettled([loadInspirationChat(), loadWritingDesk(), loadNovelDetail(), loadBlueprintPreview()]);

const preloadCodingWorkflowRoutes = () =>
  Promise.allSettled([loadCodingDetail(), loadCodingDesk()]);

const shouldSkipAggressivePrefetch = (): boolean => {
  if (typeof navigator === 'undefined') return false;

  const networkInfo = (navigator as Navigator & { connection?: { saveData?: boolean; effectiveType?: string } }).connection;
  if (!networkInfo) return false;

  if (networkInfo.saveData) return true;
  const effectiveType = String(networkInfo.effectiveType || '').toLowerCase();
  return effectiveType.includes('2g') || effectiveType.includes('3g');
};

const RouteFallback: React.FC = () => (
  <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/20 backdrop-blur-sm p-6">
    <div className="flex items-center gap-2 text-sm text-book-text-muted bg-book-bg-paper/90 border border-book-border/60 rounded-lg px-4 py-3 shadow-lg">
      <Loader2 size={18} className="animate-spin" />
      加载中…
    </div>
  </div>
);

// Layout wrapper to handle theme and common UI
const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isDark, setIsDark] = useState(false);
  const { isSettingsOpen, openSettings, closeSettings } = useUIStore();
  const { initialized, authEnabled, user } = useAuthStore();
  const [appearance, setAppearance] = useState(() => readWebAppearanceConfig());
  const canOpenSettings = !authEnabled || Boolean(user);

  useEffect(() => {
    const saved = localStorage.getItem('afn-theme-mode');
    if (saved === 'dark') setIsDark(true);
    if (saved === 'light') setIsDark(false);
  }, []);

  useEffect(() => {
    const cancel = scheduleIdleTask(() => {
      void loadSettingsModal();
    }, { delay: 1200, timeout: 2400 });

    return cancel;
  }, []);

  useEffect(() => {
    if (!initialized) return;
    if (authEnabled && !user) return;
    if (shouldSkipAggressivePrefetch()) return;

    const cancelPrimary = scheduleIdleTask(() => {
      void preloadCoreWorkflowRoutes();
    }, { delay: 1000, timeout: 2600 });

    const cancelSecondary = scheduleIdleTask(() => {
      void preloadCodingWorkflowRoutes();
    }, { delay: 2600, timeout: 3600 });

    return () => {
      cancelPrimary();
      cancelSecondary();
    };
  }, [initialized, authEnabled, user]);

  useEffect(() => {
    if (!initialized) return;
    if (authEnabled && !user) return;
    if (!isAdminUser(authEnabled, user)) return;

    const cancel = scheduleIdleTask(() => {
      void preloadAdminRoutes();
      adminDashboardApi.prefetchTrends(21);
    }, { delay: 1500, timeout: 2800 });

    return cancel;
  }, [initialized, authEnabled, user]);

  useEffect(() => {
    const refresh = () => setAppearance(readWebAppearanceConfig());
    const onCustom = () => refresh();
    const onStorage = (e: StorageEvent) => {
      if (e.key === WEB_APPEARANCE_STORAGE_KEY) refresh();
    };
    window.addEventListener(WEB_APPEARANCE_CHANGED_EVENT, onCustom as any);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(WEB_APPEARANCE_CHANGED_EVENT, onCustom as any);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  useEffect(() => {
    if (!initialized) return;
    if (authEnabled && !user) return;

    localStorage.setItem('afn-theme-mode', isDark ? 'dark' : 'light');
    clearThemeVariables();

    const mode = isDark ? 'dark' : 'light';
    themeConfigsApi
      .getActive(mode)
      .then((cfg) => {
        if (cfg) applyThemeFromUnifiedConfig(cfg);
      })
      .catch((e) => {
        const status = Number((e as any)?.response?.status || 0);
        if (status === 401 || status === 403) return;
        console.error(e);
      });
  }, [isDark, initialized, authEnabled, user]);

  useEffect(() => {
    if (!canOpenSettings && isSettingsOpen) {
      closeSettings();
    }
  }, [canOpenSettings, isSettingsOpen, closeSettings]);

  const bgEnabled = Boolean(appearance.enabled && String(appearance.backgroundImageUrl || '').trim());
  const bgUrl = bgEnabled ? String(appearance.backgroundImageUrl || '').trim() : '';
  const bgBlur = bgEnabled ? Math.max(0, Math.min(48, Number(appearance.blurPx) || 0)) : 0;
  const bgOverlayOpacity = bgEnabled ? Math.max(0, Math.min(1, Number(appearance.overlayOpacity))) : 0;

  return (
    <div className="min-h-screen bg-book-bg transition-colors duration-300 flex flex-col relative">
      {bgEnabled ? (
        <div className="fixed inset-0 -z-10 pointer-events-none">
          <div
            className="absolute inset-0 bg-center bg-cover"
            style={{
              backgroundImage: `url(${bgUrl})`,
              filter: bgBlur > 0 ? `blur(${bgBlur}px)` : undefined,
              transform: bgBlur > 0 ? 'scale(1.05)' : undefined,
            }}
          />
          <div className="absolute inset-0 bg-book-bg" style={{ opacity: bgOverlayOpacity }} />
        </div>
      ) : null}

      <ToastContainer />
      <ConfirmDialogHost />
      {isSettingsOpen ? (
        <Suspense fallback={null}>
          <SettingsModalLazy isOpen={isSettingsOpen} onClose={closeSettings} />
        </Suspense>
      ) : null}

      <main className="flex-1 flex flex-col min-h-0">{children}</main>

      {canOpenSettings ? (
        <button
          onClick={openSettings}
          className="fixed bottom-20 right-6 z-[100] p-3 rounded-full bg-book-bg-paper border border-book-border shadow-lg hover:border-book-primary hover:text-book-primary transition-all duration-300 group"
          title="全局设置"
        >
          <Settings size={20} className="group-hover:rotate-90 transition-transform duration-500" />
        </button>
      ) : null}

      <button
        onClick={() => setIsDark(!isDark)}
        className="fixed bottom-6 right-6 z-[100] p-3 rounded-full bg-book-bg-paper border border-book-border shadow-lg hover:border-book-primary hover:text-book-primary transition-all duration-300 group"
        title={isDark ? '切换到亮色模式' : '切换到深色模式'}
      >
        {isDark ? (
          <Sun size={20} className="group-hover:rotate-90 transition-transform duration-500" />
        ) : (
          <Moon size={20} className="group-hover:-rotate-12 transition-transform duration-500" />
        )}
      </button>
    </div>
  );
};

function App() {
  return (
    <Router>
      <Layout>
        <ErrorBoundary>
          <AuthGate>
            <Suspense fallback={<RouteFallback />}>
              <Routes>
                <Route path="/" element={<NovelList />} />
                <Route path="/inspiration/:id" element={<InspirationChat />} />
                <Route path="/blueprint/:id" element={<BlueprintPreview />} />
                <Route path="/novel/:id" element={<NovelDetail />} />
                <Route path="/write/:id" element={<WritingDesk />} />

                <Route path="/coding/inspiration/:id" element={<InspirationChat mode="coding" />} />
                <Route path="/coding/detail/:id" element={<CodingDetail />} />
                <Route path="/coding/desk/:id" element={<CodingDesk />} />

                <Route path="/admin" element={<Navigate to="/admin/overview" replace />} />
                <Route path="/admin/overview" element={<AdminOverview />} />
                <Route path="/admin/users" element={<AdminUsers />} />
                <Route path="/admin/projects" element={<AdminProjects />} />
                <Route path="/admin/configs" element={<AdminConfigs />} />
              </Routes>
            </Suspense>
          </AuthGate>
        </ErrorBoundary>
      </Layout>
    </Router>
  );
}

export default App;
