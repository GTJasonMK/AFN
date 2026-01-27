import React from 'react';

type ConfigsListProps<T> = {
  items: readonly T[];
  loading?: boolean;
  emptyText?: string;
  className?: string;
  getKey: (item: T) => React.Key;
  renderItem: (item: T) => React.ReactNode;
};

export const ConfigsList = <T,>({
  items,
  loading = false,
  emptyText = '暂无配置',
  className = 'space-y-3',
  getKey,
  renderItem,
}: ConfigsListProps<T>) => {
  return (
    <div className={className}>
      {items.length === 0 && !loading && (
        <div className="py-10 text-center text-book-text-muted text-sm">{emptyText}</div>
      )}

      {items.map((item) => (
        <React.Fragment key={getKey(item)}>{renderItem(item)}</React.Fragment>
      ))}
    </div>
  );
};

