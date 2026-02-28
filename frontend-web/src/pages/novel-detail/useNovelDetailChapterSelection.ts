import { useEffect } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { writerApi } from '../../api/writer';
import {
  readNovelDetailChapterDetail,
  writeNovelDetailChapterDetail,
  writeNovelDetailChapterSelection,
} from './bootstrapCache';

type UseNovelDetailChapterSelectionParams = {
  id: string | undefined;
  activeTab: string;
  completedChapters: any[];
  selectedCompletedChapterNumber: number | null;
  selectedCompletedChapter: any | null;
  setSelectedCompletedChapterNumber: Dispatch<SetStateAction<number | null>>;
  setSelectedCompletedChapter: Dispatch<SetStateAction<any | null>>;
  setSelectedCompletedChapterLoading: Dispatch<SetStateAction<boolean>>;
};

export const useNovelDetailChapterSelection = ({
  id,
  activeTab,
  completedChapters,
  selectedCompletedChapterNumber,
  selectedCompletedChapter,
  setSelectedCompletedChapterNumber,
  setSelectedCompletedChapter,
  setSelectedCompletedChapterLoading,
}: UseNovelDetailChapterSelectionParams) => {
  useEffect(() => {
    if (!id) return;
    const chapterNo = Number(selectedCompletedChapterNumber || 0);
    const detailChapterNo = Number(selectedCompletedChapter?.chapter_number || 0);
    const matchedDetail =
      chapterNo > 0 && detailChapterNo === chapterNo ? selectedCompletedChapter : null;

    writeNovelDetailChapterSelection(id, chapterNo > 0 ? chapterNo : null, matchedDetail);
  }, [id, selectedCompletedChapter, selectedCompletedChapterNumber]);

  // 已完成章节 Tab：默认选中第一章；若选择的章节被删除则自动回退到第一章
  useEffect(() => {
    if (activeTab !== 'chapters') return;
    if (!completedChapters.length) {
      setSelectedCompletedChapterNumber(null);
      setSelectedCompletedChapter(null);
      return;
    }
    setSelectedCompletedChapterNumber((prev) => {
      if (prev && completedChapters.some((c: any) => Number(c?.chapter_number || 0) === Number(prev))) return prev;
      const first = Number(completedChapters[0]?.chapter_number || 0);
      return first || null;
    });
  }, [activeTab, completedChapters, setSelectedCompletedChapter, setSelectedCompletedChapterNumber]);

  // 已完成章节 Tab：按需加载正文（避免一次性把所有正文塞进页面）
  useEffect(() => {
    if (activeTab !== 'chapters') return;
    if (!id) return;
    const chapterNo = Number(selectedCompletedChapterNumber || 0);
    if (!chapterNo) {
      setSelectedCompletedChapter(null);
      setSelectedCompletedChapterLoading(false);
      writeNovelDetailChapterSelection(id, null, null);
      return;
    }

    const chapterDetailCache = readNovelDetailChapterDetail(id, chapterNo);
    const hasCachedDetail = Boolean(chapterDetailCache?.chapterDetail);
    if (hasCachedDetail) {
      setSelectedCompletedChapter(chapterDetailCache?.chapterDetail ?? null);
      setSelectedCompletedChapterLoading(false);
      writeNovelDetailChapterSelection(id, chapterNo, chapterDetailCache?.chapterDetail ?? null);
    } else {
      setSelectedCompletedChapterLoading(true);
    }

    let cancelled = false;
    writerApi
      .getChapter(id, chapterNo)
      .then((data) => {
        if (cancelled) return;
        setSelectedCompletedChapter(data);
        writeNovelDetailChapterDetail(id, chapterNo, data ?? null);
        writeNovelDetailChapterSelection(id, chapterNo, data ?? null);
      })
      .catch((e) => {
        console.error(e);
        if (cancelled) return;
        if (!hasCachedDetail) {
          setSelectedCompletedChapter(null);
        }
      })
      .finally(() => {
        if (cancelled) return;
        setSelectedCompletedChapterLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [
    activeTab,
    id,
    selectedCompletedChapterNumber,
    setSelectedCompletedChapter,
    setSelectedCompletedChapterLoading,
  ]);
};
