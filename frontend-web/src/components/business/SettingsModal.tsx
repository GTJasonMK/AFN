import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import {
  Bot,
  Boxes,
  BrainCircuit,
  Database,
  Gauge,
  Image,
  Palette,
  ScrollText,
  Settings2,
  Sparkles,
  Thermometer,
  Upload,
  Workflow,
} from 'lucide-react';
import { Modal } from '../ui/Modal';
import { BookCard } from '../ui/BookCard';
import {
  NovelDialogSurface,
} from './novel/NovelDialogPrimitives';
import { AdvancedTab } from './settings/AdvancedTab';
import { SettingsModalFooterProvider } from './settings/components/SettingsModalFooterContext';

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
  const [tabFooter, setTabFooter] = useState<React.ReactNode | null>(null);
  const reservedFooter = useMemo(
    () => tabFooter ?? <span className="block h-9 w-px opacity-0" aria-hidden="true" />,
    [tabFooter],
  );

  useEffect(() => {
    if (!isOpen) return;

    setActiveTab('advanced');
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      setTabFooter(null);
      return;
    }
    setTabFooter(null);
  }, [activeTab, isOpen]);

  const groupedTabs = useMemo(
    () =>
      settingsTabGroups.map((group) => ({
        ...group,
        tabs: settingsTabDefinitions.filter((item) => item.group === group.id),
      })),
    []
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="全局设置"
      maxWidthClassName="max-w-5xl"
      className="!h-[calc(100dvh-0.5rem)] !min-h-[calc(100dvh-0.5rem)] !max-h-[calc(100dvh-0.5rem)] sm:!h-[min(100dvh-2rem,52rem)] sm:!min-h-[min(100dvh-2rem,52rem)] sm:!max-h-[min(100dvh-2rem,52rem)]"
      bodyClassName="flex min-h-0 flex-1 flex-col overflow-hidden px-5 py-5 sm:px-7 sm:py-6"
      footer={reservedFooter}
    >
      <SettingsModalFooterProvider setFooter={setTabFooter}>
        <div className="flex h-full min-h-0 flex-col gap-5">
          <NovelDialogSurface className="shrink-0 lg:hidden">
            <div className="flex gap-2 overflow-x-auto pb-1 custom-scrollbar">
              {settingsTabDefinitions.map((tab) => {
                const Icon = tab.icon;
                const isActive = tab.id === activeTab;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => {
                      setTabFooter(null);
                      setActiveTab(tab.id);
                    }}
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

          <div className="min-h-0 flex flex-1 flex-col lg:grid lg:grid-cols-[240px_minmax(0,1fr)] lg:grid-rows-[minmax(0,1fr)] lg:gap-5">
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
                              onClick={() => {
                                setTabFooter(null);
                                setActiveTab(tab.id);
                              }}
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

            <div
              className="flex min-h-0 flex-1 flex-col overflow-hidden pt-5 lg:pt-0"
            >
              <BookCard
                variant="glass"
                className="flex min-h-0 flex-1 flex-col p-0"
                contentClassName="h-full min-h-0"
              >
                <div
                  data-settings-scroll-body="1"
                  className="h-full min-h-0 overflow-y-auto overflow-x-hidden p-4 pr-1 custom-scrollbar sm:p-5"
                >
                  <Suspense fallback={<SettingsTabLoading />}>
                    {activeTab === 'advanced' ? <AdvancedTab onClose={onClose} /> : null}
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
                </div>
              </BookCard>
            </div>
          </div>
        </div>
      </SettingsModalFooterProvider>
    </Modal>
  );
};
