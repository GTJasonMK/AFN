import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { NovelList } from './pages/NovelList';
import { InspirationChat } from './pages/InspirationChat';
import { WritingDesk } from './pages/WritingDesk';
import { NovelDetail } from './pages/NovelDetail';
import { CodingDetail } from './pages/CodingDetail';
import { ToastContainer } from './components/feedback/Toast';
import { ErrorBoundary } from './components/feedback/ErrorBoundary';
import { Settings, Moon, Sun } from 'lucide-react';
import { SettingsModal } from './components/business/SettingsModal';
import { useUIStore } from './store/ui';
import { themeConfigsApi } from './api/themeConfigs';
import { applyThemeFromUnifiedConfig, clearThemeVariables } from './theme/applyTheme';

// Layout wrapper to handle theme and common UI
const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isDark, setIsDark] = useState(false);
  const { isSettingsOpen, openSettings, closeSettings } = useUIStore();

  useEffect(() => {
    const saved = localStorage.getItem('afn-theme-mode');
    if (saved === 'dark') setIsDark(true);
    if (saved === 'light') setIsDark(false);
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

  return (
    <div className="min-h-screen bg-book-bg transition-colors duration-300 flex flex-col relative">
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
          <Routes>
            <Route path="/" element={<NovelList />} />
            <Route path="/inspiration/:id" element={<InspirationChat />} />
            <Route path="/novel/:id" element={<NovelDetail />} />
            <Route path="/write/:id" element={<WritingDesk />} />
            
            {/* Coding Routes */}
            <Route path="/coding/inspiration/:id" element={<InspirationChat mode="coding" />} />
            <Route path="/coding/detail/:id" element={<CodingDetail />} />
          </Routes>
        </ErrorBoundary>
      </Layout>
    </Router>
  );
}

export default App;
