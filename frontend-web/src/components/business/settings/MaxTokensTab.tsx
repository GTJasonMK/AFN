import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { BookButton } from '../../ui/BookButton';
import { BookInput } from '../../ui/BookInput';
import { settingsApi, MaxTokensConfig } from '../../../api/settings';
import { useToast } from '../../feedback/Toast';
import { SettingsTabPanel } from './components/SettingsTabPanel';
import { SettingsFixedCard } from './components/SettingsFixedCard';
import { useSettingsModalFooter } from './components/SettingsModalFooterContext';
import { SETTINGS_CARD_HEIGHTS } from './components/settingsLayout';

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
  const { setFooter } = useSettingsModalFooter();
  const [config, setConfig] = useState<MaxTokensConfig>(DEFAULTS);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const configRef = useRef(config);
  configRef.current = config;

  const fetchConfig = useCallback(async () => {
    setLoading(true);
    try {
      const data = await settingsApi.getMaxTokensConfig();
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

  const setField = (key: keyof MaxTokensConfig, value: string) => {
    const n = Math.max(256, Math.floor(Number(value || 0)));
    setConfig((prev) => ({ ...prev, [key]: Number.isFinite(n) ? n : prev[key] }));
  };

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await settingsApi.updateMaxTokensConfig(configRef.current);
      addToast('Max Tokens 配置已保存', 'success');
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
      <div className="grid h-full min-h-0 gap-4 lg:grid-cols-2 lg:grid-rows-[minmax(0,1fr)]">
        <SettingsFixedCard
          title="小说系统"
          description="写入 `storage/config.json` 并尝试热更新；数值过大可能导致响应变慢或超出模型限制。"
          heightClassName={`${SETTINGS_CARD_HEIGHTS.primary} lg:h-full`}
          actions={(
            <BookButton variant="ghost" size="sm" onClick={fetchConfig} disabled={loading}>
              <RefreshCw size={14} className={`mr-1 ${loading ? 'animate-spin' : ''}`} />
              刷新
            </BookButton>
          )}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <BookInput label="蓝图" type="number" min={256} value={config.llm_max_tokens_blueprint} onChange={(e) => setField('llm_max_tokens_blueprint', e.target.value)} />
            <BookInput label="章节写作" type="number" min={256} value={config.llm_max_tokens_chapter} onChange={(e) => setField('llm_max_tokens_chapter', e.target.value)} />
            <BookInput label="章节大纲" type="number" min={256} value={config.llm_max_tokens_outline} onChange={(e) => setField('llm_max_tokens_outline', e.target.value)} />
            <BookInput label="漫画分镜" type="number" min={256} value={config.llm_max_tokens_manga} onChange={(e) => setField('llm_max_tokens_manga', e.target.value)} />
            <BookInput label="分析" type="number" min={256} value={config.llm_max_tokens_analysis} onChange={(e) => setField('llm_max_tokens_analysis', e.target.value)} />
            <BookInput label="默认" type="number" min={256} value={config.llm_max_tokens_default} onChange={(e) => setField('llm_max_tokens_default', e.target.value)} />
          </div>
        </SettingsFixedCard>

        <SettingsFixedCard
          title="编程系统"
          description="影响编程工作台 / Prompt 工程相关的生成上限。"
          heightClassName={`${SETTINGS_CARD_HEIGHTS.primary} lg:h-full`}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <BookInput label="蓝图" type="number" min={256} value={config.llm_max_tokens_coding_blueprint} onChange={(e) => setField('llm_max_tokens_coding_blueprint', e.target.value)} />
            <BookInput label="系统" type="number" min={256} value={config.llm_max_tokens_coding_system} onChange={(e) => setField('llm_max_tokens_coding_system', e.target.value)} />
            <BookInput label="模块" type="number" min={256} value={config.llm_max_tokens_coding_module} onChange={(e) => setField('llm_max_tokens_coding_module', e.target.value)} />
            <BookInput label="特性" type="number" min={256} value={config.llm_max_tokens_coding_feature} onChange={(e) => setField('llm_max_tokens_coding_feature', e.target.value)} />
            <BookInput label="提示词" type="number" min={256} value={config.llm_max_tokens_coding_prompt} onChange={(e) => setField('llm_max_tokens_coding_prompt', e.target.value)} />
            <BookInput label="目录" type="number" min={256} value={config.llm_max_tokens_coding_directory} onChange={(e) => setField('llm_max_tokens_coding_directory', e.target.value)} />
          </div>
        </SettingsFixedCard>
      </div>
    </SettingsTabPanel>
  );
};
