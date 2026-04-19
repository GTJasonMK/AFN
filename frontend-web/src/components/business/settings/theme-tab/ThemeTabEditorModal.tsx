import React from 'react';
import type { ThemeConfigUnifiedRead } from '../../../../api/themeConfigs';
import { BookButton } from '../../../ui/BookButton';
import { BookInput, BookTextarea } from '../../../ui/BookInput';
import { Modal } from '../../../ui/Modal';
import {
  NovelDialogIntro,
  NovelDialogMetric,
  NovelDialogMetricGrid,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from '../../novel/NovelDialogPrimitives';

interface ThemeTabEditorModalProps {
  isOpen: boolean;
  editingConfig: ThemeConfigUnifiedRead | null;
  editingLoading: boolean;
  editingSaving: boolean;
  editingName: string;
  editingJson: string;
  editingError: string | null;
  onClose: () => void;
  onSave: () => void;
  onNameChange: (value: string) => void;
  onJsonChange: (value: string) => void;
  onReload: () => void;
  onMigrateToV2: () => void;
}

export const ThemeTabEditorModal: React.FC<ThemeTabEditorModalProps> = ({
  isOpen,
  editingConfig,
  editingLoading,
  editingSaving,
  editingName,
  editingJson,
  editingError,
  onClose,
  onSave,
  onNameChange,
  onJsonChange,
  onReload,
  onMigrateToV2,
}) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={editingConfig ? `编辑主题：${editingConfig.config_name}` : '编辑主题'}
      maxWidthClassName="max-w-4xl"
      footer={
        <div className="flex w-full items-center justify-end gap-2">
          <BookButton variant="ghost" onClick={onClose} disabled={editingSaving}>
            取消
          </BookButton>
          <BookButton
            variant="primary"
            onClick={onSave}
            disabled={editingSaving || editingLoading}
          >
            {editingSaving ? '保存中…' : '保存'}
          </BookButton>
        </div>
      }
    >
      {editingLoading ? (
        <NovelDialogSurface className="text-sm text-book-text-muted">
          加载中…
        </NovelDialogSurface>
      ) : editingConfig ? (
        <NovelDialogStack>
          <NovelDialogIntro
            eyebrow="Theme Editor"
            title={`编辑主题：${editingConfig.config_name}`}
            description="这里直接编辑后端主题配置 JSON。适合在明确理解 Schema 的前提下做精细调整和版本迁移。"
          >
            <div className="flex flex-wrap gap-2">
              <span className="story-pill">
                {editingConfig.parent_mode === 'dark' ? '深色模式' : '亮色模式'}
              </span>
              <span className="story-pill">
                V{editingConfig.config_version || 1}
              </span>
              {editingConfig.is_active ? (
                <span className="story-pill">当前已激活</span>
              ) : null}
            </div>
          </NovelDialogIntro>

          <NovelDialogMetricGrid>
            <NovelDialogMetric
              label="主题模式"
              value={editingConfig.parent_mode === 'dark' ? 'Dark' : 'Light'}
              note="决定这份主题配置作用于亮色还是深色外观。"
            />
            <NovelDialogMetric
              label="配置版本"
              value={`V${editingConfig.config_version || 1}`}
              note={
                Number(editingConfig.config_version || 1) === 1
                  ? '可迁移到组件模式 V2。'
                  : '当前已是 V2 结构。'
              }
            />
          </NovelDialogMetricGrid>

          <NovelDialogSection
            eyebrow="Metadata"
            title="配置元信息"
            description="先确认配置名称、模式和版本，再决定是否需要重新加载或迁移。"
            actions={
              <>
                <BookButton
                  variant="ghost"
                  size="sm"
                  onClick={onReload}
                  disabled={editingSaving}
                >
                  重新加载
                </BookButton>
                {Number(editingConfig.config_version || 1) === 1 ? (
                  <BookButton
                    variant="secondary"
                    size="sm"
                    onClick={onMigrateToV2}
                    disabled={editingSaving}
                    title="桌面端默认使用组件模式（V2）。迁移后可编辑 token/comp/effects。"
                  >
                    迁移到V2
                  </BookButton>
                ) : null}
              </>
            }
          >
            <BookInput
              label="配置名称"
              value={editingName}
              onChange={(event) => onNameChange(event.target.value)}
              disabled={editingSaving}
            />
          </NovelDialogSection>

          {editingError ? (
            <NovelDialogSurface className="border-red-200 bg-red-50/80 text-xs leading-relaxed text-red-600">
              {editingError}
            </NovelDialogSurface>
          ) : null}

          <NovelDialogSection
            eyebrow="JSON"
            title="配置 JSON"
            description="按后端 Schema 字段填写。这里的修改会直接影响 Web 主题变量与组件外观表现。"
          >
            <BookTextarea
              label="配置 JSON（按后端 Schema 字段填写）"
              value={editingJson}
              onChange={(event) => onJsonChange(event.target.value)}
              rows={18}
              className="font-mono text-xs leading-relaxed"
              disabled={editingSaving}
            />
          </NovelDialogSection>

          <NovelDialogSurface className="text-[11px] leading-relaxed text-book-text-muted">
            提示：保存后会更新后端主题配置；如果该配置是当前模式已激活主题，
            WebUI 会立即重新计算并应用 CSS 变量。
          </NovelDialogSurface>
        </NovelDialogStack>
      ) : (
        <NovelDialogSurface className="text-sm text-book-text-muted">
          无法加载该配置
        </NovelDialogSurface>
      )}
    </Modal>
  );
};
