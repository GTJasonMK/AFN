import React, { useEffect, useMemo, useRef, useState } from 'react';
import { BookCard } from '../../ui/BookCard';
import { BookButton } from '../../ui/BookButton';
import { BookInput, BookTextarea } from '../../ui/BookInput';
import { useToast } from '../../feedback/Toast';
import { confirmDialog } from '../../feedback/ConfirmDialog';
import { themeConfigsApi, ThemeConfigListItem, ThemeConfigUnifiedRead, ThemeMode } from '../../../api/themeConfigs';
import { applyThemeFromUnifiedConfig } from '../../../theme/applyTheme';
import { CheckCircle2, Circle, Copy, Download, Edit3, Palette, RotateCcw, Trash2, Upload } from 'lucide-react';
import { SettingsInfoBox } from './components/SettingsInfoBox';
import { SettingsTabHeader } from './components/SettingsTabHeader';
import { defaultWebAppearanceConfig, notifyWebAppearanceChanged, readWebAppearanceConfig, writeWebAppearanceConfig, type WebAppearanceConfig } from '../../../theme/webAppearance';
import { Dropdown } from '../../ui/Dropdown';
import { Modal } from '../../ui/Modal';
import { downloadJson } from '../../../utils/downloadFile';

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
  const [appearance, setAppearance] = useState<WebAppearanceConfig>(() => readWebAppearanceConfig());
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

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

                  <div className="shrink-0 flex items-start gap-2">
                    {!cfg.is_active && (
                      <BookButton
                        variant="primary"
                        size="sm"
                        onClick={() => handleActivate(cfg.id)}
                        disabled={activatingId === cfg.id || busyId === cfg.id}
                      >
                        {activatingId === cfg.id ? '切换中…' : '激活'}
                      </BookButton>
                    )}
                    <Dropdown
                      items={[
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
                      ]}
                    />
                  </div>
                </div>
              </BookCard>
            ))}
          </div>
        )}
      </BookCard>
    );
  };

  const applyAppearance = () => {
    writeWebAppearanceConfig(appearance);
    notifyWebAppearanceChanged();
    addToast('已应用 Web 外观设置（仅本地浏览器生效）', 'success');
  };

  const resetAppearance = () => {
    const cfg = defaultWebAppearanceConfig();
    setAppearance(cfg);
    writeWebAppearanceConfig(cfg);
    notifyWebAppearanceChanged();
    addToast('已重置 Web 外观设置', 'success');
  };

  return (
    <div className="space-y-4">
      <SettingsTabHeader
        title="主题"
        loading={loading}
        onRefresh={fetchList}
        showRefreshIcon
        extraActions={
          <div className="flex items-center gap-2">
            <BookButton variant="ghost" size="sm" onClick={handleSyncCurrent}>
              同步当前主题
            </BookButton>
            <BookButton variant="ghost" size="sm" onClick={handleExportAll} disabled={exporting}>
              <Download size={14} className="mr-1" />
              {exporting ? '导出中…' : '导出'}
            </BookButton>
            <BookButton variant="ghost" size="sm" onClick={handleImportClick} disabled={importing}>
              <Upload size={14} className="mr-1" />
              {importing ? '导入中…' : '导入'}
            </BookButton>
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
        }
      />

      <SettingsInfoBox>
        说明：主题配置来自后端主题系统。激活后会立即应用到当前 WebUI（仅对对应模式生效）。
      </SettingsInfoBox>

      <BookCard className="p-4">
        <div className="text-xs font-bold text-book-text-muted flex items-center gap-2">
          <Palette size={14} className="text-book-accent" />
          Web 外观（本地）
        </div>
        <div className="mt-1 text-[11px] text-book-text-muted leading-relaxed">
          仅写入浏览器 localStorage，不影响后端/桌面端。可用于模拟桌面端“背景图/透明/玻璃态”等效果（浏览器只能做 CSS 级近似）。
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <label className="text-xs font-bold text-book-text-sub flex items-center gap-2">
            <input
              type="checkbox"
              checked={Boolean(appearance.enabled)}
              onChange={(e) => setAppearance((prev) => ({ ...prev, enabled: e.target.checked }))}
            />
            启用背景图
          </label>

          <label className="text-xs font-bold text-book-text-sub">
            背景图 URL
            <input
              type="text"
              value={appearance.backgroundImageUrl || ''}
              onChange={(e) => setAppearance((prev) => ({ ...prev, backgroundImageUrl: e.target.value }))}
              placeholder="https://..."
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main outline-none focus:border-book-primary/50"
            />
          </label>

          <label className="text-xs font-bold text-book-text-sub">
            模糊（px）
            <input
              type="number"
              min={0}
              max={48}
              value={Number(appearance.blurPx) || 0}
              onChange={(e) => setAppearance((prev) => ({ ...prev, blurPx: Math.max(0, Math.min(48, Number(e.target.value) || 0)) }))}
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main outline-none focus:border-book-primary/50"
            />
          </label>

          <label className="text-xs font-bold text-book-text-sub">
            遮罩不透明度（0~1）
            <input
              type="number"
              step={0.05}
              min={0}
              max={1}
              value={Number(appearance.overlayOpacity) || 0}
              onChange={(e) => setAppearance((prev) => ({ ...prev, overlayOpacity: Math.max(0, Math.min(1, Number(e.target.value) || 0)) }))}
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main outline-none focus:border-book-primary/50"
            />
          </label>
        </div>

        {appearance.enabled && (appearance.backgroundImageUrl || '').trim() ? (
          <div className="mt-4">
            <div className="text-[11px] text-book-text-muted mb-1">预览</div>
            <div className="h-28 rounded-lg overflow-hidden border border-book-border/40 bg-book-bg relative">
              <div
                className="absolute inset-0 bg-center bg-cover"
                style={{
                  backgroundImage: `url(${String(appearance.backgroundImageUrl || '').trim()})`,
                  filter: (Number(appearance.blurPx) || 0) > 0 ? `blur(${Math.max(0, Math.min(48, Number(appearance.blurPx) || 0))}px)` : undefined,
                  transform: (Number(appearance.blurPx) || 0) > 0 ? 'scale(1.05)' : undefined,
                }}
              />
              <div className="absolute inset-0 bg-book-bg" style={{ opacity: Math.max(0, Math.min(1, Number(appearance.overlayOpacity) || 0)) }} />
            </div>
          </div>
        ) : null}

        <div className="mt-4 flex justify-end gap-2">
          <BookButton variant="ghost" size="sm" onClick={resetAppearance}>
            重置
          </BookButton>
          <BookButton variant="primary" size="sm" onClick={applyAppearance}>
            应用
          </BookButton>
        </div>
      </BookCard>

      <div className="grid grid-cols-2 gap-4">
        {renderSection('light', byMode.light)}
        {renderSection('dark', byMode.dark)}
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
          <div className="text-sm text-book-text-muted">加载中…</div>
        ) : editingConfig ? (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <BookInput
                label="配置名称"
                value={editingName}
                onChange={(e) => setEditingName(e.target.value)}
                disabled={editingSaving}
              />
              <div className="text-xs text-book-text-muted flex items-end">
                <div className="pb-1">
                  模式：<span className="font-bold text-book-text-main">{editingConfig.parent_mode === 'dark' ? '深色' : '亮色'}</span>
                  <span className="mx-2 opacity-40">|</span>
                  版本：<span className="font-bold text-book-text-main">V{editingConfig.config_version || 1}</span>
                  {editingConfig.is_active ? (
                    <span className="ml-2 text-[10px] px-2 py-0.5 rounded bg-book-primary/10 text-book-primary font-bold">已激活</span>
                  ) : null}
                </div>
              </div>
              <div className="flex items-end justify-end gap-2">
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
              </div>
            </div>

            {editingError ? (
              <div className="text-xs text-red-600 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/30 p-2 rounded">
                {editingError}
              </div>
            ) : null}

            <BookTextarea
              label="配置 JSON（按后端 Schema 字段填写）"
              value={editingJson}
              onChange={(e) => setEditingJson(e.target.value)}
              rows={18}
              className="font-mono text-xs leading-relaxed"
              disabled={editingSaving}
            />

            <div className="text-[11px] text-book-text-muted leading-relaxed">
              提示：保存后会更新后端主题配置；如果该配置为当前模式已激活主题，会立即应用到 WebUI（CSS 变量）。
            </div>
          </div>
        ) : (
          <div className="text-sm text-book-text-muted">无法加载该配置</div>
        )}
      </Modal>
    </div>
  );
};
