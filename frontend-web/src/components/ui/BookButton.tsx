import React from 'react';

interface BookButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

export const BookButton: React.FC<BookButtonProps> = ({ 
  children, 
  variant = 'primary', 
  size = 'md',
  className = '',
  ...props 
}) => {
  const base = "font-sans font-semibold rounded transition-all duration-200 flex items-center justify-center";
  
  const variants = {
    primary: "bg-book-primary text-white hover:bg-book-primary-light active:transform active:scale-95 shadow-sm",
    secondary: "bg-transparent border border-book-border text-book-text-main hover:border-book-primary hover:text-book-primary",
    ghost: "bg-transparent text-book-text-sub hover:bg-book-text-main/5 hover:text-book-text-main",
  };

  const sizes = {
    sm: "px-3 py-1 text-xs",
    md: "px-6 py-2 text-sm",
    lg: "px-8 py-3 text-base",
  };

  return (
    <button 
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};