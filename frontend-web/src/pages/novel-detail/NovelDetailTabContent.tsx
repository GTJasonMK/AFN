import React from 'react';
import { OverviewTab } from './OverviewTab';
import { CharactersTab } from './CharactersTab';
import { RelationshipsTab } from './RelationshipsTab';
import { WorldTab } from './WorldTab';
import { OutlinesTab } from './OutlinesTab';
import { ChaptersTab } from './ChaptersTab';
import { NOVEL_DETAIL_TAB_ITEMS, type NovelDetailTab } from './NovelDetailTabBar';
import type { NovelDetailTabProps } from './tab-props/types';
import {
  CHAPTER_OUTLINES_RENDER_BATCH_SIZE,
  CHARACTERS_RENDER_BATCH_SIZE,
  COMPLETED_CHAPTERS_RENDER_BATCH_SIZE,
  PART_OUTLINES_RENDER_BATCH_SIZE,
  RELATIONSHIPS_RENDER_BATCH_SIZE,
} from './useNovelDetailRenderLimits';
import { AppViewportScrollArea } from '../../components/layout/AppViewport';

type NovelDetailTabContentProps = {
  activeTab: NovelDetailTab;
  tabProps: NovelDetailTabProps;
};

export const NovelDetailTabContent: React.FC<NovelDetailTabContentProps> = ({
  activeTab,
  tabProps,
}) => {
  const {
    overviewTabProps,
    worldTabProps,
    charactersTabProps,
    relationshipsTabProps,
    outlinesTabProps,
    chaptersTabProps,
  } = tabProps;
  const activeTabMeta = NOVEL_DETAIL_TAB_ITEMS.find((item) => item.id === activeTab) || NOVEL_DETAIL_TAB_ITEMS[0];

  return (
    <AppViewportScrollArea className="h-full" data-novel-detail-scroll-body="1">
      <div className="mx-auto w-full max-w-6xl px-5 sm:px-7">
        <div className="sticky top-0 z-20 -mx-5 border-b border-book-border/45 bg-book-bg-paper/92 px-5 py-4 shadow-sm backdrop-blur-md sm:-mx-7 sm:px-7">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div className="min-w-0">
              <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                当前模块
              </div>
              <h2 className="mt-2 font-serif text-2xl font-bold leading-tight text-book-text-main sm:text-3xl">
                {activeTabMeta.label}
              </h2>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-book-text-sub sm:text-base">
                {activeTabMeta.description}
              </p>
            </div>
            <div className="hidden rounded-[18px] border border-book-border/50 bg-book-bg/72 px-4 py-3 text-sm text-book-text-sub lg:block">
              左侧切换分区，右侧只保留当前分区需要的内容与动作。
            </div>
          </div>
        </div>

        <div className="py-6">
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
      </div>
    </AppViewportScrollArea>
  );
};
