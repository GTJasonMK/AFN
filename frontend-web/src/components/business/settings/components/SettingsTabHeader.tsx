import React from 'react';
import { Plus, RefreshCw } from 'lucide-react';
import { BookButton } from '../../../ui/BookButton';

interface SettingsTabHeaderProps {
  title: string;
  loading: boolean;
  onRefresh: () => void;
  showRefreshIcon?: boolean;
  refreshLabel?: string;
  refreshingLabel?: string;
  extraActions?: React.ReactNode;
  onCreate?: () => void;
  createLabel?: string;
}

export const SettingsTabHeader: React.FC<SettingsTabHeaderProps> = ({
  title,
  loading,
  onRefresh,
  showRefreshIcon,
  refreshLabel,
  refreshingLabel,
  extraActions,
  onCreate,
  createLabel,
}) => {
  const label = refreshLabel || '刷新';
  return (
    <div className="flex items-center justify-between">
      <div className="text-sm font-bold text-book-text-main">{title}</div>
      <div className="flex items-center gap-2">
        <BookButton variant="ghost" size="sm" onClick={onRefresh} disabled={loading}>
          {showRefreshIcon && <RefreshCw size={14} className={`mr-1 ${loading ? 'animate-spin' : ''}`} />}
          {showRefreshIcon ? label : loading ? (refreshingLabel || '刷新中…') : label}
        </BookButton>
        {extraActions}
        {onCreate && (
          <BookButton variant="primary" size="sm" onClick={onCreate}>
            <Plus size={14} className="mr-1" />
            {createLabel || '新增'}
          </BookButton>
        )}
      </div>
    </div>
  );
};
