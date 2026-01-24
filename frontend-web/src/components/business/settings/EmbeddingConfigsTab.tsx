import React, { useEffect, useMemo, useState } from 'react';
import { BookCard } from '../../ui/BookCard';
import { BookButton } from '../../ui/BookButton';
import { BookInput } from '../../ui/BookInput';
import { Modal } from '../../ui/Modal';
import { useToast } from '../../feedback/Toast';
import {
  embeddingConfigsApi,
  EmbeddingConfigCreate,
  EmbeddingConfigRead,
  EmbeddingConfigUpdate,
  EmbeddingProvider,
  EmbeddingProviderInfo,
} from '../../../api/embeddingConfigs';
import { CheckCircle2, Circle, FlaskConical, Plus, Trash2, Pencil } from 'lucide-react';

type EditorMode = 'create' | 'edit';

interface EditorState {
  mode: EditorMode;
  target?: EmbeddingConfigRead;
}

const PROVIDER_LABELS: Record<EmbeddingProvider, string> = {
  openai: 'OpenAI / 兼容 API',
  ollama: 'Ollama',
  local: '本地（sentence-transformers）',
};

export const EmbeddingConfigsTab: React.FC = () => {
  const { addToast } = useToast();
  const [providers, setProviders] = useState<EmbeddingProviderInfo[]>([]);
  const [configs, setConfigs] = useState<EmbeddingConfigRead[]>([]);
  const [loading, setLoading] = useState(false);

  const [editor, setEditor] = useState<EditorState | null>(null);
  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState<number | null>(null);

  const [formName, setFormName] = useState('');
  const [formProvider, setFormProvider] = useState<EmbeddingProvider>('openai');
  const [formBaseUrl, setFormBaseUrl] = useState('');
  const [formApiKey, setFormApiKey] = useState('');
  const [formModel, setFormModel] = useState('');
  const [formVectorSize, setFormVectorSize] = useState<string>('');

  const providerInfo = useMemo(() => {
    return providers.find((p) => p.provider === formProvider);
  }, [providers, formProvider]);

  const sorted = useMemo(() => {
    return [...configs].sort((a, b) => Number(b.is_active) - Number(a.is_active));
  }, [configs]);

  const fetchProviders = async () => {
    try {
      const data = await embeddingConfigsApi.listProviders();
      setProviders(data);
    } catch (e) {
      console.error(e);
      setProviders([]);
    }
  };

  const fetchList = async () => {
    setLoading(true);
    try {
      const data = await embeddingConfigsApi.list();
      setConfigs(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProviders();
    fetchList();
  }, []);

  const openCreate = () => {
    const defaultProvider: EmbeddingProvider = 'openai';
    const info = providers.find((p) => p.provider === defaultProvider);
    setEditor({ mode: 'create' });
    setFormName('新嵌入配置');
    setFormProvider(defaultProvider);
    setFormBaseUrl(info?.default_base_url || '');
    setFormApiKey('');
    setFormModel(info?.default_model || '');
    setFormVectorSize('');
  };

  const openEdit = (cfg: EmbeddingConfigRead) => {
    setEditor({ mode: 'edit', target: cfg });
    setFormName(cfg.config_name || '');
    setFormProvider(cfg.provider);
    setFormBaseUrl(cfg.api_base_url || '');
    setFormApiKey('');
    setFormModel(cfg.model_name || '');
    setFormVectorSize(cfg.vector_size ? String(cfg.vector_size) : '');
  };

  const closeEditor = () => setEditor(null);

  const parseVectorSize = (raw: string): number | null | undefined => {
    const v = raw.trim();
    if (!v) return undefined;
    const n = Number(v);
    if (!Number.isFinite(n) || n <= 0) return undefined;
    return Math.floor(n);
  };

  const buildCreatePayload = (): EmbeddingConfigCreate => {
    const name = formName.trim() || '默认嵌入配置';
    const baseUrl = formBaseUrl.trim();
    const apiKey = formApiKey.trim();
    const model = formModel.trim();
    const vectorSize = parseVectorSize(formVectorSize);
    return {
      config_name: name,
      provider: formProvider,
      api_base_url: baseUrl ? baseUrl : null,
      api_key: apiKey ? apiKey : null,
      model_name: model ? model : null,
      vector_size: typeof vectorSize === 'number' ? vectorSize : null,
    };
  };

  const buildUpdatePayload = (): EmbeddingConfigUpdate => {
    const payload: EmbeddingConfigUpdate = {};

    const name = formName.trim();
    payload.config_name = name ? name : undefined;

    payload.provider = formProvider;

    const baseUrl = formBaseUrl.trim();
    payload.api_base_url = baseUrl ? baseUrl : undefined;

    const apiKey = formApiKey.trim();
    payload.api_key = apiKey ? apiKey : undefined;

    const model = formModel.trim();
    payload.model_name = model ? model : undefined;

    const vectorSize = parseVectorSize(formVectorSize);
    payload.vector_size = typeof vectorSize === 'number' ? vectorSize : undefined;

    return payload;
  };

  const handleSave = async () => {
    if (!editor) return;
    setSaving(true);
    try {
      if (editor.mode === 'create') {
        await embeddingConfigsApi.create(buildCreatePayload());
        addToast('已创建嵌入配置', 'success');
      } else if (editor.mode === 'edit' && editor.target) {
        await embeddingConfigsApi.update(editor.target.id, buildUpdatePayload());
        addToast('已更新嵌入配置', 'success');
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
      await embeddingConfigsApi.activate(id);
      addToast('已切换激活配置', 'success');
      await fetchList();
    } catch (e) {
      console.error(e);
    }
  };

  const handleTest = async (id: number) => {
    setTestingId(id);
    try {
      const res = await embeddingConfigsApi.test(id);
      addToast(res.success ? `测试成功：${res.message}` : `测试失败：${res.message}`, res.success ? 'success' : 'error');
      await fetchList();
    } catch (e) {
      console.error(e);
    } finally {
      setTestingId(null);
    }
  };

  const handleDelete = async (cfg: EmbeddingConfigRead) => {
    if (!confirm(`确定要删除嵌入配置「${cfg.config_name}」吗？`)) return;
    try {
      await embeddingConfigsApi.delete(cfg.id);
      addToast('已删除嵌入配置', 'success');
      await fetchList();
    } catch (e) {
      console.error(e);
    }
  };

  const onProviderChange = (provider: EmbeddingProvider) => {
    setFormProvider(provider);
    const info = providers.find((p) => p.provider === provider);
    if (info?.default_base_url) setFormBaseUrl(info.default_base_url);
    if (info?.default_model) setFormModel(info.default_model);
    if (info?.requires_api_key === false) setFormApiKey('');
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-bold text-book-text-main">嵌入配置</div>
        <div className="flex items-center gap-2">
          <BookButton variant="ghost" size="sm" onClick={fetchList} disabled={loading}>
            {loading ? '刷新中…' : '刷新'}
          </BookButton>
          <BookButton variant="primary" size="sm" onClick={openCreate}>
            <Plus size={14} className="mr-1" />
            新增
          </BookButton>
        </div>
      </div>

      <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 leading-relaxed">
        说明：嵌入配置用于 RAG 检索。若你使用本地模型，请确保模型目录存在（桌面默认：`storage/models`）。
      </div>

      <div className="space-y-3">
        {sorted.length === 0 && !loading && (
          <div className="py-10 text-center text-book-text-muted text-sm">暂无配置</div>
        )}

        {sorted.map((cfg) => (
          <BookCard key={cfg.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  {cfg.is_active ? (
                    <CheckCircle2 size={16} className="text-book-primary" />
                  ) : (
                    <Circle size={16} className="text-book-text-muted" />
                  )}
                  <div className="font-bold text-book-text-main truncate">{cfg.config_name}</div>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-book-bg text-book-text-muted font-bold border border-book-border/40">
                    {PROVIDER_LABELS[cfg.provider] || cfg.provider}
                  </span>
                  {cfg.is_verified && (
                    <span className="text-[10px] px-2 py-0.5 rounded bg-book-primary/10 text-book-primary font-bold">已验证</span>
                  )}
                  {cfg.test_status === 'failed' && (
                    <span className="text-[10px] px-2 py-0.5 rounded bg-book-accent/10 text-book-accent font-bold">测试失败</span>
                  )}
                </div>

                <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-book-text-muted">
                  <div className="truncate">Base URL：{cfg.api_base_url || '—'}</div>
                  <div className="truncate">模型：{cfg.model_name || '—'}</div>
                  <div className="truncate">Key：{cfg.api_key_masked || '—'}</div>
                  <div className="truncate">维度：{cfg.vector_size || '自动检测'}</div>
                </div>

                {cfg.test_message && (
                  <div className="mt-2 text-xs text-book-text-tertiary bg-book-bg p-2 rounded border border-book-border/40">
                    {cfg.test_message}
                  </div>
                )}
              </div>

              <div className="flex flex-col gap-2 shrink-0">
                {!cfg.is_active && (
                  <BookButton variant="primary" size="sm" onClick={() => handleActivate(cfg.id)}>
                    设为激活
                  </BookButton>
                )}
                <BookButton
                  variant="ghost"
                  size="sm"
                  onClick={() => handleTest(cfg.id)}
                  disabled={testingId === cfg.id}
                >
                  <FlaskConical size={14} className={`mr-1 ${testingId === cfg.id ? 'animate-pulse' : ''}`} />
                  {testingId === cfg.id ? '测试中…' : '测试'}
                </BookButton>
                <BookButton variant="ghost" size="sm" onClick={() => openEdit(cfg)}>
                  <Pencil size={14} className="mr-1" />
                  编辑
                </BookButton>
                <BookButton variant="ghost" size="sm" onClick={() => handleDelete(cfg)} className="text-book-accent">
                  <Trash2 size={14} className="mr-1" />
                  删除
                </BookButton>
              </div>
            </div>
          </BookCard>
        ))}
      </div>

      <Modal
        isOpen={Boolean(editor)}
        onClose={closeEditor}
        title={editor?.mode === 'create' ? '新增嵌入配置' : '编辑嵌入配置'}
        maxWidthClassName="max-w-2xl"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={closeEditor}>取消</BookButton>
            <BookButton variant="primary" onClick={handleSave} disabled={saving}>
              {saving ? '保存中…' : '保存'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <BookInput label="配置名称" value={formName} onChange={(e) => setFormName(e.target.value)} />

          <div>
            <label className="block text-sm font-bold text-book-text-sub mb-1.5 ml-1">提供方</label>
            <select
              className="w-full px-4 py-2 rounded-lg bg-book-bg-paper text-book-text-main border border-book-border focus:outline-none focus:ring-2 focus:ring-book-primary/20 focus:border-book-primary transition-all duration-200"
              value={formProvider}
              onChange={(e) => onProviderChange(e.target.value as EmbeddingProvider)}
            >
              <option value="openai">OpenAI / 兼容 API</option>
              <option value="ollama">Ollama</option>
              <option value="local">本地（sentence-transformers）</option>
            </select>
            {providerInfo && (
              <div className="mt-2 text-xs text-book-text-muted leading-relaxed">
                {providerInfo.description}
              </div>
            )}
          </div>

          <BookInput
            label="API Base URL（可选）"
            value={formBaseUrl}
            onChange={(e) => setFormBaseUrl(e.target.value)}
            placeholder={providerInfo?.default_base_url || '例如：http://localhost:11434'}
            disabled={formProvider === 'local'}
          />
          <BookInput
            label="API Key（可选）"
            value={formApiKey}
            onChange={(e) => setFormApiKey(e.target.value)}
            placeholder="留空则不修改/不设置"
            disabled={formProvider !== 'openai'}
          />
          <BookInput
            label="模型名称（可选）"
            value={formModel}
            onChange={(e) => setFormModel(e.target.value)}
            placeholder={providerInfo?.default_model || 'BAAI/bge-base-zh-v1.5'}
          />
          <BookInput
            label="向量维度（可选）"
            value={formVectorSize}
            onChange={(e) => setFormVectorSize(e.target.value)}
            placeholder="留空自动检测"
          />

          <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 leading-relaxed">
            提示：编辑时 API Key 留空表示“保持不变”；如需更新，请重新输入新的 Key。
          </div>
        </div>
      </Modal>
    </div>
  );
};
