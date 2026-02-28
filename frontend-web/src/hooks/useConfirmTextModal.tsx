import React, { useCallback, useRef, useState } from 'react';
import { Modal } from '../components/ui/Modal';
import { BookButton } from '../components/ui/BookButton';
import { BookTextarea } from '../components/ui/BookInput';
import type { ToastType } from '../components/feedback/Toast';

type AddToast = (message: unknown, type: ToastType) => void;

export type OpenConfirmTextModalOptions = {
  title?: string;
  hint?: string;
  initialValue?: string;
  label?: string;
  rows?: number;
  placeholder?: string;
  onConfirm: (text?: string) => void | Promise<void>;
};

export type UseConfirmTextModalOptions = {
  addToast: AddToast;
  defaultTitle: string;
  defaultLabel: string;
  defaultRows?: number;
  defaultPlaceholder?: string;
  maxWidthClassName?: string;
  errorToastMessage?: unknown;
};

export const useConfirmTextModal = (opts: UseConfirmTextModalOptions) => {
  const {
    addToast,
    defaultTitle,
    defaultLabel,
    defaultRows = 6,
    defaultPlaceholder = '',
    maxWidthClassName = 'max-w-2xl',
    errorToastMessage = '操作失败',
  } = opts;

  const pendingActionRef = useRef<OpenConfirmTextModalOptions['onConfirm'] | null>(null);

  const [isOpen, setIsOpen] = useState(false);
  const [title, setTitle] = useState(defaultTitle);
  const [hint, setHint] = useState<string | null>(null);
  const [value, setValue] = useState('');
  const [label, setLabel] = useState(defaultLabel);
  const [rows, setRows] = useState(defaultRows);
  const [placeholder, setPlaceholder] = useState(defaultPlaceholder);

  const close = useCallback(() => {
    pendingActionRef.current = null;
    setIsOpen(false);
  }, []);

  const open = useCallback(
    (openOpts: OpenConfirmTextModalOptions) => {
      setTitle(openOpts.title || defaultTitle);
      setHint(openOpts.hint || null);
      setValue(openOpts.initialValue || '');
      setLabel(openOpts.label || defaultLabel);

      if (typeof openOpts.rows === 'number' && Number.isFinite(openOpts.rows) && openOpts.rows > 0) {
        setRows(Math.max(1, Math.round(openOpts.rows)));
      } else {
        setRows(defaultRows);
      }

      if (openOpts.placeholder !== undefined) {
        setPlaceholder(openOpts.placeholder);
      } else {
        setPlaceholder(defaultPlaceholder);
      }

      pendingActionRef.current = openOpts.onConfirm;
      setIsOpen(true);
    },
    [defaultLabel, defaultPlaceholder, defaultRows, defaultTitle],
  );

  const confirm = useCallback(async () => {
    const fn = pendingActionRef.current;
    pendingActionRef.current = null;
    setIsOpen(false);

    const text = (value || '').trim();
    try {
      await fn?.(text ? text : undefined);
    } catch (e) {
      console.error(e);
      addToast(errorToastMessage, 'error');
    }
  }, [addToast, errorToastMessage, value]);

  const modal = (
    <Modal
      isOpen={isOpen}
      onClose={close}
      title={title}
      maxWidthClassName={maxWidthClassName}
      footer={
        <div className="flex justify-end gap-2">
          <BookButton variant="ghost" onClick={close}>
            取消
          </BookButton>
          <BookButton variant="primary" onClick={confirm}>
            确定
          </BookButton>
        </div>
      }
    >
      <div className="space-y-4">
        {hint ? (
          <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
            {hint}
          </div>
        ) : null}
        <BookTextarea
          label={label}
          rows={rows}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
        />
      </div>
    </Modal>
  );

  return { open, modal };
};

