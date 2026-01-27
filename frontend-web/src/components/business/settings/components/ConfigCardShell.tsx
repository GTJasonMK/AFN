import React from 'react';
import { BookCard } from '../../../ui/BookCard';
import { ConfigCardActions } from './ConfigCardActions';

type ConfigCardShellProps = {
  children: React.ReactNode;
  testMessage?: string | null;
  isActive: boolean;
  isTesting: boolean;
  onActivate: () => void;
  onTest: () => void;
  onEdit: () => void;
  onDelete: () => void;
};

export const ConfigCardShell: React.FC<ConfigCardShellProps> = ({
  children,
  testMessage,
  isActive,
  isTesting,
  onActivate,
  onTest,
  onEdit,
  onDelete,
}) => {
  return (
    <BookCard className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          {children}
          {testMessage ? (
            <div className="mt-2 text-xs text-book-text-tertiary bg-book-bg p-2 rounded border border-book-border/40">
              {testMessage}
            </div>
          ) : null}
        </div>

        <ConfigCardActions
          isActive={isActive}
          isTesting={isTesting}
          onActivate={onActivate}
          onTest={onTest}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      </div>
    </BookCard>
  );
};

