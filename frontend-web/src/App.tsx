import { useState, useEffect, lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from './components/feedback/Toast';
import { ErrorBoundary } from './components/feedback/ErrorBoundary';
import { ConfirmDialogHost } from './components/feedback/ConfirmDialog';
import { BookIconButton } from './components/ui/BookButton';
import { Settings, Moon, Sun, Loader2 } from 'lucide-react';
import { useUIStore } from './store/ui';
import { themeConfigsApi } from './api/themeConfigs';
import { applyThemeFromUnifiedConfig, clearThemeVariables } from './theme/applyTheme';
import { readWebAppearanceConfig, WEB_APPEARANCE_CHANGED_EVENT, WEB_APPEARANCE_STORAGE_KEY } from './theme/webAppearance';
import { AuthGate } from './components/auth/AuthGate';
import { useAuthStore } from './store/auth';
import { scheduleIdleTask } from './utils/scheduleIdleTask';
import { usePersistedState } from './hooks/usePersistedState';

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
const THEME_APPLIED_EVENT = 'afn:theme-applied';

const RouteFallback: React.FC = () => (
  <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/20 backdrop-blur-sm p-6">
    <div className="flex items-center gap-2 text-sm text-book-text-muted bg-book-bg-paper/90 border border-book-border/60 rounded-lg px-4 py-3 shadow-lg">
      <Loader2 size={18} className="animate-spin" />
      加载中…
    </div>
  </div>
);

// Layout wrapper to handle theme and common UI
const Layout: React.FC<{ children: (context: { isDark: boolean }) => React.ReactNode }> = ({ children }) => {
  const [isDark, setIsDark] = usePersistedState<boolean>('afn-theme-mode', false, {
    parse: (raw) => String(raw).trim().toLowerCase() === 'dark',
    serialize: (value) => (value ? 'dark' : 'light'),
  });
  const { isSettingsOpen, openSettings, closeSettings } = useUIStore();
  const { initialized, authEnabled, user } = useAuthStore();
  const [appearance, setAppearance] = useState(() => readWebAppearanceConfig());
  const canOpenSettings = !authEnabled || Boolean(user);

  useEffect(() => {
    const cancel = scheduleIdleTask(() => {
      void loadSettingsModal();
    }, { delay: 1200, timeout: 2400 });

    return cancel;
  }, []);

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
    window.dispatchEvent(new CustomEvent(THEME_APPLIED_EVENT, { detail: { mode: isDark ? 'dark' : 'light' } }));
  }, [isDark]);

  useEffect(() => {
    if (!initialized) return;
    if (authEnabled && !user) return;
    clearThemeVariables();

    const mode = isDark ? 'dark' : 'light';
    let cancelled = false;

    themeConfigsApi
      .getActive(mode)
      .then((cfg) => {
        if (cancelled) return;
        if (cfg && cfg.parent_mode === mode) {
          applyThemeFromUnifiedConfig(cfg);
        }
        window.dispatchEvent(new CustomEvent(THEME_APPLIED_EVENT, { detail: { mode } }));
      })
      .catch((e) => {
        if (cancelled) return;
        const status = Number((e as any)?.response?.status || 0);
        if (status === 401 || status === 403) return;
        console.error(e);
      });

    return () => {
      cancelled = true;
    };
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
    <div className="h-[100dvh] min-h-0 overflow-hidden bg-book-bg transition-colors duration-300 flex flex-col relative">
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

      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">{children({ isDark })}</main>

      <div className="fixed z-[100] flex flex-col gap-3 right-[calc(1.5rem+env(safe-area-inset-right))] bottom-[calc(1.5rem+env(safe-area-inset-bottom))]">
        {canOpenSettings ? (
          <BookIconButton
            label="全局设置"
            onClick={openSettings}
            className="group"
            variant="secondary"
            size="md"
          >
            <Settings size={20} className="group-hover:rotate-90 transition-transform duration-500" />
          </BookIconButton>
        ) : null}

        <BookIconButton
          label={isDark ? '切换到亮色模式' : '切换到深色模式'}
          onClick={() => setIsDark((prev) => !prev)}
          className="group"
          variant="secondary"
          size="md"
        >
          {isDark ? (
            <Sun size={20} className="group-hover:rotate-90 transition-transform duration-500" />
          ) : (
            <Moon size={20} className="group-hover:-rotate-12 transition-transform duration-500" />
          )}
        </BookIconButton>
      </div>
    </div>
  );
};

function App() {
  return (
    <Router>
      <Layout>
        {({ isDark }) => (
          <ErrorBoundary>
            <AuthGate>
              <div className="flex-1 min-h-0 overflow-hidden">
                <Suspense fallback={<RouteFallback />}>
                  <Routes>
                    <Route path="/" element={<NovelList isDark={isDark} />} />
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
              </div>
            </AuthGate>
          </ErrorBoundary>
        )}
      </Layout>
    </Router>
  );
}

export default App;
