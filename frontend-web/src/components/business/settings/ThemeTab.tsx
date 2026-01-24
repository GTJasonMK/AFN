import React, { useEffect, useMemo, useState } from 'react';
import { BookCard } from '../../ui/BookCard';
import { BookButton } from '../../ui/BookButton';
import { useToast } from '../../feedback/Toast';
import { themeConfigsApi, ThemeConfigListItem, ThemeMode } from '../../../api/themeConfigs';
import { applyThemeFromUnifiedConfig } from '../../../theme/applyTheme';
import { CheckCircle2, Circle, RefreshCw, Palette } from 'lucide-react';

function formatTime(iso?: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export const ThemeTab: React.FC = () => {
  const { addToast } = useToast();
  const [items, setItems] = useState<ThemeConfigListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [activatingId, setActivatingId] = useState<number | null>(null);

  const fetchList = async () => {
    setLoading(true);
    try {
      const data = await themeConfigsApi.list();
      setItems(data);
    } catch (e) {
      console.error(e);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchList();
  }, []);

  const byMode = useMemo(() => {
    const light = items.filter((i) => i.parent_mode === 'light');
    const dark = items.filter((i) => i.parent_mode === 'dark');
    return { light, dark };
  }, [items]);

  const currentMode: ThemeMode = document.documentElement.classList.contains('dark') ? 'dark' : 'light';

  const handleActivate = async (id: number) => {
    setActivatingId(id);
    try {
      const cfg = await themeConfigsApi.activate(id);
      addToast(`已激活主题：${cfg.config_name}`, 'success');

      // 若激活的是当前模式，立刻应用到 CSS 变量
      if (cfg.parent_mode === currentMode) {
        applyThemeFromUnifiedConfig(cfg);
      }

      await fetchList();
    } catch (e) {
      console.error(e);
    } finally {
      setActivatingId(null);
    }
  };

  const handleSyncCurrent = async () => {
    try {
      const cfg = await themeConfigsApi.getActive(currentMode);
      if (cfg) {
        applyThemeFromUnifiedConfig(cfg);
        addToast('已同步当前主题到 WebUI', 'success');
      } else {
        addToast('当前模式没有激活的主题配置（已使用默认主题）', 'error');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const renderSection = (mode: ThemeMode, list: ThemeConfigListItem[]) => {
    return (
      <BookCard className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs font-bold text-book-text-muted flex items-center gap-2">
            <Palette size={14} className="text-book-primary" />
            {mode === 'light' ? '亮色主题' : '深色主题'}
          </div>
          <div className="text-[11px] text-book-text-muted">
            当前显示模式：{currentMode === 'light' ? '亮色' : '深色'}
          </div>
        </div>

        {list.length === 0 ? (
          <div className="py-8 text-center text-book-text-muted text-sm">暂无主题配置</div>
        ) : (
          <div className="space-y-3">
            {list.map((cfg) => (
              <BookCard key={cfg.id} className="p-4 bg-book-bg/40 border-book-border/40">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      {cfg.is_active ? (
                        <CheckCircle2 size={16} className="text-book-primary" />
                      ) : (
                        <Circle size={16} className="text-book-text-muted" />
                      )}
                      <div className="font-bold text-book-text-main truncate">{cfg.config_name}</div>
                      {cfg.is_active && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-book-primary/10 text-book-primary font-bold">
                          已激活
                        </span>
                      )}
                    </div>
                    <div className="mt-2 text-xs text-book-text-muted grid grid-cols-2 gap-2">
                      <div className="truncate">创建：{formatTime(cfg.created_at)}</div>
                      <div className="truncate">更新：{formatTime(cfg.updated_at)}</div>
                    </div>
                  </div>

                  <div className="shrink-0 flex flex-col gap-2">
                    {!cfg.is_active && (
                      <BookButton
                        variant="primary"
                        size="sm"
                        onClick={() => handleActivate(cfg.id)}
                        disabled={activatingId === cfg.id}
                      >
                        {activatingId === cfg.id ? '切换中…' : '激活'}
                      </BookButton>
                    )}
                  </div>
                </div>
              </BookCard>
            ))}
          </div>
        )}
      </BookCard>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-bold text-book-text-main">主题</div>
        <div className="flex items-center gap-2">
          <BookButton variant="ghost" size="sm" onClick={handleSyncCurrent}>
            同步当前主题
          </BookButton>
          <BookButton variant="ghost" size="sm" onClick={fetchList} disabled={loading}>
            <RefreshCw size={14} className={`mr-1 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </BookButton>
        </div>
      </div>

      <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 leading-relaxed">
        说明：主题配置来自后端主题系统。激活后会立即应用到当前 WebUI（仅对对应模式生效）。
      </div>

      <div className="grid grid-cols-2 gap-4">
        {renderSection('light', byMode.light)}
        {renderSection('dark', byMode.dark)}
      </div>
    </div>
  );
};

