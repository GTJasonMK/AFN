import { hasRecentBlueprintGenerationPending } from './blueprintPending';
import { resolveWorkflowStage } from './projectWorkflow';

export type RoutedProject = {
  id?: string;
  status?: string | null;
  kind?: 'novel' | 'coding';
};

const normalizeProjectStatus = (status?: string | null): string =>
  String(status || '').trim().toLowerCase();

const isCodingProject = (project: RoutedProject): boolean => project.kind === 'coding';

export const isDraftLikeProject = (project: RoutedProject): boolean => {
  const status = normalizeProjectStatus(project.status);
  if (isCodingProject(project)) {
    return status.includes('draft');
  }
  return status === 'draft' || status === 'inspiration';
};

const shouldPreferInspirationEntry = (project: RoutedProject): boolean => {
  if (typeof window === 'undefined') return false;
  if (isDraftLikeProject(project)) return false;
  if (isCodingProject(project)) return false;
  const projectId = String(project.id || '').trim();
  if (!projectId) return false;
  return hasRecentBlueprintGenerationPending('novel', projectId);
};

export const getProjectPrimaryRoute = (project: RoutedProject): string => {
  const projectId = String(project.id || '');
  if (isDraftLikeProject(project)) {
    return isCodingProject(project)
      ? `/coding/inspiration/${projectId}`
      : `/inspiration/${projectId}`;
  }

  return isCodingProject(project)
    ? `/coding/detail/${projectId}`
    : `/novel/${projectId}`;
};

export const getProjectPrimaryLabel = (project: RoutedProject): string => {
  if (isDraftLikeProject(project)) {
    return isCodingProject(project) ? '继续需求访谈' : '继续灵感对话';
  }

  return '进入项目详情';
};

export const getProjectWorkspaceRoute = (project: RoutedProject): string | null => {
  const projectId = String(project.id || '');
  if (isDraftLikeProject(project)) {
    return null;
  }

  return isCodingProject(project)
    ? `/coding/desk/${projectId}`
    : `/write/${projectId}`;
};

export const getProjectWorkspaceLabel = (project: RoutedProject): string | null => {
  const workspaceRoute = getProjectWorkspaceRoute(project);
  if (!workspaceRoute) {
    return null;
  }

  return isCodingProject(project) ? '进入工作台' : '进入写作台';
};

export const getProjectHomeEntryRoute = (project: RoutedProject): string => {
  if (isDraftLikeProject(project)) {
    return getProjectPrimaryRoute(project);
  }

  if (!isCodingProject(project)) {
    if (shouldPreferInspirationEntry(project)) {
      return `/inspiration/${String(project.id || '')}`;
    }
    const stage = resolveWorkflowStage(project.status);
    // 小说项目：蓝图/大纲阶段默认先进 Story Control，写作阶段默认进写作台
    if (stage === 'writing' || stage === 'completed') {
      return getProjectWorkspaceRoute(project) || getProjectPrimaryRoute(project);
    }
    return getProjectPrimaryRoute(project);
  }

  return getProjectPrimaryRoute(project);
};

export const getProjectHomeEntryLabel = (project: RoutedProject): string => {
  if (isDraftLikeProject(project)) {
    return getProjectPrimaryLabel(project);
  }

  if (!isCodingProject(project)) {
    if (shouldPreferInspirationEntry(project)) {
      return '检查蓝图结果';
    }
    const stage = resolveWorkflowStage(project.status);
    if (stage === 'writing' || stage === 'completed') {
      return getProjectWorkspaceLabel(project) || getProjectPrimaryLabel(project);
    }
    return getProjectPrimaryLabel(project);
  }

  return getProjectPrimaryLabel(project);
};

/**
 * 项目卡片的“次要入口”（与 HomeEntry 相反的那个入口）
 * - 小说：在蓝图/大纲阶段提供“写作台”，在写作阶段提供“项目详情”
 * - Coding：在详情页入口旁提供“工作台”
 */
export const getProjectSecondaryEntryRoute = (project: RoutedProject): string | null => {
  if (isDraftLikeProject(project)) {
    return null;
  }

  const projectId = String(project.id || '');
  if (!projectId) return null;

  if (!isCodingProject(project)) {
    if (shouldPreferInspirationEntry(project)) {
      return `/novel/${projectId}`;
    }
    const stage = resolveWorkflowStage(project.status);
    if (stage === 'writing' || stage === 'completed') {
      return `/novel/${projectId}`;
    }
    return `/write/${projectId}`;
  }

  return `/coding/desk/${projectId}`;
};

export const getProjectSecondaryEntryLabel = (project: RoutedProject): string | null => {
  const secondary = getProjectSecondaryEntryRoute(project);
  if (!secondary) return null;
  if (isCodingProject(project)) return '进入工作台';

  if (shouldPreferInspirationEntry(project)) {
    return '进入项目详情';
  }

  const stage = resolveWorkflowStage(project.status);
  if (stage === 'writing' || stage === 'completed') return '进入项目详情';
  return '进入写作台';
};

export const getProjectKindLabel = (project: RoutedProject): string =>
  isCodingProject(project) ? 'Prompt 工程' : '小说项目';
