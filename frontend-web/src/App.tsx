import { useState, useEffect } from 'react';
import { NovelList } from './pages/NovelList';

function App() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  return (
    <div className="min-h-screen bg-book-bg transition-colors duration-300">
      {/* 简单的顶部导航 */}
      <nav className="border-b border-book-border bg-book-bg-glass sticky top-0 z-50 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="font-serif font-bold text-xl text-book-primary tracking-wide">
            AFN <span className="text-book-text-main text-sm font-sans font-normal opacity-70">Web Edition</span>
          </div>
          
          <button 
            onClick={() => setIsDark(!isDark)}
            className="p-2 rounded-full hover:bg-book-text-main/10 text-book-text-secondary transition-colors"
          >
            {isDark ? '🌞 Organic' : '🌙 Academia'}
          </button>
        </div>
      </nav>

      <main>
        <NovelList />
      </main>
    </div>
  );
}

export default App;