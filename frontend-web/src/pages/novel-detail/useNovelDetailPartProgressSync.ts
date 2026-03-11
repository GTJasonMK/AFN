import { useCallback, useEffect } from 'react';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import { writerApi } from '../../api/writer';
import { writeNovelDetailPartProgress } from './bootstrapCache';

type UseNovelDetailPartProgressSyncParams = {
  projectId: string;
  activeTab: string;
  partProgress: any | null;
  setPartProgress: Dispatch<SetStateAction<any | null>>;
  setPartLoading: Dispatch<SetStateAction<boolean>>;
  hasPartProgressBootstrapRef: MutableRefObject<boolean>;
  fetchProject: () => Promise<void>;
};

export const useNovelDetailPartProgressSync = ({
  projectId,
  activeTab,
  partProgress,
  setPartProgress,
  setPartLoading,
  hasPartProgressBootstrapRef,
  fetchProject,
}: UseNovelDetailPartProgressSyncParams) => {
  useEffect(() => {
    writeNovelDetailPartProgress(projectId, partProgress ?? null);
    hasPartProgressBootstrapRef.current = partProgress !== null;
  }, [hasPartProgressBootstrapRef, partProgress, projectId]);

  const fetchPartProgress = useCallback(async () => {
    const hadPartSnapshot = hasPartProgressBootstrapRef.current;
    if (!hadPartSnapshot) {
      setPartLoading(true);
    }
    try {
      const data = await writerApi.getPartOutlines(projectId);
      setPartProgress(data);
      hasPartProgressBootstrapRef.current = data !== null;
      writeNovelDetailPartProgress(projectId, data ?? null);
    } catch (e) {
      if (!hadPartSnapshot) {
        setPartProgress(null);
        hasPartProgressBootstrapRef.current = false;
      }
    } finally {
      setPartLoading(false);
    }
  }, [hasPartProgressBootstrapRef, projectId, setPartLoading, setPartProgress]);

  const refreshProjectAndPartProgress = useCallback(async () => {
    await fetchProject();
    await fetchPartProgress();
  }, [fetchPartProgress, fetchProject]);

  useEffect(() => {
    if (activeTab !== 'outlines') return;
    fetchPartProgress();
  }, [activeTab, fetchPartProgress]);

  return {
    fetchPartProgress,
    refreshProjectAndPartProgress,
  };
};
