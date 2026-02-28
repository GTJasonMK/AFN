import React, { useMemo, useRef, useState } from 'react';
import { BookCard } from '../../ui/BookCard';
import { BookButton } from '../../ui/BookButton';
import { useToast } from '../../feedback/Toast';
import { confirmDialog } from '../../feedback/ConfirmDialog';
import { settingsApi, type AllConfigExportData, type ConfigImportResult } from '../../../api/settings';
import { downloadJson } from '../../../utils/downloadFile';
import { Download, Upload, FileJson, RefreshCw, AlertTriangle } from 'lucide-react';

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

  const [exporting, setExporting] = useState(false);
  const [lastExport, setLastExport] = useState<AllConfigExportData | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ConfigImportResult | null>(null);

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

  const handleExportAll = async () => {
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
  };

  const handlePickFile = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange: React.ChangeEventHandler<HTMLInputElement> = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    try {
      const text = await f.text();
      const parsed = JSON.parse(text);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        addToast('配置文件格式不正确（应为 JSON 对象）', 'error');
        setImportPreview(null);
        return;
      }
      setImportPreview({ fileName: f.name, data: parsed as Record<string, any> });
      setImportResult(null);
      addToast('已读取配置文件（尚未导入）', 'success');
    } catch (err) {
      console.error(err);
      addToast('读取/解析配置文件失败', 'error');
      setImportPreview(null);
    } finally {
      // 允许重复选择同一个文件
      e.target.value = '';
    }
  };

  const clearImport = () => {
    setImportPreview(null);
    setImportResult(null);
  };

  const handleImportAll = async () => {
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
  };

  return (
    <div className="space-y-6">
      <BookCard className="p-4 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="font-bold text-book-text-main flex items-center gap-2">
            <Download size={16} className="text-book-primary" />
            导出配置
          </div>
          <BookButton variant="primary" size="sm" onClick={handleExportAll} disabled={exporting}>
            <FileJson size={14} className="mr-1" />
            {exporting ? '导出中…' : '导出全部配置'}
          </BookButton>
        </div>
        <div className="text-xs text-book-text-muted leading-relaxed">
          将 LLM/嵌入/图片/提示词/主题/高级参数等配置导出为 JSON 文件，便于迁移与备份。
        </div>
        {lastExport?.export_time && (
          <div className="text-[11px] text-book-text-muted">
            最近导出时间：<span className="font-mono">{lastExport.export_time}</span>
          </div>
        )}
      </BookCard>

      <BookCard className="p-4 space-y-4">
        <div className="flex items-center justify-between gap-2">
          <div className="font-bold text-book-text-main flex items-center gap-2">
            <Upload size={16} className="text-book-primary" />
            导入配置
          </div>
          <div className="flex items-center gap-2">
            <BookButton variant="ghost" size="sm" onClick={handlePickFile} disabled={importing}>
              选择文件
            </BookButton>
            <BookButton variant="primary" size="sm" onClick={handleImportAll} disabled={importing || !importPreview}>
              <RefreshCw size={14} className={`mr-1 ${importing ? 'animate-spin' : ''}`} />
              {importing ? '导入中…' : '开始导入'}
            </BookButton>
          </div>
        </div>

        <input
          ref={fileInputRef}
          className="hidden"
          type="file"
          accept=".json,application/json"
          onChange={handleFileChange}
        />

        <div className="text-xs text-book-accent bg-book-bg p-3 rounded-lg border border-book-border/50 flex items-start gap-2 leading-relaxed">
          <AlertTriangle size={16} className="mt-0.5 flex-none" />
          <div>
            导入会覆盖当前配置（含提示词/主题）。建议先导出备份；导入后如发现 UI 缓存未刷新，请刷新页面。
          </div>
        </div>

        {importPreview ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs text-book-text-muted">
                已选择：<span className="font-mono">{importPreview.fileName}</span>
              </div>
              <BookButton variant="ghost" size="sm" onClick={clearImport} disabled={importing}>
                清空
              </BookButton>
            </div>

            {previewMeta && (
              <div className="grid grid-cols-2 gap-2 text-xs text-book-text-muted">
                <div>export_type：<span className="font-mono">{previewMeta.export_type || '—'}</span></div>
                <div>version：<span className="font-mono">{previewMeta.version || '—'}</span></div>
                <div className="col-span-2">
                  export_time：<span className="font-mono">{previewMeta.export_time || '—'}</span>
                </div>
                <div>LLM：{previewMeta.llmCount}</div>
                <div>嵌入：{previewMeta.embeddingCount}</div>
                <div>图片：{previewMeta.imageCount}</div>
                <div>提示词：{previewMeta.hasPrompts ? '有' : '无'}</div>
                <div>主题：{previewMeta.hasTheme ? '有' : '无'}</div>
                <div>高级：{previewMeta.hasAdvanced ? '有' : '无'}</div>
                <div>队列：{previewMeta.hasQueue ? '有' : '无'}</div>
                <div>MaxTokens：{previewMeta.hasMaxTokens ? '有' : '无'}</div>
                <div>Temperature：{previewMeta.hasTemperature ? '有' : '无'}</div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-xs text-book-text-muted">
            尚未选择文件。请选择由“导出全部配置”生成的 JSON 文件进行导入。
          </div>
        )}

        {importResult && (
          <div className="space-y-2">
            <div className={`text-sm font-bold ${importResult.success ? 'text-book-primary' : 'text-book-accent'}`}>
              {importResult.success ? '导入成功' : '导入失败'}：{importResult.message}
            </div>
            {Array.isArray(importResult.details) && importResult.details.length > 0 && (
              <ul className="list-disc list-inside text-xs text-book-text-main space-y-1">
                {importResult.details.map((d, idx) => (
                  <li key={`detail-${idx}`}>{d}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </BookCard>
    </div>
  );
};
