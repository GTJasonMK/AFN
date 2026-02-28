import { useCallback, useEffect, useRef } from 'react';
import type { NavigateFunction } from 'react-router-dom';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';

type UseNovelDetailLeaveGuardParams = {
  isBlueprintDirty: boolean;
  dirtySummary: string;
  navigate: NavigateFunction;
};

export const useNovelDetailLeaveGuard = ({
  isBlueprintDirty,
  dirtySummary,
  navigate,
}: UseNovelDetailLeaveGuardParams) => {
  const isBlueprintDirtyRef = useRef(false);
  const dirtySummaryRef = useRef('');
  const historyIdxRef = useRef<number>(0);
  const ignoreNextPopStateRef = useRef(false);

  const safeNavigate = useCallback(async (to: string) => {
    if (isBlueprintDirty) {
      const ok = await confirmDialog({
        title: '未保存修改',
        message: `${dirtySummary || '有未保存的修改'}。\n\n确定要离开当前页面吗？`,
        confirmText: '离开',
        dialogType: 'warning',
      });
      if (!ok) return;
    }
    navigate(to);
  }, [dirtySummary, isBlueprintDirty, navigate]);

  useEffect(() => {
    isBlueprintDirtyRef.current = isBlueprintDirty;
    dirtySummaryRef.current = dirtySummary;
  }, [dirtySummary, isBlueprintDirty]);

  useEffect(() => {
    try {
      const idx = Number((window.history.state as any)?.idx);
      if (Number.isFinite(idx)) historyIdxRef.current = idx;
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    const onPopState = () => {
      let nextIdx = NaN;
      try {
        nextIdx = Number((window.history.state as any)?.idx);
      } catch {
        nextIdx = NaN;
      }

      if (ignoreNextPopStateRef.current) {
        ignoreNextPopStateRef.current = false;
        if (Number.isFinite(nextIdx)) historyIdxRef.current = nextIdx;
        return;
      }

      if (!isBlueprintDirtyRef.current) {
        if (Number.isFinite(nextIdx)) historyIdxRef.current = nextIdx;
        return;
      }

      const prevIdx = historyIdxRef.current;
      const delta = Number.isFinite(nextIdx) ? nextIdx - prevIdx : 0;
      const ok = confirm(`${dirtySummaryRef.current || '有未保存的修改'}。\n\n确定要离开当前页面吗？`);
      if (ok) {
        if (Number.isFinite(nextIdx)) historyIdxRef.current = nextIdx;
        return;
      }

      ignoreNextPopStateRef.current = true;
      if (delta < 0) {
        navigate(1);
        return;
      }
      if (delta > 0) {
        navigate(-1);
        return;
      }

      navigate(1);
    };

    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, [navigate]);

  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!isBlueprintDirty) return;
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [isBlueprintDirty]);

  return {
    safeNavigate,
  };
};
