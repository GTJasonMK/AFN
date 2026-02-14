export interface RoutePrefetchProjectInfo {
  kind?: 'novel' | 'coding';
  status?: string;
}

const prefetchedKeys = new Set<string>();

const markAndRun = (key: string, run: () => void) => {
  if (prefetchedKeys.has(key)) return;
  prefetchedKeys.add(key);
  run();
};

const preloadInspiration = () => {
  markAndRun('page:inspiration', () => {
    void import('../pages/InspirationChat');
  });
};

const preloadWritingDesk = () => {
  markAndRun('page:writing-desk', () => {
    void import('../pages/WritingDesk');
  });
};

const preloadNovelDetail = () => {
  markAndRun('page:novel-detail', () => {
    void import('../pages/NovelDetail');
  });
};

const preloadBlueprintPreview = () => {
  markAndRun('page:blueprint-preview', () => {
    void import('../pages/BlueprintPreview');
  });
};

const preloadCodingDetail = () => {
  markAndRun('page:coding-detail', () => {
    void import('../pages/CodingDetail');
  });
};

const preloadCodingDesk = () => {
  markAndRun('page:coding-desk', () => {
    void import('../pages/CodingDesk');
  });
};

export const prefetchProjectRouteByStatus = (project: RoutePrefetchProjectInfo) => {
  const kind = project.kind === 'coding' ? 'coding' : 'novel';
  const status = String(project.status || '').trim().toLowerCase();

  if (kind === 'coding') {
    if (status.includes('draft')) {
      preloadInspiration();
      preloadCodingDetail();
      return;
    }

    preloadCodingDetail();
    preloadCodingDesk();
    return;
  }

  if (status === 'draft' || status === 'inspiration') {
    preloadInspiration();
    return;
  }

  preloadWritingDesk();
  preloadNovelDetail();
  if (status.includes('blueprint')) {
    preloadBlueprintPreview();
  }
};
