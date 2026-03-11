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
    <div className="flex-1 overflow-y-auto custom-scrollbar">
      <div className="mx-auto w-full max-w-6xl px-5 py-6 sm:px-7 sm:py-7">
        <div className="rounded-[28px] border border-book-border/55 bg-book-bg-paper/76 px-5 py-5 shadow-[0_24px_50px_-36px_rgba(36,18,6,0.92)]">
          <div className="eyebrow">Current Section</div>
          <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h2 className="font-serif text-3xl font-bold text-book-text-main sm:text-4xl">
                {activeTabMeta.label}
              </h2>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-book-text-sub sm:text-base">
                {activeTabMeta.description}
              </p>
            </div>
            <div className="rounded-[22px] border border-book-border/50 bg-book-bg/72 px-4 py-3 text-sm text-book-text-sub">
              当前工作区只展示与本节相关的内容和动作，减少在大页面里来回跳找信息的成本。
            </div>
          </div>
        </div>

        <div className="mt-6">
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
    </div>
  );
};
