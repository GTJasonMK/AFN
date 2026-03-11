import { useCallback, useMemo } from 'react';
import type { NovelDetailTabProps, NovelDetailTabSources } from './types';

type UseChaptersTabPropsParams = {
  projectId: string;
  chapters: NovelDetailTabSources['chapters'];
};

export const useChaptersTabProps = ({
  projectId,
  chapters,
}: UseChaptersTabPropsParams): NovelDetailTabProps['chaptersTabProps'] => {
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

  const onChapterImported = useCallback(async (chapterNo: number) => {
    await fetchProject();
    setSelectedCompletedChapterNumber(chapterNo);
  }, [fetchProject, setSelectedCompletedChapterNumber]);

  const chaptersTabProps = useMemo(() => ({
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

  return chaptersTabProps;
};
