import React from 'react';
import { BookButton } from '../../../ui/BookButton';
import { Modal } from '../../../ui/Modal';
import {
  NovelDialogIntro,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from '../../novel/NovelDialogPrimitives';

interface SettingsEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  saving: boolean;
  onSave: () => void;
  maxWidthClassName?: string;
  children: React.ReactNode;
}

export const SettingsEditorModal: React.FC<SettingsEditorModalProps> = ({
  isOpen,
  onClose,
  title,
  saving,
  onSave,
  maxWidthClassName,
  children,
}) => {
  const isCreate = title.includes('新增');

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      maxWidthClassName={maxWidthClassName || 'max-w-2xl'}
      footer={
        <div className="flex justify-end gap-2">
          <BookButton variant="ghost" onClick={onClose}>
            取消
          </BookButton>
          <BookButton variant="primary" onClick={onSave} disabled={saving}>
            {saving ? '保存中…' : '保存'}
          </BookButton>
        </div>
      }
    >
      <NovelDialogStack>
        <NovelDialogIntro
          eyebrow="Settings Editor"
          title={title}
          description={
            isCreate
              ? '填写配置项后保存到全局设置中心。保存成功后，这项配置就可以在对应能力面板中被激活或测试。'
              : '修改当前配置项后保存到全局设置中心。涉及密钥字段时，留空通常表示保持后端现有值不变。'
          }
        />

        <NovelDialogSection
          eyebrow="Configuration"
          title="配置表单"
          description="按字段填写当前配置，未明确说明的项目建议保持与服务端 Schema 一致。"
        >
          {children}
        </NovelDialogSection>

        <NovelDialogSurface className="text-xs leading-relaxed text-book-text-muted">
          提示：如果修改内容涉及默认激活配置、测试连通性或主题变量，保存后通常需要回到对应列表页做一次结果确认。
        </NovelDialogSurface>
      </NovelDialogStack>
    </Modal>
  );
};
