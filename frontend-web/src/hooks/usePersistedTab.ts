import { useCallback } from 'react';
import { usePersistedState } from './usePersistedState';

export const usePersistedTab = <T extends string>(
  storageKey: string | null | undefined,
  defaultTab: T,
  allowedTabs: readonly T[],
) => {
  const isAllowed = useCallback((value: string): value is T => allowedTabs.includes(value as T), [allowedTabs]);
  const parseTab = useCallback((raw: string): T => {
    if (isAllowed(raw)) return raw as T;
    return defaultTab;
  }, [defaultTab, isAllowed]);

  const [activeTab, setActiveTab] = usePersistedState<T>(storageKey, defaultTab, {
    parse: parseTab,
    serialize: (value) => value,
  });

  return [activeTab, setActiveTab] as const;
};
