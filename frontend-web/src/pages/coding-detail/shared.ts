import { CodingDependency, CodingFilePriority, CodingModule, CodingSystem } from '../../api/coding';

export type CodingTab = 'overview' | 'architecture' | 'directory' | 'generation';

export const CODING_DETAIL_TABS: readonly CodingTab[] = ['overview', 'architecture', 'directory', 'generation'];
export const DEFAULT_VERSION_CREATED_AT = '1970-01-01T00:00:00.000Z';
export const CODING_DETAIL_BOOTSTRAP_TTL_MS = 4 * 60 * 1000;
export const getCodingDetailBootstrapKey = (projectId: string) => `afn:web:coding-detail:${projectId}:bootstrap:v1`;

export type ResourceKey = 'systems' | 'modules' | 'dependencies' | 'ragCompleteness' | 'treeData';

export type ResourceStatus = {
  loaded: boolean;
  loading: boolean;
  error: string | null;
  lastLoadedAt: number | null;
};

export type ResourceStatusMap = Record<ResourceKey, ResourceStatus>;

export type CodingDetailBootstrapSnapshot = {
  project: any | null;
  treeData: any | null;
  systems: CodingSystem[];
  modules: CodingModule[];
  dependencies: CodingDependency[];
  ragCompleteness: any | null;
  resourceState?: Partial<Record<ResourceKey, Pick<ResourceStatus, 'loaded' | 'lastLoadedAt'>>>;
};

export type FileInfoFormState = {
  description: string;
  purpose: string;
  priority: CodingFilePriority;
};

export type DirectoryInfoFormState = {
  description: string;
};

export type SystemFormState = {
  name: string;
  description: string;
  responsibilitiesText: string;
  techRequirements: string;
};

export type ModuleFormState = {
  systemNumber: number | '';
  name: string;
  type: string;
  description: string;
  iface: string;
  dependenciesText: string;
};

export const RESOURCE_KEYS: readonly ResourceKey[] = ['systems', 'modules', 'dependencies', 'ragCompleteness', 'treeData'];

export const createEmptyResourceStatus = (): ResourceStatusMap => ({
  systems: { loaded: false, loading: false, error: null, lastLoadedAt: null },
  modules: { loaded: false, loading: false, error: null, lastLoadedAt: null },
  dependencies: { loaded: false, loading: false, error: null, lastLoadedAt: null },
  ragCompleteness: { loaded: false, loading: false, error: null, lastLoadedAt: null },
  treeData: { loaded: false, loading: false, error: null, lastLoadedAt: null },
});

export const createInitialResourceStatus = (cached: CodingDetailBootstrapSnapshot | null): ResourceStatusMap => {
  const next = createEmptyResourceStatus();
  if (!cached) return next;

  for (const key of RESOURCE_KEYS) {
    const meta = cached.resourceState?.[key];
    if (!meta) continue;
    next[key] = {
      ...next[key],
      loaded: Boolean(meta.loaded),
      lastLoadedAt: Number.isFinite(meta.lastLoadedAt) ? Number(meta.lastLoadedAt) : null,
    };
  }

  if (!cached.resourceState) {
    next.treeData.loaded = cached.treeData !== null;
    next.ragCompleteness.loaded = cached.ragCompleteness !== null;
    next.systems.loaded = Array.isArray(cached.systems) && cached.systems.length > 0;
    next.modules.loaded = Array.isArray(cached.modules) && cached.modules.length > 0;
    next.dependencies.loaded = Array.isArray(cached.dependencies) && cached.dependencies.length > 0;
  }

  return next;
};

export const serializeResourceStatus = (
  resourceState: ResourceStatusMap,
): Partial<Record<ResourceKey, Pick<ResourceStatus, 'loaded' | 'lastLoadedAt'>>> => {
  const next: Partial<Record<ResourceKey, Pick<ResourceStatus, 'loaded' | 'lastLoadedAt'>>> = {};
  for (const key of RESOURCE_KEYS) {
    next[key] = {
      loaded: Boolean(resourceState[key].loaded),
      lastLoadedAt: resourceState[key].lastLoadedAt,
    };
  }
  return next;
};
