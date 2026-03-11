import { useCallback, useMemo } from 'react';

const lowerBound = (list: number[], target: number): number => {
  let left = 0;
  let right = list.length;
  while (left < right) {
    const mid = Math.floor((left + right) / 2);
    if (list[mid] < target) left = mid + 1;
    else right = mid;
  }
  return left;
};

const upperBound = (list: number[], target: number): number => {
  let left = 0;
  let right = list.length;
  while (left < right) {
    const mid = Math.floor((left + right) / 2);
    if (list[mid] <= target) left = mid + 1;
    else right = mid;
  }
  return left;
};

type UseNovelDetailOutlineDerivedParams = {
  blueprintData: any;
  partProgress: any | null;
  chapterOutlinesRenderLimit: number;
  partOutlinesRenderLimit: number;
};

export const useNovelDetailOutlineDerived = ({
  blueprintData,
  partProgress,
  chapterOutlinesRenderLimit,
  partOutlinesRenderLimit,
}: UseNovelDetailOutlineDerivedParams) => {
  const chapterOutlines = useMemo(() => {
    const list = Array.isArray(blueprintData?.chapter_outline) ? blueprintData.chapter_outline : [];
    return [...list].sort((a: any, b: any) => Number(a.chapter_number || 0) - Number(b.chapter_number || 0));
  }, [blueprintData]);

  const partOutlines = useMemo(() => {
    const list = Array.isArray(partProgress?.parts) ? partProgress.parts : [];
    return [...list].sort((a: any, b: any) => Number(a?.part_number || 0) - Number(b?.part_number || 0));
  }, [partProgress]);

  const partCoveredChapters = useMemo(() => {
    if (!partOutlines.length) return 0;
    return partOutlines.reduce((max: number, part: any) => {
      const end = Number(part?.end_chapter || 0);
      return Math.max(max, Number.isFinite(end) ? end : 0);
    }, 0);
  }, [partOutlines]);

  const partTotalChapters = useMemo(() => {
    const value = Number(blueprintData?.total_chapters || 0);
    return Number.isFinite(value) ? value : 0;
  }, [blueprintData]);

  const canContinuePartOutlines = useMemo(() => {
    if (!partTotalChapters || !partOutlines.length) return false;
    return partCoveredChapters > 0 && partCoveredChapters < partTotalChapters;
  }, [partCoveredChapters, partOutlines.length, partTotalChapters]);

  const maxDeletablePartCount = useMemo(() => Math.max(0, partOutlines.length - 1), [partOutlines.length]);

  const chapterOutlineNumbers = useMemo(() => {
    return chapterOutlines
      .map((outline: any) => Number(outline?.chapter_number || 0))
      .filter((num: number) => Number.isFinite(num) && num > 0);
  }, [chapterOutlines]);

  const countOutlinesInRange = useCallback((startChapter: number, endChapter: number) => {
    if (!Number.isFinite(startChapter) || !Number.isFinite(endChapter)) return 0;
    if (endChapter < startChapter) return 0;
    const startIndex = lowerBound(chapterOutlineNumbers, Math.max(1, Math.floor(startChapter)));
    const endIndex = upperBound(chapterOutlineNumbers, Math.floor(endChapter));
    return Math.max(0, endIndex - startIndex);
  }, [chapterOutlineNumbers]);

  const visibleChapterOutlines = useMemo(() => {
    return chapterOutlines.slice(0, chapterOutlinesRenderLimit);
  }, [chapterOutlines, chapterOutlinesRenderLimit]);

  const visiblePartOutlines = useMemo(() => {
    return partOutlines.slice(0, partOutlinesRenderLimit);
  }, [partOutlines, partOutlinesRenderLimit]);

  const remainingChapterOutlines = Math.max(0, chapterOutlines.length - visibleChapterOutlines.length);
  const remainingPartOutlines = Math.max(0, partOutlines.length - visiblePartOutlines.length);

  return {
    chapterOutlines,
    partOutlines,
    partCoveredChapters,
    partTotalChapters,
    canContinuePartOutlines,
    maxDeletablePartCount,
    countOutlinesInRange,
    visibleChapterOutlines,
    visiblePartOutlines,
    remainingChapterOutlines,
    remainingPartOutlines,
  };
};
