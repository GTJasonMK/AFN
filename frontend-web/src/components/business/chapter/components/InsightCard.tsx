import React from 'react';
import { BookCard } from '../../../ui/BookCard';

type InsightCardProps = {
  icon: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  descriptionClassName?: string;
  actionsClassName?: string;
};

export const InsightCard: React.FC<InsightCardProps> = ({
  icon,
  title,
  description,
  actions,
  descriptionClassName = 'text-xs text-book-text-muted mt-2 leading-relaxed',
  actionsClassName = 'flex items-center gap-2',
}) => {
  return (
    <BookCard className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-bold text-book-text-main flex items-center gap-2">
            {icon}
            {title}
          </div>
          {description ? <div className={descriptionClassName}>{description}</div> : null}
        </div>
        {actions ? <div className={actionsClassName}>{actions}</div> : null}
      </div>
    </BookCard>
  );
};

