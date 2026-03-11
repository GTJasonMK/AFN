import { useNovelDetailOutlineDerived } from './derived-data/useNovelDetailOutlineDerived';
import { useNovelDetailCharacterDerived } from './derived-data/useNovelDetailCharacterDerived';
import { useNovelDetailCompletedChapterDerived } from './derived-data/useNovelDetailCompletedChapterDerived';

type UseNovelDetailDerivedDataParams = {
  blueprintData: any;
  partProgress: any | null;
  project: any;
  deferredChaptersSearch: string;
  charactersRenderLimit: number;
  relationshipsRenderLimit: number;
  chapterOutlinesRenderLimit: number;
  partOutlinesRenderLimit: number;
  completedChaptersRenderLimit: number;
};

export const useNovelDetailDerivedData = ({
  blueprintData,
  partProgress,
  project,
  deferredChaptersSearch,
  charactersRenderLimit,
  relationshipsRenderLimit,
  chapterOutlinesRenderLimit,
  partOutlinesRenderLimit,
  completedChaptersRenderLimit,
}: UseNovelDetailDerivedDataParams) => {
  const outlineDerived = useNovelDetailOutlineDerived({
    blueprintData,
    partProgress,
    chapterOutlinesRenderLimit,
    partOutlinesRenderLimit,
  });

  const characterDerived = useNovelDetailCharacterDerived({
    blueprintData,
    charactersRenderLimit,
    relationshipsRenderLimit,
  });

  const completedChapterDerived = useNovelDetailCompletedChapterDerived({
    project,
    chapterOutlines: outlineDerived.chapterOutlines,
    deferredChaptersSearch,
    completedChaptersRenderLimit,
  });

  return {
    ...outlineDerived,
    ...completedChapterDerived,
    ...characterDerived,
  };
};
