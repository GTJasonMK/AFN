import { useCallback, useEffect } from 'react';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';
import { useNovelDetailBootstrap } from './useNovelDetailBootstrap';
import { useNovelDetailImportStatus } from './useNovelDetailImportStatus';

type UseNovelDetailProjectSyncParams = {
  projectId: string;
  isBlueprintDirty: boolean;
  dirtySummary: string;
  applyProjectBlueprint: (blueprint: any) => void;
  setProject: Dispatch<SetStateAction<any>>;
  setLoading: Dispatch<SetStateAction<boolean>>;
  importStatus: any | null;
  projectImportAnalysisStatus: any;
  setImportStatus: Dispatch<SetStateAction<any | null>>;
  setImportStatusLoading: Dispatch<SetStateAction<boolean>>;
  setImportStarting: Dispatch<SetStateAction<boolean>>;
  setPartProgress: Dispatch<SetStateAction<any | null>>;
  setSelectedCompletedChapterNumber: Dispatch<SetStateAction<number | null>>;
  setSelectedCompletedChapter: Dispatch<SetStateAction<any | null>>;
  hasImportStatusBootstrapRef: MutableRefObject<boolean>;
  hasPartProgressBootstrapRef: MutableRefObject<boolean>;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailProjectSync = ({
  projectId,
  isBlueprintDirty,
  dirtySummary,
  applyProjectBlueprint,
  setProject,
  setLoading,
  importStatus,
  projectImportAnalysisStatus,
  setImportStatus,
  setImportStatusLoading,
  setImportStarting,
  setPartProgress,
  setSelectedCompletedChapterNumber,
  setSelectedCompletedChapter,
  hasImportStatusBootstrapRef,
  hasPartProgressBootstrapRef,
  addToast,
}: UseNovelDetailProjectSyncParams) => {
  const applyProjectPayload = useCallback((data: any) => {
    setProject(data);
    applyProjectBlueprint(data?.blueprint);
  }, [applyProjectBlueprint, setProject]);

  const { fetchProject } = useNovelDetailBootstrap({
    id: projectId,
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
  });

  const fetchProjectButton = useCallback(async () => {
    if (isBlueprintDirty) {
      const ok = await confirmDialog({
        title: '刷新确认',
        message: `${dirtySummary || '有未保存的修改'}。\n\n确定要刷新并丢弃本地修改吗？`,
        confirmText: '刷新并丢弃',
        dialogType: 'warning',
      });
      if (!ok) return;
    }
    await fetchProject();
  }, [dirtySummary, fetchProject, isBlueprintDirty]);

  const {
    refreshImportStatus,
    cancelImportAnalysis,
    startImportAnalysis,
  } = useNovelDetailImportStatus({
    id: projectId,
    importStatus,
    projectImportAnalysisStatus,
    setImportStatus,
    setImportStatusLoading,
    setImportStarting,
    hasImportStatusBootstrapRef,
    fetchProject,
    addToast,
  });

  useEffect(() => {
    fetchProject();
  }, [fetchProject]);

  return {
    fetchProject,
    fetchProjectButton,
    refreshImportStatus,
    cancelImportAnalysis,
    startImportAnalysis,
  };
};
