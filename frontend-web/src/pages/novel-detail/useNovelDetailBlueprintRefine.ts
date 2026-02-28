import { useCallback, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { novelsApi } from '../../api/novels';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';

type UseNovelDetailBlueprintRefineParams = {
  id: string | undefined;
  fetchProject: () => Promise<void>;
  setBlueprintData: Dispatch<SetStateAction<any>>;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailBlueprintRefine = ({
  id,
  fetchProject,
  setBlueprintData,
  addToast,
}: UseNovelDetailBlueprintRefineParams) => {
  const [isRefineModalOpen, setIsRefineModalOpen] = useState(false);
  const [refineInstruction, setRefineInstruction] = useState('');
  const [refineForce, setRefineForce] = useState(false);
  const [refining, setRefining] = useState(false);
  const [refineResult, setRefineResult] = useState<string | null>(null);

  const closeRefineModal = useCallback(() => {
    setIsRefineModalOpen(false);
  }, []);

  const openRefineModal = useCallback(() => {
    setRefineInstruction('');
    setRefineForce(false);
    setRefineResult(null);
    setIsRefineModalOpen(true);
  }, []);

  const handleRefineBlueprint = useCallback(async () => {
    if (!id) return;
    const instruction = refineInstruction.trim();
    if (!instruction) {
      addToast('请输入优化指令', 'error');
      return;
    }

    setRefining(true);
    setRefineResult(null);

    const run = async (force: boolean) => {
      const result = await novelsApi.refineBlueprint(id, instruction, force);
      if (result?.blueprint) setBlueprintData(result.blueprint);
      setRefineResult(result?.ai_message || null);
      addToast('蓝图优化完成', 'success');
      await fetchProject();
    };

    try {
      await run(refineForce);
    } catch (e: any) {
      const status = e?.response?.status;
      const detail = e?.response?.data?.detail;

      if (status === 409 && !refineForce) {
        const ok = await confirmDialog({
          title: '强制优化蓝图',
          message: `${detail || '检测到已有后续数据，优化蓝图会清空这些数据。'}\n\n是否强制优化？`,
          confirmText: '强制优化',
          dialogType: 'danger',
        });
        if (ok) {
          try {
            setRefineForce(true);
            await run(true);
          } catch (e2) {
            console.error(e2);
          }
        }
        return;
      }

      console.error(e);
    } finally {
      setRefining(false);
    }
  }, [addToast, fetchProject, id, refineForce, refineInstruction, setBlueprintData]);

  return {
    isRefineModalOpen,
    refineInstruction,
    refineForce,
    refining,
    refineResult,
    setRefineInstruction,
    setRefineForce,
    closeRefineModal,
    openRefineModal,
    handleRefineBlueprint,
  };
};
