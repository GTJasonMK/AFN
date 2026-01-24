import React from 'react';

interface BookCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'flat' | 'glass';
  hover?: boolean;
}

export const BookCard: React.FC<BookCardProps> = ({ 
  children, 
  className = '', 
  variant = 'default',
  hover = false,
  ...props 
}) => {
  const baseStyles = "rounded-lg p-4 transition-all duration-300";
  
  const variants = {
    default: "bg-book-bg-paper border border-book-border",
    flat: "bg-book-bg-paper",
    glass: "glass-panel",
  };

  const hoverStyles = hover ? "hover:border-book-primary/50 hover:shadow-md cursor-pointer" : "";

  return (
    <div 
      className={`${baseStyles} ${variants[variant]} ${hoverStyles} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};