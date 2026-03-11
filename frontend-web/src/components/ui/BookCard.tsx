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
  const baseStyles =
    'relative overflow-hidden rounded-[24px] border p-5 transition-all duration-300';

  const variants = {
    default:
      'bg-book-bg-paper/86 border-book-border/60 shadow-[0_24px_56px_-42px_rgba(46,23,9,0.88)] before:pointer-events-none before:absolute before:inset-0 before:bg-gradient-to-br before:from-white/45 before:via-transparent before:to-book-primary/10',
    flat:
      'bg-book-bg-paper/72 border-book-border/40 before:pointer-events-none before:absolute before:inset-0 before:bg-gradient-to-br before:from-white/30 before:to-transparent',
    glass:
      'glass-panel border-book-border/50 before:pointer-events-none before:absolute before:inset-0 before:bg-gradient-to-br before:from-white/28 before:via-transparent before:to-book-primary/8',
  };

  const hoverStyles = hover
    ? 'cursor-pointer hover:-translate-y-1 hover:border-book-primary/25 hover:shadow-[0_34px_70px_-46px_rgba(46,23,9,0.92)]'
    : '';

  return (
    <div
      className={`${baseStyles} ${variants[variant]} ${hoverStyles} ${className}`}
      {...props}
    >
      <div className="relative z-[1]">{children}</div>
    </div>
  );
};
