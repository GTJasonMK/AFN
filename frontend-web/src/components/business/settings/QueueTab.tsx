import React, { useCallback, useEffect, useState } from 'react';
import { BookCard } from '../../ui/BookCard';
import { BookButton } from '../../ui/BookButton';
import { BookInput } from '../../ui/BookInput';
import { queueApi, QueueConfigResponse, QueueStatusResponse } from '../../../api/queue';
import { useToast } from '../../feedback/Toast';
import { SettingsTabHeader } from './components/SettingsTabHeader';

export const QueueTab: React.FC = () => {
  const { addToast } = useToast();
  const [status, setStatus] = useState<QueueStatusResponse | null>(null);
  const [config, setConfig] = useState<QueueConfigResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const [llmMax, setLlmMax] = useState('1');
  const [imageMax, setImageMax] = useState('1');

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [s, c] = await Promise.all([queueApi.getStatus(), queueApi.getConfig()]);
      setStatus(s);
      setConfig(c);
      setLlmMax(String(c.llm_max_concurrent));
      setImageMax(String(c.image_max_concurrent));
    } catch (e) {
      console.error(e);
      setStatus(null);
      setConfig(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // 对齐桌面端：状态定时刷新（2秒一次）
  useEffect(() => {
    let cancelled = false;

    const tick = async () => {
      if (document.hidden) return;
      try {
        const s = await queueApi.getStatus();
        if (cancelled) return;
        setStatus(s);
      } catch (e) {
        // 仅记录日志；不打断用户操作
        console.error(e);
      }
    };

    const timer = window.setInterval(tick, 2000);
    const onVisibilityChange = () => {
      if (!document.hidden) tick();
    };
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, []);

  const handleSave = async () => {
    const llm = Math.max(1, Math.floor(Number(llmMax || 1)));
    const image = Math.max(1, Math.floor(Number(imageMax || 1)));
    setSaving(true);
    try {
      const updated = await queueApi.updateConfig({
        llm_max_concurrent: llm,
        image_max_concurrent: image,
      });
      setConfig(updated);
      setLlmMax(String(updated.llm_max_concurrent));
      setImageMax(String(updated.image_max_concurrent));
      addToast('队列配置已保存', 'success');
      await fetchAll();
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <SettingsTabHeader title="队列" loading={loading} onRefresh={fetchAll} showRefreshIcon />

      <div className="grid grid-cols-2 gap-3">
        <BookCard className="p-4">
          <div className="text-xs font-bold text-book-text-muted">LLM 队列</div>
          <div className="mt-2 text-sm text-book-text-main">
            <div>执行中：{status?.llm.active ?? '—'}</div>
            <div>等待中：{status?.llm.waiting ?? '—'}</div>
            <div>最大并发：{status?.llm.max_concurrent ?? '—'}</div>
            <div>已处理：{status?.llm.total_processed ?? '—'}</div>
          </div>
        </BookCard>
        <BookCard className="p-4">
          <div className="text-xs font-bold text-book-text-muted">图片队列</div>
          <div className="mt-2 text-sm text-book-text-main">
            <div>执行中：{status?.image.active ?? '—'}</div>
            <div>等待中：{status?.image.waiting ?? '—'}</div>
            <div>最大并发：{status?.image.max_concurrent ?? '—'}</div>
            <div>已处理：{status?.image.total_processed ?? '—'}</div>
          </div>
        </BookCard>
      </div>

      <BookCard className="p-4">
        <div className="text-xs font-bold text-book-text-muted mb-3">并发配置</div>
        <div className="grid grid-cols-2 gap-4">
          <BookInput
            label="LLM 最大并发"
            type="number"
            min={1}
            value={llmMax}
            onChange={(e) => setLlmMax(e.target.value)}
          />
          <BookInput
            label="图片最大并发"
            type="number"
            min={1}
            value={imageMax}
            onChange={(e) => setImageMax(e.target.value)}
          />
        </div>
        <div className="mt-4 flex justify-end">
          <BookButton variant="primary" onClick={handleSave} disabled={saving}>
            {saving ? '保存中…' : '保存'}
          </BookButton>
        </div>
        {!config && !loading && (
          <div className="mt-3 text-xs text-book-text-muted">无法读取当前配置，请检查后端是否已启动。</div>
        )}
        <div className="mt-3 text-xs text-book-text-muted">
          提示：队列状态每 2 秒自动刷新（仅在当前浏览器标签页前台时刷新）。
        </div>
      </BookCard>
    </div>
  );
};
