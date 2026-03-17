import React from 'react';

type NovelDialogTone = 'default' | 'warning' | 'danger' | 'success';

const toneClassMap: Record<NovelDialogTone, string> = {
  default: 'border-book-border/50 bg-book-bg/72',
  warning: 'border-amber-500/20 bg-amber-500/10',
  danger: 'border-red-500/20 bg-red-500/10',
  success: 'border-emerald-500/20 bg-emerald-500/10',
};

export const NovelDialogStack: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className = '' }) => (
  <div className={`space-y-5 ${className}`}>{children}</div>
);

export const NovelDialogIntro: React.FC<{
  title: string;
  description: React.ReactNode;
  eyebrow?: string;
  tone?: NovelDialogTone;
  children?: React.ReactNode;
  className?: string;
}> = ({
  title,
  description,
  eyebrow = 'Overview',
  tone = 'default',
  children,
  className = '',
}) => (
  <section
    className={`rounded-[26px] border px-4 py-4 shadow-[0_24px_58px_-48px_rgba(33,16,6,0.94)] backdrop-blur-xl sm:px-5 sm:py-5 ${toneClassMap[tone]} ${className}`}
  >
    <div className="space-y-3">
      <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
        {eyebrow}
      </div>
      <div>
        <h4 className="font-serif text-[clamp(1.3rem,2vw,1.9rem)] font-bold leading-none tracking-[-0.03em] text-book-text-main">
          {title}
        </h4>
        <div className="mt-3 text-sm leading-relaxed text-book-text-sub">{description}</div>
      </div>
      {children ? <div className="pt-1">{children}</div> : null}
    </div>
  </section>
);

export const NovelDialogSection: React.FC<{
  title: string;
  description?: React.ReactNode;
  eyebrow?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  contentClassName?: string;
}> = ({
  title,
  description,
  eyebrow = 'Section',
  actions,
  children,
  className = '',
  contentClassName = '',
}) => (
  <section
    className={`rounded-[28px] border border-book-border/55 bg-book-bg-paper/80 p-4 shadow-[0_24px_58px_-48px_rgba(34,17,7,0.94)] backdrop-blur-xl sm:p-5 ${className}`}
  >
    <div className="flex flex-col gap-3 border-b border-book-border/45 pb-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
          {eyebrow}
        </div>
        <h4 className="mt-2 font-serif text-xl font-bold text-book-text-main sm:text-2xl">{title}</h4>
        {description ? (
          <div className="mt-2 text-sm leading-relaxed text-book-text-sub">{description}</div>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
    </div>
    <div className={`pt-4 ${contentClassName}`}>{children}</div>
  </section>
);

export const NovelDialogMetricGrid: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className = '' }) => (
  <div className={`grid gap-3 sm:grid-cols-2 ${className}`}>{children}</div>
);

export const NovelDialogMetric: React.FC<{
  label: string;
  value: React.ReactNode;
  note: React.ReactNode;
}> = ({ label, value, note }) => (
  <div className="rounded-[22px] border border-book-border/50 bg-book-bg/74 px-4 py-4 shadow-[0_20px_46px_-42px_rgba(30,14,5,0.94)]">
    <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
      {label}
    </div>
    <div className="mt-3 font-serif text-2xl font-bold text-book-text-main">{value}</div>
    <div className="mt-2 text-sm leading-relaxed text-book-text-sub">{note}</div>
  </div>
);

export const NovelDialogSurface: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className = '' }) => (
  <div
    className={`rounded-[24px] border border-book-border/45 bg-book-bg-paper/74 p-4 shadow-[0_20px_48px_-42px_rgba(31,15,6,0.94)] backdrop-blur-xl ${className}`}
  >
    {children}
  </div>
);
