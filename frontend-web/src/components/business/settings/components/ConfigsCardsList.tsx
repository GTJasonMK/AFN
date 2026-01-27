import React from 'react';
import { ConfigCardShell } from './ConfigCardShell';
import { ConfigsList } from './ConfigsList';

type BaseConfigItem = {
  id: number;
  is_active: boolean;
  test_message?: string | null;
};

type ConfigsCardsListProps<T extends BaseConfigItem> = {
  items: readonly T[];
  loading?: boolean;
  testingId?: number | null;
  onActivate: (id: number) => void;
  onTest: (id: number) => void;
  onEdit: (item: T) => void;
  onDelete: (item: T) => void;
  renderLeft: (item: T) => React.ReactNode;
};

export const ConfigsCardsList = <T extends BaseConfigItem,>({
  items,
  loading = false,
  testingId,
  onActivate,
  onTest,
  onEdit,
  onDelete,
  renderLeft,
}: ConfigsCardsListProps<T>) => {
  return (
    <ConfigsList
      items={items}
      loading={loading}
      getKey={(cfg) => cfg.id}
      renderItem={(cfg) => (
        <ConfigCardShell
          testMessage={cfg.test_message}
          isActive={cfg.is_active}
          isTesting={Boolean(testingId !== null && testingId === cfg.id)}
          onActivate={() => onActivate(cfg.id)}
          onTest={() => onTest(cfg.id)}
          onEdit={() => onEdit(cfg)}
          onDelete={() => onDelete(cfg)}
        >
          {renderLeft(cfg)}
        </ConfigCardShell>
      )}
    />
  );
};

