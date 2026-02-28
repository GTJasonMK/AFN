import { useCallback, useMemo } from 'react';

const CHARACTER_PROFILE_KEYS = [
  'appearance',
  'appearance_description',
  'looks',
  'look',
  'visual',
  'portrait',
  'portrait_prompt',
  'image_prompt',
  'description',
  'desc',
  'profile',
  '外貌',
  '外观',
  '形象',
  '描述',
] as const;

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
    const n = Number(blueprintData?.total_chapters || 0);
    return Number.isFinite(n) ? n : 0;
  }, [blueprintData]);

  const canContinuePartOutlines = useMemo(() => {
    if (!partTotalChapters || !partOutlines.length) return false;
    return partCoveredChapters > 0 && partCoveredChapters < partTotalChapters;
  }, [partCoveredChapters, partOutlines.length, partTotalChapters]);

  const maxDeletablePartCount = useMemo(() => Math.max(0, partOutlines.length - 1), [partOutlines.length]);

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

  const charactersList = useMemo(() => {
    return Array.isArray(blueprintData?.characters) ? blueprintData.characters : [];
  }, [blueprintData]);

  const relationshipsList = useMemo(() => {
    return Array.isArray(blueprintData?.relationships) ? blueprintData.relationships : [];
  }, [blueprintData]);

  const characterNames = useMemo(() => {
    const set = new Set<string>();
    charactersList.forEach((character: any) => {
      const name = String(character?.name || '').trim();
      if (name) set.add(name);
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'zh-CN'));
  }, [charactersList]);

  const characterProfiles = useMemo(() => {
    const map: Record<string, string> = {};
    for (const character of charactersList) {
      const name = String((character as any)?.name || '').trim();
      if (!name) continue;

      let desc = '';
      for (const key of CHARACTER_PROFILE_KEYS) {
        const value = (character as any)?.[key];
        if (typeof value === 'string' && value.trim()) {
          desc = value.trim();
          break;
        }
      }

      if (!desc) {
        const parts: string[] = [];
        for (const [key, value] of Object.entries(character || {})) {
          if (key === 'name') continue;
          if (typeof value === 'string' && value.trim()) parts.push(value.trim());
        }
        desc = parts.join('；').trim();
      }

      if (desc) map[name] = desc.length > 600 ? desc.slice(0, 600) : desc;
    }
    return map;
  }, [charactersList]);

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

  const visibleCharacters = useMemo(() => {
    return charactersList.slice(0, charactersRenderLimit);
  }, [charactersList, charactersRenderLimit]);

  const visibleRelationships = useMemo(() => {
    return relationshipsList.slice(0, relationshipsRenderLimit);
  }, [relationshipsList, relationshipsRenderLimit]);

  const visibleChapterOutlines = useMemo(() => {
    return chapterOutlines.slice(0, chapterOutlinesRenderLimit);
  }, [chapterOutlines, chapterOutlinesRenderLimit]);

  const visiblePartOutlines = useMemo(() => {
    return partOutlines.slice(0, partOutlinesRenderLimit);
  }, [partOutlines, partOutlinesRenderLimit]);

  const visibleCompletedChapters = useMemo(() => {
    return filteredCompletedChapters.slice(0, completedChaptersRenderLimit);
  }, [filteredCompletedChapters, completedChaptersRenderLimit]);

  const remainingCharacters = Math.max(0, charactersList.length - visibleCharacters.length);
  const remainingRelationships = Math.max(0, relationshipsList.length - visibleRelationships.length);
  const remainingChapterOutlines = Math.max(0, chapterOutlines.length - visibleChapterOutlines.length);
  const remainingPartOutlines = Math.max(0, partOutlines.length - visiblePartOutlines.length);
  const remainingCompletedChapters = Math.max(0, filteredCompletedChapters.length - visibleCompletedChapters.length);

  const latestChapterNumber = useMemo(() => {
    const fromDb = Array.isArray(project?.chapters)
      ? Math.max(0, ...project.chapters.map((chapter: any) => Number(chapter?.chapter_number || 0)))
      : 0;
    const fromOutline = chapterOutlines.length
      ? Number(chapterOutlines[chapterOutlines.length - 1]?.chapter_number || 0)
      : 0;
    return Math.max(1, fromDb, fromOutline);
  }, [chapterOutlines, project]);

  return {
    chapterOutlines,
    partOutlines,
    partCoveredChapters,
    partTotalChapters,
    canContinuePartOutlines,
    maxDeletablePartCount,
    chaptersByNumber,
    completedChapters,
    charactersList,
    relationshipsList,
    characterNames,
    characterProfiles,
    countOutlinesInRange,
    visibleCharacters,
    visibleRelationships,
    visibleChapterOutlines,
    visiblePartOutlines,
    visibleCompletedChapters,
    remainingCharacters,
    remainingRelationships,
    remainingChapterOutlines,
    remainingPartOutlines,
    remainingCompletedChapters,
    latestChapterNumber,
  };
};
