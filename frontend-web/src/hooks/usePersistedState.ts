import { useEffect, useMemo, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

type UsePersistedStateOptions<T> = {
  parse?: (raw: string) => T;
  serialize?: (value: T) => string;
};

const defaultParse = <T,>(raw: string): T => JSON.parse(raw) as T;
const defaultSerialize = <T,>(value: T): string => JSON.stringify(value);

const readPersisted = <T,>(
  key: string | null | undefined,
  fallback: T,
  parse: (raw: string) => T,
): T => {
  if (!key) return fallback;
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    return parse(raw);
  } catch {
    return fallback;
  }
};

export const usePersistedState = <T,>(
  storageKey: string | null | undefined,
  initialValue: T,
  opts: UsePersistedStateOptions<T> = {},
): [T, Dispatch<SetStateAction<T>>] => {
  const parse = useMemo(() => opts.parse ?? defaultParse<T>, [opts.parse]);
  const serialize = useMemo(() => opts.serialize ?? defaultSerialize<T>, [opts.serialize]);

  const [value, setValue] = useState<T>(() => readPersisted(storageKey, initialValue, parse));

  useEffect(() => {
    setValue(readPersisted(storageKey, initialValue, parse));
  }, [initialValue, parse, storageKey]);

  useEffect(() => {
    if (!storageKey) return;
    try {
      localStorage.setItem(storageKey, serialize(value));
    } catch {
      // ignore
    }
  }, [serialize, storageKey, value]);

  return [value, setValue];
};

