import React from 'react';
import {
  OutlinesChapterSection,
  type OutlinesChapterSectionProps,
} from './OutlinesChapterSection';
import {
  OutlinesPartSection,
  type OutlinesPartSectionProps,
} from './OutlinesPartSection';

export type OutlinesTabProps = OutlinesChapterSectionProps & OutlinesPartSectionProps;

export const OutlinesTab: React.FC<OutlinesTabProps> = (props) => {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 space-y-10">
      <OutlinesChapterSection {...props} />
      <OutlinesPartSection {...props} />
    </div>
  );
};
