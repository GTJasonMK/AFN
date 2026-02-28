import React from 'react';
import { OverviewTab, type OverviewTabProps } from './OverviewTab';
import { CharactersTab, type CharactersTabProps } from './CharactersTab';
import { RelationshipsTab, type RelationshipsTabProps } from './RelationshipsTab';
import { WorldTab, type WorldTabProps } from './WorldTab';
import { OutlinesTab, type OutlinesTabProps } from './OutlinesTab';
import { ChaptersTab, type ChaptersTabProps } from './ChaptersTab';
import type { NovelDetailTab } from './NovelDetailTabBar';

const CHARACTERS_RENDER_BATCH_SIZE = 24;
const RELATIONSHIPS_RENDER_BATCH_SIZE = 24;
const CHAPTER_OUTLINES_RENDER_BATCH_SIZE = 40;
const PART_OUTLINES_RENDER_BATCH_SIZE = 20;
const COMPLETED_CHAPTERS_RENDER_BATCH_SIZE = 120;

type NovelDetailTabContentProps = {
  activeTab: NovelDetailTab;
  overviewTabProps: OverviewTabProps;
  worldTabProps: WorldTabProps;
  charactersTabProps: Omit<CharactersTabProps, 'renderBatchSize'>;
  relationshipsTabProps: Omit<RelationshipsTabProps, 'renderBatchSize'>;
  outlinesTabProps: Omit<OutlinesTabProps, 'chapterOutlinesRenderBatchSize' | 'partOutlinesRenderBatchSize'>;
  chaptersTabProps: Omit<ChaptersTabProps, 'renderBatchSize'>;
};

export const NovelDetailTabContent: React.FC<NovelDetailTabContentProps> = ({
  activeTab,
  overviewTabProps,
  worldTabProps,
  charactersTabProps,
  relationshipsTabProps,
  outlinesTabProps,
  chaptersTabProps,
}) => {
  return (
    <div className="flex-1 overflow-y-auto p-8 max-w-5xl mx-auto w-full custom-scrollbar">
      {activeTab === 'overview' && (
        <OverviewTab {...overviewTabProps} />
      )}

      {activeTab === 'world' && (
        <WorldTab {...worldTabProps} />
      )}

      {activeTab === 'characters' && (
        <CharactersTab
          {...charactersTabProps}
          renderBatchSize={CHARACTERS_RENDER_BATCH_SIZE}
        />
      )}

      {activeTab === 'relationships' && (
        <RelationshipsTab
          {...relationshipsTabProps}
          renderBatchSize={RELATIONSHIPS_RENDER_BATCH_SIZE}
        />
      )}

      {activeTab === 'outlines' && (
        <OutlinesTab
          {...outlinesTabProps}
          chapterOutlinesRenderBatchSize={CHAPTER_OUTLINES_RENDER_BATCH_SIZE}
          partOutlinesRenderBatchSize={PART_OUTLINES_RENDER_BATCH_SIZE}
        />
      )}

      {activeTab === 'chapters' && (
        <ChaptersTab
          {...chaptersTabProps}
          renderBatchSize={COMPLETED_CHAPTERS_RENDER_BATCH_SIZE}
        />
      )}
    </div>
  );
};
