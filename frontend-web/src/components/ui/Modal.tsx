import React from 'react';
import { createPortal } from 'react-dom';
import { BookCard } from './BookCard';
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

export const Modal: React.FC<ModalProps> = ({ 
  isOpen, 
  onClose, 
  title, 
  children,
  footer,
  maxWidthClassName = "max-w-lg",
  className = "",
  zIndexClassName = "z-50",
  closeOnBackdrop = true,
  showCloseButton = true,
}) => {
  if (!isOpen) return null;

  const portalContainer =
    typeof document !== 'undefined'
      ? document.getElementById('afn-portal-root') || document.body
      : null;

  if (!portalContainer) return null;

  return createPortal(
    <div
      className={`fixed inset-0 ${zIndexClassName} flex items-center justify-center p-4`}
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/20 backdrop-blur-sm transition-opacity"
        onClick={closeOnBackdrop ? onClose : undefined}
      />

      {/* Modal Content */}
      <BookCard
        className={`relative z-10 w-full ${maxWidthClassName} shadow-2xl animate-in fade-in zoom-in-95 duration-200 ${className}`}
        variant="default"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4 border-b border-book-border/50 pb-3">
          <h3 className="font-serif text-xl font-bold text-book-text-main">
            {title}
          </h3>
          {showCloseButton ? (
            <button
              onClick={onClose}
              className="text-book-text-muted hover:text-book-text-main transition-colors"
            >
              <X size={20} />
            </button>
          ) : null}
        </div>

        <div className="mb-6">
          {children}
        </div>

        {footer && (
          <div className="flex justify-end gap-3 pt-4 border-t border-book-border/50">
            {footer}
          </div>
        )}
      </BookCard>
    </div>,
    portalContainer,
  );
};
