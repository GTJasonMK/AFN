import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bot,
  Boxes,
  BrainCircuit,
  Database,
  Gauge,
  Image,
  KeyRound,
  Palette,
  ScrollText,
  Settings2,
  Sparkles,
  Thermometer,
  Upload,
  Workflow,
} from 'lucide-react';
import { Modal } from '../ui/Modal';
import { BookInput } from '../ui/BookInput';
import { BookButton } from '../ui/BookButton';
import { settingsApi, type AdvancedConfig } from '../../api/settings';
import { useToast } from '../feedback/Toast';
import { isAdminUser, useAuthStore } from '../../store/auth';
import {
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from './novel/NovelDialogPrimitives';

const LLMConfigsTab = lazy(() =>
  import('./settings/LLMConfigsTab').then((module) => ({ default: module.LLMConfigsTab }))
);
const EmbeddingConfigsTab = lazy(() =>
  import('./settings/EmbeddingConfigsTab').then((module) => ({ default: module.EmbeddingConfigsTab }))
);
const ImageConfigsTab = lazy(() =>
  import('./settings/ImageConfigsTab').then((module) => ({ default: module.ImageConfigsTab }))
);
const ThemeTab = lazy(() =>
  import('./settings/ThemeTab').then((module) => ({ default: module.ThemeTab }))
);
const QueueTab = lazy(() =>
  import('./settings/QueueTab').then((module) => ({ default: module.QueueTab }))
);
const PromptsTab = lazy(() =>
  import('./settings/PromptsTab').then((module) => ({ default: module.PromptsTab }))
);
const MaxTokensTab = lazy(() =>
  import('./settings/MaxTokensTab').then((module) => ({ default: module.MaxTokensTab }))
);
const TemperatureTab = lazy(() =>
  import('./settings/TemperatureTab').then((module) => ({ default: module.TemperatureTab }))
);
const ImportExportTab = lazy(() =>
  import('./settings/ImportExportTab').then((module) => ({ default: module.ImportExportTab }))
);

const SettingsTabLoading: React.FC = () => (
  <NovelDialogSurface className="flex items-center justify-center py-12 text-sm text-book-text-muted">
    面板加载中…
  </NovelDialogSurface>
);

type SettingsTabId =
  | 'advanced'
  | 'llm'
  | 'embedding'
  | 'image'
  | 'theme'
  | 'queue'
  | 'prompts'
  | 'maxTokens'
  | 'temperature'
  | 'io';

type SettingsTabGroupId = 'platform' | 'models' | 'experience';

type SettingsTabDefinition = {
  id: SettingsTabId;
  group: SettingsTabGroupId;
  label: string;
  icon: React.ElementType;
};

const settingsTabDefinitions: SettingsTabDefinition[] = [
  { id: 'advanced', group: 'platform', label: '高级策略', icon: Settings2 },
  { id: 'queue', group: 'platform', label: '队列编排', icon: Workflow },
  { id: 'io', group: 'platform', label: '导入导出', icon: Upload },
  { id: 'llm', group: 'models', label: 'LLM 模型', icon: Bot },
  { id: 'embedding', group: 'models', label: '嵌入配置', icon: Database },
  { id: 'image', group: 'models', label: '图片模型', icon: Image },
  { id: 'theme', group: 'experience', label: '主题系统', icon: Palette },
  { id: 'prompts', group: 'experience', label: '提示词库', icon: ScrollText },
  { id: 'maxTokens', group: 'experience', label: 'Max Tokens', icon: Gauge },
  { id: 'temperature', group: 'experience', label: 'Temperature', icon: Thermometer },
];

const settingsTabGroups: Array<{
  id: SettingsTabGroupId;
  label: string;
  icon: React.ElementType;
}> = [
  { id: 'platform', label: '平台', icon: Boxes },
  { id: 'models', label: '模型', icon: BrainCircuit },
  { id: 'experience', label: '体验', icon: Sparkles },
];

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<SettingsTabId>('advanced');
  const [config, setConfig] = useState<AdvancedConfig>({
    coding_project_enabled: false,
    writer_chapter_version_count: 1,
    writer_parallel_generation: false,
    part_outline_threshold: 50,
    agent_context_max_chars: 100000,
  });
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();
  const { authEnabled, user, logout, changePassword } = useAuthStore();
  const navigate = useNavigate();
  const isAdmin = isAdminUser(authEnabled, user);
  const canEditGlobal = !authEnabled || isAdmin;
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');

  useEffect(() => {
    if (!isOpen) return;

    setActiveTab('advanced');

    const fetchConfig = async () => {
      try {
        const data = await settingsApi.getAdvancedConfig();
        setConfig(data);
      } catch (error) {
        console.error(error);
      }
    };

    fetchConfig();
  }, [isOpen]);

  const activeTabMeta = useMemo(
    () => settingsTabDefinitions.find((item) => item.id === activeTab) ?? settingsTabDefinitions[0],
    [activeTab]
  );

  const groupedTabs = useMemo(
    () =>
      settingsTabGroups.map((group) => ({
        ...group,
        tabs: settingsTabDefinitions.filter((item) => item.group === group.id),
      })),
    []
  );

  const handleSave = async () => {
    if (!canEditGlobal) {
      addToast('需要管理员权限才能修改全局设置', 'error');
      return;
    }

    setLoading(true);
    try {
      await settingsApi.updateAdvancedConfig(config);
      addToast('设置已保存', 'success');
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const renderAdvancedContent = () => (
    <NovelDialogStack>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <div className="space-y-4">
          <NovelDialogSection
            eyebrow="Feature Switches"
            title="功能开关"
          >
            <NovelDialogSurface>
              <label className="flex cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  className="mt-1 rounded border-book-border text-book-primary focus:ring-book-primary"
                  checked={config.coding_project_enabled}
                  onChange={(e) => setConfig({ ...config, coding_project_enabled: e.target.checked })}
                />
                <div>
                  <div className="font-semibold text-book-text-main">启用编程项目功能</div>
                  <div className="mt-1 text-sm leading-relaxed text-book-text-sub">
                    关闭后首页将隐藏 Prompt 工程相关入口，聚焦小说工作流。
                  </div>
                </div>
              </label>
            </NovelDialogSurface>
          </NovelDialogSection>

          <NovelDialogSection
            eyebrow="Generation"
            title="生成配置"
          >
            <div className="grid gap-4 md:grid-cols-2">
              <BookInput
                label="章节候选版本数量"
                type="number"
                min={1}
                max={5}
                value={config.writer_chapter_version_count}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    writer_chapter_version_count: parseInt(e.target.value, 10) || 1,
                  })
                }
              />

              <NovelDialogSurface>
                <label className="flex cursor-pointer items-center gap-3">
                  <input
                    type="checkbox"
                    className="rounded border-book-border text-book-primary focus:ring-book-primary"
                    checked={config.writer_parallel_generation}
                    onChange={(e) => setConfig({ ...config, writer_parallel_generation: e.target.checked })}
                  />
                  <div>
                    <div className="font-semibold text-book-text-main">启用并行生成</div>
                    <div className="mt-1 text-sm text-book-text-sub">允许后台并发推进章节生成。</div>
                  </div>
                </label>
              </NovelDialogSurface>

              <BookInput
                label="长篇分部阈值（章）"
                type="number"
                value={config.part_outline_threshold}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    part_outline_threshold: parseInt(e.target.value, 10) || 50,
                  })
                }
              />

              <BookInput
                label="Agent 上下文上限（字符）"
                type="number"
                step={1000}
                value={config.agent_context_max_chars}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    agent_context_max_chars: parseInt(e.target.value, 10) || 50000,
                  })
                }
              />
            </div>
          </NovelDialogSection>
        </div>

        <div className="space-y-4">
          <NovelDialogSection
            eyebrow="Auth"
            title="账号与权限"
          >
            <div className="space-y-4">
              <NovelDialogSurface>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="story-pill">{authEnabled ? '登录模式' : '单用户模式'}</span>
                  <span className="story-pill">{canEditGlobal ? '可写全局策略' : '只读全局策略'}</span>
                </div>

                <div className="mt-4 space-y-2 text-sm text-book-text-sub">
                  {authEnabled ? (
                    <>
                      <div>
                        当前账号：
                        <span className="ml-2 font-mono text-book-text-main">{user?.username || '未知'}</span>
                      </div>
                      <div>内置管理员账号为 `desktop_user`，可在后台统一重置密码。</div>
                    </>
                  ) : (
                    <div>当前处于单用户模式，无需登录，部署期权限由服务端配置决定。</div>
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
                        }
                      }}
                    >
                      退出登录
                    </BookButton>
                  ) : null}
                </div>
              </NovelDialogSurface>

              {authEnabled ? (
                <NovelDialogSurface>
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
                    />
                    <BookInput
                      label="新密码"
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      autoComplete="new-password"
                    />
                  </div>

                  <div className="mt-4 flex justify-end">
                    <BookButton
                      variant="secondary"
                      size="sm"
                      onClick={async () => {
                        if (!oldPassword || !newPassword) {
                          addToast('请输入旧密码和新密码', 'error');
                          return;
                        }

                        try {
                          await changePassword(oldPassword, newPassword);
                          setOldPassword('');
                          setNewPassword('');
                          addToast('密码已更新', 'success');
                        } catch (error) {
                          console.error(error);
                        }
                      }}
                    >
                      修改密码
                    </BookButton>
                  </div>
                </NovelDialogSurface>
              ) : null}
            </div>
          </NovelDialogSection>
        </div>
      </div>

      <div className="flex justify-end pt-2">
        <BookButton variant="primary" onClick={handleSave} disabled={loading}>
          {loading ? '保存中…' : '保存高级配置'}
        </BookButton>
      </div>
    </NovelDialogStack>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="全局设置"
      maxWidthClassName="max-w-5xl"
      className="max-h-[85vh]"
      bodyClassName="flex min-h-0 flex-1 overflow-hidden px-5 py-5 sm:px-7 sm:py-6"
      footer={
        <BookButton variant="ghost" onClick={onClose}>
          关闭
        </BookButton>
      }
    >
      <div className="flex h-full min-h-0 flex-col gap-5">
        <NovelDialogSurface className="shrink-0 lg:hidden">
          <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
            {settingsTabDefinitions.map((tab) => {
              const Icon = tab.icon;
              const isActive = tab.id === activeTab;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`inline-flex shrink-0 items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition-all ${
                    isActive
                      ? 'border-book-primary/35 bg-book-primary text-white shadow-lg'
                      : 'border-book-border/50 bg-book-bg-paper/76 text-book-text-sub hover:border-book-primary/20 hover:text-book-text-main'
                  }`}
                >
                  <Icon size={14} />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </NovelDialogSurface>

        <div className="min-h-0 flex-1 lg:grid lg:grid-cols-[240px_minmax(0,1fr)] lg:gap-5">
          <aside className="hidden min-h-0 overflow-y-auto pr-1 custom-scrollbar lg:block">
            <nav className="space-y-4">
              {groupedTabs.map((group) => {
                const GroupIcon = group.icon;
                return (
                  <div key={group.id} className="space-y-1">
                    <div className="flex items-center gap-2 px-2 py-1.5 text-xs font-bold uppercase tracking-widest text-book-text-muted">
                      <GroupIcon size={14} />
                      {group.label}
                    </div>

                    <div className="space-y-0.5">
                      {group.tabs.map((tab) => {
                        const Icon = tab.icon;
                        const isActive = tab.id === activeTab;
                        return (
                          <button
                            key={tab.id}
                            type="button"
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm font-semibold transition-all ${
                              isActive
                                ? 'bg-book-primary/10 text-book-primary'
                                : 'text-book-text-sub hover:bg-book-bg hover:text-book-text-main'
                            }`}
                          >
                            <Icon size={16} className={isActive ? 'text-book-primary' : 'text-book-text-muted'} />
                            {tab.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </nav>
          </aside>

          <div className="min-h-0 pt-5 lg:pt-0">
            <NovelDialogSection
              eyebrow={activeTabMeta.label}
              title={activeTabMeta.label}
              className="flex h-full min-h-0 min-w-0 flex-col"
              contentClassName="min-h-0 flex-1 overflow-y-auto pr-1 custom-scrollbar"
            >
              {activeTab === 'advanced' ? (
                renderAdvancedContent()
              ) : (
                <Suspense fallback={<SettingsTabLoading />}>
                  {activeTab === 'llm' ? <LLMConfigsTab /> : null}
                  {activeTab === 'embedding' ? <EmbeddingConfigsTab /> : null}
                  {activeTab === 'queue' ? <QueueTab /> : null}
                  {activeTab === 'image' ? <ImageConfigsTab /> : null}
                  {activeTab === 'theme' ? <ThemeTab /> : null}
                  {activeTab === 'prompts' ? <PromptsTab /> : null}
                  {activeTab === 'maxTokens' ? <MaxTokensTab /> : null}
                  {activeTab === 'temperature' ? <TemperatureTab /> : null}
                  {activeTab === 'io' ? <ImportExportTab /> : null}
                </Suspense>
              )}
            </NovelDialogSection>
          </div>
        </div>
      </div>
    </Modal>
  );
};
