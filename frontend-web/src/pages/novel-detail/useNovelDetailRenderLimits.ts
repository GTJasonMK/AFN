import { useEffect, useState } from 'react';

export const CHARACTERS_RENDER_BATCH_SIZE = 24;
export const RELATIONSHIPS_RENDER_BATCH_SIZE = 24;
export const CHAPTER_OUTLINES_RENDER_BATCH_SIZE = 40;
export const PART_OUTLINES_RENDER_BATCH_SIZE = 20;
export const COMPLETED_CHAPTERS_RENDER_BATCH_SIZE = 120;

const INITIAL_CHARACTERS_RENDER_LIMIT = CHARACTERS_RENDER_BATCH_SIZE;
const INITIAL_RELATIONSHIPS_RENDER_LIMIT = RELATIONSHIPS_RENDER_BATCH_SIZE;
const INITIAL_CHAPTER_OUTLINES_RENDER_LIMIT = CHAPTER_OUTLINES_RENDER_BATCH_SIZE;
const INITIAL_PART_OUTLINES_RENDER_LIMIT = PART_OUTLINES_RENDER_BATCH_SIZE;
const INITIAL_COMPLETED_CHAPTERS_RENDER_LIMIT = COMPLETED_CHAPTERS_RENDER_BATCH_SIZE;

type UseNovelDetailRenderLimitsParams = {
  id: string | undefined;
  activeTab: string;
  deferredChaptersSearch: string;
};

export const useNovelDetailRenderLimits = ({
  id,
  activeTab,
  deferredChaptersSearch,
}: UseNovelDetailRenderLimitsParams) => {
  const [charactersRenderLimit, setCharactersRenderLimit] = useState(INITIAL_CHARACTERS_RENDER_LIMIT);
  const [relationshipsRenderLimit, setRelationshipsRenderLimit] = useState(INITIAL_RELATIONSHIPS_RENDER_LIMIT);
  const [chapterOutlinesRenderLimit, setChapterOutlinesRenderLimit] = useState(INITIAL_CHAPTER_OUTLINES_RENDER_LIMIT);
  const [partOutlinesRenderLimit, setPartOutlinesRenderLimit] = useState(INITIAL_PART_OUTLINES_RENDER_LIMIT);
  const [completedChaptersRenderLimit, setCompletedChaptersRenderLimit] = useState(INITIAL_COMPLETED_CHAPTERS_RENDER_LIMIT);

  useEffect(() => {
    setCharactersRenderLimit(INITIAL_CHARACTERS_RENDER_LIMIT);
    setRelationshipsRenderLimit(INITIAL_RELATIONSHIPS_RENDER_LIMIT);
    setChapterOutlinesRenderLimit(INITIAL_CHAPTER_OUTLINES_RENDER_LIMIT);
    setPartOutlinesRenderLimit(INITIAL_PART_OUTLINES_RENDER_LIMIT);
    setCompletedChaptersRenderLimit(INITIAL_COMPLETED_CHAPTERS_RENDER_LIMIT);
  }, [id]);

  useEffect(() => {
    if (activeTab === 'characters') {
      setCharactersRenderLimit(INITIAL_CHARACTERS_RENDER_LIMIT);
      return;
    }
    if (activeTab === 'relationships') {
      setRelationshipsRenderLimit(INITIAL_RELATIONSHIPS_RENDER_LIMIT);
      return;
    }
    if (activeTab === 'outlines') {
      setChapterOutlinesRenderLimit(INITIAL_CHAPTER_OUTLINES_RENDER_LIMIT);
      setPartOutlinesRenderLimit(INITIAL_PART_OUTLINES_RENDER_LIMIT);
      return;
    }
    if (activeTab === 'chapters') {
      setCompletedChaptersRenderLimit(INITIAL_COMPLETED_CHAPTERS_RENDER_LIMIT);
    }
  }, [activeTab]);

  useEffect(() => {
    if (activeTab !== 'chapters') return;
    setCompletedChaptersRenderLimit(INITIAL_COMPLETED_CHAPTERS_RENDER_LIMIT);
  }, [activeTab, deferredChaptersSearch]);

  return {
    charactersRenderLimit,
    relationshipsRenderLimit,
    chapterOutlinesRenderLimit,
    partOutlinesRenderLimit,
    completedChaptersRenderLimit,
    setCharactersRenderLimit,
    setRelationshipsRenderLimit,
    setChapterOutlinesRenderLimit,
    setPartOutlinesRenderLimit,
    setCompletedChaptersRenderLimit,
  };
};
