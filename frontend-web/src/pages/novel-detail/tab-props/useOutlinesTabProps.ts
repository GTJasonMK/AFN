import { useMemo } from 'react';
import type { NovelDetailTabSources } from './types';

type UseOutlinesTabPropsParams = {
  projectId: string;
  outlines: NovelDetailTabSources['outlines'];
};

export const useOutlinesTabProps = ({
  projectId,
  outlines,
}: UseOutlinesTabPropsParams) => {
  const outlinesTabProps = useMemo(() => ({
    projectId,
    ...outlines,
  }), [outlines, projectId]);

  return outlinesTabProps;
};
