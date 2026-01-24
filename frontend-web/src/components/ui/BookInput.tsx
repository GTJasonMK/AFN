import React, { forwardRef } from 'react';

interface BookInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const BookInput = forwardRef<HTMLInputElement, BookInputProps>(
  ({ className = '', label, error, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-bold text-book-text-sub mb-1.5 ml-1">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`
            w-full px-4 py-2 rounded-lg
            bg-book-bg-paper text-book-text-main
            border border-book-border
            focus:outline-none focus:ring-2 focus:ring-book-primary/20 focus:border-book-primary
            placeholder:text-book-text-muted
            transition-all duration-200
            ${error ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20' : ''}
            ${className}
          `}
          {...props}
        />
        {error && (
          <p className="mt-1 text-xs text-red-500 ml-1">{error}</p>
        )}
      </div>
    );
  }
);

BookInput.displayName = 'BookInput';

interface BookTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const BookTextarea = forwardRef<HTMLTextAreaElement, BookTextareaProps>(
  ({ className = '', label, error, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-bold text-book-text-sub mb-1.5 ml-1">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          className={`
            w-full px-4 py-2 rounded-lg
            bg-book-bg-paper text-book-text-main
            border border-book-border
            focus:outline-none focus:ring-2 focus:ring-book-primary/20 focus:border-book-primary
            placeholder:text-book-text-muted
            transition-all duration-200
            resize-none
            ${error ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20' : ''}
            ${className}
          `}
          {...props}
        />
        {error && (
          <p className="mt-1 text-xs text-red-500 ml-1">{error}</p>
        )}
      </div>
    );
  }
);

BookTextarea.displayName = 'BookTextarea';