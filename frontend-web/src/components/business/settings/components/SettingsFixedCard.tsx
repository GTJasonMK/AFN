import React from 'react';
import { BookCard } from '../../../ui/BookCard';
import { SETTINGS_CARD_HEIGHTS } from './settingsLayout';

export type SettingsFixedCardProps = {
  title: React.ReactNode;
  description?: React.ReactNode;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
  headerExtras?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
  heightClassName?: string;
  bodyScrollable?: boolean;
};

export const SettingsFixedCard: React.FC<SettingsFixedCardProps> = ({
  title,
  description,
  icon,
  actions,
  headerExtras,
  children,
  className = '',
  bodyClassName = '',
  heightClassName = SETTINGS_CARD_HEIGHTS.standard,
  bodyScrollable = true,
}) => {
  return (
    <BookCard
      className={`p-4 min-w-0 ${heightClassName} ${className}`}
      contentClassName="h-full min-h-0 flex flex-col"
    >
      <div className="shrink-0">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 text-xs font-bold text-book-text-sub/90">
              {icon}
              <span className="truncate">{title}</span>
            </div>
            {description ? (
              <div className="mt-1 text-[11px] text-book-text-muted leading-relaxed">
                {description}
              </div>
            ) : null}
          </div>
          {actions ? (
            <div className="min-w-0 flex flex-wrap items-center justify-end gap-2">
              {actions}
            </div>
          ) : null}
        </div>

        {headerExtras ? <div className="mt-3">{headerExtras}</div> : null}
      </div>

      <div className="mt-3 min-h-0 flex-1 overflow-hidden">
        {bodyScrollable ? (
          <div
            className={`h-full min-h-0 overflow-y-auto overflow-x-hidden pr-1 custom-scrollbar ${bodyClassName}`}
          >
            {children}
          </div>
        ) : (
          <div className={`h-full min-h-0 overflow-hidden ${bodyClassName}`}>{children}</div>
        )}
      </div>
    </BookCard>
  );
};
