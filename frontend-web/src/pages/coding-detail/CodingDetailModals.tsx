import React from 'react';
import { CodingFilePriority, CodingModule, CodingSystem } from '../../api/coding';
import { Modal } from '../../components/ui/Modal';
import { BookButton } from '../../components/ui/BookButton';
import { BookInput, BookTextarea } from '../../components/ui/BookInput';
import {
  DirectoryInfoFormState,
  FileInfoFormState,
  ModuleFormState,
  SystemFormState,
} from './shared';

type PreferenceModalConfig = {
  isOpen: boolean;
  title: string;
  hint: string | null;
  value: string;
  onChange: (value: string) => void;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
};

type DirectoryInfoModalConfig = {
  isOpen: boolean;
  saving: boolean;
  selectedDirectory: any;
  form: DirectoryInfoFormState;
  onChange: (next: DirectoryInfoFormState) => void;
  onClose: () => void;
  onSave: () => void | Promise<void>;
};

type FileInfoModalConfig = {
  isOpen: boolean;
  saving: boolean;
  currentFile: any;
  form: FileInfoFormState;
  onChange: (next: FileInfoFormState) => void;
  onClose: () => void;
  onSave: () => void | Promise<void>;
};

type SystemModalConfig = {
  isOpen: boolean;
  saving: boolean;
  editingSystem: CodingSystem | null;
  form: SystemFormState;
  onChange: (next: SystemFormState) => void;
  onClose: () => void;
  onSave: () => void | Promise<void>;
};

type ModuleModalConfig = {
  isOpen: boolean;
  saving: boolean;
  editingModule: CodingModule | null;
  sortedSystemNumbers: number[];
  form: ModuleFormState;
  onChange: (next: ModuleFormState) => void;
  onClose: () => void;
  onSave: () => void | Promise<void>;
};

type CodingDetailModalsProps = {
  preferenceModal: PreferenceModalConfig;
  directoryInfoModal: DirectoryInfoModalConfig;
  fileInfoModal: FileInfoModalConfig;
  systemModal: SystemModalConfig;
  moduleModal: ModuleModalConfig;
};

export const CodingDetailModals: React.FC<CodingDetailModalsProps> = ({
  preferenceModal,
  directoryInfoModal,
  fileInfoModal,
  systemModal,
  moduleModal,
}) => {
  return (
    <>
      <Modal
        isOpen={preferenceModal.isOpen}
        onClose={preferenceModal.onClose}
        title={preferenceModal.title}
        maxWidthClassName="max-w-2xl"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={preferenceModal.onClose}>
              取消
            </BookButton>
            <BookButton variant="primary" onClick={preferenceModal.onConfirm}>
              确定
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          {preferenceModal.hint ? (
            <div className="rounded-lg border border-book-border/50 bg-book-bg p-3 text-xs leading-relaxed text-book-text-muted">
              {preferenceModal.hint}
            </div>
          ) : null}
          <BookTextarea
            label="偏好指导（可选）"
            rows={6}
            value={preferenceModal.value}
            onChange={(event) => preferenceModal.onChange(event.target.value)}
            placeholder="例如：优先领域层/应用层分层；命名用驼峰；尽量少引入新依赖…"
          />
        </div>
      </Modal>

      <Modal
        isOpen={directoryInfoModal.isOpen}
        onClose={directoryInfoModal.onClose}
        title="编辑目录信息"
        maxWidthClassName="max-w-2xl"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton
              variant="ghost"
              onClick={directoryInfoModal.onClose}
              disabled={directoryInfoModal.saving}
            >
              取消
            </BookButton>
            <BookButton
              variant="primary"
              onClick={directoryInfoModal.onSave}
              disabled={directoryInfoModal.saving}
            >
              {directoryInfoModal.saving ? '保存中…' : '保存'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="break-all text-xs text-book-text-muted">
            {directoryInfoModal.selectedDirectory?.path || directoryInfoModal.selectedDirectory?.name || ''}
          </div>
          <BookTextarea
            label="描述"
            rows={6}
            value={directoryInfoModal.form.description}
            onChange={(event) => directoryInfoModal.onChange({ description: event.target.value })}
            placeholder="例如：该目录用于…"
          />
        </div>
      </Modal>

      <Modal
        isOpen={fileInfoModal.isOpen}
        onClose={fileInfoModal.onClose}
        title="编辑文件信息"
        maxWidthClassName="max-w-2xl"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={fileInfoModal.onClose} disabled={fileInfoModal.saving}>
              取消
            </BookButton>
            <BookButton variant="primary" onClick={fileInfoModal.onSave} disabled={fileInfoModal.saving}>
              {fileInfoModal.saving ? '保存中…' : '保存'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="break-all text-xs text-book-text-muted">
            {fileInfoModal.currentFile?.file_path || fileInfoModal.currentFile?.filename || ''}
          </div>
          <BookTextarea
            label="描述"
            rows={4}
            value={fileInfoModal.form.description}
            onChange={(event) =>
              fileInfoModal.onChange({ ...fileInfoModal.form, description: event.target.value })
            }
            placeholder="例如：该文件负责…"
          />
          <BookTextarea
            label="用途"
            rows={4}
            value={fileInfoModal.form.purpose}
            onChange={(event) => fileInfoModal.onChange({ ...fileInfoModal.form, purpose: event.target.value })}
            placeholder="例如：提供…接口/实现…逻辑"
          />
          <label className="text-xs font-bold text-book-text-sub">
            优先级
            <select
              className="book-control book-select mt-1 w-full rounded-lg border px-3 py-2 text-sm text-book-text-main"
              value={fileInfoModal.form.priority}
              onChange={(event) =>
                fileInfoModal.onChange({
                  ...fileInfoModal.form,
                  priority: event.target.value as CodingFilePriority,
                })
              }
            >
              <option value="high">高</option>
              <option value="medium">中</option>
              <option value="low">低</option>
            </select>
          </label>
        </div>
      </Modal>

      <Modal
        isOpen={systemModal.isOpen}
        onClose={systemModal.onClose}
        title={systemModal.editingSystem ? `编辑系统 #${systemModal.editingSystem.system_number}` : '新增系统'}
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={systemModal.onClose} disabled={systemModal.saving}>
              取消
            </BookButton>
            <BookButton variant="primary" onClick={systemModal.onSave} disabled={systemModal.saving}>
              {systemModal.saving ? '保存中…' : '保存'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <BookInput
            label="系统名称"
            value={systemModal.form.name}
            onChange={(event) => systemModal.onChange({ ...systemModal.form, name: event.target.value })}
          />
          <BookTextarea
            label="系统描述"
            rows={3}
            value={systemModal.form.description}
            onChange={(event) => systemModal.onChange({ ...systemModal.form, description: event.target.value })}
          />
          <BookTextarea
            label="系统职责（每行一条）"
            rows={4}
            value={systemModal.form.responsibilitiesText}
            onChange={(event) =>
              systemModal.onChange({ ...systemModal.form, responsibilitiesText: event.target.value })
            }
          />
          <BookTextarea
            label="技术要求"
            rows={4}
            value={systemModal.form.techRequirements}
            onChange={(event) =>
              systemModal.onChange({ ...systemModal.form, techRequirements: event.target.value })
            }
          />
        </div>
      </Modal>

      <Modal
        isOpen={moduleModal.isOpen}
        onClose={moduleModal.onClose}
        title={moduleModal.editingModule ? `编辑模块 #${moduleModal.editingModule.module_number}` : '新增模块'}
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={moduleModal.onClose} disabled={moduleModal.saving}>
              取消
            </BookButton>
            <BookButton variant="primary" onClick={moduleModal.onSave} disabled={moduleModal.saving}>
              {moduleModal.saving ? '保存中…' : '保存'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <label className="text-xs font-bold text-book-text-sub">
            所属系统
            <select
              className="book-control book-select mt-1 w-full rounded-lg border px-3 py-2 text-sm text-book-text-main"
              value={moduleModal.form.systemNumber}
              onChange={(event) =>
                moduleModal.onChange({
                  ...moduleModal.form,
                  systemNumber: event.target.value ? Number(event.target.value) : '',
                })
              }
              disabled={Boolean(moduleModal.editingModule)}
            >
              <option value="">请选择</option>
              {moduleModal.sortedSystemNumbers.map((systemNumber) => (
                <option key={`sys-${systemNumber}`} value={systemNumber}>
                  系统 #{systemNumber}
                </option>
              ))}
            </select>
          </label>

          <BookInput
            label="模块名称"
            value={moduleModal.form.name}
            onChange={(event) => moduleModal.onChange({ ...moduleModal.form, name: event.target.value })}
          />
          <BookInput
            label="模块类型"
            value={moduleModal.form.type}
            onChange={(event) => moduleModal.onChange({ ...moduleModal.form, type: event.target.value })}
          />
          <BookTextarea
            label="模块描述"
            rows={3}
            value={moduleModal.form.description}
            onChange={(event) => moduleModal.onChange({ ...moduleModal.form, description: event.target.value })}
          />
          <BookTextarea
            label="接口说明"
            rows={3}
            value={moduleModal.form.iface}
            onChange={(event) => moduleModal.onChange({ ...moduleModal.form, iface: event.target.value })}
          />
          <BookTextarea
            label="依赖模块（每行一个模块名）"
            rows={4}
            value={moduleModal.form.dependenciesText}
            onChange={(event) =>
              moduleModal.onChange({ ...moduleModal.form, dependenciesText: event.target.value })
            }
          />
        </div>
      </Modal>
    </>
  );
};
