import { useCallback, useEffect } from 'react';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import { novelsApi } from '../../api/novels';
import { scheduleIdleTask } from '../../utils/scheduleIdleTask';
import {
  readNovelDetailBootstrap,
  readNovelDetailChapterSelection,
  readNovelDetailImportStatus,
  readNovelDetailPartProgress,
  writeNovelDetailBootstrap,
  writeNovelDetailImportStatus,
} from './bootstrapCache';

type UseNovelDetailBootstrapParams = {
  id: string | undefined;
  applyProjectPayload: (data: any) => void;
  setProject: Dispatch<SetStateAction<any>>;
  setLoading: Dispatch<SetStateAction<boolean>>;
  setImportStatus: Dispatch<SetStateAction<any | null>>;
  setImportStatusLoading: Dispatch<SetStateAction<boolean>>;
  setPartProgress: Dispatch<SetStateAction<any | null>>;
  setSelectedCompletedChapterNumber: Dispatch<SetStateAction<number | null>>;
  setSelectedCompletedChapter: Dispatch<SetStateAction<any | null>>;
  hasImportStatusBootstrapRef: MutableRefObject<boolean>;
  hasPartProgressBootstrapRef: MutableRefObject<boolean>;
};

export const useNovelDetailBootstrap = ({
  id,
  applyProjectPayload,
  setProject,
  setLoading,
  setImportStatus,
  setImportStatusLoading,
  setPartProgress,
  setSelectedCompletedChapterNumber,
  setSelectedCompletedChapter,
  hasImportStatusBootstrapRef,
  hasPartProgressBootstrapRef,
}: UseNovelDetailBootstrapParams) => {
  useEffect(() => {
    if (!id) return;
    const cached = readNovelDetailBootstrap(id);
    if (!cached?.project) {
      setProject(null);
      setLoading(true);
      return;
    }
    applyProjectPayload(cached.project);
    setLoading(false);
  }, [applyProjectPayload, id, setLoading, setProject]);

  useEffect(() => {
    if (!id) return;

    const importCached = readNovelDetailImportStatus(id);
    if (importCached) {
      setImportStatus(importCached.importStatus ?? null);
      hasImportStatusBootstrapRef.current = importCached.importStatus !== null;
    } else {
      setImportStatus(null);
      hasImportStatusBootstrapRef.current = false;
    }

    const partCached = readNovelDetailPartProgress(id);
    if (partCached) {
      setPartProgress(partCached.partProgress ?? null);
      hasPartProgressBootstrapRef.current = partCached.partProgress !== null;
    } else {
      setPartProgress(null);
      hasPartProgressBootstrapRef.current = false;
    }

    const chapterSelectionCached = readNovelDetailChapterSelection(id);
    const chapterNo = Number(chapterSelectionCached?.chapterNumber || 0);
    if (Number.isFinite(chapterNo) && chapterNo > 0) {
      setSelectedCompletedChapterNumber(chapterNo);
      setSelectedCompletedChapter(chapterSelectionCached?.chapterDetail ?? null);
    } else {
      setSelectedCompletedChapterNumber(null);
      setSelectedCompletedChapter(null);
    }
  }, [
    hasImportStatusBootstrapRef,
    hasPartProgressBootstrapRef,
    id,
    setImportStatus,
    setPartProgress,
    setSelectedCompletedChapter,
    setSelectedCompletedChapterNumber,
  ]);

  const fetchProject = useCallback(async () => {
    if (!id) return;

    try {
      const data = await novelsApi.get(id);
      applyProjectPayload(data);
      writeNovelDetailBootstrap(id, data);

      if (data.is_imported) {
        const hadImportSnapshot = hasImportStatusBootstrapRef.current;
        if (!hadImportSnapshot) {
          setImportStatusLoading(true);
        } else {
          setImportStatusLoading(false);
        }

        scheduleIdleTask(() => {
          void novelsApi
            .getImportAnalysisStatus(id)
            .then((status) => {
              setImportStatus(status);
              hasImportStatusBootstrapRef.current = status !== null;
              writeNovelDetailImportStatus(id, status ?? null);
            })
            .catch((e) => {
              console.error(e);
              if (!hadImportSnapshot) {
                setImportStatus(null);
                hasImportStatusBootstrapRef.current = false;
              }
            })
            .finally(() => {
              setImportStatusLoading(false);
            });
        }, { delay: 120, timeout: 2200 });
      } else {
        setImportStatus(null);
        hasImportStatusBootstrapRef.current = false;
        setImportStatusLoading(false);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [
    applyProjectPayload,
    hasImportStatusBootstrapRef,
    id,
    setImportStatus,
    setImportStatusLoading,
    setLoading,
  ]);

  return {
    fetchProject,
  };
};
