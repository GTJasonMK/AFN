import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { BookButton } from '../../ui/BookButton';
import { BookSlider } from '../../ui/BookSlider';
import { settingsApi, TemperatureConfig } from '../../../api/settings';
import { useToast } from '../../feedback/Toast';
import { SettingsTabPanel } from './components/SettingsTabPanel';
import { useSettingsModalFooter } from './components/SettingsModalFooterContext';

const DEFAULTS: TemperatureConfig = {
  llm_temp_inspiration: 0.7,
  llm_temp_blueprint: 0.7,
  llm_temp_outline: 0.7,
  llm_temp_writing: 0.7,
  llm_temp_evaluation: 0.3,
  llm_temp_summary: 0.3,
};

export const TemperatureTab: React.FC = () => {
  const { addToast } = useToast();
  const { setFooter } = useSettingsModalFooter();
  const [config, setConfig] = useState<TemperatureConfig>(DEFAULTS);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const configRef = useRef(config);
  configRef.current = config;

  const fetchConfig = useCallback(async () => {
    setLoading(true);
    try {
      const data = await settingsApi.getTemperatureConfig();
      setConfig(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchConfig();
  }, [fetchConfig]);

  const setField = (key: keyof TemperatureConfig, value: string) => {
    const n = Number(value);
    if (!Number.isFinite(n)) return;
    const clamped = Math.max(0, Math.min(2, n));
    setConfig((prev) => ({ ...prev, [key]: clamped }));
  };

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await settingsApi.updateTemperatureConfig(configRef.current);
      addToast('Temperature 配置已保存', 'success');
      await fetchConfig();
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  }, [addToast, fetchConfig]);

  const footer = useMemo(
    () => (
      <BookButton variant="primary" size="sm" onClick={handleSave} disabled={saving}>
        {saving ? '应用中…' : '应用'}
      </BookButton>
    ),
    [handleSave, saving],
  );

  useEffect(() => {
    setFooter(footer);
    return () => setFooter(null);
  }, [footer, setFooter]);

  return (
    <SettingsTabPanel className="h-full min-h-0" bodyClassName="h-full min-h-0">
      <div className="flex h-full min-h-0 flex-col gap-4">
        <div className="shrink-0">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <div className="text-sm font-bold text-book-text-main">Temperature</div>
              <div className="mt-1 text-xs leading-relaxed text-book-text-muted">
                Temperature 越大越“发散”，越小越“稳定”。建议范围 0–1；此处允许 0–2。
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-end gap-2">
              <BookButton variant="ghost" size="sm" onClick={fetchConfig} disabled={loading}>
                <RefreshCw size={14} className={`mr-1 ${loading ? 'animate-spin' : ''}`} />
                刷新
              </BookButton>
            </div>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto pr-1 custom-scrollbar">
          <div className="grid gap-4 pb-1 sm:grid-cols-2">
            <BookSlider
              label="灵感对话"
              min={0}
              max={2}
              step={0.05}
              value={config.llm_temp_inspiration}
              onChange={(next) => setField('llm_temp_inspiration', String(next))}
              formatValue={(v) => v.toFixed(2)}
            />
            <BookSlider
              label="蓝图"
              min={0}
              max={2}
              step={0.05}
              value={config.llm_temp_blueprint}
              onChange={(next) => setField('llm_temp_blueprint', String(next))}
              formatValue={(v) => v.toFixed(2)}
            />
            <BookSlider
              label="大纲"
              min={0}
              max={2}
              step={0.05}
              value={config.llm_temp_outline}
              onChange={(next) => setField('llm_temp_outline', String(next))}
              formatValue={(v) => v.toFixed(2)}
            />
            <BookSlider
              label="写作"
              min={0}
              max={2}
              step={0.05}
              value={config.llm_temp_writing}
              onChange={(next) => setField('llm_temp_writing', String(next))}
              formatValue={(v) => v.toFixed(2)}
            />
            <BookSlider
              label="评估"
              min={0}
              max={2}
              step={0.05}
              value={config.llm_temp_evaluation}
              onChange={(next) => setField('llm_temp_evaluation', String(next))}
              formatValue={(v) => v.toFixed(2)}
            />
            <BookSlider
              label="摘要"
              min={0}
              max={2}
              step={0.05}
              value={config.llm_temp_summary}
              onChange={(next) => setField('llm_temp_summary', String(next))}
              formatValue={(v) => v.toFixed(2)}
            />
          </div>
        </div>
      </div>
    </SettingsTabPanel>
  );
};
