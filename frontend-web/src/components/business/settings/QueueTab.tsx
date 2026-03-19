import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { BookButton } from '../../ui/BookButton';
import { BookInput } from '../../ui/BookInput';
import { queueApi, QueueConfigResponse, QueueStatusResponse } from '../../../api/queue';
import { useToast } from '../../feedback/Toast';
import { isAdminUser, useAuthStore } from '../../../store/auth';
import { SettingsTabPanel } from './components/SettingsTabPanel';
import { SettingsFixedCard } from './components/SettingsFixedCard';
import { useSettingsModalFooter } from './components/SettingsModalFooterContext';
import { SETTINGS_CARD_HEIGHTS } from './components/settingsLayout';

export const QueueTab: React.FC = () => {
  const { addToast } = useToast();
  const { authEnabled, user } = useAuthStore();
  const isAdmin = isAdminUser(authEnabled, user);
  const { setFooter } = useSettingsModalFooter();
  const [status, setStatus] = useState<QueueStatusResponse | null>(null);
  const [config, setConfig] = useState<QueueConfigResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const [llmMax, setLlmMax] = useState('1');
  const [imageMax, setImageMax] = useState('1');
  const llmMaxRef = useRef(llmMax);
  llmMaxRef.current = llmMax;
  const imageMaxRef = useRef(imageMax);
  imageMaxRef.current = imageMax;

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

  const handleSave = useCallback(async () => {
    if (!isAdmin) {
      addToast('需要管理员权限才能修改队列配置', 'error');
      return;
    }
    const llm = Math.max(1, Math.floor(Number(llmMaxRef.current || 1)));
    const image = Math.max(1, Math.floor(Number(imageMaxRef.current || 1)));
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
  }, [addToast, fetchAll, isAdmin]);

  const footer = useMemo(
    () => (
      <BookButton variant="primary" size="sm" onClick={handleSave} disabled={saving || !isAdmin}>
        {saving ? '应用中…' : '应用'}
      </BookButton>
    ),
    [handleSave, isAdmin, saving],
  );

  useEffect(() => {
    setFooter(footer);
    return () => setFooter(null);
  }, [footer, setFooter]);

  return (
    <SettingsTabPanel className="h-full min-h-0" bodyClassName="h-full min-h-0">
      <div className="grid h-full min-h-0 gap-4 lg:grid-rows-[auto_minmax(0,1fr)]">
        <div className="grid grid-cols-2 gap-3">
          <SettingsFixedCard title="LLM 队列" heightClassName={SETTINGS_CARD_HEIGHTS.compact} bodyScrollable={false}>
            <div className="text-sm text-book-text-main space-y-1">
              <div>执行中：{status?.llm.active ?? '—'}</div>
              <div>等待中：{status?.llm.waiting ?? '—'}</div>
              <div>最大并发：{status?.llm.max_concurrent ?? '—'}</div>
              <div>已处理：{status?.llm.total_processed ?? '—'}</div>
            </div>
          </SettingsFixedCard>

          <SettingsFixedCard title="图片队列" heightClassName={SETTINGS_CARD_HEIGHTS.compact} bodyScrollable={false}>
            <div className="text-sm text-book-text-main space-y-1">
              <div>执行中：{status?.image.active ?? '—'}</div>
              <div>等待中：{status?.image.waiting ?? '—'}</div>
              <div>最大并发：{status?.image.max_concurrent ?? '—'}</div>
              <div>已处理：{status?.image.total_processed ?? '—'}</div>
            </div>
          </SettingsFixedCard>
        </div>

        <SettingsFixedCard
          title="并发配置"
          description="队列状态每 2 秒自动刷新（仅在当前标签页前台时刷新）。"
          heightClassName={`${SETTINGS_CARD_HEIGHTS.primary} lg:h-full`}
          bodyClassName="space-y-4"
          actions={(
            <BookButton variant="ghost" size="sm" onClick={fetchAll} disabled={loading}>
              <RefreshCw size={14} className={`mr-1 ${loading ? 'animate-spin' : ''}`} />
              刷新
            </BookButton>
          )}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <BookInput
              label="LLM 最大并发"
              type="number"
              min={1}
              value={llmMax}
              onChange={(e) => setLlmMax(e.target.value)}
              disabled={!isAdmin || saving}
            />
            <BookInput
              label="图片最大并发"
              type="number"
              min={1}
              value={imageMax}
              onChange={(e) => setImageMax(e.target.value)}
              disabled={!isAdmin || saving}
            />
          </div>

          {!config && !loading ? (
            <div className="text-xs text-book-text-muted">无法读取当前配置，请检查后端是否已启动。</div>
          ) : null}

          {!isAdmin ? (
            <div className="text-xs text-book-text-muted">当前账号仅可查看队列状态，修改并发配置需要管理员权限。</div>
          ) : null}
        </SettingsFixedCard>
      </div>
    </SettingsTabPanel>
  );
};
