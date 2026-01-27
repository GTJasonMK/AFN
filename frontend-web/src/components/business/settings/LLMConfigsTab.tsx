import React, { useEffect, useMemo, useState } from 'react';
import { BookInput } from '../../ui/BookInput';
import { useToast } from '../../feedback/Toast';
import { llmConfigsApi, LLMConfigCreate, LLMConfigRead, LLMConfigUpdate } from '../../../api/llmConfigs';
import { CheckCircle2, Circle } from 'lucide-react';
import { ConfigsCardsList } from './components/ConfigsCardsList';
import { SettingsEditorModal } from './components/SettingsEditorModal';
import { SettingsInfoBox } from './components/SettingsInfoBox';
import { SettingsTabHeader } from './components/SettingsTabHeader';

type EditorMode = 'create' | 'edit';

interface EditorState {
  mode: EditorMode;
  target?: LLMConfigRead;
}

export const LLMConfigsTab: React.FC = () => {
  const { addToast } = useToast();
  const [configs, setConfigs] = useState<LLMConfigRead[]>([]);
  const [loading, setLoading] = useState(false);

  const [editor, setEditor] = useState<EditorState | null>(null);
  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState<number | null>(null);

  const [formName, setFormName] = useState('');
  const [formUrl, setFormUrl] = useState('');
  const [formApiKey, setFormApiKey] = useState('');
  const [formModel, setFormModel] = useState('');

  const sorted = useMemo(() => {
    return [...configs].sort((a, b) => Number(b.is_active) - Number(a.is_active));
  }, [configs]);

  const fetchList = async () => {
    setLoading(true);
    try {
      const data = await llmConfigsApi.list();
      setConfigs(data);
    } catch (e) {
      // 错误已由全局拦截器提示
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchList();
  }, []);

  const openCreate = () => {
    setEditor({ mode: 'create' });
    setFormName('新配置');
    setFormUrl('');
    setFormApiKey('');
    setFormModel('');
  };

  const openEdit = (cfg: LLMConfigRead) => {
    setEditor({ mode: 'edit', target: cfg });
    setFormName(cfg.config_name || '');
    setFormUrl(cfg.llm_provider_url || '');
    setFormApiKey('');
    setFormModel(cfg.llm_provider_model || '');
  };

  const closeEditor = () => setEditor(null);

  const buildCreatePayload = (): LLMConfigCreate => {
    const name = formName.trim() || '默认配置';
    const url = formUrl.trim();
    const apiKey = formApiKey.trim();
    const model = formModel.trim();
    return {
      config_name: name,
      llm_provider_url: url ? url : null,
      llm_provider_api_key: apiKey ? apiKey : null,
      llm_provider_model: model ? model : null,
    };
  };

  const buildUpdatePayload = (): LLMConfigUpdate => {
    const payload: LLMConfigUpdate = {};

    const name = formName.trim();
    payload.config_name = name ? name : undefined;

    const url = formUrl.trim();
    payload.llm_provider_url = url ? url : undefined;

    const apiKey = formApiKey.trim();
    payload.llm_provider_api_key = apiKey ? apiKey : undefined;

    const model = formModel.trim();
    payload.llm_provider_model = model ? model : undefined;

    return payload;
  };

  const handleSave = async () => {
    if (!editor) return;
    setSaving(true);
    try {
      if (editor.mode === 'create') {
        await llmConfigsApi.create(buildCreatePayload());
        addToast('已创建 LLM 配置', 'success');
      } else if (editor.mode === 'edit' && editor.target) {
        await llmConfigsApi.update(editor.target.id, buildUpdatePayload());
        addToast('已更新 LLM 配置', 'success');
      }
      closeEditor();
      await fetchList();
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handleActivate = async (id: number) => {
    try {
      await llmConfigsApi.activate(id);
      addToast('已切换激活配置', 'success');
      await fetchList();
    } catch (e) {
      console.error(e);
    }
  };

  const handleTest = async (id: number) => {
    setTestingId(id);
    try {
      const res = await llmConfigsApi.test(id);
      addToast(res.success ? `测试成功：${res.message}` : `测试失败：${res.message}`, res.success ? 'success' : 'error');
      await fetchList();
    } catch (e) {
      console.error(e);
    } finally {
      setTestingId(null);
    }
  };

  const handleDelete = async (cfg: LLMConfigRead) => {
    if (!confirm(`确定要删除 LLM 配置「${cfg.config_name}」吗？`)) return;
    try {
      await llmConfigsApi.delete(cfg.id);
      addToast('已删除 LLM 配置', 'success');
      await fetchList();
    } catch (e) {
      console.error(e);
    }
  };

  const commonListProps = { items: sorted, loading, testingId, onActivate: handleActivate, onTest: handleTest, onEdit: openEdit, onDelete: handleDelete };

  return (
    <div className="space-y-4">
      <SettingsTabHeader title="LLM 配置" loading={loading} onRefresh={fetchList} onCreate={openCreate} />

      <SettingsInfoBox>
        说明：LLM 配置用于蓝图/大纲/写作等生成。桌面版默认使用“激活的配置”；WebUI 与桌面保持一致。
      </SettingsInfoBox>

      <ConfigsCardsList
        {...commonListProps}
        renderLeft={(cfg) => (
          <>
            <div className="flex items-center gap-2">
              {cfg.is_active ? (
                <CheckCircle2 size={16} className="text-book-primary" />
              ) : (
                <Circle size={16} className="text-book-text-muted" />
              )}
              <div className="font-bold text-book-text-main truncate">{cfg.config_name}</div>
              {cfg.is_verified && (
                <span className="text-[10px] px-2 py-0.5 rounded bg-book-primary/10 text-book-primary font-bold">已验证</span>
              )}
              {cfg.test_status === 'failed' && (
                <span className="text-[10px] px-2 py-0.5 rounded bg-book-accent/10 text-book-accent font-bold">测试失败</span>
              )}
            </div>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-book-text-muted">
              <div className="truncate">URL：{cfg.llm_provider_url || '（使用默认）'}</div>
              <div className="truncate">模型：{cfg.llm_provider_model || '（使用默认）'}</div>
              <div className="truncate">Key：{cfg.llm_provider_api_key_masked || '（未设置）'}</div>
              <div className="truncate">上次测试：{cfg.last_test_at || '—'}</div>
            </div>
          </>
        )}
      />

      <SettingsEditorModal
        isOpen={Boolean(editor)}
        onClose={closeEditor}
        title={editor?.mode === 'create' ? '新增 LLM 配置' : '编辑 LLM 配置'}
        saving={saving}
        onSave={handleSave}
        maxWidthClassName="max-w-2xl"
      >
        <div className="space-y-4">
          <BookInput label="配置名称" value={formName} onChange={(e) => setFormName(e.target.value)} />
          <BookInput label="LLM Base URL（可选）" value={formUrl} onChange={(e) => setFormUrl(e.target.value)} placeholder="例如：https://api.openai.com/v1" />
          <BookInput label="LLM API Key（可选）" value={formApiKey} onChange={(e) => setFormApiKey(e.target.value)} placeholder="留空则不修改/不设置" />
          <BookInput label="模型名称（可选）" value={formModel} onChange={(e) => setFormModel(e.target.value)} placeholder="例如：gpt-4o-mini" />
          <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 leading-relaxed">
            提示：编辑时 API Key 留空表示“保持不变”；如需更新，请重新输入新的 Key。
          </div>
        </div>
      </SettingsEditorModal>
    </div>
  );
};
