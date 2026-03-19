import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { KeyRound, RefreshCw, Settings2, ShieldCheck } from 'lucide-react';
import { BookButton } from '../../ui/BookButton';
import { BookInput } from '../../ui/BookInput';
import { useToast } from '../../feedback/Toast';
import { settingsApi, type AdvancedConfig } from '../../../api/settings';
import { isAdminUser, useAuthStore } from '../../../store/auth';
import { SettingsTabPanel } from './components/SettingsTabPanel';
import { useSettingsModalFooter } from './components/SettingsModalFooterContext';

const DEFAULT_CONFIG: AdvancedConfig = {
  coding_project_enabled: false,
  writer_chapter_version_count: 1,
  writer_parallel_generation: false,
  part_outline_threshold: 50,
  agent_context_max_chars: 100000,
};

type AdvancedTabProps = {
  onClose: () => void;
};

export const AdvancedTab: React.FC<AdvancedTabProps> = ({ onClose }) => {
  const { addToast } = useToast();
  const navigate = useNavigate();
  const { setFooter } = useSettingsModalFooter();
  const { authEnabled, user, logout, changePassword } = useAuthStore();

  const isAdmin = isAdminUser(authEnabled, user);
  const canEditGlobal = !authEnabled || isAdmin;

  const [config, setConfig] = useState<AdvancedConfig>(DEFAULT_CONFIG);
  const [baseline, setBaseline] = useState<AdvancedConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);

  const fetchConfig = useCallback(async () => {
    setLoading(true);
    try {
      const data = await settingsApi.getAdvancedConfig();
      setConfig(data);
      setBaseline(data);
    } catch (error) {
      console.error(error);
      addToast('读取高级策略失败，请检查后端是否启动', 'error');
      setBaseline(null);
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    void fetchConfig();
  }, [fetchConfig]);

  const isDirty = useMemo(() => {
    if (!baseline) return false;
    return JSON.stringify(config) !== JSON.stringify(baseline);
  }, [baseline, config]);

  const resetDraft = useCallback(() => {
    if (!baseline) return;
    setConfig(baseline);
  }, [baseline]);

  const setNumberField = <K extends keyof AdvancedConfig>(key: K, raw: string, fallback: number) => {
    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) return;
    const next = Math.max(0, Math.floor(parsed));
    setConfig((prev) => ({ ...prev, [key]: (Number.isFinite(next) ? next : fallback) as AdvancedConfig[K] }));
  };

  const handleSave = useCallback(async () => {
    if (!canEditGlobal) {
      addToast('需要管理员权限才能修改全局设置', 'error');
      return;
    }

    setSaving(true);
    try {
      await settingsApi.updateAdvancedConfig(config);
      addToast('设置已应用', 'success');
      await fetchConfig();
    } catch (error) {
      console.error(error);
      addToast('应用失败（请查看后端日志/接口返回）', 'error');
    } finally {
      setSaving(false);
    }
  }, [addToast, canEditGlobal, config, fetchConfig]);

  const footer = useMemo(
    () => (
      <>
        {isDirty ? (
          <BookButton variant="ghost" size="sm" onClick={resetDraft} disabled={saving || loading || !baseline}>
            放弃更改
          </BookButton>
        ) : null}
        <BookButton
          variant="primary"
          size="sm"
          onClick={handleSave}
          disabled={saving || loading || !isDirty || !canEditGlobal}
        >
          {saving ? '应用中…' : '应用'}
        </BookButton>
      </>
    ),
    [baseline, canEditGlobal, handleSave, isDirty, loading, resetDraft, saving],
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
              <div className="flex items-center gap-2 text-sm font-bold text-book-text-main">
                <Settings2 size={16} className="text-book-primary" />
                高级策略
              </div>
              <div className="mt-1 text-xs leading-relaxed text-book-text-muted">
                <span className="font-semibold text-book-text-main">全局策略</span> 会写入 `storage/config.json` 并尽量热更新。
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-end gap-2">
              <BookButton variant="ghost" size="sm" onClick={fetchConfig} disabled={loading}>
                <RefreshCw size={14} className={`mr-1 ${loading ? 'animate-spin' : ''}`} />
                刷新
              </BookButton>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="inline-flex rounded-full border border-book-border/55 bg-book-bg-paper/80 px-3 py-1 text-xs font-semibold text-book-text-muted">
              {authEnabled ? '登录模式' : '单用户模式'}
            </span>
            <span
              className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${
                canEditGlobal
                  ? 'border-book-primary/25 bg-book-primary/10 text-book-primary'
                  : 'border-book-border/55 bg-book-bg-paper/80 text-book-text-muted'
              }`}
            >
              {canEditGlobal ? '可写' : '只读'}
            </span>
            {authEnabled ? (
              <span className="inline-flex rounded-full border border-book-border/55 bg-book-bg-paper/80 px-3 py-1 text-xs font-semibold text-book-text-muted">
                {isAdmin ? '管理员' : '普通用户'}
              </span>
            ) : null}
            {isDirty ? (
              <span className="inline-flex rounded-full border border-book-primary/30 bg-book-primary/10 px-3 py-1 text-xs font-bold text-book-primary">
                未应用
              </span>
            ) : null}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto pr-1 custom-scrollbar">
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-4">
              <div className="flex items-center gap-2 px-1 text-xs font-bold text-book-text-muted">
                <Settings2 size={14} className="text-book-primary" />
                运行与生成
              </div>

            <div className="rounded-2xl border border-book-border/50 bg-book-bg-paper/60 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-sm font-bold text-book-text-main">功能开关</div>
                  <div className="mt-1 text-xs leading-relaxed text-book-text-muted">
                    关闭后首页隐藏 Prompt 工程入口，聚焦小说工作流。
                  </div>
                </div>
              </div>

              <label className="mt-4 flex cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4 rounded border-book-border text-book-primary focus:ring-book-primary"
                  checked={config.coding_project_enabled}
                  disabled={!canEditGlobal || saving}
                  onChange={(e) => setConfig((prev) => ({ ...prev, coding_project_enabled: e.target.checked }))}
                />
                <div className="min-w-0">
                  <div className="font-semibold text-book-text-main">启用编程项目功能</div>
                  <div className="mt-1 text-xs leading-relaxed text-book-text-muted">
                    面向 Vibe Coding / Prompt 工程用户，开启后首页显示编程工作台相关入口。
                  </div>
                </div>
              </label>
            </div>

            <div className="rounded-2xl border border-book-border/50 bg-book-bg-paper/60 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-sm font-bold text-book-text-main">生成参数</div>
                  <div className="mt-1 text-xs leading-relaxed text-book-text-muted">
                    这些参数影响章节生成候选数、分部阈值与 Agent 上下文大小。
                  </div>
                </div>
              </div>

              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <BookInput
                  label="章节候选版本数量（1~5）"
                  type="number"
                  min={1}
                  max={5}
                  value={config.writer_chapter_version_count}
                  disabled={!canEditGlobal || saving}
                  onChange={(e) => {
                    const v = Math.max(1, Math.min(5, Math.floor(Number(e.target.value || 1))));
                    if (!Number.isFinite(v)) return;
                    setConfig((prev) => ({ ...prev, writer_chapter_version_count: v }));
                  }}
                />

                <BookInput
                  label="长篇分部阈值（章）"
                  type="number"
                  min={1}
                  value={config.part_outline_threshold}
                  disabled={!canEditGlobal || saving}
                  onChange={(e) => setNumberField('part_outline_threshold', e.target.value, 50)}
                />

                <BookInput
                  label="Agent 上下文上限（字符）"
                  type="number"
                  min={10000}
                  step={1000}
                  value={config.agent_context_max_chars}
                  disabled={!canEditGlobal || saving}
                  onChange={(e) => setNumberField('agent_context_max_chars', e.target.value, 100000)}
                />

                <div className="flex flex-col justify-end">
                  <label className="flex cursor-pointer items-center gap-3 rounded-2xl border border-book-border/50 bg-book-bg-paper/70 px-4 py-3 text-sm">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-book-border text-book-primary focus:ring-book-primary"
                      checked={config.writer_parallel_generation}
                      disabled={!canEditGlobal || saving}
                      onChange={(e) => setConfig((prev) => ({ ...prev, writer_parallel_generation: e.target.checked }))}
                    />
                    <div className="min-w-0">
                      <div className="font-semibold text-book-text-main">启用并行生成</div>
                      <div className="mt-1 text-xs text-book-text-muted">允许后台并发推进章节生成。</div>
                    </div>
                  </label>
                </div>
              </div>

              {!canEditGlobal ? (
                <div className="mt-4 text-xs text-book-text-muted">
                  当前账号无管理员权限：参数只读。如需修改，请使用管理员账号登录。
                </div>
              ) : null}
            </div>
          </div>

            <div className="space-y-4">
              <div className="flex items-center gap-2 px-1 text-xs font-bold text-book-text-muted">
                <ShieldCheck size={14} className="text-book-primary" />
                账号与权限
              </div>

            <div className="rounded-2xl border border-book-border/50 bg-book-bg-paper/60 p-4">
              <div className="mt-1 space-y-2 text-sm text-book-text-sub">
                {authEnabled ? (
                  <>
                    <div>
                      当前账号：
                      <span className="ml-2 font-mono text-book-text-main">{user?.username || '未知'}</span>
                    </div>
                    <div className="text-xs text-book-text-muted">
                      内置管理员账号通常为 <span className="font-mono">desktop_user</span>（以服务端配置为准）。
                    </div>
                  </>
                ) : (
                  <div className="text-xs text-book-text-muted">
                    当前处于单用户模式，无需登录；部署期权限由服务端配置决定。
                  </div>
                )}
              </div>

              <div className="mt-4 flex flex-wrap justify-end gap-2">
                {isAdmin ? (
                  <BookButton
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      onClose();
                      navigate('/admin/overview');
                    }}
                  >
                    管理后台
                  </BookButton>
                ) : null}

                {authEnabled ? (
                  <BookButton
                    variant="ghost"
                    size="sm"
                    onClick={async () => {
                      try {
                        await logout();
                        addToast('已退出登录', 'success');
                        onClose();
                      } catch (error) {
                        console.error(error);
                        addToast('退出登录失败', 'error');
                      }
                    }}
                  >
                    退出登录
                  </BookButton>
                ) : null}
              </div>
            </div>

            {authEnabled ? (
              <div className="rounded-2xl border border-book-border/50 bg-book-bg-paper/60 p-4">
                <div className="flex items-center gap-2 text-book-text-main">
                  <KeyRound size={16} className="text-book-primary" />
                  <div className="font-semibold">修改当前账号密码</div>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <BookInput
                    label="旧密码"
                    type="password"
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    autoComplete="current-password"
                    disabled={changingPassword}
                  />
                  <BookInput
                    label="新密码"
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    autoComplete="new-password"
                    disabled={changingPassword}
                  />
                </div>

                <div className="mt-4 flex justify-end">
                  <BookButton
                    variant="secondary"
                    size="sm"
                    disabled={changingPassword}
                    onClick={async () => {
                      if (!oldPassword || !newPassword) {
                        addToast('请输入旧密码和新密码', 'error');
                        return;
                      }

                      setChangingPassword(true);
                      try {
                        await changePassword(oldPassword, newPassword);
                        setOldPassword('');
                        setNewPassword('');
                        addToast('密码已更新', 'success');
                      } catch (error) {
                        console.error(error);
                        addToast('修改密码失败', 'error');
                      } finally {
                        setChangingPassword(false);
                      }
                    }}
                  >
                    {changingPassword ? '处理中…' : '修改密码'}
                  </BookButton>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
      </div>
    </SettingsTabPanel>
  );
};
