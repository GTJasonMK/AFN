import React, { useEffect, useState } from 'react';
import { BookCard } from '../../ui/BookCard';
import { BookButton } from '../../ui/BookButton';
import { BookInput } from '../../ui/BookInput';
import { settingsApi, TemperatureConfig } from '../../../api/settings';
import { useToast } from '../../feedback/Toast';
import { SettingsInfoBox } from './components/SettingsInfoBox';
import { SettingsTabHeader } from './components/SettingsTabHeader';

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
  const [config, setConfig] = useState<TemperatureConfig>(DEFAULTS);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const data = await settingsApi.getTemperatureConfig();
      setConfig(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const setField = (key: keyof TemperatureConfig, value: string) => {
    const n = Number(value);
    if (!Number.isFinite(n)) return;
    const clamped = Math.max(0, Math.min(2, n));
    setConfig((prev) => ({ ...prev, [key]: clamped }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await settingsApi.updateTemperatureConfig(config);
      addToast('Temperature 配置已保存', 'success');
      await fetchConfig();
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <SettingsTabHeader title="Temperature" loading={loading} onRefresh={fetchConfig} showRefreshIcon />

      <SettingsInfoBox>说明：Temperature 越大越“发散”，越小越“稳定”。建议范围 0–1；此处允许 0–2。</SettingsInfoBox>

      <BookCard className="p-4">
        <div className="grid grid-cols-2 gap-4">
          <BookInput label="灵感对话" type="number" step={0.05} min={0} max={2} value={config.llm_temp_inspiration} onChange={(e) => setField('llm_temp_inspiration', e.target.value)} />
          <BookInput label="蓝图" type="number" step={0.05} min={0} max={2} value={config.llm_temp_blueprint} onChange={(e) => setField('llm_temp_blueprint', e.target.value)} />
          <BookInput label="大纲" type="number" step={0.05} min={0} max={2} value={config.llm_temp_outline} onChange={(e) => setField('llm_temp_outline', e.target.value)} />
          <BookInput label="写作" type="number" step={0.05} min={0} max={2} value={config.llm_temp_writing} onChange={(e) => setField('llm_temp_writing', e.target.value)} />
          <BookInput label="评估" type="number" step={0.05} min={0} max={2} value={config.llm_temp_evaluation} onChange={(e) => setField('llm_temp_evaluation', e.target.value)} />
          <BookInput label="摘要" type="number" step={0.05} min={0} max={2} value={config.llm_temp_summary} onChange={(e) => setField('llm_temp_summary', e.target.value)} />
        </div>
      </BookCard>

      <div className="flex justify-end">
        <BookButton variant="primary" onClick={handleSave} disabled={saving}>
          {saving ? '保存中…' : '保存'}
        </BookButton>
      </div>
    </div>
  );
};
