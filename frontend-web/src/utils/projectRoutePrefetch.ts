import { RoutedProject, isDraftLikeProject } from './projectRouting';
import { resolveWorkflowStage } from './projectWorkflow';

export interface RoutePrefetchProjectInfo extends RoutedProject {}

const prefetchedKeys = new Set<string>();
const inflightKeys = new Set<string>();
const HOVER_PREFETCH_DELAY_MS = 220;

const lowPowerMode = () => {
  if (typeof navigator === 'undefined') return false;
  const nav = navigator as Navigator & {
    connection?: {
      saveData?: boolean;
      effectiveType?: string;
    };
    hardwareConcurrency?: number;
  };
  if (nav.connection?.saveData) return true;
  const effectiveType = String(nav.connection?.effectiveType || '').toLowerCase();
  if (effectiveType.includes('2g') || effectiveType.includes('3g')) return true;
  const cores = Number(nav.hardwareConcurrency || 0);
  return Number.isFinite(cores) && cores > 0 && cores <= 4;
};

const canPrefetch = () => {
  if (typeof window === 'undefined') return false;
  if (document.visibilityState !== 'visible') return false;
  return !lowPowerMode();
};

const runPrefetch = (key: string, load: () => Promise<unknown>) => {
  if (!canPrefetch()) return;
  if (prefetchedKeys.has(key) || inflightKeys.has(key) || inflightKeys.size >= 1) return;

  inflightKeys.add(key);
  void load()
    .then(() => {
      prefetchedKeys.add(key);
    })
    .catch(() => {
      // ignore
    })
    .finally(() => {
      inflightKeys.delete(key);
    });
};

const resolveProjectPrefetchTarget = (project: RoutePrefetchProjectInfo): { key: string; load: () => Promise<unknown> } | null => {
  if (isDraftLikeProject(project)) {
    return {
      key: 'page:inspiration',
      load: () => import('../pages/InspirationChat'),
    };
  }

  if (project.kind === 'coding') {
    return {
      key: 'page:coding-detail',
      load: () => import('../pages/CodingDetail'),
    };
  }

  const stage = resolveWorkflowStage(project.status);
  if (stage === 'writing' || stage === 'completed') {
    return {
      key: 'page:writing-desk',
      load: () => import('../pages/WritingDesk'),
    };
  }

  return {
    key: 'page:novel-detail',
    load: () => import('../pages/NovelDetail'),
  };
};

export const prefetchProjectRouteByStatus = (
  project: RoutePrefetchProjectInfo,
  opts: { immediate?: boolean; delayMs?: number } = {},
): (() => void) => {
  if (typeof window === 'undefined') return () => {};
  const target = resolveProjectPrefetchTarget(project);
  if (!target) return () => {};

  const { immediate = false, delayMs = HOVER_PREFETCH_DELAY_MS } = opts;
  if (immediate) {
    runPrefetch(target.key, target.load);
    return () => {};
  }

  let cancelled = false;
  const timerId = window.setTimeout(() => {
    if (cancelled) return;
    runPrefetch(target.key, target.load);
  }, Math.max(0, delayMs));

  return () => {
    cancelled = true;
    window.clearTimeout(timerId);
  };
};
