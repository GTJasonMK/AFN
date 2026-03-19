import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, Download, FileJson, FolderOpen, RefreshCw, Upload, XCircle } from 'lucide-react';
import { settingsApi, type AllConfigExportData, type ConfigImportResult } from '../../../api/settings';
import { downloadJson } from '../../../utils/downloadFile';
import { confirmDialog } from '../../feedback/ConfirmDialog';
import { useToast } from '../../feedback/Toast';
import { BookButton } from '../../ui/BookButton';
import { SettingsTabPanel } from './components/SettingsTabPanel';
import { useSettingsModalFooter } from './components/SettingsModalFooterContext';

type ImportPreview = {
  fileName: string;
  data: Record<string, any>;
};

const safeDateStringForFilename = (iso?: string) => {
  try {
    const dt = iso ? new Date(iso) : new Date();
    if (Number.isNaN(dt.getTime())) return new Date().toISOString().replace(/[:.]/g, '-');
    return dt.toISOString().replace(/[:.]/g, '-');
  } catch {
    return new Date().toISOString().replace(/[:.]/g, '-');
  }
};

const sanitizeFilename = (name: string) => name.replace(/[\\/:*?"<>|]/g, '-');

export const ImportExportTab: React.FC = () => {
  const { addToast } = useToast();
  const { setFooter } = useSettingsModalFooter();

  const [mode, setMode] = useState<'backup' | 'restore'>('backup');
  const [exporting, setExporting] = useState(false);
  const [lastExport, setLastExport] = useState<AllConfigExportData | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ConfigImportResult | null>(null);
  const [dropActive, setDropActive] = useState(false);

  const previewMeta = useMemo(() => {
    const d = importPreview?.data;
    if (!d) return null;
    return {
      version: typeof d.version === 'string' ? d.version : '',
      export_time: typeof d.export_time === 'string' ? d.export_time : '',
      export_type: typeof d.export_type === 'string' ? d.export_type : '',
      llmCount: Array.isArray(d.llm_configs) ? d.llm_configs.length : 0,
      embeddingCount: Array.isArray(d.embedding_configs) ? d.embedding_configs.length : 0,
      imageCount: Array.isArray(d.image_configs) ? d.image_configs.length : 0,
      hasAdvanced: Boolean(d.advanced_config),
      hasQueue: Boolean(d.queue_config),
      hasMaxTokens: Boolean(d.max_tokens_config),
      hasTemperature: Boolean(d.temperature_config),
      hasPrompts: Boolean(d.prompt_configs),
      hasTheme: Boolean(d.theme_configs),
    };
  }, [importPreview]);

  const handleExportAll = useCallback(async () => {
    setExporting(true);
    try {
      const data = await settingsApi.exportAllConfigs();
      setLastExport(data);
      const stamp = safeDateStringForFilename(data.export_time);
      downloadJson(data, sanitizeFilename(`afn-settings-all-${stamp}.json`));
      addToast('已导出配置文件', 'success');
    } catch (e) {
      console.error(e);
      addToast('导出失败', 'error');
    } finally {
      setExporting(false);
    }
  }, [addToast]);

  const handlePickFile = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const clearImport = useCallback(() => {
    setImportPreview(null);
    setImportResult(null);
  }, []);

  const readImportFile = useCallback(async (file: File) => {
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        addToast('配置文件格式不正确（应为 JSON 对象）', 'error');
        setImportPreview(null);
        return;
      }
      setImportPreview({ fileName: file.name, data: parsed as Record<string, any> });
      setImportResult(null);
      addToast('已读取配置文件（尚未导入）', 'success');
      setMode('restore');
    } catch (err) {
      console.error(err);
      addToast('读取/解析配置文件失败', 'error');
      setImportPreview(null);
    } finally {
      setDropActive(false);
    }
  }, [addToast]);

  const handleFileChange = useCallback<React.ChangeEventHandler<HTMLInputElement>>(
    async (e) => {
      const f = e.target.files?.[0];
      if (!f) return;
      await readImportFile(f);
      // 允许重复选择同一个文件
      e.target.value = '';
    },
    [readImportFile],
  );

  const canImport = useMemo(() => {
    const type = String(importPreview?.data?.export_type || '');
    return Boolean(importPreview) && type === 'all';
  }, [importPreview]);

  const handleImportAll = useCallback(async () => {
    if (!importPreview) return;
    const type = String(importPreview.data?.export_type || '');
    if (type !== 'all') {
      addToast(`导入数据类型不匹配（export_type=${type || 'unknown'}），请使用“导出全部配置”生成的文件`, 'error');
      return;
    }
    const ok = await confirmDialog({
      title: '导入确认',
      message: '导入会覆盖当前配置（LLM/嵌入/图片/提示词/主题等）。\n建议先导出备份。\n\n确定继续导入？',
      confirmText: '继续导入',
      dialogType: 'danger',
    });
    if (!ok) return;

    setImporting(true);
    try {
      const res = await settingsApi.importAllConfigs(importPreview.data);
      setImportResult(res);
      addToast(res.success ? '导入完成' : '导入失败', res.success ? 'success' : 'error');
    } catch (e) {
      console.error(e);
      addToast('导入失败', 'error');
      setImportResult(null);
    } finally {
      setImporting(false);
    }
  }, [addToast, importPreview]);

  const footer = useMemo(() => {
    if (mode === 'backup') {
      return (
        <BookButton variant="primary" size="sm" onClick={handleExportAll} disabled={exporting}>
          <FileJson size={14} className="mr-1" />
          {exporting ? '导出中…' : '导出全部配置'}
        </BookButton>
      );
    }

    return (
      <>
        <BookButton variant="ghost" size="sm" onClick={handlePickFile} disabled={importing}>
          <FolderOpen size={14} className="mr-1" />
          选择文件
        </BookButton>
        {importPreview ? (
          <BookButton variant="ghost" size="sm" onClick={clearImport} disabled={importing}>
            <XCircle size={14} className="mr-1" />
            清空
          </BookButton>
        ) : null}
        <BookButton variant="primary" size="sm" onClick={handleImportAll} disabled={importing || !canImport}>
          <RefreshCw size={14} className={`mr-1 ${importing ? 'animate-spin' : ''}`} />
          {importing ? '导入中…' : '开始导入'}
        </BookButton>
      </>
    );
  }, [canImport, clearImport, exporting, handleExportAll, handleImportAll, handlePickFile, importPreview, importing, mode]);

  useEffect(() => {
    setFooter(footer);
    return () => setFooter(null);
  }, [footer, setFooter]);

  return (
    <SettingsTabPanel className="h-full min-h-0" bodyClassName="h-full min-h-0">
      <div className="flex min-h-0 flex-col gap-4">
        <input
          ref={fileInputRef}
          className="hidden"
          type="file"
          accept=".json,application/json"
          onChange={handleFileChange}
        />

        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-sm font-bold text-book-text-main">
              <Upload size={16} className="text-book-primary" />
              备份与恢复
            </div>
            <div className="mt-1 text-xs leading-relaxed text-book-text-sub">
              导出当前配置为 JSON 备份；或导入备份文件覆盖本机配置。按钮固定在右下角，避免页面跳动。
            </div>
          </div>

          <div className="inline-flex rounded-full border border-book-border/55 bg-book-bg-paper/70 p-1">
            <button
              type="button"
              aria-pressed={mode === 'backup'}
              onClick={() => setMode('backup')}
              className={`inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-bold transition-all ${
                mode === 'backup'
                  ? 'bg-book-primary text-white shadow'
                  : 'text-book-text-sub hover:text-book-text-main'
              }`}
            >
              <Download size={14} />
              备份
            </button>
            <button
              type="button"
              aria-pressed={mode === 'restore'}
              onClick={() => setMode('restore')}
              className={`inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-bold transition-all ${
                mode === 'restore'
                  ? 'bg-book-primary text-white shadow'
                  : 'text-book-text-sub hover:text-book-text-main'
              }`}
            >
              <Upload size={14} />
              恢复
            </button>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-[minmax(280px,340px)_minmax(0,1fr)]">
          <aside className="space-y-4">
            <div className="rounded-2xl border border-book-border/50 bg-book-bg-paper/60 p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="text-xs font-bold text-book-text-sub">当前状态</div>
                <div className="text-[11px] text-book-text-muted">
                  {mode === 'backup' ? '备份模式' : '恢复模式'}
                </div>
              </div>

              <div className="mt-3 grid gap-2 text-xs">
                <div className="rounded-xl border border-book-border/45 bg-book-bg-paper/70 px-3 py-2">
                  <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                    最近导出
                  </div>
                  <div className="mt-1 font-mono text-book-text-main">
                    {lastExport?.export_time ? lastExport.export_time : '—'}
                  </div>
                </div>
                <div className="rounded-xl border border-book-border/45 bg-book-bg-paper/70 px-3 py-2">
                  <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                    已选择文件
                  </div>
                  <div className="mt-1 font-mono text-book-text-main">
                    {importPreview?.fileName ? importPreview.fileName : '—'}
                  </div>
                  {importPreview?.fileName ? (
                    <div className="mt-1 text-[11px] text-book-text-muted leading-relaxed">
                      {canImport ? '文件类型匹配，可导入。' : 'export_type 不匹配：仅支持“导出全部配置”的文件。'}
                    </div>
                  ) : null}
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-book-border/50 bg-book-bg-paper/55 p-4 text-xs leading-relaxed text-book-text-sub">
              <div className="flex items-start gap-2">
                <AlertTriangle size={16} className="mt-0.5 flex-none text-book-accent" />
                <div>
                  <div className="font-semibold text-book-text-main">重要提示</div>
                  <div className="mt-1">
                    恢复会覆盖当前配置（含提示词/主题/模型列表等）。建议在恢复前先做一次备份。
                    如果 UI 未立即刷新，可关闭并重新打开设置弹窗。
                  </div>
                </div>
              </div>
            </div>
          </aside>

          <section className="space-y-4">
            {mode === 'backup' ? (
              <>
                <div className="rounded-2xl border border-book-border/50 bg-book-bg-paper/60 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-sm font-bold text-book-text-main">导出范围</div>
                      <div className="mt-1 text-xs leading-relaxed text-book-text-sub">
                        导出文件包含模型配置、提示词、主题、队列与高级策略等，适用于迁移/备份。
                      </div>
                    </div>
                    <div className="text-[11px] text-book-text-muted">操作按钮在右下角</div>
                  </div>

                  <div className="mt-4 grid gap-2 sm:grid-cols-2 text-xs text-book-text-sub">
                    {[
                      'LLM 模型配置',
                      '嵌入配置',
                      '图片模型配置',
                      '提示词库',
                      '主题系统',
                      '队列编排',
                      '高级策略',
                      'Max Tokens',
                      'Temperature',
                    ].map((label) => (
                      <div
                        key={label}
                        className="flex items-center gap-2 rounded-xl border border-book-border/45 bg-book-bg-paper/70 px-3 py-2"
                      >
                        <span className="inline-flex h-2 w-2 rounded-full bg-book-primary/80" />
                        <span className="font-semibold text-book-text-main">{label}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-2xl border border-book-border/50 bg-book-bg-paper/55 p-4 text-xs leading-relaxed text-book-text-muted">
                  导出后会自动下载文件；文件名包含时间戳，便于版本管理与回滚。
                </div>
              </>
            ) : (
              <>
                <div
                  role="button"
                  tabIndex={0}
                  onClick={handlePickFile}
                  onKeyDown={(e) => {
                    if (e.key !== 'Enter' && e.key !== ' ') return;
                    e.preventDefault();
                    handlePickFile();
                  }}
                  onDragEnter={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setDropActive(true);
                  }}
                  onDragOver={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setDropActive(true);
                  }}
                  onDragLeave={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setDropActive(false);
                  }}
                  onDrop={async (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const file = e.dataTransfer.files?.[0];
                    if (!file) return;
                    await readImportFile(file);
                  }}
                  className={`rounded-2xl border border-dashed p-5 transition-all outline-none focus-visible:ring-2 focus-visible:ring-book-primary/25 ${
                    dropActive
                      ? 'border-book-primary/60 bg-book-primary/5'
                      : 'border-book-border/55 bg-book-bg-paper/60 hover:border-book-primary/30'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-book-border/55 bg-book-bg-paper/80">
                      <FileJson size={18} className="text-book-primary" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-sm font-bold text-book-text-main">拖拽配置文件到这里</div>
                      <div className="mt-1 text-xs text-book-text-sub">
                        或点击选择由“导出全部配置”生成的 JSON 文件（.json）。
                      </div>
                    </div>
                  </div>

                  {importPreview ? (
                    <div className="mt-4 text-xs text-book-text-sub">
                      已选择：<span className="font-mono text-book-text-main">{importPreview.fileName}</span>
                      {canImport ? null : (
                        <span className="ml-2 font-semibold text-book-accent">（export_type 不匹配）</span>
                      )}
                    </div>
                  ) : null}
                </div>

                {importPreview ? (
                  <div className="rounded-2xl border border-book-border/50 bg-book-bg-paper/55 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm font-bold text-book-text-main">文件预览</div>
                      <div className="text-[11px] text-book-text-muted">
                        export_type：<span className="font-mono">{previewMeta?.export_type || '—'}</span>
                      </div>
                    </div>

                    {previewMeta ? (
                      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                        <div className="rounded-xl border border-book-border/45 bg-book-bg-paper/70 p-3">
                          <div className="text-[11px] text-book-text-muted">version</div>
                          <div className="mt-1 font-mono text-book-text-main">{previewMeta.version || '—'}</div>
                        </div>
                        <div className="rounded-xl border border-book-border/45 bg-book-bg-paper/70 p-3">
                          <div className="text-[11px] text-book-text-muted">export_time</div>
                          <div className="mt-1 font-mono text-book-text-main">{previewMeta.export_time || '—'}</div>
                        </div>

                        <div className="rounded-xl border border-book-border/45 bg-book-bg-paper/70 p-3">
                          <div className="text-[11px] text-book-text-muted">LLM / 嵌入</div>
                          <div className="mt-1 font-semibold text-book-text-main">
                            {previewMeta.llmCount} / {previewMeta.embeddingCount}
                          </div>
                        </div>
                        <div className="rounded-xl border border-book-border/45 bg-book-bg-paper/70 p-3">
                          <div className="text-[11px] text-book-text-muted">图片模型</div>
                          <div className="mt-1 font-semibold text-book-text-main">{previewMeta.imageCount}</div>
                        </div>

                        {[
                          { k: '提示词库', v: previewMeta.hasPrompts },
                          { k: '主题系统', v: previewMeta.hasTheme },
                          { k: '高级策略', v: previewMeta.hasAdvanced },
                          { k: '队列编排', v: previewMeta.hasQueue },
                          { k: 'Max Tokens', v: previewMeta.hasMaxTokens },
                          { k: 'Temperature', v: previewMeta.hasTemperature },
                        ].map((item) => (
                          <div
                            key={item.k}
                            className="rounded-xl border border-book-border/45 bg-book-bg-paper/70 p-3"
                          >
                            <div className="text-[11px] text-book-text-muted">{item.k}</div>
                            <div className={`mt-1 font-semibold ${item.v ? 'text-book-primary' : 'text-book-text-main'}`}>
                              {item.v ? '包含' : '无'}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <div className="rounded-2xl border border-book-border/50 bg-book-bg-paper/55 p-4 text-xs text-book-text-muted">
                    尚未选择文件。恢复模式下可拖拽/选择 JSON 文件进行预览与导入。
                  </div>
                )}

                {importResult ? (
                  <div className="rounded-2xl border border-book-border/50 bg-book-bg-paper/55 p-4">
                    <div className={`text-sm font-bold ${importResult.success ? 'text-book-primary' : 'text-book-accent'}`}>
                      {importResult.success ? '导入成功' : '导入失败'}：{importResult.message}
                    </div>
                    {Array.isArray(importResult.details) && importResult.details.length > 0 ? (
                      <ul className="mt-3 list-disc list-inside space-y-1 text-xs text-book-text-main">
                        {importResult.details.map((d, idx) => (
                          <li key={`detail-${idx}`}>{d}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ) : null}
              </>
            )}
          </section>
        </div>
      </div>
    </SettingsTabPanel>
  );
};
