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
    return getProjectWorkspaceRoute(project) || getProjectPrimaryRoute(project);
  }

  return getProjectPrimaryRoute(project);
};

export const getProjectHomeEntryLabel = (project: RoutedProject): string => {
  if (isDraftLikeProject(project)) {
    return getProjectPrimaryLabel(project);
  }

  if (!isCodingProject(project)) {
    return getProjectWorkspaceLabel(project) || getProjectPrimaryLabel(project);
  }

  return getProjectPrimaryLabel(project);
};

export const getProjectKindLabel = (project: RoutedProject): string =>
  isCodingProject(project) ? 'Prompt 工程' : '小说项目';
