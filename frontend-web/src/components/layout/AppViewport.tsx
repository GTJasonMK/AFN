import React from 'react';

type ViewportFrameSize = 'default' | 'wide' | 'narrow';

type SegmentItem = {
  id: string;
  label: string;
  hint?: string;
};

const cx = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(' ');

const frameSizeClassName: Record<ViewportFrameSize, string> = {
  default: 'max-w-[1600px] gap-4 px-3 py-3 sm:px-5 sm:py-5',
  wide: 'max-w-[1800px] gap-3 p-3 sm:gap-4 sm:p-4',
  narrow: 'max-w-7xl gap-4 px-4 py-4 sm:px-6 sm:py-6',
};

export const AppViewportShell: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className }) => (
  <div className={cx('page-shell h-full min-h-0 overflow-hidden', className)}>
    {children}
  </div>
);

export const AppViewportFrame: React.FC<{
  children: React.ReactNode;
  className?: string;
  size?: ViewportFrameSize;
}> = ({ children, className, size = 'default' }) => (
  <div className={cx('relative mx-auto flex h-full min-h-0 w-full flex-col', frameSizeClassName[size], className)}>
    {children}
  </div>
);

export const AppViewportScrollArea: React.FC<{
  children: React.ReactNode;
  className?: string;
} & React.HTMLAttributes<HTMLDivElement>> = ({ children, className, ...props }) => (
  <div
    {...props}
    className={cx('perf-scroll-region custom-scrollbar min-h-0 flex-1 overflow-y-auto overscroll-contain', className)}
  >
    {children}
  </div>
);

export const SegmentPager: React.FC<{
  items: SegmentItem[];
  value: string;
  onChange: (next: string) => void;
  className?: string;
}> = ({ items, value, onChange, className }) => (
  <div className={cx('flex flex-wrap items-center gap-3', className)}>
    <div className="inline-flex rounded-full border border-book-border/55 bg-book-bg/78 p-1">
      {items.map((item) => {
        const isActive = item.id === value;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onChange(item.id)}
            className={cx(
              'rounded-full px-4 py-2 text-sm font-semibold transition-all duration-300',
              isActive
                ? 'bg-book-primary text-white shadow-[0_18px_38px_-24px_rgba(87,44,17,0.96)]'
                : 'text-book-text-sub hover:text-book-text-main'
            )}
          >
            {item.label}
          </button>
        );
      })}
    </div>

    {items.find((item) => item.id === value)?.hint ? (
      <div className="rounded-full border border-book-border/55 bg-book-bg/78 px-4 py-2 text-sm text-book-text-sub">
        {items.find((item) => item.id === value)?.hint}
      </div>
    ) : null}
  </div>
);
