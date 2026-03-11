import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bot,
  BrainCircuit,
  Boxes,
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
  <div className="flex items-center justify-center py-12 text-sm text-book-text-muted">面板加载中…</div>
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
  description: string;
  eyebrow: string;
  icon: React.ElementType;
};

const settingsTabDefinitions: SettingsTabDefinition[] = [
  {
    id: 'advanced',
    group: 'platform',
    label: '高级策略',
    description: '全局开关、Agent 字符预算与账号策略',
    eyebrow: 'Platform',
    icon: Settings2,
  },
  {
    id: 'queue',
    group: 'platform',
    label: '队列编排',
    description: '并发度、排队状态与后台任务节奏',
    eyebrow: 'Queue',
    icon: Workflow,
  },
  {
    id: 'io',
    group: 'platform',
    label: '导入导出',
    description: '备份、迁移、恢复与环境同步',
    eyebrow: 'IO',
    icon: Upload,
  },
  {
    id: 'llm',
    group: 'models',
    label: 'LLM 模型',
    description: '主模型配置、Key 与连通性测试',
    eyebrow: 'LLM',
    icon: Bot,
  },
  {
    id: 'embedding',
    group: 'models',
    label: '嵌入配置',
    description: 'RAG 向量化、召回基础与默认策略',
    eyebrow: 'Vector',
    icon: Database,
  },
  {
    id: 'image',
    group: 'models',
    label: '图片模型',
    description: '绘图提供商、参数与测试面板',
    eyebrow: 'Vision',
    icon: Image,
  },
  {
    id: 'theme',
    group: 'experience',
    label: '主题系统',
    description: '视觉主题、同步行为与配色偏好',
    eyebrow: 'Theme',
    icon: Palette,
  },
  {
    id: 'prompts',
    group: 'experience',
    label: '提示词库',
    description: '查看、编辑、恢复与调优模板',
    eyebrow: 'Prompt',
    icon: ScrollText,
  },
  {
    id: 'maxTokens',
    group: 'experience',
    label: 'Max Tokens',
    description: 'Token 上下限与预算边界',
    eyebrow: 'Budget',
    icon: Gauge,
  },
  {
    id: 'temperature',
    group: 'experience',
    label: 'Temperature',
    description: '采样随机性与文本风格强度',
    eyebrow: 'Sampling',
    icon: Thermometer,
  },
];

const settingsTabGroups: Array<{
  id: SettingsTabGroupId;
  label: string;
  description: string;
  icon: React.ElementType;
}> = [
  {
    id: 'platform',
    label: '平台',
    description: '系统策略、队列调度和数据迁移',
    icon: Boxes,
  },
  {
    id: 'models',
    label: '模型',
    description: 'LLM、嵌入与图像能力总线',
    icon: BrainCircuit,
  },
  {
    id: 'experience',
    label: '体验',
    description: '视觉、提示词与采样体验',
    icon: Sparkles,
  },
];

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SettingsSectionCard: React.FC<{
  title: string;
  description: string;
  children: React.ReactNode;
}> = ({ title, description, children }) => (
  <section className="rounded-[26px] border border-book-border/55 bg-book-bg-paper/76 p-4 shadow-[0_20px_48px_-42px_rgba(31,15,6,0.95)] backdrop-blur-xl sm:p-5">
    <div className="flex flex-col gap-2 border-b border-book-border/45 pb-4">
      <h4 className="font-serif text-xl font-bold text-book-text-main">{title}</h4>
      <p className="text-sm leading-relaxed text-book-text-sub">{description}</p>
    </div>
    <div className="pt-4">{children}</div>
  </section>
);

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

  const activeGroupMeta = useMemo(
    () => settingsTabGroups.find((item) => item.id === activeTabMeta.group) ?? settingsTabGroups[0],
    [activeTabMeta.group]
  );

  const groupedTabs = useMemo(
    () =>
      settingsTabGroups.map((group) => ({
        ...group,
        tabs: settingsTabDefinitions.filter((item) => item.group === group.id),
      })),
    []
  );

  const summaryTiles = useMemo(
    () => [
      {
        label: '账号模式',
        value: authEnabled ? (isAdmin ? '管理员' : '受限账号') : '单用户',
        note: authEnabled ? (user?.username || '未登录') : '本地运行模式',
      },
      {
        label: '章节候选',
        value: `${Math.max(1, Number(config.writer_chapter_version_count) || 1)} 份`,
        note: '每章保留的候选版本数',
      },
      {
        label: 'Agent 上限',
        value: `${Math.round((Number(config.agent_context_max_chars) || 0) / 1000)}k`,
        note: '当前上下文字符预算',
      },
    ],
    [authEnabled, config.agent_context_max_chars, config.writer_chapter_version_count, isAdmin, user?.username]
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
      onClose();
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const renderAdvancedContent = () => (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="metric-tile">
          <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
            并行生成
          </div>
          <div className="mt-3 text-lg font-semibold text-book-text-main">
            {config.writer_parallel_generation ? '已启用' : '串行模式'}
          </div>
          <div className="mt-2 text-sm text-book-text-sub">影响章节生成的并发方式</div>
        </div>
        <div className="metric-tile">
          <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
            长篇分部阈值
          </div>
          <div className="mt-3 text-lg font-semibold text-book-text-main">
            {Number(config.part_outline_threshold) || 0} 章
          </div>
          <div className="mt-2 text-sm text-book-text-sub">超过阈值后自动切入分部结构</div>
        </div>
        <div className="metric-tile">
          <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
            Prompt 工程
          </div>
          <div className="mt-3 text-lg font-semibold text-book-text-main">
            {config.coding_project_enabled ? '已开放' : '已关闭'}
          </div>
          <div className="mt-2 text-sm text-book-text-sub">首页是否显示编程项目入口</div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <div className="space-y-4">
          <SettingsSectionCard
            title="功能开关"
            description="收束入口暴露和生成策略，避免在多个页面分散调整核心行为。"
          >
            <div className="space-y-3">
              <label className="flex cursor-pointer items-start gap-3 rounded-[20px] border border-book-border/45 bg-book-bg/78 px-4 py-3">
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
            </div>
          </SettingsSectionCard>

          <SettingsSectionCard
            title="生成配置"
            description="直接决定章节生成的候选数、并行模式和长篇拆分阈值。"
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

              <label className="flex cursor-pointer items-center gap-3 rounded-[20px] border border-book-border/45 bg-book-bg/78 px-4 py-3">
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
          </SettingsSectionCard>
        </div>

        <div className="space-y-4">
          <SettingsSectionCard
            title="账号与权限"
            description="当前账号状态、密码修改与后台入口统一收束在这里。"
          >
            <div className="space-y-4">
              <div className="rounded-[20px] border border-book-border/45 bg-book-bg/78 p-4">
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
              </div>

              {authEnabled ? (
                <div className="rounded-[20px] border border-book-border/45 bg-book-bg/78 p-4">
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
                </div>
              ) : null}
            </div>
          </SettingsSectionCard>

          <SettingsSectionCard
            title="运行提示"
            description="帮助你快速理解当前设置控制台的边界和使用方式。"
          >
            <div className="space-y-3 text-sm leading-relaxed text-book-text-sub">
              <div className="rounded-[20px] border border-book-border/45 bg-book-bg/78 px-4 py-3">
                LLM、嵌入、图片、提示词和主题均可在本弹窗内管理，无需手动编辑 `config.json`。
              </div>
              <div className="rounded-[20px] border border-book-border/45 bg-book-bg/78 px-4 py-3">
                高级策略页负责平台级参数，其余页签保留各自的懒加载面板与独立保存逻辑。
              </div>
            </div>
          </SettingsSectionCard>
        </div>
      </div>
    </div>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="全局设置"
      maxWidthClassName="max-w-[88rem]"
      className="max-h-[92vh]"
      footer={
        <>
          <BookButton variant="ghost" onClick={onClose}>
            关闭
          </BookButton>
          {activeTab === 'advanced' ? (
            <BookButton variant="primary" onClick={handleSave} disabled={loading}>
              {loading ? '保存中…' : '保存高级配置'}
            </BookButton>
          ) : null}
        </>
      }
    >
      <div className="space-y-5">
        <section className="rounded-[28px] border border-book-border/55 bg-[linear-gradient(145deg,rgba(255,251,240,0.94),rgba(249,245,240,0.88))] p-5 shadow-[0_30px_70px_-56px_rgba(38,18,7,0.98)] backdrop-blur-xl sm:p-6">
          <div className="space-y-5">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div className="space-y-3">
                <div className="eyebrow">System Console</div>
                <div>
                  <h4 className="font-serif text-[clamp(1.8rem,3vw,2.6rem)] font-bold leading-[0.98] tracking-[-0.04em] text-book-text-main">
                    把模型、平台和体验策略收束到一个控制台里。
                  </h4>
                  <p className="mt-3 max-w-2xl text-sm leading-relaxed text-book-text-sub sm:text-base">
                    当前页签聚焦于「{activeGroupMeta.label}」域下的「{activeTabMeta.label}」，避免在多个浮窗中来回寻找配置入口。
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <span className="story-pill">{activeGroupMeta.label}</span>
                  <span className="story-pill">{activeTabMeta.label}</span>
                  <span className="story-pill">{canEditGlobal ? '可写全局策略' : '受限查看模式'}</span>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-3 xl:w-[30rem]">
                {summaryTiles.map((tile) => (
                  <div key={tile.label} className="metric-tile">
                    <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                      {tile.label}
                    </div>
                    <div className="mt-3 text-lg font-semibold text-book-text-main">{tile.value}</div>
                    <div className="mt-2 text-sm text-book-text-sub">{tile.note}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="story-divider" />

            <div className="lg:hidden">
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
                          ? 'border-book-primary/35 bg-book-primary text-white shadow-[0_20px_44px_-28px_rgba(72,36,16,0.9)]'
                          : 'border-book-border/50 bg-book-bg-paper/76 text-book-text-sub hover:border-book-primary/20 hover:text-book-text-main'
                      }`}
                    >
                      <Icon size={14} />
                      {tab.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        <div className="grid gap-5 lg:grid-cols-[290px_minmax(0,1fr)]">
          <aside className="hidden space-y-4 lg:block">
            {groupedTabs.map((group) => {
              const GroupIcon = group.icon;
              return (
                <section
                  key={group.id}
                  className="rounded-[26px] border border-book-border/55 bg-book-bg-paper/74 p-4 shadow-[0_20px_52px_-44px_rgba(33,16,6,0.95)] backdrop-blur-xl"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                        Group
                      </div>
                      <div className="mt-2 font-serif text-2xl font-bold text-book-text-main">{group.label}</div>
                      <p className="mt-2 text-sm leading-relaxed text-book-text-sub">{group.description}</p>
                    </div>
                    <GroupIcon size={18} className="mt-1 text-book-primary" />
                  </div>

                  <div className="mt-4 space-y-2">
                    {group.tabs.map((tab) => {
                      const Icon = tab.icon;
                      const isActive = tab.id === activeTab;
                      return (
                        <button
                          key={tab.id}
                          type="button"
                          onClick={() => setActiveTab(tab.id)}
                          className={`w-full rounded-[20px] border px-4 py-3 text-left transition-all ${
                            isActive
                              ? 'border-book-primary/30 bg-book-primary/10 shadow-[0_18px_40px_-32px_rgba(64,31,14,0.95)]'
                              : 'border-book-border/45 bg-book-bg/68 hover:border-book-primary/20 hover:bg-book-bg-paper'
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <span
                              className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl ${
                                isActive
                                  ? 'bg-book-primary text-white'
                                  : 'bg-book-bg-paper text-book-text-muted'
                              }`}
                            >
                              <Icon size={16} />
                            </span>
                            <span className="min-w-0">
                              <span className="text-[0.68rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                                {tab.eyebrow}
                              </span>
                              <span className="mt-1 block font-semibold text-book-text-main">{tab.label}</span>
                              <span className="mt-1 block text-sm leading-relaxed text-book-text-sub">
                                {tab.description}
                              </span>
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </section>
              );
            })}
          </aside>

          <section className="min-w-0 rounded-[30px] border border-book-border/58 bg-book-bg-paper/80 shadow-[0_32px_76px_-54px_rgba(35,18,7,0.98)] backdrop-blur-xl">
            <div className="border-b border-book-border/45 px-5 py-5 sm:px-6">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                    {activeTabMeta.eyebrow}
                  </div>
                  <h4 className="mt-2 font-serif text-[clamp(1.6rem,2.6vw,2.4rem)] font-bold leading-none tracking-[-0.04em] text-book-text-main">
                    {activeTabMeta.label}
                  </h4>
                  <p className="mt-3 max-w-2xl text-sm leading-relaxed text-book-text-sub">
                    {activeTabMeta.description}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <span className="story-pill">分组：{activeGroupMeta.label}</span>
                  <span className="story-pill">{canEditGlobal ? '可写' : '只读'}</span>
                </div>
              </div>
            </div>

            <div className="p-5 sm:p-6">
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
            </div>
          </section>
        </div>
      </div>
    </Modal>
  );
};
