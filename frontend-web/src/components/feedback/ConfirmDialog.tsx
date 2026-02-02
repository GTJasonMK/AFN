import React from 'react';
import { create } from 'zustand';
import { Modal } from '../ui/Modal';
import { BookButton } from '../ui/BookButton';

export type ConfirmDialogType = 'normal' | 'warning' | 'danger';

export interface ConfirmDialogOptions {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  dialogType?: ConfirmDialogType;
}

type InternalConfirmDialog = Required<Omit<ConfirmDialogOptions, 'title'>> & {
  title: string;
  resolve: (confirmed: boolean) => void;
};

interface ConfirmDialogStore {
  current: InternalConfirmDialog | null;
  open: (opts: ConfirmDialogOptions) => Promise<boolean>;
  cancel: () => void;
  confirm: () => void;
}

export const useConfirmDialog = create<ConfirmDialogStore>((set, get) => ({
  current: null,
  open: (opts) => {
    const prev = get().current;
    if (prev) {
      try {
        prev.resolve(false);
      } catch {
        // ignore
      }
    }

    return new Promise<boolean>((resolve) => {
      const title = String(opts.title || '确认');
      const message = String(opts.message || '');
      const confirmText = String(opts.confirmText || '确认');
      const cancelText = String(opts.cancelText || '取消');
      const dialogType: ConfirmDialogType = opts.dialogType || 'normal';
      set({
        current: { title, message, confirmText, cancelText, dialogType, resolve },
      });
    });
  },
  cancel: () => {
    const cur = get().current;
    if (cur) {
      try {
        cur.resolve(false);
      } catch {
        // ignore
      }
    }
    set({ current: null });
  },
  confirm: () => {
    const cur = get().current;
    if (cur) {
      try {
        cur.resolve(true);
      } catch {
        // ignore
      }
    }
    set({ current: null });
  },
}));

/**
 * 全局确认弹窗（Promise 风格）
 *
 * 说明：
 * - 用于替代 `window.confirm()`，统一弹窗样式（对齐桌面端 ConfirmDialog 的“统一主题”体验）。
 * - 对于必须“同步阻塞”的场景（如 popstate/浏览器后退拦截），仍可能需要保留原生 confirm。
 */
export const confirmDialog = (opts: ConfirmDialogOptions): Promise<boolean> => {
  return useConfirmDialog.getState().open(opts);
};

export function ConfirmDialogHost() {
  const current = useConfirmDialog((s) => s.current);
  const cancel = useConfirmDialog((s) => s.cancel);
  const confirm = useConfirmDialog((s) => s.confirm);

  if (!current) return null;

  const confirmVariant: React.ComponentProps<typeof BookButton>['variant'] =
    current.dialogType === 'danger' ? 'danger' : current.dialogType === 'warning' ? 'warning' : 'primary';

  return (
    <Modal
      isOpen
      onClose={cancel}
      title={current.title}
      maxWidthClassName="max-w-xl"
      zIndexClassName="z-[120]"
      closeOnBackdrop={false}
      showCloseButton={false}
      footer={
        <>
          <BookButton variant="ghost" onClick={cancel}>
            {current.cancelText}
          </BookButton>
          <BookButton variant={confirmVariant} onClick={confirm}>
            {current.confirmText}
          </BookButton>
        </>
      }
    >
      <div className="text-sm text-book-text-main whitespace-pre-wrap leading-relaxed">
        {current.message}
      </div>
    </Modal>
  );
}
