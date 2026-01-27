import React from 'react';
import { BookButton } from '../../../ui/BookButton';
import { Modal } from '../../../ui/Modal';

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
      {children}
    </Modal>
  );
};

