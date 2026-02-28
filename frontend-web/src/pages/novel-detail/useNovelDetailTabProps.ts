import { useCallback, useMemo } from 'react';
import type { OverviewTabProps } from './OverviewTab';
import type { WorldTabProps } from './WorldTab';
import type { CharactersTabProps } from './CharactersTab';
import type { RelationshipsTabProps } from './RelationshipsTab';
import type { OutlinesTabProps } from './OutlinesTab';
import type { ChaptersTabProps } from './ChaptersTab';

type CharactersTabInputProps = Omit<CharactersTabProps, 'renderBatchSize'>;
type RelationshipsTabInputProps = Omit<RelationshipsTabProps, 'renderBatchSize'>;
type OverviewWorldTabSource = OverviewTabProps & WorldTabProps;
type CharacterRelationshipTabSource = Omit<CharactersTabInputProps, 'projectId'> & RelationshipsTabInputProps;
type OutlinesTabInputProps = Omit<OutlinesTabProps, 'chapterOutlinesRenderBatchSize' | 'partOutlinesRenderBatchSize'>;
type OutlinesTabSource = Omit<OutlinesTabInputProps, 'projectId'>;
type ChaptersTabInputProps = Omit<ChaptersTabProps, 'renderBatchSize'>;
type ChaptersTabSource = Omit<ChaptersTabInputProps, 'projectId' | 'suggestedImportChapterNumber' | 'onChapterImported'> & {
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

type UseNovelDetailTabPropsResult = {
  overviewTabProps: OverviewTabProps;
  worldTabProps: WorldTabProps;
  charactersTabProps: CharactersTabInputProps;
  relationshipsTabProps: RelationshipsTabInputProps;
  outlinesTabProps: OutlinesTabInputProps;
  chaptersTabProps: ChaptersTabInputProps;
};

export const useNovelDetailTabProps = ({
  projectId,
  sources,
}: UseNovelDetailTabPropsParams): UseNovelDetailTabPropsResult => {
  const { overviewWorld, characterRelationship, outlines, chapters } = sources;
  const {
    blueprintData,
    setBlueprintData,
    project,
    importStatus,
    importStatusLoading,
    importStarting,
    startImportAnalysis,
    refreshImportStatus,
    cancelImportAnalysis,
    worldEditMode,
    setWorldEditMode,
    worldSettingObj,
    worldListToText,
    worldTextToList,
    updateWorldSettingDraft,
    worldSettingDraft,
    setWorldSettingDraft,
    worldSettingError,
  } = overviewWorld;
  const {
    charactersList,
    visibleCharacters,
    remainingCharacters,
    charactersView,
    setCharactersView,
    handleAddChar,
    handleEditChar,
    handleDeleteChar,
    setCharactersRenderLimit,
    characterNames,
    characterProfiles,
    relationshipsList,
    visibleRelationships,
    remainingRelationships,
    handleAddRel,
    handleEditRel,
    handleDeleteRel,
    setRelationshipsRenderLimit,
  } = characterRelationship;
  const {
    completedChapters,
    visibleCompletedChapters,
    remainingCompletedChapters,
    setCompletedChaptersRenderLimit,
    chaptersSearch,
    setChaptersSearch,
    selectedCompletedChapterNumber,
    setSelectedCompletedChapterNumber,
    selectedCompletedChapter,
    selectedCompletedChapterLoading,
    exportSelectedChapter,
    latestChapterNumber,
    fetchProject,
    safeNavigate,
  } = chapters;

  const overviewTabProps: OverviewTabProps = {
    blueprintData,
    setBlueprintData,
    project,
    importStatus,
    importStatusLoading,
    importStarting,
    startImportAnalysis,
    refreshImportStatus,
    cancelImportAnalysis,
  };

  const worldTabProps: WorldTabProps = {
    worldEditMode,
    setWorldEditMode,
    worldSettingObj,
    worldListToText,
    worldTextToList,
    updateWorldSettingDraft,
    worldSettingDraft,
    setWorldSettingDraft,
    worldSettingError,
  };

  const charactersTabProps: CharactersTabInputProps = {
    projectId,
    charactersList,
    visibleCharacters,
    remainingCharacters,
    charactersView,
    setCharactersView,
    handleAddChar,
    handleEditChar,
    handleDeleteChar,
    setCharactersRenderLimit,
    characterNames,
    characterProfiles,
  };

  const relationshipsTabProps: RelationshipsTabInputProps = {
    relationshipsList,
    visibleRelationships,
    remainingRelationships,
    handleAddRel,
    handleEditRel,
    handleDeleteRel,
    setRelationshipsRenderLimit,
  };

  const outlinesTabProps: OutlinesTabInputProps = {
    projectId,
    ...outlines,
  };

  const onChapterImported = useCallback(async (chapterNo: number) => {
    await fetchProject();
    setSelectedCompletedChapterNumber(chapterNo);
  }, [fetchProject, setSelectedCompletedChapterNumber]);

  const chaptersTabProps = useMemo<ChaptersTabInputProps>(() => ({
    projectId,
    completedChapters,
    visibleCompletedChapters,
    remainingCompletedChapters,
    setCompletedChaptersRenderLimit,
    chaptersSearch,
    setChaptersSearch,
    selectedCompletedChapterNumber,
    setSelectedCompletedChapterNumber,
    selectedCompletedChapter,
    selectedCompletedChapterLoading,
    exportSelectedChapter,
    suggestedImportChapterNumber: latestChapterNumber + 1,
    onChapterImported,
    safeNavigate,
  }), [
    chaptersSearch,
    completedChapters,
    exportSelectedChapter,
    latestChapterNumber,
    onChapterImported,
    projectId,
    remainingCompletedChapters,
    safeNavigate,
    selectedCompletedChapter,
    selectedCompletedChapterLoading,
    selectedCompletedChapterNumber,
    setChaptersSearch,
    setCompletedChaptersRenderLimit,
    setSelectedCompletedChapterNumber,
    visibleCompletedChapters,
  ]);

  return {
    overviewTabProps,
    worldTabProps,
    charactersTabProps,
    relationshipsTabProps,
    outlinesTabProps,
    chaptersTabProps,
  };
};
