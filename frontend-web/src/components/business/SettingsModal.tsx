import React, { Suspense, lazy, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Modal } from '../ui/Modal';
import { BookInput } from '../ui/BookInput';
import { BookButton } from '../ui/BookButton';
import { settingsApi, AdvancedConfig } from '../../api/settings';
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
  <div className="flex items-center justify-center py-10 text-sm text-book-text-muted">面板加载中…</div>
);


interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<
    'advanced' | 'llm' | 'embedding' | 'image' | 'theme' | 'queue' | 'prompts' | 'maxTokens' | 'temperature' | 'io'
  >('advanced');
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
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');

  useEffect(() => {
    if (isOpen) {
      setActiveTab('advanced');
      const fetchConfig = async () => {
        try {
          const data = await settingsApi.getAdvancedConfig();
          setConfig(data);
        } catch (e) {
          console.error(e);
        }
      };
      fetchConfig();
    }
  }, [isOpen]);

  const handleSave = async () => {
    if (authEnabled && !isAdmin) {
      addToast('需要管理员权限才能修改全局设置', 'error');
      return;
    }
    setLoading(true);
    try {
      await settingsApi.updateAdvancedConfig(config);
      addToast('设置已保存', 'success');
      onClose();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="全局设置"
      maxWidthClassName="max-w-6xl"
      className="max-h-[90vh]"
      footer={
        <div className="flex justify-end gap-2">
          <BookButton variant="ghost" onClick={onClose}>关闭</BookButton>
          {activeTab === 'advanced' && (
            <BookButton variant="primary" onClick={handleSave} disabled={loading}>
              {loading ? '保存中...' : '保存高级配置'}
            </BookButton>
          )}
        </div>
      }
    >
      <div className="grid grid-cols-[220px_1fr] gap-4 h-[75vh]">
        <div className="space-y-2 overflow-y-auto custom-scrollbar pr-1">
          <button
            onClick={() => setActiveTab('advanced')}
            className={`w-full text-left px-3 py-2 rounded-lg border transition-all ${
              activeTab === 'advanced'
                ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
                : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
            }`}
          >
            <div className="text-sm font-bold">高级</div>
            <div className="text-[11px] text-book-text-muted mt-1">生成参数 / Agent</div>
          </button>

          <button
            onClick={() => setActiveTab('llm')}
            className={`w-full text-left px-3 py-2 rounded-lg border transition-all ${
              activeTab === 'llm'
                ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
                : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
            }`}
          >
            <div className="text-sm font-bold">LLM</div>
            <div className="text-[11px] text-book-text-muted mt-1">模型 / Key / 测试</div>
          </button>

          <button
            onClick={() => setActiveTab('embedding')}
            className={`w-full text-left px-3 py-2 rounded-lg border transition-all ${
              activeTab === 'embedding'
                ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
                : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
            }`}
          >
            <div className="text-sm font-bold">嵌入</div>
            <div className="text-[11px] text-book-text-muted mt-1">RAG 向量化</div>
          </button>

          <button
            onClick={() => setActiveTab('queue')}
            className={`w-full text-left px-3 py-2 rounded-lg border transition-all ${
              activeTab === 'queue'
                ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
                : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
            }`}
          >
            <div className="text-sm font-bold">队列</div>
            <div className="text-[11px] text-book-text-muted mt-1">并发 / 状态</div>
          </button>

          <button
            onClick={() => setActiveTab('image')}
            className={`w-full text-left px-3 py-2 rounded-lg border transition-all ${
              activeTab === 'image'
                ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
                : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
            }`}
          >
            <div className="text-sm font-bold">图片</div>
            <div className="text-[11px] text-book-text-muted mt-1">生成配置 / 测试</div>
          </button>

          <button
            onClick={() => setActiveTab('theme')}
            className={`w-full text-left px-3 py-2 rounded-lg border transition-all ${
              activeTab === 'theme'
                ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
                : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
            }`}
          >
            <div className="text-sm font-bold">主题</div>
            <div className="text-[11px] text-book-text-muted mt-1">切换 / 同步</div>
          </button>

          <button
            onClick={() => setActiveTab('prompts')}
            className={`w-full text-left px-3 py-2 rounded-lg border transition-all ${
              activeTab === 'prompts'
                ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
                : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
            }`}
          >
            <div className="text-sm font-bold">提示词</div>
            <div className="text-[11px] text-book-text-muted mt-1">查看 / 编辑 / 恢复</div>
          </button>

          <button
            onClick={() => setActiveTab('maxTokens')}
            className={`w-full text-left px-3 py-2 rounded-lg border transition-all ${
              activeTab === 'maxTokens'
                ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
                : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
            }`}
          >
            <div className="text-sm font-bold">Max Tokens</div>
            <div className="text-[11px] text-book-text-muted mt-1">上下限配置</div>
          </button>

          <button
            onClick={() => setActiveTab('temperature')}
            className={`w-full text-left px-3 py-2 rounded-lg border transition-all ${
              activeTab === 'temperature'
                ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
                : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
            }`}
          >
            <div className="text-sm font-bold">Temperature</div>
            <div className="text-[11px] text-book-text-muted mt-1">采样温度</div>
          </button>

          <button
            onClick={() => setActiveTab('io')}
            className={`w-full text-left px-3 py-2 rounded-lg border transition-all ${
              activeTab === 'io'
                ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
                : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
            }`}
          >
            <div className="text-sm font-bold">导入导出</div>
            <div className="text-[11px] text-book-text-muted mt-1">备份 / 迁移</div>
          </button>
        </div>

        <div className="min-w-0 overflow-auto custom-scrollbar pr-1">
          {activeTab === 'advanced' && (
            <div className="space-y-6">
              <div className="space-y-4">
                <h4 className="font-bold text-sm text-book-text-main border-b border-book-border pb-2">功能开关</h4>

                <div className="flex items-center">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      className="rounded border-book-border text-book-primary focus:ring-book-primary"
                      checked={config.coding_project_enabled}
                      onChange={(e) => setConfig({...config, coding_project_enabled: e.target.checked})}
                    />
                    <span className="text-sm font-bold text-book-text-sub">启用编程项目(Prompt工程)功能</span>
                  </label>
                  <span className="ml-3 text-xs text-book-text-muted">关闭后首页将隐藏编程项目相关入口</span>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="font-bold text-sm text-book-text-main border-b border-book-border pb-2">账号</h4>

                <div className="space-y-3">
                  {authEnabled ? (
                    <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 space-y-2">
                      <div>当前账号：<span className="font-mono">{user?.username || '未知'}</span></div>
                      <div className="text-[11px] text-book-text-muted">
                        内置管理员账号：<span className="font-mono">desktop_user</span>（密码可在管理后台重置/在此处修改）
                      </div>
                      <div className="flex gap-2 justify-end">
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
                        <BookButton
                          variant="ghost"
                          size="sm"
                          onClick={async () => {
                            try {
                              await logout();
                              addToast('已退出登录', 'success');
                              onClose();
                            } catch (e) {
                              console.error(e);
                            }
                          }}
                        >
                          退出登录
                        </BookButton>
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 space-y-2">
                      <div>当前处于单用户模式（无需登录）。登录是否启用由部署配置决定（不在此处修改）。</div>
                      {isAdmin ? (
                        <div className="flex justify-end">
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
                        </div>
                      ) : null}
                    </div>
                  )}

                  {authEnabled ? (
                    <div className="grid grid-cols-2 gap-3">
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
                      <div className="col-span-2 flex justify-end">
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
                            } catch (e) {
                              console.error(e);
                            }
                          }}
                        >
                          修改密码
                        </BookButton>
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="font-bold text-sm text-book-text-main border-b border-book-border pb-2">生成配置</h4>
                
                <div className="grid grid-cols-2 gap-4">
                  <BookInput 
                    label="章节候选版本数量"
                    type="number"
                    min={1}
                    max={5}
                    value={config.writer_chapter_version_count}
                    onChange={(e) => setConfig({...config, writer_chapter_version_count: parseInt(e.target.value) || 1})}
                  />
                  
                  <div className="flex items-center pt-6">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input 
                        type="checkbox"
                        className="rounded border-book-border text-book-primary focus:ring-book-primary"
                        checked={config.writer_parallel_generation}
                        onChange={(e) => setConfig({...config, writer_parallel_generation: e.target.checked})}
                      />
                      <span className="text-sm font-bold text-book-text-sub">启用并行生成</span>
                    </label>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <BookInput 
                    label="长篇分部阈值 (章)"
                    type="number"
                    value={config.part_outline_threshold}
                    onChange={(e) => setConfig({...config, part_outline_threshold: parseInt(e.target.value) || 50})}
                  />
                  <BookInput 
                    label="Agent上下文上限 (字符)"
                    type="number"
                    step={1000}
                    value={config.agent_context_max_chars}
                    onChange={(e) => setConfig({...config, agent_context_max_chars: parseInt(e.target.value) || 50000})}
                  />
                </div>
              </div>

              <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50">
                提示：LLM/嵌入/提示词等配置已支持在本弹窗中管理，无需手动编辑 config.json。
              </div>
            </div>
          )}

          <Suspense fallback={<SettingsTabLoading />}>
            {activeTab === 'llm' && <LLMConfigsTab />}
            {activeTab === 'embedding' && <EmbeddingConfigsTab />}
            {activeTab === 'queue' && <QueueTab />}
            {activeTab === 'image' && <ImageConfigsTab />}
            {activeTab === 'theme' && <ThemeTab />}
            {activeTab === 'prompts' && <PromptsTab />}
            {activeTab === 'maxTokens' && <MaxTokensTab />}
            {activeTab === 'temperature' && <TemperatureTab />}
            {activeTab === 'io' && <ImportExportTab />}
          </Suspense>
        </div>
      </div>
    </Modal>
  );
};
