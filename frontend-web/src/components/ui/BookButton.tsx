import React from 'react';

interface BookButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'warning' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}

export const BookButton: React.FC<BookButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  type,
  ...props
}) => {
  const base =
    'relative inline-flex items-center justify-center gap-2 rounded-full border font-sans font-semibold tracking-[0.02em] transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-book-primary/25 focus-visible:ring-offset-2 focus-visible:ring-offset-book-bg disabled:pointer-events-none disabled:translate-y-0 disabled:opacity-50 disabled:shadow-none';

  const variants = {
    primary:
      'border-book-primary bg-book-primary text-white shadow-[0_20px_40px_-24px_rgba(87,44,17,0.96)] hover:-translate-y-0.5 hover:bg-book-primary-light hover:shadow-[0_28px_54px_-28px_rgba(87,44,17,0.96)] active:translate-y-0',
    secondary:
      'border-book-border/70 bg-book-bg-paper/78 text-book-text-main backdrop-blur-md hover:-translate-y-0.5 hover:border-book-primary/35 hover:text-book-primary hover:shadow-[0_24px_42px_-34px_rgba(87,44,17,0.9)] active:translate-y-0',
    ghost:
      'border-transparent bg-transparent text-book-text-sub hover:border-book-border/40 hover:bg-book-bg-paper/55 hover:text-book-text-main',
    warning:
      'border-yellow-500 bg-yellow-500 text-white shadow-[0_20px_40px_-24px_rgba(202,138,4,0.96)] hover:-translate-y-0.5 hover:bg-yellow-600 active:translate-y-0',
    danger:
      'border-red-600 bg-red-600 text-white shadow-[0_20px_40px_-24px_rgba(185,28,28,0.96)] hover:-translate-y-0.5 hover:bg-red-700 active:translate-y-0',
  };

  const sizes = {
    sm: 'min-h-9 px-3.5 text-xs',
    md: 'min-h-11 px-5 text-sm',
    lg: 'min-h-12 px-6 text-base',
  };

  return (
    <button
      type={type ?? 'button'}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};
