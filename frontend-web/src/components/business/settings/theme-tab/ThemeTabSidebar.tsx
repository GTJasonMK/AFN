import React from 'react';
import {
  CheckCircle2,
  Circle,
  Download,
  Palette,
  RefreshCw,
  Search,
  Upload,
} from 'lucide-react';
import type {
  ThemeConfigListItem,
  ThemeMode,
} from '../../../../api/themeConfigs';
import { BookButton } from '../../../ui/BookButton';
import { BookInput } from '../../../ui/BookInput';
import { Dropdown } from '../../../ui/Dropdown';
import { formatDate, type ThemeActionMenuItem } from './shared';

interface ThemeTabSidebarProps {
  loading: boolean;
  exporting: boolean;
  importing: boolean;
  query: string;
  currentMode: ThemeMode;
  modeView: ThemeMode;
  modeListCount: number;
  filteredList: ThemeConfigListItem[];
  selectedId: number | null;
  activatingId: number | null;
  busyId: number | null;
  fileInputRef: React.RefObject<HTMLInputElement>;
  onRefresh: () => void;
  onSyncCurrent: () => void;
  onExportAll: () => void;
  onImportClick: () => void;
  onImportFile: (file: File) => void;
  onModeViewChange: (mode: ThemeMode) => void;
  onQueryChange: (value: string) => void;
  onSelectTheme: (id: number) => void;
  getThemeMenuItems: (cfg: ThemeConfigListItem) => ThemeActionMenuItem[];
}

export const ThemeTabSidebar: React.FC<ThemeTabSidebarProps> = ({
  loading,
  exporting,
  importing,
  query,
  currentMode,
  modeView,
  modeListCount,
  filteredList,
  selectedId,
  activatingId,
  busyId,
  fileInputRef,
  onRefresh,
  onSyncCurrent,
  onExportAll,
  onImportClick,
  onImportFile,
  onModeViewChange,
  onQueryChange,
  onSelectTheme,
  getThemeMenuItems,
}) => {
  return (
    <aside className="min-h-0 flex flex-col border-b border-book-border/45 lg:border-b-0 lg:border-r lg:border-book-border/45">
      <div className="shrink-0 border-b border-book-border/45 bg-book-bg/40 p-4">
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-sm font-bold text-book-text-main">
              <Palette size={16} className="text-book-primary" />
              主题库
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              <BookButton
                variant="ghost"
                size="sm"
                onClick={onRefresh}
                disabled={loading}
              >
                <RefreshCw
                  size={14}
                  className={`mr-1 ${loading ? 'animate-spin' : ''}`}
                />
                刷新
              </BookButton>
              <BookButton variant="ghost" size="sm" onClick={onSyncCurrent}>
                <RefreshCw size={14} className="mr-1" />
                同步
              </BookButton>
              <Dropdown
                label="备份"
                items={[
                  {
                    label: exporting ? '导出中…' : '导出全部',
                    icon: <Download size={14} />,
                    onClick: () => {
                      if (exporting) {
                        return;
                      }
                      onExportAll();
                    },
                  },
                  {
                    label: importing ? '导入中…' : '导入…',
                    icon: <Upload size={14} />,
                    onClick: onImportClick,
                  },
                ]}
              />
              <input
                ref={fileInputRef}
                type="file"
                accept="application/json"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) {
                    onImportFile(file);
                  }
                }}
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="inline-flex rounded-full border border-book-border/55 bg-book-bg-paper/80 p-1">
              <button
                type="button"
                onClick={() => onModeViewChange('light')}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-all ${
                  modeView === 'light'
                    ? 'bg-book-primary text-white shadow-lg'
                    : 'text-book-text-muted hover:text-book-text-main'
                }`}
              >
                亮色
              </button>
              <button
                type="button"
                onClick={() => onModeViewChange('dark')}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-all ${
                  modeView === 'dark'
                    ? 'bg-book-primary text-white shadow-lg'
                    : 'text-book-text-muted hover:text-book-text-main'
                }`}
              >
                深色
              </button>
            </div>
            <div className="text-[11px] text-book-text-muted">
              当前界面：
              <span className="font-mono">
                {currentMode === 'light' ? 'LIGHT' : 'DARK'}
              </span>
              {' · '}
              共 <span className="font-mono">{modeListCount}</span> 条
            </div>
          </div>

          <div className="relative">
            <BookInput
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="搜索主题…"
              className="py-2 pl-9 text-xs"
            />
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-book-text-muted"
            />
          </div>
        </div>
      </div>

      <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto p-3 pr-1">
        {loading ? (
          <div className="py-10 text-center text-sm text-book-text-muted">
            加载中…
          </div>
        ) : filteredList.length === 0 ? (
          <div className="py-10 text-center text-sm text-book-text-muted">
            {query.trim() ? '未找到匹配主题' : '暂无主题配置'}
          </div>
        ) : (
          <div className="space-y-2">
            {filteredList.map((cfg) => {
              const isSelected = cfg.id === selectedId;
              const isBusy = activatingId === cfg.id || busyId === cfg.id;

              return (
                <button
                  key={cfg.id}
                  type="button"
                  onClick={() => onSelectTheme(cfg.id)}
                  className={`group w-full rounded-[22px] border px-3 py-2 text-left transition-all ${
                    isSelected
                      ? 'border-book-primary/30 bg-book-primary/10'
                      : 'border-book-border/40 bg-book-bg-paper/40 hover:border-book-primary/20 hover:bg-book-bg-paper/55'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        {cfg.is_active ? (
                          <CheckCircle2
                            size={16}
                            className="text-book-primary"
                          />
                        ) : (
                          <Circle
                            size={16}
                            className="text-book-text-muted"
                          />
                        )}
                        <div className="min-w-0 flex-1 truncate text-xs font-bold text-book-text-main">
                          {cfg.config_name}
                        </div>
                        {cfg.is_active ? (
                          <span className="shrink-0 rounded-full border border-book-primary/25 bg-book-primary/10 px-2 py-0.5 text-[10px] font-bold text-book-primary">
                            已激活
                          </span>
                        ) : null}
                      </div>
                      <div className="mt-1 text-[10px] text-book-text-muted">
                        更新：{formatDate(cfg.updated_at)} · ID {cfg.id}
                      </div>
                    </div>

                    <div className="shrink-0 flex items-center gap-2">
                      <Dropdown items={getThemeMenuItems(cfg)} />
                    </div>
                  </div>

                  {isBusy ? (
                    <div className="mt-2 text-[10px] text-book-text-muted">
                      处理中…
                    </div>
                  ) : null}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
};
