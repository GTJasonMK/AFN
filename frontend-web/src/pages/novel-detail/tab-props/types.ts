import type { OverviewTabProps } from '../OverviewTab';
import type { WorldTabProps } from '../WorldTab';
import type { CharactersTabProps } from '../CharactersTab';
import type { RelationshipsTabProps } from '../RelationshipsTab';
import type { OutlinesTabProps } from '../OutlinesTab';
import type { ChaptersTabProps } from '../ChaptersTab';

export type CharactersTabInputProps = Omit<CharactersTabProps, 'renderBatchSize'>;
export type RelationshipsTabInputProps = Omit<RelationshipsTabProps, 'renderBatchSize'>;
export type OverviewWorldTabSource = OverviewTabProps & WorldTabProps;
export type CharacterRelationshipTabSource = Omit<CharactersTabInputProps, 'projectId'> & RelationshipsTabInputProps;
export type OutlinesTabInputProps = Omit<OutlinesTabProps, 'chapterOutlinesRenderBatchSize' | 'partOutlinesRenderBatchSize'>;
export type OutlinesTabSource = Omit<OutlinesTabInputProps, 'projectId'>;
export type ChaptersTabInputProps = Omit<ChaptersTabProps, 'renderBatchSize'>;
export type ChaptersTabSource = Omit<
  ChaptersTabInputProps,
  'projectId' | 'suggestedImportChapterNumber' | 'onChapterImported'
> & {
  latestChapterNumber: number;
  fetchProject: () => Promise<void>;
};

export type NovelDetailTabSources = {
  overviewWorld: OverviewWorldTabSource;
  characterRelationship: CharacterRelationshipTabSource;
  outlines: OutlinesTabSource;
  chapters: ChaptersTabSource;
};

export type UseNovelDetailTabPropsParams = {
  projectId: string;
  sources: NovelDetailTabSources;
};

export type NovelDetailTabProps = {
  overviewTabProps: OverviewTabProps;
  worldTabProps: WorldTabProps;
  charactersTabProps: CharactersTabInputProps;
  relationshipsTabProps: RelationshipsTabInputProps;
  outlinesTabProps: OutlinesTabInputProps;
  chaptersTabProps: ChaptersTabInputProps;
};
