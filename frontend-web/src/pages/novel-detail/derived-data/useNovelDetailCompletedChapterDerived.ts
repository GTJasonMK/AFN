import { useMemo } from 'react';

type UseNovelDetailCompletedChapterDerivedParams = {
  project: any;
  chapterOutlines: any[];
  deferredChaptersSearch: string;
  completedChaptersRenderLimit: number;
};

export const useNovelDetailCompletedChapterDerived = ({
  project,
  chapterOutlines,
  deferredChaptersSearch,
  completedChaptersRenderLimit,
}: UseNovelDetailCompletedChapterDerivedParams) => {
  const chaptersByNumber = useMemo(() => {
    const map = new Map<number, any>();
    const list = Array.isArray(project?.chapters) ? project.chapters : [];
    list.forEach((chapter: any) => map.set(Number(chapter.chapter_number), chapter));
    return map;
  }, [project]);

  const completedChapters = useMemo(() => {
    const list = Array.isArray(project?.chapters) ? project.chapters : [];
    const completed = list.filter((chapter: any) => {
      const hasSelected = typeof chapter?.selected_version === 'number';
      const hasContent = Boolean(String(chapter?.content || '').trim());
      return hasSelected || hasContent;
    });
    return [...completed].sort((a, b) => Number(a?.chapter_number || 0) - Number(b?.chapter_number || 0));
  }, [project]);

  const filteredCompletedChapters = useMemo(() => {
    const query = String(deferredChaptersSearch || '').trim().toLowerCase();
    if (!query) return completedChapters;
    return completedChapters.filter((chapter: any) => {
      const chapterNo = String(chapter?.chapter_number || '').toLowerCase();
      const title = String(chapter?.title || '').toLowerCase();
      return chapterNo.includes(query) || title.includes(query) || `第${chapterNo}章`.includes(query);
    });
  }, [completedChapters, deferredChaptersSearch]);

  const visibleCompletedChapters = useMemo(() => {
    return filteredCompletedChapters.slice(0, completedChaptersRenderLimit);
  }, [filteredCompletedChapters, completedChaptersRenderLimit]);

  const remainingCompletedChapters = Math.max(0, filteredCompletedChapters.length - visibleCompletedChapters.length);

  const latestChapterNumber = useMemo(() => {
    const fromDb = Array.isArray(project?.chapters)
      ? Math.max(0, ...project.chapters.map((chapter: any) => Number(chapter?.chapter_number || 0)))
      : 0;
    const fromOutline = chapterOutlines.length
      ? Number(chapterOutlines[chapterOutlines.length - 1]?.chapter_number || 0)
      : 0;
    return Math.max(0, fromDb, fromOutline);
  }, [chapterOutlines, project]);

  return {
    chaptersByNumber,
    completedChapters,
    visibleCompletedChapters,
    remainingCompletedChapters,
    latestChapterNumber,
  };
};
