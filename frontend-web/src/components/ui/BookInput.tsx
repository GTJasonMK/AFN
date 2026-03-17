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
          <label className="mb-2 ml-1 block text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`
            book-control w-full rounded-2xl border px-4 py-3
            focus:border-book-primary/45 focus:outline-none focus:ring-2 focus:ring-book-primary/18
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
          <label className="mb-2 ml-1 block text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          className={`
            book-control w-full rounded-[24px] border px-4 py-3
            focus:border-book-primary/45 focus:outline-none focus:ring-2 focus:ring-book-primary/18
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
