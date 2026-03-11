import {
  useCharacterRelationshipTabProps,
} from './tab-props/useCharacterRelationshipTabProps';
import {
  useChaptersTabProps,
} from './tab-props/useChaptersTabProps';
import {
  useOutlinesTabProps,
} from './tab-props/useOutlinesTabProps';
import {
  useOverviewWorldTabProps,
} from './tab-props/useOverviewWorldTabProps';
import type {
  NovelDetailTabProps,
  UseNovelDetailTabPropsParams,
} from './tab-props/types';

export type {
  NovelDetailTabProps,
  NovelDetailTabSources,
  UseNovelDetailTabPropsParams,
} from './tab-props/types';

export const useNovelDetailTabProps = ({
  projectId,
  sources,
}: UseNovelDetailTabPropsParams): NovelDetailTabProps => {
  const { overviewWorld, characterRelationship, outlines, chapters } = sources;
  const { overviewTabProps, worldTabProps } = useOverviewWorldTabProps(overviewWorld);
  const { charactersTabProps, relationshipsTabProps } = useCharacterRelationshipTabProps({
    projectId,
    characterRelationship,
  });
  const outlinesTabProps = useOutlinesTabProps({ projectId, outlines });
  const chaptersTabProps = useChaptersTabProps({ projectId, chapters });

  return {
    overviewTabProps,
    worldTabProps,
    charactersTabProps,
    relationshipsTabProps,
    outlinesTabProps,
    chaptersTabProps,
  };
};
