import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { BookButton } from '../../ui/BookButton';
import { BookCard } from '../../ui/BookCard';
import { BookSlider } from '../../ui/BookSlider';
import { BookInput, BookTextarea } from '../../ui/BookInput';
import { useToast } from '../../feedback/Toast';
import { confirmDialog } from '../../feedback/ConfirmDialog';
import { themeConfigsApi, ThemeConfigListItem, ThemeConfigUnifiedRead, ThemeMode } from '../../../api/themeConfigs';
import { applyThemeFromUnifiedConfig, buildCssVarsFromUnifiedConfig } from '../../../theme/applyTheme';
import { CheckCircle2, Circle, Copy, Download, Edit3, Palette, RefreshCw, RotateCcw, Search, Trash2, Upload } from 'lucide-react';
import { SettingsTabPanel } from './components/SettingsTabPanel';
import { defaultWebAppearanceConfig, notifyWebAppearanceChanged, readWebAppearanceConfig, writeWebAppearanceConfig, type WebAppearanceConfig } from '../../../theme/webAppearance';
import { Dropdown } from '../../ui/Dropdown';
import { Modal } from '../../ui/Modal';
import { downloadJson } from '../../../utils/downloadFile';
import {
  NovelDialogIntro,
  NovelDialogMetric,
  NovelDialogMetricGrid,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from '../novel/NovelDialogPrimitives';
import { useSettingsModalFooter } from './components/SettingsModalFooterContext';

function formatTime(iso?: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function formatDate(iso?: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

export const ThemeTab: React.FC = () => {
  const { addToast } = useToast();
  const { setFooter } = useSettingsModalFooter();
  const [items, setItems] = useState<ThemeConfigListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [activatingId, setActivatingId] = useState<number | null>(null);
  const [appearance, setAppearance] = useState<WebAppearanceConfig>(() => readWebAppearanceConfig());
  const [appearanceBaseline, setAppearanceBaseline] = useState<WebAppearanceConfig>(() => readWebAppearanceConfig());
  const appearanceRef = useRef(appearance);
  appearanceRef.current = appearance;
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedUnified, setSelectedUnified] = useState<ThemeConfigUnifiedRead | null>(null);
  const [selectedLoading, setSelectedLoading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingConfig, setEditingConfig] = useState<ThemeConfigUnifiedRead | null>(null);
  const [editingLoading, setEditingLoading] = useState(false);
  const [editingSaving, setEditingSaving] = useState(false);
  const [editingName, setEditingName] = useState('');
  const [editingJson, setEditingJson] = useState('');
  const [editingError, setEditingError] = useState<string | null>(null);

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

  const namesByMode = useMemo(() => {
    const map: Record<ThemeMode, Set<string>> = { light: new Set(), dark: new Set() };
    for (const it of items) {
      const name = String(it.config_name || '').trim();
      if (!name) continue;
      if (it.parent_mode === 'light' || it.parent_mode === 'dark') {
        map[it.parent_mode].add(name);
      }
    }
    return map;
  }, [items]);

  const currentMode: ThemeMode = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
  const [modeView, setModeView] = useState<ThemeMode>(currentMode);
  const modeList = modeView === 'light' ? byMode.light : byMode.dark;

  const filteredList = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return modeList;
    return modeList.filter((it) => String(it.config_name || '').toLowerCase().includes(q));
  }, [modeList, query]);

  const selectedItem = useMemo(() => {
    if (!selectedId) return null;
    return items.find((it) => it.id === selectedId) ?? null;
  }, [items, selectedId]);

  useEffect(() => {
    if (modeList.length === 0) {
      setSelectedId(null);
      return;
    }
    if (selectedId && modeList.some((it) => it.id === selectedId)) return;
    const active = modeList.find((it) => it.is_active);
    setSelectedId(active?.id ?? modeList[0].id);
  }, [modeList, selectedId]);

  const refreshSelectedUnified = useCallback(
    async (id?: number | null) => {
      const targetId = Number(id ?? selectedId ?? 0);
      if (!targetId) return;
      setSelectedLoading(true);
      try {
        const cfg = await themeConfigsApi.getUnified(targetId);
        setSelectedUnified(cfg);
      } catch (e) {
        console.error(e);
        setSelectedUnified(null);
      } finally {
        setSelectedLoading(false);
      }
    },
    [selectedId],
  );

  useEffect(() => {
    if (!selectedId) {
      setSelectedUnified(null);
      return;
    }
    let cancelled = false;
    setSelectedLoading(true);
    themeConfigsApi
      .getUnified(selectedId)
      .then((cfg) => {
        if (cancelled) return;
        setSelectedUnified(cfg);
      })
      .catch((e) => {
        console.error(e);
        if (cancelled) return;
        setSelectedUnified(null);
      })
      .finally(() => {
        if (cancelled) return;
        setSelectedLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const appearanceDirty = useMemo(() => {
    return JSON.stringify(appearance) !== JSON.stringify(appearanceBaseline);
  }, [appearance, appearanceBaseline]);

  const previewStyle = useMemo(() => {
    if (!selectedUnified) return undefined;
    const vars = buildCssVarsFromUnifiedConfig(selectedUnified);
    const style: React.CSSProperties = {};
    Object.entries(vars).forEach(([key, value]) => {
      (style as any)[key] = value;
    });
    return style;
  }, [selectedUnified]);

  const sanitizeFilename = (name: string) => {
    const raw = String(name || '').trim();
    if (!raw) return 'theme';
    return raw.replace(/[\\/:*?"<>|]/g, '_').slice(0, 80);
  };

  const buildEditPayloadText = (cfg: ThemeConfigUnifiedRead): string => {
    const v = Number(cfg.config_version || 1);
    if (v === 2) {
      const payload = {
        token_colors: cfg.token_colors ?? null,
        token_typography: cfg.token_typography ?? null,
        token_spacing: cfg.token_spacing ?? null,
        token_radius: cfg.token_radius ?? null,
        comp_button: cfg.comp_button ?? null,
        comp_card: cfg.comp_card ?? null,
        comp_input: cfg.comp_input ?? null,
        comp_sidebar: cfg.comp_sidebar ?? null,
        comp_header: cfg.comp_header ?? null,
        comp_dialog: cfg.comp_dialog ?? null,
        comp_scrollbar: cfg.comp_scrollbar ?? null,
        comp_tooltip: cfg.comp_tooltip ?? null,
        comp_tabs: cfg.comp_tabs ?? null,
        comp_text: cfg.comp_text ?? null,
        comp_semantic: cfg.comp_semantic ?? null,
        effects: cfg.effects ?? null,
      };
      return JSON.stringify(payload, null, 2);
    }
    const payload = {
      primary_colors: cfg.primary_colors ?? null,
      accent_colors: cfg.accent_colors ?? null,
      semantic_colors: cfg.semantic_colors ?? null,
      text_colors: cfg.text_colors ?? null,
      background_colors: cfg.background_colors ?? null,
      border_effects: cfg.border_effects ?? null,
      button_colors: cfg.button_colors ?? null,
      typography: cfg.typography ?? null,
      border_radius: cfg.border_radius ?? null,
      spacing: cfg.spacing ?? null,
      animation: cfg.animation ?? null,
      button_sizes: cfg.button_sizes ?? null,
    };
    return JSON.stringify(payload, null, 2);
  };

  const openEditor = async (id: number) => {
    setEditingError(null);
    setEditingId(id);
    setEditingConfig(null);
    setEditingName('');
    setEditingJson('');
    setEditingLoading(true);
    try {
      const cfg = await themeConfigsApi.getUnified(id);
      setEditingConfig(cfg);
      setEditingName(cfg.config_name || '');
      setEditingJson(buildEditPayloadText(cfg));
    } catch (e) {
      console.error(e);
      addToast('加载主题配置失败', 'error');
      setEditingId(null);
    } finally {
      setEditingLoading(false);
    }
  };

  const closeEditor = () => {
    if (editingSaving) return;
    setEditingId(null);
    setEditingConfig(null);
    setEditingError(null);
  };

  const saveEditor = async () => {
    if (!editingId || !editingConfig) return;
    const name = (editingName || '').trim();
    if (!name) {
      setEditingError('配置名称不能为空');
      return;
    }

    let parsed: any;
    try {
      parsed = JSON.parse(editingJson || '{}');
    } catch {
      setEditingError('JSON 格式错误：请检查括号/逗号/引号');
      return;
    }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      setEditingError('JSON 顶层必须是对象（object）');
      return;
    }

    setEditingSaving(true);
    setEditingError(null);
    try {
      const v = Number(editingConfig.config_version || 1);
      if (v === 2) {
        await themeConfigsApi.updateV2(editingId, {
          config_name: name,
          token_colors: parsed.token_colors,
          token_typography: parsed.token_typography,
          token_spacing: parsed.token_spacing,
          token_radius: parsed.token_radius,
          comp_button: parsed.comp_button,
          comp_card: parsed.comp_card,
          comp_input: parsed.comp_input,
          comp_sidebar: parsed.comp_sidebar,
          comp_header: parsed.comp_header,
          comp_dialog: parsed.comp_dialog,
          comp_scrollbar: parsed.comp_scrollbar,
          comp_tooltip: parsed.comp_tooltip,
          comp_tabs: parsed.comp_tabs,
          comp_text: parsed.comp_text,
          comp_semantic: parsed.comp_semantic,
          effects: parsed.effects,
        });
      } else {
        await themeConfigsApi.updateV1(editingId, {
          config_name: name,
          primary_colors: parsed.primary_colors,
          accent_colors: parsed.accent_colors,
          semantic_colors: parsed.semantic_colors,
          text_colors: parsed.text_colors,
          background_colors: parsed.background_colors,
          border_effects: parsed.border_effects,
          button_colors: parsed.button_colors,
          typography: parsed.typography,
          border_radius: parsed.border_radius,
          spacing: parsed.spacing,
          animation: parsed.animation,
          button_sizes: parsed.button_sizes,
        });
      }

      addToast('已保存主题配置', 'success');

      // 如果编辑的是当前模式的激活主题，刷新并立刻应用到 CSS 变量（仅影响 WebUI）
      if (editingConfig.is_active && editingConfig.parent_mode === currentMode) {
        const active = await themeConfigsApi.getActive(currentMode);
        if (active) applyThemeFromUnifiedConfig(active);
      }

      await fetchList();
      if (editingId === selectedId) {
        await refreshSelectedUnified(editingId);
      }
      closeEditor();
    } catch (e) {
      console.error(e);
      addToast('保存失败（请查看后端日志/接口返回）', 'error');
    } finally {
      setEditingSaving(false);
    }
  };

  const handleExportAll = async () => {
    setExporting(true);
    try {
	      const data = await themeConfigsApi.exportAll();
	      const date = new Date().toISOString().slice(0, 10);
	      downloadJson(data, `afn-theme-configs-${date}.json`);
	      addToast('已导出主题配置', 'success');
	    } catch (e) {
	      console.error(e);
	      addToast('导出失败', 'error');
    } finally {
      setExporting(false);
    }
  };

  const handleExportOne = async (cfg: ThemeConfigListItem) => {
    setBusyId(cfg.id);
    try {
	      const data = await themeConfigsApi.exportOne(cfg.id);
	      const date = new Date().toISOString().slice(0, 10);
	      downloadJson(data, `afn-theme-${sanitizeFilename(cfg.config_name)}-${cfg.parent_mode}-${date}.json`);
	      addToast('已导出主题配置', 'success');
	    } catch (e) {
	      console.error(e);
	      addToast('导出失败', 'error');
    } finally {
      setBusyId(null);
    }
  };

  const handleImportClick = () => {
    if (importing) return;
    fileInputRef.current?.click();
  };

  const handleImportFile = async (file: File) => {
    setImporting(true);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed) || !Array.isArray(parsed.configs)) {
        addToast('导入失败：文件结构不符合 theme-configs export 格式', 'error');
        return;
      }
      const result = await themeConfigsApi.importAll(parsed);
      if (result.success) {
        addToast(`导入完成：成功 ${result.imported_count}，跳过 ${result.skipped_count}，失败 ${result.failed_count}`, 'success');
      } else {
        addToast(result.message || '导入失败', 'error');
      }
      await fetchList();
    } catch (e) {
      console.error(e);
      addToast('导入失败：无法解析文件或接口调用失败', 'error');
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDuplicate = async (cfg: ThemeConfigListItem) => {
    setBusyId(cfg.id);
    try {
      const unified = await themeConfigsApi.getUnified(cfg.id);
      const base = String(unified.config_name || cfg.config_name || '主题').trim() || '主题';
      const mode = unified.parent_mode;
      const existing = namesByMode[mode] || new Set<string>();
      let name = `${base} (副本)`;
      let n = 2;
      while (existing.has(name) && n < 50) {
        name = `${base} (副本 ${n})`;
        n += 1;
      }

      if (Number(unified.config_version || 1) === 2) {
        await themeConfigsApi.createV2({
          config_name: name,
          parent_mode: mode,
          token_colors: unified.token_colors ?? undefined,
          token_typography: unified.token_typography ?? undefined,
          token_spacing: unified.token_spacing ?? undefined,
          token_radius: unified.token_radius ?? undefined,
          comp_button: unified.comp_button ?? undefined,
          comp_card: unified.comp_card ?? undefined,
          comp_input: unified.comp_input ?? undefined,
          comp_sidebar: unified.comp_sidebar ?? undefined,
          comp_header: unified.comp_header ?? undefined,
          comp_dialog: unified.comp_dialog ?? undefined,
          comp_scrollbar: unified.comp_scrollbar ?? undefined,
          comp_tooltip: unified.comp_tooltip ?? undefined,
          comp_tabs: unified.comp_tabs ?? undefined,
          comp_text: unified.comp_text ?? undefined,
          comp_semantic: unified.comp_semantic ?? undefined,
          effects: unified.effects ?? undefined,
        } as any);
      } else {
        await themeConfigsApi.createV1({
          config_name: name,
          parent_mode: mode,
          primary_colors: unified.primary_colors ?? undefined,
          accent_colors: unified.accent_colors ?? undefined,
          semantic_colors: unified.semantic_colors ?? undefined,
          text_colors: unified.text_colors ?? undefined,
          background_colors: unified.background_colors ?? undefined,
          border_effects: unified.border_effects ?? undefined,
          button_colors: unified.button_colors ?? undefined,
          typography: unified.typography ?? undefined,
          border_radius: unified.border_radius ?? undefined,
          spacing: unified.spacing ?? undefined,
          animation: unified.animation ?? undefined,
          button_sizes: unified.button_sizes ?? undefined,
        } as any);
      }

      addToast('已复制主题配置', 'success');
      await fetchList();
    } catch (e) {
      console.error(e);
      addToast('复制失败', 'error');
    } finally {
      setBusyId(null);
    }
  };

  const handleReset = async (cfg: ThemeConfigListItem) => {
    const ok = await confirmDialog({
      title: '重置主题配置',
      message: `将重置主题配置“${cfg.config_name}”为默认值。\n是否继续？`,
      confirmText: '重置',
      dialogType: 'warning',
    });
    if (!ok) return;

    setBusyId(cfg.id);
    try {
      const unified = await themeConfigsApi.getUnified(cfg.id);
      if (Number(unified.config_version || 1) === 2) {
        await themeConfigsApi.resetV2(cfg.id);
      } else {
        await themeConfigsApi.resetV1(cfg.id);
      }
      addToast('已重置主题配置', 'success');
      await fetchList();
      if (cfg.id === selectedId) {
        await refreshSelectedUnified(cfg.id);
      }

      if (cfg.is_active && cfg.parent_mode === currentMode) {
        const active = await themeConfigsApi.getActive(currentMode);
        if (active) applyThemeFromUnifiedConfig(active);
      }
    } catch (e) {
      console.error(e);
      addToast('重置失败', 'error');
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (cfg: ThemeConfigListItem) => {
    const ok = await confirmDialog({
      title: '删除主题配置',
      message: `将删除主题配置“${cfg.config_name}”。\n注意：激活中的配置可能无法删除（需先激活其他配置）。\n是否继续？`,
      confirmText: '删除',
      dialogType: 'danger',
    });
    if (!ok) return;

    setBusyId(cfg.id);
    try {
      await themeConfigsApi.delete(cfg.id);
      addToast('已删除主题配置', 'success');
      await fetchList();
    } catch (e) {
      console.error(e);
      addToast('删除失败', 'error');
    } finally {
      setBusyId(null);
    }
  };

  const handleActivate = async (id: number) => {
    setActivatingId(id);
    try {
      const cfg = await themeConfigsApi.activate(id);
      const modeLabel = cfg.parent_mode === 'dark' ? '深色' : '亮色';
      const isCurrentMode = cfg.parent_mode === currentMode;
      addToast(
        isCurrentMode
          ? `已激活并应用${modeLabel}主题：${cfg.config_name}`
          : `已激活${modeLabel}主题：${cfg.config_name}（切换到${modeLabel}模式后生效）`,
        'success'
      );

      // 若激活的是当前模式，立刻应用到 CSS 变量
      if (cfg.parent_mode === currentMode) {
        applyThemeFromUnifiedConfig(cfg);
      }

      await fetchList();
      if (id === selectedId) {
        setSelectedUnified(cfg);
      }
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
        addToast('已同步当前主题到界面', 'success');
      } else {
        addToast('当前模式没有激活主题配置', 'error');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const getThemeMenuItems = (cfg: ThemeConfigListItem) => [
    {
      label: '编辑',
      icon: <Edit3 size={14} />,
      onClick: () => openEditor(cfg.id),
    },
    {
      label: '复制',
      icon: <Copy size={14} />,
      onClick: () => handleDuplicate(cfg),
    },
    {
      label: '导出',
      icon: <Download size={14} />,
      onClick: () => handleExportOne(cfg),
    },
    { type: 'divider' as const },
    {
      label: '重置',
      icon: <RotateCcw size={14} />,
      onClick: () => handleReset(cfg),
      danger: true,
    },
    {
      label: '删除',
      icon: <Trash2 size={14} />,
      onClick: () => handleDelete(cfg),
      danger: true,
    },
  ];

  const applyAppearance = useCallback(() => {
    writeWebAppearanceConfig(appearanceRef.current);
    notifyWebAppearanceChanged();
    setAppearanceBaseline(appearanceRef.current);
    addToast('已应用界面外观（本机生效）', 'success');
  }, [addToast]);

  const resetAppearance = useCallback(() => {
    const cfg = defaultWebAppearanceConfig();
    setAppearance(cfg);
    writeWebAppearanceConfig(cfg);
    notifyWebAppearanceChanged();
    setAppearanceBaseline(cfg);
    addToast('已恢复默认外观', 'success');
  }, [addToast]);

  const footer = useMemo(
    () => (
      <>
        <BookButton variant="ghost" size="sm" onClick={resetAppearance}>
          恢复默认
        </BookButton>
        <BookButton variant="primary" size="sm" onClick={applyAppearance} disabled={!appearanceDirty}>
          {appearanceDirty ? '应用外观' : '已应用'}
        </BookButton>
      </>
    ),
    [applyAppearance, appearanceDirty, resetAppearance],
  );

  useEffect(() => {
    setFooter(footer);
    return () => setFooter(null);
  }, [footer, setFooter]);

  return (
    <SettingsTabPanel className="h-full min-h-0" bodyClassName="h-full min-h-0">
      <div className="flex h-full min-h-0 flex-col gap-4">
        <div className="min-h-0 flex-1 overflow-hidden rounded-[28px] border border-book-border/55 bg-book-bg-paper/70 shadow-surface backdrop-blur-xl">
          <div className="grid h-full min-h-0 lg:grid-cols-[minmax(280px,340px)_minmax(0,1fr)]">
            <aside className="min-h-0 flex flex-col border-b border-book-border/45 lg:border-b-0 lg:border-r lg:border-book-border/45">
              <div className="shrink-0 border-b border-book-border/45 bg-book-bg/40 p-4">
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-sm font-bold text-book-text-main">
                      <Palette size={16} className="text-book-primary" />
                      主题库
                    </div>
                    <div className="flex flex-wrap items-center justify-end gap-2">
                      <BookButton variant="ghost" size="sm" onClick={fetchList} disabled={loading}>
                        <RefreshCw size={14} className={`mr-1 ${loading ? 'animate-spin' : ''}`} />
                        刷新
                      </BookButton>
                      <BookButton variant="ghost" size="sm" onClick={handleSyncCurrent}>
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
                              if (exporting) return;
                              void handleExportAll();
                            },
                          },
                          {
                            label: importing ? '导入中…' : '导入…',
                            icon: <Upload size={14} />,
                            onClick: handleImportClick,
                          },
                        ]}
                      />
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="application/json"
                        className="hidden"
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (f) void handleImportFile(f);
                        }}
                      />
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="inline-flex rounded-full border border-book-border/55 bg-book-bg-paper/80 p-1">
                      <button
                        type="button"
                        onClick={() => setModeView('light')}
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
                        onClick={() => setModeView('dark')}
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
                      当前界面：<span className="font-mono">{currentMode === 'light' ? 'LIGHT' : 'DARK'}</span>
                      {' · '}
                      共 <span className="font-mono">{modeList.length}</span> 条
                    </div>
                  </div>

                  <div className="relative">
                    <BookInput
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="搜索主题…"
                      className="py-2 pl-9 text-xs"
                    />
                    <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-book-text-muted" />
                  </div>
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto p-3 pr-1 custom-scrollbar">
                {loading ? (
                  <div className="py-10 text-center text-book-text-muted text-sm">加载中…</div>
                ) : filteredList.length === 0 ? (
                  <div className="py-10 text-center text-book-text-muted text-sm">
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
                          onClick={() => setSelectedId(cfg.id)}
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
                                  <CheckCircle2 size={16} className="text-book-primary" />
                                ) : (
                                  <Circle size={16} className="text-book-text-muted" />
                                )}
                                <div className="min-w-0 flex-1 truncate text-xs font-bold text-book-text-main">
                                  {cfg.config_name}
                                </div>
                                {cfg.is_active ? (
                                  <span className="shrink-0 text-[10px] rounded-full border border-book-primary/25 bg-book-primary/10 px-2 py-0.5 font-bold text-book-primary">
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
                            <div className="mt-2 text-[10px] text-book-text-muted">处理中…</div>
                          ) : null}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            </aside>

            <section className="min-h-0 flex flex-col">
              <div className="shrink-0 border-b border-book-border/45 bg-book-bg/40 p-4">
                {!selectedItem ? (
                  <div className="text-sm text-book-text-muted">请选择一个主题配置</div>
                ) : (
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="max-w-full truncate text-sm font-bold text-book-text-main">
                          {selectedItem.config_name}
                        </div>
                        <span className="inline-flex rounded-full border border-book-border/55 bg-book-bg-paper/80 px-2.5 py-1 text-[10px] font-bold text-book-text-muted">
                          {selectedItem.parent_mode === 'dark' ? '深色' : '亮色'}
                        </span>
                        {selectedItem.is_active ? (
                          <span className="inline-flex rounded-full border border-book-primary/25 bg-book-primary/10 px-2.5 py-1 text-[10px] font-bold text-book-primary">
                            当前已激活
                          </span>
                        ) : null}
                      </div>
                      <div className="mt-1 text-[11px] text-book-text-muted">
                        创建：{formatDate(selectedItem.created_at)} · 更新：{formatDate(selectedItem.updated_at)}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center justify-end gap-2">
                      {!selectedItem.is_active ? (
                        <BookButton
                          variant="primary"
                          size="sm"
                          onClick={() => handleActivate(selectedItem.id)}
                          disabled={activatingId === selectedItem.id || busyId === selectedItem.id}
                        >
                          {activatingId === selectedItem.id ? '切换中…' : '激活'}
                        </BookButton>
                      ) : null}
                      <BookButton
                        variant="secondary"
                        size="sm"
                        onClick={() => openEditor(selectedItem.id)}
                        disabled={busyId === selectedItem.id}
                      >
                        <Edit3 size={14} className="mr-1" />
                        编辑
                      </BookButton>
                      <Dropdown items={getThemeMenuItems(selectedItem)} label="更多" />
                    </div>
                  </div>
                )}
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto p-4 pr-1 custom-scrollbar">
                {!selectedItem ? (
                  <div className="h-full flex items-center justify-center text-book-text-muted">从左侧选择一个主题</div>
                ) : selectedLoading ? (
                  <div className="py-10 text-center text-book-text-muted text-sm">加载主题详情…</div>
                ) : selectedUnified ? (
                  <div className="space-y-4">
                    <div className="rounded-[24px] border border-book-border/45 bg-book-bg-paper/50 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div className="text-xs font-bold text-book-text-sub">概览</div>
                        <div className="text-[10px] text-book-text-muted">V{selectedUnified.config_version || 1}</div>
                      </div>
                      <div className="mt-3 grid gap-3 sm:grid-cols-2">
                        <div className="rounded-[22px] border border-book-border/45 bg-book-bg/50 px-4 py-3">
                          <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                            Mode
                          </div>
                          <div className="mt-2 text-sm font-bold text-book-text-main">
                            {selectedUnified.parent_mode === 'dark' ? 'Dark' : 'Light'}
                          </div>
                          <div className="mt-1 text-[11px] text-book-text-muted">
                            影响 {selectedUnified.parent_mode === 'dark' ? '深色' : '亮色'} 外观
                          </div>
                        </div>
                        <div className="rounded-[22px] border border-book-border/45 bg-book-bg/50 px-4 py-3">
                          <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                            Version
                          </div>
                          <div className="mt-2 text-sm font-bold text-book-text-main">V{selectedUnified.config_version || 1}</div>
                          <div className="mt-1 text-[11px] text-book-text-muted">
                            {Number(selectedUnified.config_version || 1) === 2 ? '组件/令牌结构' : '传统字段结构'}
                          </div>
                        </div>
                        <div className="rounded-[22px] border border-book-border/45 bg-book-bg/50 px-4 py-3">
                          <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                            Created
                          </div>
                          <div className="mt-2 text-sm font-bold text-book-text-main">{formatDate(selectedUnified.created_at)}</div>
                          <div className="mt-1 text-[11px] text-book-text-muted">{formatTime(selectedUnified.created_at)}</div>
                        </div>
                        <div className="rounded-[22px] border border-book-border/45 bg-book-bg/50 px-4 py-3">
                          <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                            Updated
                          </div>
                          <div className="mt-2 text-sm font-bold text-book-text-main">{formatDate(selectedUnified.updated_at)}</div>
                          <div className="mt-1 text-[11px] text-book-text-muted">{formatTime(selectedUnified.updated_at)}</div>
                        </div>
                      </div>
                    </div>

                    <div
                      className={`rounded-[24px] border border-book-border/45 bg-book-bg-paper/50 p-4 ${
                        selectedUnified.parent_mode === 'dark' ? 'dark' : ''
                      }`}
                      style={previewStyle}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="text-xs font-bold text-book-text-sub">预览（局部）</div>
                        <div className="text-[10px] text-book-text-muted">不会影响整体界面</div>
                      </div>
                      <div className="mt-3 grid gap-3 sm:grid-cols-2">
                        <BookCard variant="glass" className="p-4">
                          <div className="text-xs font-bold text-book-text-main">玻璃卡片</div>
                          <div className="mt-1 text-[11px] leading-relaxed text-book-text-sub">
                            检查在当前主题下的对比度与层次。
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <BookButton size="sm" variant="primary">
                              主按钮
                            </BookButton>
                            <BookButton size="sm" variant="secondary">
                              次按钮
                            </BookButton>
                          </div>
                        </BookCard>
                        <div className="rounded-[24px] border border-book-border/45 bg-book-bg/55 p-4">
                          <div className="text-xs font-bold text-book-text-main">控件</div>
                          <div className="mt-3 space-y-3">
                            <BookInput placeholder="输入框预览…" className="py-2 text-xs" />
                            <div className="flex flex-wrap gap-2">
                              <span className="inline-flex items-center rounded-full border border-book-border/55 bg-book-bg-paper/70 px-3 py-1 text-[10px] font-semibold text-book-text-muted">
                                tag
                              </span>
                              <span className="inline-flex items-center rounded-full border border-book-primary/25 bg-book-primary/10 px-3 py-1 text-[10px] font-bold text-book-primary">
                                active
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-[24px] border border-book-border/45 bg-book-bg-paper/50 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <div className="text-xs font-bold text-book-text-sub">背景与玻璃效果</div>
                          {appearanceDirty ? (
                            <span className="inline-flex rounded-full border border-book-primary/25 bg-book-primary/10 px-2.5 py-1 text-[10px] font-bold text-book-primary">
                              未应用
                            </span>
                          ) : (
                            <span className="inline-flex rounded-full border border-book-border/55 bg-book-bg-paper/70 px-2.5 py-1 text-[10px] font-semibold text-book-text-muted">
                              已应用
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-book-text-muted">应用按钮在右下角</div>
                      </div>

                      <div className="mt-4 grid gap-3 sm:grid-cols-2">
                        <label className="flex items-center gap-2 text-xs font-bold text-book-text-sub">
                          <input
                            type="checkbox"
                            checked={Boolean(appearance.enabled)}
                            onChange={(e) => setAppearance((prev) => ({ ...prev, enabled: e.target.checked }))}
                            className="book-check h-4 w-4 rounded border-book-border/60 bg-book-bg-paper/80"
                          />
                          启用背景图
                        </label>

                        <div className="sm:col-span-2">
                          <div className="text-[11px] font-bold text-book-text-sub">背景图 URL</div>
                          <input
                            type="text"
                            value={appearance.backgroundImageUrl || ''}
                            onChange={(e) => setAppearance((prev) => ({ ...prev, backgroundImageUrl: e.target.value }))}
                            placeholder="https://..."
                            className="book-control mt-1 w-full rounded-2xl border px-4 py-2 text-xs text-book-text-main outline-none focus:border-book-primary/50"
                          />
                        </div>

                        <BookSlider
                          label="模糊（px）"
                          min={0}
                          max={48}
                          step={1}
                          value={Number(appearance.blurPx) || 0}
                          onChange={(next) => setAppearance((prev) => ({ ...prev, blurPx: next }))}
                          formatValue={(v) => `${Math.round(v)}px`}
                          numberInputWidthClassName="w-20"
                        />

                        <BookSlider
                          label="遮罩不透明度（0~1）"
                          min={0}
                          max={1}
                          step={0.05}
                          value={Number(appearance.overlayOpacity) || 0}
                          onChange={(next) => setAppearance((prev) => ({ ...prev, overlayOpacity: next }))}
                          formatValue={(v) => v.toFixed(2)}
                          numberInputWidthClassName="w-20"
                        />
                      </div>

                      {appearance.enabled && (appearance.backgroundImageUrl || '').trim() ? (
                        <div className="mt-4">
                          <div className="text-[11px] text-book-text-muted mb-1">预览</div>
                          <div className="h-28 rounded-2xl overflow-hidden border border-book-border/40 bg-book-bg relative">
                            <div
                              className="absolute inset-0 bg-center bg-cover"
                              style={{
                                backgroundImage: `url(${String(appearance.backgroundImageUrl || '').trim()})`,
                                filter:
                                  (Number(appearance.blurPx) || 0) > 0
                                    ? `blur(${Math.max(0, Math.min(48, Number(appearance.blurPx) || 0))}px)`
                                    : undefined,
                                transform: (Number(appearance.blurPx) || 0) > 0 ? 'scale(1.05)' : undefined,
                              }}
                            />
                            <div
                              className="absolute inset-0 bg-book-bg"
                              style={{ opacity: Math.max(0, Math.min(1, Number(appearance.overlayOpacity) || 0)) }}
                            />
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </div>
                ) : (
                  <div className="py-10 text-center text-book-text-muted text-sm">无法加载该主题详情</div>
                )}
              </div>
            </section>
          </div>
        </div>
      </div>

      <Modal
        isOpen={Boolean(editingId)}
        onClose={closeEditor}
        title={editingConfig ? `编辑主题：${editingConfig.config_name}` : '编辑主题'}
        maxWidthClassName="max-w-4xl"
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <BookButton variant="ghost" onClick={closeEditor} disabled={editingSaving}>
              取消
            </BookButton>
            <BookButton variant="primary" onClick={saveEditor} disabled={editingSaving || editingLoading}>
              {editingSaving ? '保存中…' : '保存'}
            </BookButton>
          </div>
        }
      >
        {editingLoading ? (
          <NovelDialogSurface className="text-sm text-book-text-muted">加载中…</NovelDialogSurface>
        ) : editingConfig ? (
          <NovelDialogStack>
            <NovelDialogIntro
              eyebrow="Theme Editor"
              title={`编辑主题：${editingConfig.config_name}`}
              description="这里直接编辑后端主题配置 JSON。适合在明确理解 Schema 的前提下做精细调整和版本迁移。"
            >
              <div className="flex flex-wrap gap-2">
                <span className="story-pill">{editingConfig.parent_mode === 'dark' ? '深色模式' : '亮色模式'}</span>
                <span className="story-pill">V{editingConfig.config_version || 1}</span>
                {editingConfig.is_active ? <span className="story-pill">当前已激活</span> : null}
              </div>
            </NovelDialogIntro>

            <NovelDialogMetricGrid>
              <NovelDialogMetric
                label="主题模式"
                value={editingConfig.parent_mode === 'dark' ? 'Dark' : 'Light'}
                note="决定这份主题配置作用于亮色还是深色外观。"
              />
              <NovelDialogMetric
                label="配置版本"
                value={`V${editingConfig.config_version || 1}`}
                note={Number(editingConfig.config_version || 1) === 1 ? '可迁移到组件模式 V2。' : '当前已是 V2 结构。'}
              />
            </NovelDialogMetricGrid>

            <NovelDialogSection
              eyebrow="Metadata"
              title="配置元信息"
              description="先确认配置名称、模式和版本，再决定是否需要重新加载或迁移。"
              actions={(
                <>
                  <BookButton
                    variant="ghost"
                    size="sm"
                    onClick={async () => {
                      if (!editingConfig) return;
                      setEditingLoading(true);
                      try {
                        const cfg = await themeConfigsApi.getUnified(editingId!);
                        setEditingConfig(cfg);
                        setEditingName(cfg.config_name || '');
                        setEditingJson(buildEditPayloadText(cfg));
                        addToast('已重新加载', 'success');
                      } catch (e) {
                        console.error(e);
                        addToast('重新加载失败', 'error');
                      } finally {
                        setEditingLoading(false);
                      }
                    }}
                    disabled={editingSaving}
                  >
                    重新加载
                  </BookButton>
                  {Number(editingConfig.config_version || 1) === 1 ? (
                    <BookButton
                      variant="secondary"
                      size="sm"
                      onClick={async () => {
                        const ok = await confirmDialog({
                          title: '迁移到 V2',
                          message: '将迁移到 V2（组件模式）并填充默认 V2 字段。\n是否继续？',
                          confirmText: '迁移',
                          dialogType: 'warning',
                        });
                        if (!ok) return;
                        setEditingLoading(true);
                        try {
                          await themeConfigsApi.migrateToV2(editingId!);
                          const cfg = await themeConfigsApi.getUnified(editingId!);
                          setEditingConfig(cfg);
                          setEditingJson(buildEditPayloadText(cfg));
                          addToast('已迁移到 V2（组件模式）', 'success');
                          await fetchList();
                        } catch (e) {
                          console.error(e);
                          addToast('迁移失败', 'error');
                        } finally {
                          setEditingLoading(false);
                        }
                      }}
                      disabled={editingSaving}
                      title="桌面端默认使用组件模式（V2）。迁移后可编辑 token/comp/effects。"
                    >
                      迁移到V2
                    </BookButton>
                  ) : null}
                </>
              )}
            >
              <BookInput
                label="配置名称"
                value={editingName}
                onChange={(e) => setEditingName(e.target.value)}
                disabled={editingSaving}
              />
            </NovelDialogSection>

            {editingError ? (
              <NovelDialogSurface className="border-red-200 bg-red-50/80 text-xs leading-relaxed text-red-600">
                {editingError}
              </NovelDialogSurface>
            ) : null}

            <NovelDialogSection
              eyebrow="JSON"
              title="配置 JSON"
              description="按后端 Schema 字段填写。这里的修改会直接影响 Web 主题变量与组件外观表现。"
            >
              <BookTextarea
                label="配置 JSON（按后端 Schema 字段填写）"
                value={editingJson}
                onChange={(e) => setEditingJson(e.target.value)}
                rows={18}
                className="font-mono text-xs leading-relaxed"
                disabled={editingSaving}
              />
            </NovelDialogSection>

            <NovelDialogSurface className="text-[11px] leading-relaxed text-book-text-muted">
              提示：保存后会更新后端主题配置；如果该配置是当前模式已激活主题，WebUI 会立即重新计算并应用 CSS 变量。
            </NovelDialogSurface>
          </NovelDialogStack>
        ) : (
          <NovelDialogSurface className="text-sm text-book-text-muted">无法加载该配置</NovelDialogSurface>
        )}
      </Modal>
    </SettingsTabPanel>
  );
};
