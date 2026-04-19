import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Copy, Download, Edit3, RotateCcw, Trash2 } from 'lucide-react';
import { BookButton } from '../../ui/BookButton';
import { useToast } from '../../feedback/Toast';
import { confirmDialog } from '../../feedback/ConfirmDialog';
import {
  themeConfigsApi,
  type ThemeConfigListItem,
  type ThemeConfigUnifiedRead,
  type ThemeMode,
} from '../../../api/themeConfigs';
import {
  applyThemeFromUnifiedConfig,
  buildCssVarsFromUnifiedConfig,
} from '../../../theme/applyTheme';
import {
  defaultWebAppearanceConfig,
  notifyWebAppearanceChanged,
  readWebAppearanceConfig,
  writeWebAppearanceConfig,
  type WebAppearanceConfig,
} from '../../../theme/webAppearance';
import { downloadJson } from '../../../utils/downloadFile';
import { SettingsTabPanel } from './components/SettingsTabPanel';
import { useSettingsModalFooter } from './components/SettingsModalFooterContext';
import { ThemeTabDetailPanel } from './theme-tab/ThemeTabDetailPanel';
import { ThemeTabEditorModal } from './theme-tab/ThemeTabEditorModal';
import { ThemeTabSidebar } from './theme-tab/ThemeTabSidebar';
import {
  buildEditPayloadText,
  sanitizeFilename,
  type ThemeActionMenuItem,
} from './theme-tab/shared';

export const ThemeTab: React.FC = () => {
  const { addToast } = useToast();
  const { setFooter } = useSettingsModalFooter();

  const [items, setItems] = useState<ThemeConfigListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [activatingId, setActivatingId] = useState<number | null>(null);
  const [appearance, setAppearance] = useState<WebAppearanceConfig>(() =>
    readWebAppearanceConfig(),
  );
  const [appearanceBaseline, setAppearanceBaseline] =
    useState<WebAppearanceConfig>(() => readWebAppearanceConfig());
  const appearanceRef = useRef(appearance);
  appearanceRef.current = appearance;
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedUnified, setSelectedUnified] =
    useState<ThemeConfigUnifiedRead | null>(null);
  const [selectedLoading, setSelectedLoading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingConfig, setEditingConfig] =
    useState<ThemeConfigUnifiedRead | null>(null);
  const [editingLoading, setEditingLoading] = useState(false);
  const [editingSaving, setEditingSaving] = useState(false);
  const [editingName, setEditingName] = useState('');
  const [editingJson, setEditingJson] = useState('');
  const [editingError, setEditingError] = useState<string | null>(null);

  const currentMode: ThemeMode = document.documentElement.classList.contains(
    'dark',
  )
    ? 'dark'
    : 'light';
  const [modeView, setModeView] = useState<ThemeMode>(currentMode);

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const data = await themeConfigsApi.list();
      setItems(data);
    } catch (error) {
      console.error(error);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchList();
  }, [fetchList]);

  const byMode = useMemo(() => {
    const light = items.filter((item) => item.parent_mode === 'light');
    const dark = items.filter((item) => item.parent_mode === 'dark');
    return { light, dark };
  }, [items]);

  const namesByMode = useMemo(() => {
    const map: Record<ThemeMode, Set<string>> = {
      light: new Set(),
      dark: new Set(),
    };
    for (const item of items) {
      const name = String(item.config_name || '').trim();
      if (!name) {
        continue;
      }
      if (item.parent_mode === 'light' || item.parent_mode === 'dark') {
        map[item.parent_mode].add(name);
      }
    }
    return map;
  }, [items]);

  const modeList = modeView === 'light' ? byMode.light : byMode.dark;

  const filteredList = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return modeList;
    }
    return modeList.filter((item) =>
      String(item.config_name || '')
        .toLowerCase()
        .includes(normalizedQuery),
    );
  }, [modeList, query]);

  const selectedItem = useMemo(() => {
    if (!selectedId) {
      return null;
    }
    return items.find((item) => item.id === selectedId) ?? null;
  }, [items, selectedId]);

  useEffect(() => {
    if (modeList.length === 0) {
      setSelectedId(null);
      return;
    }
    if (selectedId && modeList.some((item) => item.id === selectedId)) {
      return;
    }
    const active = modeList.find((item) => item.is_active);
    setSelectedId(active?.id ?? modeList[0].id);
  }, [modeList, selectedId]);

  const refreshSelectedUnified = useCallback(
    async (id?: number | null) => {
      const targetId = Number(id ?? selectedId ?? 0);
      if (!targetId) {
        return;
      }
      setSelectedLoading(true);
      try {
        const config = await themeConfigsApi.getUnified(targetId);
        setSelectedUnified(config);
      } catch (error) {
        console.error(error);
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
      .then((config) => {
        if (cancelled) {
          return;
        }
        setSelectedUnified(config);
      })
      .catch((error) => {
        console.error(error);
        if (cancelled) {
          return;
        }
        setSelectedUnified(null);
      })
      .finally(() => {
        if (cancelled) {
          return;
        }
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
    if (!selectedUnified) {
      return undefined;
    }
    const vars = buildCssVarsFromUnifiedConfig(selectedUnified);
    const style: React.CSSProperties = {};
    Object.entries(vars).forEach(([key, value]) => {
      (style as Record<string, string>)[key] = value;
    });
    return style;
  }, [selectedUnified]);

  const openEditor = useCallback(
    async (id: number) => {
      setEditingError(null);
      setEditingId(id);
      setEditingConfig(null);
      setEditingName('');
      setEditingJson('');
      setEditingLoading(true);
      try {
        const config = await themeConfigsApi.getUnified(id);
        setEditingConfig(config);
        setEditingName(config.config_name || '');
        setEditingJson(buildEditPayloadText(config));
      } catch (error) {
        console.error(error);
        addToast('加载主题配置失败', 'error');
        setEditingId(null);
      } finally {
        setEditingLoading(false);
      }
    },
    [addToast],
  );

  const closeEditor = useCallback(() => {
    if (editingSaving) {
      return;
    }
    setEditingId(null);
    setEditingConfig(null);
    setEditingError(null);
  }, [editingSaving]);

  const saveEditor = useCallback(async () => {
    if (!editingId || !editingConfig) {
      return;
    }

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
      const version = Number(editingConfig.config_version || 1);
      if (version === 2) {
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

      if (editingConfig.is_active && editingConfig.parent_mode === currentMode) {
        const active = await themeConfigsApi.getActive(currentMode);
        if (active) {
          applyThemeFromUnifiedConfig(active);
        }
      }

      await fetchList();
      if (editingId === selectedId) {
        await refreshSelectedUnified(editingId);
      }
      closeEditor();
    } catch (error) {
      console.error(error);
      addToast('保存失败（请查看后端日志/接口返回）', 'error');
    } finally {
      setEditingSaving(false);
    }
  }, [
    addToast,
    closeEditor,
    currentMode,
    editingConfig,
    editingId,
    editingJson,
    editingName,
    fetchList,
    refreshSelectedUnified,
    selectedId,
  ]);

  const handleExportAll = useCallback(async () => {
    setExporting(true);
    try {
      const data = await themeConfigsApi.exportAll();
      const date = new Date().toISOString().slice(0, 10);
      downloadJson(data, `afn-theme-configs-${date}.json`);
      addToast('已导出主题配置', 'success');
    } catch (error) {
      console.error(error);
      addToast('导出失败', 'error');
    } finally {
      setExporting(false);
    }
  }, [addToast]);

  const handleExportOne = useCallback(
    async (config: ThemeConfigListItem) => {
      setBusyId(config.id);
      try {
        const data = await themeConfigsApi.exportOne(config.id);
        const date = new Date().toISOString().slice(0, 10);
        downloadJson(
          data,
          `afn-theme-${sanitizeFilename(config.config_name)}-${config.parent_mode}-${date}.json`,
        );
        addToast('已导出主题配置', 'success');
      } catch (error) {
        console.error(error);
        addToast('导出失败', 'error');
      } finally {
        setBusyId(null);
      }
    },
    [addToast],
  );

  const handleImportClick = useCallback(() => {
    if (importing) {
      return;
    }
    fileInputRef.current?.click();
  }, [importing]);

  const handleImportFile = useCallback(
    async (file: File) => {
      setImporting(true);
      try {
        const text = await file.text();
        const parsed = JSON.parse(text);
        if (
          !parsed ||
          typeof parsed !== 'object' ||
          Array.isArray(parsed) ||
          !Array.isArray(parsed.configs)
        ) {
          addToast('导入失败：文件结构不符合 theme-configs export 格式', 'error');
          return;
        }

        const result = await themeConfigsApi.importAll(parsed);
        if (result.success) {
          addToast(
            `导入完成：成功 ${result.imported_count}，跳过 ${result.skipped_count}，失败 ${result.failed_count}`,
            'success',
          );
        } else {
          addToast(result.message || '导入失败', 'error');
        }
        await fetchList();
      } catch (error) {
        console.error(error);
        addToast('导入失败：无法解析文件或接口调用失败', 'error');
      } finally {
        setImporting(false);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }
    },
    [addToast, fetchList],
  );

  const handleDuplicate = useCallback(
    async (config: ThemeConfigListItem) => {
      setBusyId(config.id);
      try {
        const unified = await themeConfigsApi.getUnified(config.id);
        const base =
          String(unified.config_name || config.config_name || '主题').trim() ||
          '主题';
        const mode = unified.parent_mode;
        const existing = namesByMode[mode] || new Set<string>();
        let name = `${base} (副本)`;
        let index = 2;
        while (existing.has(name) && index < 50) {
          name = `${base} (副本 ${index})`;
          index += 1;
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
      } catch (error) {
        console.error(error);
        addToast('复制失败', 'error');
      } finally {
        setBusyId(null);
      }
    },
    [addToast, fetchList, namesByMode],
  );

  const handleReset = useCallback(
    async (config: ThemeConfigListItem) => {
      const ok = await confirmDialog({
        title: '重置主题配置',
        message: `将重置主题配置“${config.config_name}”为默认值。\n是否继续？`,
        confirmText: '重置',
        dialogType: 'warning',
      });
      if (!ok) {
        return;
      }

      setBusyId(config.id);
      try {
        const unified = await themeConfigsApi.getUnified(config.id);
        if (Number(unified.config_version || 1) === 2) {
          await themeConfigsApi.resetV2(config.id);
        } else {
          await themeConfigsApi.resetV1(config.id);
        }
        addToast('已重置主题配置', 'success');
        await fetchList();
        if (config.id === selectedId) {
          await refreshSelectedUnified(config.id);
        }

        if (config.is_active && config.parent_mode === currentMode) {
          const active = await themeConfigsApi.getActive(currentMode);
          if (active) {
            applyThemeFromUnifiedConfig(active);
          }
        }
      } catch (error) {
        console.error(error);
        addToast('重置失败', 'error');
      } finally {
        setBusyId(null);
      }
    },
    [addToast, currentMode, fetchList, refreshSelectedUnified, selectedId],
  );

  const handleDelete = useCallback(
    async (config: ThemeConfigListItem) => {
      const ok = await confirmDialog({
        title: '删除主题配置',
        message: `将删除主题配置“${config.config_name}”。\n注意：激活中的配置可能无法删除（需先激活其他配置）。\n是否继续？`,
        confirmText: '删除',
        dialogType: 'danger',
      });
      if (!ok) {
        return;
      }

      setBusyId(config.id);
      try {
        await themeConfigsApi.delete(config.id);
        addToast('已删除主题配置', 'success');
        await fetchList();
      } catch (error) {
        console.error(error);
        addToast('删除失败', 'error');
      } finally {
        setBusyId(null);
      }
    },
    [addToast, fetchList],
  );

  const handleActivate = useCallback(
    async (id: number) => {
      setActivatingId(id);
      try {
        const config = await themeConfigsApi.activate(id);
        const modeLabel = config.parent_mode === 'dark' ? '深色' : '亮色';
        const isCurrentMode = config.parent_mode === currentMode;
        addToast(
          isCurrentMode
            ? `已激活并应用${modeLabel}主题：${config.config_name}`
            : `已激活${modeLabel}主题：${config.config_name}（切换到${modeLabel}模式后生效）`,
          'success',
        );

        if (config.parent_mode === currentMode) {
          applyThemeFromUnifiedConfig(config);
        }

        await fetchList();
        if (id === selectedId) {
          setSelectedUnified(config);
        }
      } catch (error) {
        console.error(error);
      } finally {
        setActivatingId(null);
      }
    },
    [addToast, currentMode, fetchList, selectedId],
  );

  const handleSyncCurrent = useCallback(async () => {
    try {
      const config = await themeConfigsApi.getActive(currentMode);
      if (config) {
        applyThemeFromUnifiedConfig(config);
        addToast('已同步当前主题到界面', 'success');
      } else {
        addToast('当前模式没有激活主题配置', 'error');
      }
    } catch (error) {
      console.error(error);
    }
  }, [addToast, currentMode]);

  const getThemeMenuItems = useCallback(
    (config: ThemeConfigListItem): ThemeActionMenuItem[] => [
      {
        label: '编辑',
        icon: <Edit3 size={14} />,
        onClick: () => openEditor(config.id),
      },
      {
        label: '复制',
        icon: <Copy size={14} />,
        onClick: () => handleDuplicate(config),
      },
      {
        label: '导出',
        icon: <Download size={14} />,
        onClick: () => handleExportOne(config),
      },
      { type: 'divider' },
      {
        label: '重置',
        icon: <RotateCcw size={14} />,
        onClick: () => handleReset(config),
        danger: true,
      },
      {
        label: '删除',
        icon: <Trash2 size={14} />,
        onClick: () => handleDelete(config),
        danger: true,
      },
    ],
    [handleDelete, handleDuplicate, handleExportOne, handleReset, openEditor],
  );

  const applyAppearance = useCallback(() => {
    writeWebAppearanceConfig(appearanceRef.current);
    notifyWebAppearanceChanged();
    setAppearanceBaseline(appearanceRef.current);
    addToast('已应用界面外观（本机生效）', 'success');
  }, [addToast]);

  const resetAppearance = useCallback(() => {
    const config = defaultWebAppearanceConfig();
    setAppearance(config);
    writeWebAppearanceConfig(config);
    notifyWebAppearanceChanged();
    setAppearanceBaseline(config);
    addToast('已恢复默认外观', 'success');
  }, [addToast]);

  const handleAppearanceEnabledChange = useCallback((enabled: boolean) => {
    setAppearance((prev) => ({ ...prev, enabled }));
  }, []);

  const handleAppearanceBackgroundImageUrlChange = useCallback(
    (backgroundImageUrl: string) => {
      setAppearance((prev) => ({ ...prev, backgroundImageUrl }));
    },
    [],
  );

  const handleAppearanceBlurChange = useCallback((blurPx: number) => {
    setAppearance((prev) => ({ ...prev, blurPx }));
  }, []);

  const handleAppearanceOverlayChange = useCallback((overlayOpacity: number) => {
    setAppearance((prev) => ({ ...prev, overlayOpacity }));
  }, []);

  const reloadEditingConfig = useCallback(async () => {
    if (!editingId) {
      return;
    }
    setEditingLoading(true);
    try {
      const config = await themeConfigsApi.getUnified(editingId);
      setEditingConfig(config);
      setEditingName(config.config_name || '');
      setEditingJson(buildEditPayloadText(config));
      addToast('已重新加载', 'success');
    } catch (error) {
      console.error(error);
      addToast('重新加载失败', 'error');
    } finally {
      setEditingLoading(false);
    }
  }, [addToast, editingId]);

  const migrateEditingConfigToV2 = useCallback(async () => {
    if (!editingId) {
      return;
    }

    const ok = await confirmDialog({
      title: '迁移到 V2',
      message: '将迁移到 V2（组件模式）并填充默认 V2 字段。\n是否继续？',
      confirmText: '迁移',
      dialogType: 'warning',
    });
    if (!ok) {
      return;
    }

    setEditingLoading(true);
    try {
      await themeConfigsApi.migrateToV2(editingId);
      const config = await themeConfigsApi.getUnified(editingId);
      setEditingConfig(config);
      setEditingName(config.config_name || '');
      setEditingJson(buildEditPayloadText(config));
      addToast('已迁移到 V2（组件模式）', 'success');
      await fetchList();
    } catch (error) {
      console.error(error);
      addToast('迁移失败', 'error');
    } finally {
      setEditingLoading(false);
    }
  }, [addToast, editingId, fetchList]);

  const footer = useMemo(
    () => (
      <>
        <BookButton variant="ghost" size="sm" onClick={resetAppearance}>
          恢复默认
        </BookButton>
        <BookButton
          variant="primary"
          size="sm"
          onClick={applyAppearance}
          disabled={!appearanceDirty}
        >
          {appearanceDirty ? '应用外观' : '已应用'}
        </BookButton>
      </>
    ),
    [appearanceDirty, applyAppearance, resetAppearance],
  );

  useEffect(() => {
    setFooter(footer);
    return () => setFooter(null);
  }, [footer, setFooter]);

  return (
    <SettingsTabPanel className="h-full min-h-0" bodyClassName="h-full min-h-0">
      <div className="h-full min-h-0 overflow-hidden">
        <div className="grid h-full min-h-0 lg:grid-cols-[minmax(280px,340px)_minmax(0,1fr)]">
          <ThemeTabSidebar
            loading={loading}
            exporting={exporting}
            importing={importing}
            query={query}
            currentMode={currentMode}
            modeView={modeView}
            modeListCount={modeList.length}
            filteredList={filteredList}
            selectedId={selectedId}
            activatingId={activatingId}
            busyId={busyId}
            fileInputRef={fileInputRef}
            onRefresh={fetchList}
            onSyncCurrent={handleSyncCurrent}
            onExportAll={handleExportAll}
            onImportClick={handleImportClick}
            onImportFile={handleImportFile}
            onModeViewChange={setModeView}
            onQueryChange={setQuery}
            onSelectTheme={setSelectedId}
            getThemeMenuItems={getThemeMenuItems}
          />

          <ThemeTabDetailPanel
            selectedItem={selectedItem}
            selectedUnified={selectedUnified}
            selectedLoading={selectedLoading}
            previewStyle={previewStyle}
            appearance={appearance}
            appearanceDirty={appearanceDirty}
            activatingId={activatingId}
            busyId={busyId}
            onActivate={handleActivate}
            onOpenEditor={openEditor}
            onAppearanceEnabledChange={handleAppearanceEnabledChange}
            onAppearanceBackgroundImageUrlChange={
              handleAppearanceBackgroundImageUrlChange
            }
            onAppearanceBlurChange={handleAppearanceBlurChange}
            onAppearanceOverlayChange={handleAppearanceOverlayChange}
            getThemeMenuItems={getThemeMenuItems}
          />
        </div>
      </div>

      <ThemeTabEditorModal
        isOpen={Boolean(editingId)}
        editingConfig={editingConfig}
        editingLoading={editingLoading}
        editingSaving={editingSaving}
        editingName={editingName}
        editingJson={editingJson}
        editingError={editingError}
        onClose={closeEditor}
        onSave={saveEditor}
        onNameChange={setEditingName}
        onJsonChange={setEditingJson}
        onReload={reloadEditingConfig}
        onMigrateToV2={migrateEditingConfigToV2}
      />
    </SettingsTabPanel>
  );
};
