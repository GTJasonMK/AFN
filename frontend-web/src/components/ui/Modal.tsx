import React, { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidthClassName?: string;
  className?: string;
  zIndexClassName?: string;
  closeOnBackdrop?: boolean;
  showCloseButton?: boolean;
}

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

const getFocusableElements = (container: HTMLElement | null): HTMLElement[] => {
  if (!container) return [];
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter((item) => {
    if (item.hasAttribute('disabled')) return false;
    if (item.getAttribute('aria-hidden') === 'true') return false;
    return item.getClientRects().length > 0;
  });
};

const focusFirstElement = (container: HTMLElement | null) => {
  const focusable = getFocusableElements(container);
  const target = focusable[0] ?? container;
  target?.focus();
};

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  maxWidthClassName = 'max-w-lg',
  className = '',
  zIndexClassName = 'z-50',
  closeOnBackdrop = true,
  showCloseButton = true,
}) => {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousActiveElementRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen || typeof document === 'undefined') return undefined;

    previousActiveElementRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const raf = window.requestAnimationFrame(() => {
      focusFirstElement(dialogRef.current);
    });

    return () => {
      window.cancelAnimationFrame(raf);
      document.body.style.overflow = previousOverflow;
      const previousActiveElement = previousActiveElementRef.current;
      if (previousActiveElement) {
        window.requestAnimationFrame(() => previousActiveElement.focus());
      }
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return undefined;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== 'Tab') return;

      const focusable = getFocusableElements(dialogRef.current);
      if (focusable.length === 0) {
        event.preventDefault();
        dialogRef.current?.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;

      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const portalContainer =
    typeof document !== 'undefined'
      ? document.getElementById('afn-portal-root') || document.body
      : null;

  if (!portalContainer) return null;

  return createPortal(
    <div
      className={`fixed inset-0 ${zIndexClassName} flex items-end justify-center p-2 sm:items-center sm:p-4`}
    >
      <div
        className="dialog-backdrop absolute inset-0 transition-opacity"
        onClick={closeOnBackdrop ? onClose : undefined}
      />

      <div
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={`dialog-panel dialog-sheet-mobile relative z-10 w-full ${maxWidthClassName} ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="pointer-events-none absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-book-primary/40 to-transparent" />
        <div className="relative z-[1] flex max-h-[inherit] min-h-[inherit] flex-col">
          <div className="flex items-start justify-between gap-4 border-b border-book-border/45 bg-book-bg-paper/86 px-5 py-4 backdrop-blur-xl sm:px-7">
            <div className="min-w-0">
              <div className="eyebrow">Dialog</div>
              <h3 id={titleId} className="mt-3 font-serif text-xl font-bold text-book-text-main sm:text-2xl">
                {title}
              </h3>
            </div>
            {showCloseButton ? (
              <button
                onClick={onClose}
                className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-book-border/50 bg-book-bg-paper/72 text-book-text-muted transition-all duration-300 hover:border-book-primary/30 hover:text-book-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-book-primary/20"
                aria-label="关闭弹窗"
              >
                <X size={18} />
              </button>
            ) : null}
          </div>

          <div className="overflow-y-auto px-5 py-5 sm:px-7 sm:py-6">
            {children}
          </div>

          {footer ? (
            <div className="border-t border-book-border/45 bg-book-bg-paper/72 px-5 py-4 backdrop-blur-xl sm:px-7">
              <div className="flex flex-wrap justify-end gap-3">
                {footer}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>,
    portalContainer,
  );
};
