import { useCallback, useEffect } from 'react';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import { novelsApi } from '../../api/novels';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';
import { writeNovelDetailImportStatus } from './bootstrapCache';

type UseNovelDetailImportStatusParams = {
  id: string | undefined;
  importStatus: any | null;
  projectImportAnalysisStatus: unknown;
  setImportStatus: Dispatch<SetStateAction<any | null>>;
  setImportStatusLoading: Dispatch<SetStateAction<boolean>>;
  setImportStarting: Dispatch<SetStateAction<boolean>>;
  hasImportStatusBootstrapRef: MutableRefObject<boolean>;
  fetchProject: () => Promise<void>;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailImportStatus = ({
  id,
  importStatus,
  projectImportAnalysisStatus,
  setImportStatus,
  setImportStatusLoading,
  setImportStarting,
  hasImportStatusBootstrapRef,
  fetchProject,
  addToast,
}: UseNovelDetailImportStatusParams) => {
  const refreshImportStatus = useCallback(async () => {
    if (!id) return;
    setImportStatusLoading(true);
    const hadImportSnapshot = hasImportStatusBootstrapRef.current;
    try {
      const status = await novelsApi.getImportAnalysisStatus(id);
      setImportStatus(status);
      hasImportStatusBootstrapRef.current = status !== null;
      writeNovelDetailImportStatus(id, status ?? null);
    } catch (e) {
      console.error(e);
      if (!hadImportSnapshot) {
        setImportStatus(null);
        hasImportStatusBootstrapRef.current = false;
      }
    } finally {
      setImportStatusLoading(false);
    }
  }, [hasImportStatusBootstrapRef, id, setImportStatus, setImportStatusLoading]);

  const cancelImportAnalysis = useCallback(async () => {
    if (!id) return;
    try {
      await novelsApi.cancelImportAnalysis(id);
      addToast('已请求取消分析任务', 'success');
      await refreshImportStatus();
      await fetchProject();
    } catch (e) {
      console.error(e);
      addToast('取消失败', 'error');
    }
  }, [addToast, fetchProject, id, refreshImportStatus]);

  const startImportAnalysis = useCallback(async () => {
    if (!id) return;

    const status = String(importStatus?.status || projectImportAnalysisStatus || 'pending');
    const isResume = status === 'failed' || status === 'cancelled';

    const ok = await confirmDialog({
      title: '导入分析',
      message: isResume
        ? '检测到之前的分析未完成，将尝试从断点继续。\n\n确定要继续分析吗？'
        : '将开始分析导入的小说内容，过程可能较久。\n\n确定要开始分析吗？',
      confirmText: isResume ? '继续分析' : '开始分析',
      dialogType: 'warning',
    });
    if (!ok) return;

    setImportStarting(true);
    try {
      await novelsApi.startImportAnalysis(id);
      addToast(isResume ? '已开始继续分析…' : '已开始分析…', 'success');
      await refreshImportStatus();
      await fetchProject();
    } catch (e) {
      console.error(e);
      addToast('启动失败', 'error');
    } finally {
      setImportStarting(false);
    }
  }, [
    addToast,
    fetchProject,
    id,
    importStatus?.status,
    projectImportAnalysisStatus,
    refreshImportStatus,
    setImportStarting,
  ]);

  useEffect(() => {
    if (!id) return;
    const status = String(importStatus?.status || projectImportAnalysisStatus || '');
    if (status !== 'analyzing') return;

    const timer = window.setInterval(() => {
      refreshImportStatus().catch(() => {});
    }, 2000);
    return () => window.clearInterval(timer);
  }, [id, importStatus?.status, projectImportAnalysisStatus, refreshImportStatus]);

  useEffect(() => {
    if (!id) return;
    writeNovelDetailImportStatus(id, importStatus ?? null);
    hasImportStatusBootstrapRef.current = importStatus !== null;
  }, [hasImportStatusBootstrapRef, id, importStatus]);

  return {
    refreshImportStatus,
    cancelImportAnalysis,
    startImportAnalysis,
  };
};
