import { useState, useEffect, lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ToastContainer } from './components/feedback/Toast';
import { ErrorBoundary } from './components/feedback/ErrorBoundary';
import { Settings, Moon, Sun, Loader2 } from 'lucide-react';
import { SettingsModal } from './components/business/SettingsModal';
import { useUIStore } from './store/ui';
import { themeConfigsApi } from './api/themeConfigs';
import { applyThemeFromUnifiedConfig, clearThemeVariables } from './theme/applyTheme';
import { readWebAppearanceConfig, WEB_APPEARANCE_CHANGED_EVENT, WEB_APPEARANCE_STORAGE_KEY } from './theme/webAppearance';

// Route-level code splitting：降低首屏 JS 体积，避免把写作台/漫画等重组件打进同一个 chunk
const NovelList = lazy(() => import('./pages/NovelList').then((m) => ({ default: m.NovelList })));
const InspirationChat = lazy(() => import('./pages/InspirationChat').then((m) => ({ default: m.InspirationChat })));
const WritingDesk = lazy(() => import('./pages/WritingDesk').then((m) => ({ default: m.WritingDesk })));
const NovelDetail = lazy(() => import('./pages/NovelDetail').then((m) => ({ default: m.NovelDetail })));
const BlueprintPreview = lazy(() => import('./pages/BlueprintPreview').then((m) => ({ default: m.BlueprintPreview })));
const CodingDetail = lazy(() => import('./pages/CodingDetail').then((m) => ({ default: m.CodingDetail })));
const CodingDesk = lazy(() => import('./pages/CodingDesk').then((m) => ({ default: m.CodingDesk })));

const RouteFallback: React.FC = () => (
  <div className="min-h-[60vh] flex items-center justify-center p-6">
    <div className="flex items-center gap-2 text-sm text-book-text-muted">
      <Loader2 size={18} className="animate-spin" />
      加载中…
    </div>
  </div>
);

// Layout wrapper to handle theme and common UI
const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isDark, setIsDark] = useState(false);
  const { isSettingsOpen, openSettings, closeSettings } = useUIStore();
  const [appearance, setAppearance] = useState(() => readWebAppearanceConfig());

  useEffect(() => {
    const saved = localStorage.getItem('afn-theme-mode');
    if (saved === 'dark') setIsDark(true);
    if (saved === 'light') setIsDark(false);
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
  }, [isDark]);

  useEffect(() => {
    localStorage.setItem('afn-theme-mode', isDark ? 'dark' : 'light');

    // 先清理 inline 主题变量，确保在后端不可用时仍能回退到 CSS 默认主题
    clearThemeVariables();

    const mode = isDark ? 'dark' : 'light';
    themeConfigsApi
      .getActive(mode)
      .then((cfg) => {
        if (cfg) applyThemeFromUnifiedConfig(cfg);
      })
      .catch((e) => {
        // 无后端时静默回退到默认 CSS 主题
        console.error(e);
      });
  }, [isDark]);

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
          <div
            className="absolute inset-0 bg-book-bg"
            style={{ opacity: bgOverlayOpacity }}
          />
        </div>
      ) : null}

      <ToastContainer />
      <SettingsModal isOpen={isSettingsOpen} onClose={closeSettings} />
      
      <main className="flex-1 flex flex-col min-h-0">
        {children}
      </main>

      {/* Settings - Fixed Bottom Right */}
      <button 
        onClick={openSettings}
        className="fixed bottom-20 right-6 z-[100] p-3 rounded-full bg-book-bg-paper border border-book-border shadow-lg hover:border-book-primary hover:text-book-primary transition-all duration-300 group"
        title="全局设置"
      >
        <Settings size={20} className="group-hover:rotate-90 transition-transform duration-500" />
      </button>

      {/* Theme Toggle - Fixed Bottom Right */}
      <button 
        onClick={() => setIsDark(!isDark)}
        className="fixed bottom-6 right-6 z-[100] p-3 rounded-full bg-book-bg-paper border border-book-border shadow-lg hover:border-book-primary hover:text-book-primary transition-all duration-300 group"
        title={isDark ? "切换到亮色模式" : "切换到深色模式"}
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
          <Suspense fallback={<RouteFallback />}>
            <Routes>
              <Route path="/" element={<NovelList />} />
              <Route path="/inspiration/:id" element={<InspirationChat />} />
              <Route path="/blueprint/:id" element={<BlueprintPreview />} />
              <Route path="/novel/:id" element={<NovelDetail />} />
              <Route path="/write/:id" element={<WritingDesk />} />
              
              {/* Coding Routes */}
              <Route path="/coding/inspiration/:id" element={<InspirationChat mode="coding" />} />
              <Route path="/coding/detail/:id" element={<CodingDetail />} />
              <Route path="/coding/desk/:id" element={<CodingDesk />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </Layout>
    </Router>
  );
}

export default App;
