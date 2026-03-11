import type { UseNovelDetailModalPropsParams } from './modal-props/types';
import type { NovelDetailTabSources } from './tab-props/types';

type LatestPartOutlineInputForTab = Pick<
  UseNovelDetailModalPropsParams['latestPart'],
  'deletingLatestParts' | 'regeneratingLatestParts'
>;

type LatestChapterOutlineInputForTab = Pick<
  UseNovelDetailModalPropsParams['latestChapter'],
  'setDeleteLatestCount' | 'setRegenerateLatestCount' | 'setRegenerateLatestPrompt'
>;

export type BuildNovelDetailTabSourcesArgs = {
  tab: {
    overviewWorld: NovelDetailTabSources['overviewWorld'];
    characterRelationship: NovelDetailTabSources['characterRelationship'];
    outlines: Omit<
      NovelDetailTabSources['outlines'],
      | 'setDeleteLatestCount'
      | 'setRegenerateLatestCount'
      | 'setRegenerateLatestPrompt'
      | 'deletingLatestParts'
      | 'regeneratingLatestParts'
    >;
    chapters: NovelDetailTabSources['chapters'];
  };
  latestPartOutlineInput: LatestPartOutlineInputForTab;
  latestChapterOutlineInput: LatestChapterOutlineInputForTab;
};

export const buildNovelDetailTabSources = ({
  tab,
  latestPartOutlineInput,
  latestChapterOutlineInput,
}: BuildNovelDetailTabSourcesArgs): NovelDetailTabSources => {
  return {
    overviewWorld: tab.overviewWorld,
    characterRelationship: tab.characterRelationship,
    outlines: {
      ...tab.outlines,
      setDeleteLatestCount: latestChapterOutlineInput.setDeleteLatestCount,
      setRegenerateLatestCount: latestChapterOutlineInput.setRegenerateLatestCount,
      setRegenerateLatestPrompt: latestChapterOutlineInput.setRegenerateLatestPrompt,
      deletingLatestParts: latestPartOutlineInput.deletingLatestParts,
      regeneratingLatestParts: latestPartOutlineInput.regeneratingLatestParts,
    },
    chapters: tab.chapters,
  };
};
