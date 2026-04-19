export type AssistantTab = 'rag' | 'agent';

export type StreamLogType =
  | 'progress'
  | 'thinking'
  | 'action'
  | 'observation'
  | 'warning'
  | 'error'
  | 'structure_update'
  | 'final_state'
  | 'saved'
  | 'planning_complete'
  | 'agent_start'
  | 'iteration_start';

export type StreamLog = {
  id: string;
  type: StreamLogType;
  title: string;
  content: string;
  ts: number;
  timeText: string;
};

export type CodingDeskBootstrapSnapshot = {
  project: any | null;
  treeData: any | null;
};

export const CODING_DESK_BOOTSTRAP_TTL_MS = 4 * 60 * 1000;

export const getCodingDeskBootstrapKey = (projectId: string) =>
  `afn:web:coding-desk:${projectId}:bootstrap:v1`;

export const LOG_LABELS: Record<StreamLogType, { label: string; cls: string }> = {
  progress: { label: 'Progress', cls: 'text-book-text-muted' },
  thinking: { label: 'Thinking', cls: 'text-book-primary' },
  action: { label: 'Action', cls: 'text-book-accent' },
  observation: { label: 'Observation', cls: 'text-green-600' },
  warning: { label: 'Warning', cls: 'text-orange-600' },
  error: { label: 'Error', cls: 'text-red-600' },
  structure_update: { label: 'Structure', cls: 'text-book-primary' },
  final_state: { label: 'Final', cls: 'text-book-primary' },
  saved: { label: 'Saved', cls: 'text-green-600' },
  planning_complete: { label: 'Complete', cls: 'text-green-600' },
  agent_start: { label: 'Start', cls: 'text-book-text-muted' },
  iteration_start: { label: 'Iteration', cls: 'text-book-text-muted' },
};

export const safeJson = (value: any): string => {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value ?? '');
  }
};

export const truncateText = (text: string, maxLen: number, suffix: string): string => {
  const s = String(text ?? '');
  if (s.length <= maxLen) return s;
  return `${s.slice(0, maxLen)}\n${suffix}`;
};

export const normalizePath = (raw: any): string => {
  const s = String(raw ?? '').trim().replace(/\\/g, '/');
  if (!s) return '';
  const noDup = s.replace(/\/{2,}/g, '/');
  const noDot = noDup.startsWith('./') ? noDup.slice(2) : noDup;
  return noDot.endsWith('/') ? noDot.slice(0, -1) : noDot;
};

export const dirname = (p: string): string => {
  const s = normalizePath(p);
  const idx = s.lastIndexOf('/');
  if (idx <= 0) return '';
  return s.slice(0, idx);
};

export const basename = (p: string): string => {
  const s = normalizePath(p);
  const idx = s.lastIndexOf('/');
  return idx >= 0 ? s.slice(idx + 1) : s;
};

export const pathDepth = (p: string): number => {
  const s = normalizePath(p);
  if (!s) return 0;
  return s.split('/').filter(Boolean).length;
};

export const buildAgentDirectoryTreeData = (preview: {
  directories?: any[];
  files?: any[];
  stats?: any;
}) => {
  const rawDirs = Array.isArray(preview?.directories) ? preview.directories : [];
  const rawFiles = Array.isArray(preview?.files) ? preview.files : [];

  const dirInfoByPath = new Map<string, any>();
  const allDirPaths = new Set<string>();

  const ensureDirPath = (rawPath: any) => {
    let cur = normalizePath(rawPath);
    if (!cur) return;
    while (cur) {
      if (!allDirPaths.has(cur)) allDirPaths.add(cur);
      const parent = dirname(cur);
      if (!parent || parent === cur) break;
      cur = parent;
    }
  };

  for (const d of rawDirs) {
    const p = normalizePath(d?.path);
    if (!p) continue;
    dirInfoByPath.set(p, { ...d, path: p });
    ensureDirPath(p);
  }

  for (const f of rawFiles) {
    const filePath = normalizePath(f?.path);
    if (!filePath) continue;
    const parentDir = dirname(filePath);
    if (parentDir) ensureDirPath(parentDir);
  }

  const sortedDirPaths = Array.from(allDirPaths).sort((a, b) => {
    const da = pathDepth(a);
    const db = pathDepth(b);
    if (da !== db) return da - db;
    return a.localeCompare(b);
  });

  const nodeByPath = new Map<string, any>();
  for (const p of sortedDirPaths) {
    const info = dirInfoByPath.get(p) || { path: p };
    nodeByPath.set(p, {
      id: `agent:dir:${p}`,
      name: basename(p) || p,
      ...info,
      children: [],
      files: [],
    });
  }

  for (const p of sortedDirPaths) {
    const parent = dirname(p);
    if (!parent) continue;
    const parentNode = nodeByPath.get(parent);
    const node = nodeByPath.get(p);
    if (!parentNode || !node) continue;
    parentNode.children.push(node);
  }

  for (const f of rawFiles) {
    const filePath = normalizePath(f?.path);
    if (!filePath) continue;
    const parent = dirname(filePath);
    const dirNode = nodeByPath.get(parent);
    if (!dirNode) continue;

    const filename = String(f?.filename || basename(filePath) || filePath);
    dirNode.files.push({
      id: `agent:file:${filePath}`,
      filename,
      file_path: filePath,
      ...f,
    });
  }

  for (const node of nodeByPath.values()) {
    node.children.sort((a: any, b: any) => String(a?.name || '').localeCompare(String(b?.name || '')));
    node.files.sort((a: any, b: any) => String(a?.filename || '').localeCompare(String(b?.filename || '')));
  }

  const rootNodes = sortedDirPaths
    .filter((p) => {
      const parent = dirname(p);
      return !parent || !nodeByPath.has(parent);
    })
    .map((p) => nodeByPath.get(p))
    .filter(Boolean);

  return {
    root_nodes: rootNodes,
    total_directories: Number(preview?.stats?.total_directories || allDirPaths.size) || 0,
    total_files: Number(preview?.stats?.total_files || rawFiles.length) || 0,
  };
};
