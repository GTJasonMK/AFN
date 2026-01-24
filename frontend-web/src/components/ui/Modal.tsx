import React from 'react';
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
}

export const Modal: React.FC<ModalProps> = ({ 
  isOpen, 
  onClose, 
  title, 
  children,
  footer,
  maxWidthClassName = "max-w-lg",
  className = "",
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/20 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />
      
      {/* Modal Content */}
      <BookCard 
        className={`relative z-10 w-full ${maxWidthClassName} shadow-2xl animate-in fade-in zoom-in-95 duration-200 ${className}`}
        variant="default"
      >
        <div className="flex justify-between items-center mb-4 border-b border-book-border/50 pb-3">
          <h3 className="font-serif text-xl font-bold text-book-text-main">
            {title}
          </h3>
          <button 
            onClick={onClose}
            className="text-book-text-muted hover:text-book-text-main transition-colors"
          >
            <X size={20} />
          </button>
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
    </div>
  );
};
