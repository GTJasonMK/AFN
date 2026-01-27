import React, { useEffect, useState } from 'react';
import { BookCard } from '../../ui/BookCard';
import { BookButton } from '../../ui/BookButton';
import { BookInput } from '../../ui/BookInput';
import { settingsApi, MaxTokensConfig } from '../../../api/settings';
import { useToast } from '../../feedback/Toast';
import { SettingsInfoBox } from './components/SettingsInfoBox';
import { SettingsTabHeader } from './components/SettingsTabHeader';

const DEFAULTS: MaxTokensConfig = {
  llm_max_tokens_blueprint: 4096,
  llm_max_tokens_chapter: 4096,
  llm_max_tokens_outline: 2048,
  llm_max_tokens_manga: 2048,
  llm_max_tokens_analysis: 2048,
  llm_max_tokens_default: 2048,
  llm_max_tokens_coding_blueprint: 4096,
  llm_max_tokens_coding_system: 2048,
  llm_max_tokens_coding_module: 2048,
  llm_max_tokens_coding_feature: 2048,
  llm_max_tokens_coding_prompt: 2048,
  llm_max_tokens_coding_directory: 2048,
};

export const MaxTokensTab: React.FC = () => {
  const { addToast } = useToast();
  const [config, setConfig] = useState<MaxTokensConfig>(DEFAULTS);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const data = await settingsApi.getMaxTokensConfig();
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

  const setField = (key: keyof MaxTokensConfig, value: string) => {
    const n = Math.max(256, Math.floor(Number(value || 0)));
    setConfig((prev) => ({ ...prev, [key]: Number.isFinite(n) ? n : prev[key] }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await settingsApi.updateMaxTokensConfig(config);
      addToast('Max Tokens 配置已保存', 'success');
      await fetchConfig();
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <SettingsTabHeader title="Max Tokens" loading={loading} onRefresh={fetchConfig} showRefreshIcon />

      <SettingsInfoBox>说明：该配置会写入 `storage/config.json` 并尝试热更新。数值过大可能导致响应变慢或超出模型限制。</SettingsInfoBox>

      <BookCard className="p-4">
        <div className="text-xs font-bold text-book-text-muted mb-3">小说系统</div>
        <div className="grid grid-cols-2 gap-4">
          <BookInput label="蓝图" type="number" min={256} value={config.llm_max_tokens_blueprint} onChange={(e) => setField('llm_max_tokens_blueprint', e.target.value)} />
          <BookInput label="章节写作" type="number" min={256} value={config.llm_max_tokens_chapter} onChange={(e) => setField('llm_max_tokens_chapter', e.target.value)} />
          <BookInput label="章节大纲" type="number" min={256} value={config.llm_max_tokens_outline} onChange={(e) => setField('llm_max_tokens_outline', e.target.value)} />
          <BookInput label="漫画分镜" type="number" min={256} value={config.llm_max_tokens_manga} onChange={(e) => setField('llm_max_tokens_manga', e.target.value)} />
          <BookInput label="分析" type="number" min={256} value={config.llm_max_tokens_analysis} onChange={(e) => setField('llm_max_tokens_analysis', e.target.value)} />
          <BookInput label="默认" type="number" min={256} value={config.llm_max_tokens_default} onChange={(e) => setField('llm_max_tokens_default', e.target.value)} />
        </div>
      </BookCard>

      <BookCard className="p-4">
        <div className="text-xs font-bold text-book-text-muted mb-3">编程系统</div>
        <div className="grid grid-cols-2 gap-4">
          <BookInput label="蓝图" type="number" min={256} value={config.llm_max_tokens_coding_blueprint} onChange={(e) => setField('llm_max_tokens_coding_blueprint', e.target.value)} />
          <BookInput label="系统" type="number" min={256} value={config.llm_max_tokens_coding_system} onChange={(e) => setField('llm_max_tokens_coding_system', e.target.value)} />
          <BookInput label="模块" type="number" min={256} value={config.llm_max_tokens_coding_module} onChange={(e) => setField('llm_max_tokens_coding_module', e.target.value)} />
          <BookInput label="特性" type="number" min={256} value={config.llm_max_tokens_coding_feature} onChange={(e) => setField('llm_max_tokens_coding_feature', e.target.value)} />
          <BookInput label="提示词" type="number" min={256} value={config.llm_max_tokens_coding_prompt} onChange={(e) => setField('llm_max_tokens_coding_prompt', e.target.value)} />
          <BookInput label="目录" type="number" min={256} value={config.llm_max_tokens_coding_directory} onChange={(e) => setField('llm_max_tokens_coding_directory', e.target.value)} />
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
