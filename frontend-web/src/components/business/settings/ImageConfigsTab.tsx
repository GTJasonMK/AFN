import React, { useEffect, useMemo, useState } from 'react';
import { BookCard } from '../../ui/BookCard';
import { BookButton } from '../../ui/BookButton';
import { BookInput, BookTextarea } from '../../ui/BookInput';
import { Modal } from '../../ui/Modal';
import { useToast } from '../../feedback/Toast';
import {
  imageConfigsApi,
  ImageConfigCreate,
  ImageConfigResponse,
  ImageConfigUpdate,
  ImageProviderType,
} from '../../../api/imageConfigs';
import { CheckCircle2, Circle, FlaskConical, Plus, Trash2, Pencil, Image as ImageIcon } from 'lucide-react';

type EditorMode = 'create' | 'edit';

interface EditorState {
  mode: EditorMode;
  target?: ImageConfigResponse;
}

const PROVIDER_LABELS: Record<ImageProviderType, string> = {
  openai_compatible: 'OpenAI 兼容接口',
  stability: 'Stability AI',
  midjourney: 'Midjourney',
  comfyui: 'ComfyUI（本地）',
};

function safeString(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function parseJsonOrNull(raw: string): Record<string, any> | null {
  const text = raw.trim();
  if (!text) return null;
  const parsed = JSON.parse(text);
  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed as Record<string, any>;
  return null;
}

export const ImageConfigsTab: React.FC = () => {
  const { addToast } = useToast();
  const [configs, setConfigs] = useState<ImageConfigResponse[]>([]);
  const [loading, setLoading] = useState(false);

  const [editor, setEditor] = useState<EditorState | null>(null);
  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState<number | null>(null);

  const [formName, setFormName] = useState('');
  const [formProvider, setFormProvider] = useState<ImageProviderType>('openai_compatible');
  const [formBaseUrl, setFormBaseUrl] = useState('');
  const [formApiKey, setFormApiKey] = useState('');
  const [formModel, setFormModel] = useState('nano-banana-pro');
  const [formStyle, setFormStyle] = useState('anime');
  const [formRatio, setFormRatio] = useState('16:9');
  const [formResolution, setFormResolution] = useState('1K');
  const [formQuality, setFormQuality] = useState('standard');
  const [formExtraParams, setFormExtraParams] = useState('');

  const sorted = useMemo(() => {
    return [...configs].sort((a, b) => Number(b.is_active) - Number(a.is_active));
  }, [configs]);

  const fetchList = async () => {
    setLoading(true);
    try {
      const data = await imageConfigsApi.list();
      setConfigs(data);
    } catch (e) {
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
    setFormName('新图片配置');
    setFormProvider('openai_compatible');
    setFormBaseUrl('');
    setFormApiKey('');
    setFormModel('nano-banana-pro');
    setFormStyle('anime');
    setFormRatio('16:9');
    setFormResolution('1K');
    setFormQuality('standard');
    setFormExtraParams('');
  };

  const openEdit = (cfg: ImageConfigResponse) => {
    setEditor({ mode: 'edit', target: cfg });
    setFormName(cfg.config_name || '');
    setFormProvider(cfg.provider_type);
    setFormBaseUrl(cfg.api_base_url || '');
    setFormApiKey('');
    setFormModel(cfg.model_name || '');
    setFormStyle(cfg.default_style || 'anime');
    setFormRatio(cfg.default_ratio || '16:9');
    setFormResolution(cfg.default_resolution || '1K');
    setFormQuality(safeString(cfg.default_quality) || 'standard');
    setFormExtraParams(cfg.extra_params ? JSON.stringify(cfg.extra_params, null, 2) : '');
  };

  const closeEditor = () => setEditor(null);

  const buildCreatePayload = (): ImageConfigCreate => {
    const extraParams = parseJsonOrNull(formExtraParams);
    return {
      config_name: formName.trim() || '默认图片配置',
      provider_type: formProvider,
      api_base_url: formBaseUrl.trim() ? formBaseUrl.trim() : null,
      api_key: formApiKey.trim() ? formApiKey.trim() : null,
      model_name: formModel.trim() ? formModel.trim() : null,
      default_style: formStyle.trim() ? formStyle.trim() : null,
      default_ratio: formRatio.trim() ? formRatio.trim() : null,
      default_resolution: formResolution.trim() ? formResolution.trim() : null,
      default_quality: formQuality.trim() ? formQuality.trim() : null,
      extra_params: extraParams,
    };
  };

  const buildUpdatePayload = (): ImageConfigUpdate => {
    const payload: ImageConfigUpdate = {
      config_name: formName.trim() || undefined,
      provider_type: formProvider,
      api_base_url: formBaseUrl.trim() ? formBaseUrl.trim() : undefined,
      api_key: formApiKey.trim() ? formApiKey.trim() : undefined,
      model_name: formModel.trim() ? formModel.trim() : undefined,
      default_style: formStyle.trim() ? formStyle.trim() : undefined,
      default_ratio: formRatio.trim() ? formRatio.trim() : undefined,
      default_resolution: formResolution.trim() ? formResolution.trim() : undefined,
      default_quality: formQuality.trim() ? formQuality.trim() : undefined,
    };
    if (formExtraParams.trim()) {
      payload.extra_params = parseJsonOrNull(formExtraParams) || undefined;
    }
    return payload;
  };

  const handleSave = async () => {
    if (!editor) return;

    // extra_params JSON 校验
    if (formExtraParams.trim()) {
      try {
        parseJsonOrNull(formExtraParams);
      } catch (e) {
        addToast('extra_params 不是合法 JSON 对象', 'error');
        return;
      }
    }

    setSaving(true);
    try {
      if (editor.mode === 'create') {
        await imageConfigsApi.create(buildCreatePayload());
        addToast('已创建图片配置', 'success');
      } else if (editor.mode === 'edit' && editor.target) {
        await imageConfigsApi.update(editor.target.id, buildUpdatePayload());
        addToast('已更新图片配置', 'success');
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
      await imageConfigsApi.activate(id);
      addToast('已切换激活配置', 'success');
      await fetchList();
    } catch (e) {
      console.error(e);
    }
  };

  const handleTest = async (id: number) => {
    setTestingId(id);
    try {
      const res = await imageConfigsApi.test(id);
      addToast(res.success ? `测试成功：${res.message}` : `测试失败：${res.message}`, res.success ? 'success' : 'error');
      await fetchList();
    } catch (e) {
      console.error(e);
    } finally {
      setTestingId(null);
    }
  };

  const handleDelete = async (cfg: ImageConfigResponse) => {
    if (!confirm(`确定要删除图片配置「${cfg.config_name}」吗？`)) return;
    try {
      await imageConfigsApi.delete(cfg.id);
      addToast('已删除图片配置', 'success');
      await fetchList();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-bold text-book-text-main">图片配置</div>
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
        说明：图片配置用于角色立绘、漫画图片等生成。请确保至少有一个“激活配置”。
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
                    {PROVIDER_LABELS[cfg.provider_type] || cfg.provider_type}
                  </span>
                  {cfg.is_verified && (
                    <span className="text-[10px] px-2 py-0.5 rounded bg-book-primary/10 text-book-primary font-bold">已验证</span>
                  )}
                </div>

                <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-book-text-muted">
                  <div className="truncate">Base URL：{cfg.api_base_url || '—'}</div>
                  <div className="truncate">模型：{cfg.model_name || '—'}</div>
                  <div className="truncate">默认风格：{cfg.default_style || '—'}</div>
                  <div className="truncate">默认比例：{cfg.default_ratio || '—'}</div>
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
        title={editor?.mode === 'create' ? '新增图片配置' : '编辑图片配置'}
        maxWidthClassName="max-w-3xl"
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
          <div className="flex items-center gap-2 text-xs text-book-text-muted">
            <ImageIcon size={14} className="text-book-primary" />
            <span>配置仅影响图片生成相关功能。</span>
          </div>

          <BookInput label="配置名称" value={formName} onChange={(e) => setFormName(e.target.value)} />

          <div>
            <label className="block text-sm font-bold text-book-text-sub mb-1.5 ml-1">提供方</label>
            <select
              className="w-full px-4 py-2 rounded-lg bg-book-bg-paper text-book-text-main border border-book-border focus:outline-none focus:ring-2 focus:ring-book-primary/20 focus:border-book-primary transition-all duration-200"
              value={formProvider}
              onChange={(e) => setFormProvider(e.target.value as ImageProviderType)}
            >
              <option value="openai_compatible">OpenAI 兼容接口</option>
              <option value="stability">Stability AI</option>
              <option value="midjourney">Midjourney</option>
              <option value="comfyui">ComfyUI（本地）</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <BookInput label="API Base URL（可选）" value={formBaseUrl} onChange={(e) => setFormBaseUrl(e.target.value)} placeholder="例如：https://api.openai.com/v1" />
            <BookInput label="API Key（可选）" value={formApiKey} onChange={(e) => setFormApiKey(e.target.value)} placeholder="留空则不修改/不设置" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <BookInput label="模型名称（可选）" value={formModel} onChange={(e) => setFormModel(e.target.value)} placeholder="例如：nano-banana-pro" />
            <BookInput label="默认风格（可选）" value={formStyle} onChange={(e) => setFormStyle(e.target.value)} placeholder="例如：anime / manga" />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <BookInput label="默认宽高比" value={formRatio} onChange={(e) => setFormRatio(e.target.value)} placeholder="16:9" />
            <BookInput label="默认分辨率" value={formResolution} onChange={(e) => setFormResolution(e.target.value)} placeholder="1K / 2K" />
            <BookInput label="默认质量" value={formQuality} onChange={(e) => setFormQuality(e.target.value)} placeholder="draft / standard / high" />
          </div>

          <BookTextarea
            label="extra_params（JSON，可选）"
            value={formExtraParams}
            onChange={(e) => setFormExtraParams(e.target.value)}
            className="min-h-[140px] font-mono text-xs"
            placeholder='例如：{ "steps": 28, "cfg_scale": 6.5 }'
          />
        </div>
      </Modal>
    </div>
  );
};

