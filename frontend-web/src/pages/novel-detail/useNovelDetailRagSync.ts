import { useCallback, useState } from 'react';
import { novelsApi } from '../../api/novels';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';

type UseNovelDetailRagSyncParams = {
  id: string | undefined;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailRagSync = ({
  id,
  addToast,
}: UseNovelDetailRagSyncParams) => {
  const [ragSyncing, setRagSyncing] = useState(false);

  const handleRagSync = useCallback(async () => {
    if (!id) return;
    if (ragSyncing) return;

    const ok = await confirmDialog({
      title: 'RAG 同步',
      message: '将同步项目到向量库：摘要/分析/索引/向量入库。\n\n强制全量入库会对所有类型重新入库，耗时更长。\n\n是否继续？',
      confirmText: '继续',
      dialogType: 'warning',
    });
    if (!ok) return;

    setRagSyncing(true);
    try {
      try {
        const diag = await novelsApi.getRagDiagnose(id);
        if (diag && diag.vector_store_enabled === false) {
          addToast('向量库未启用，无法同步（请先在设置中启用/配置）', 'error');
          return;
        }
        if (diag && diag.embedding_service_enabled === false) {
          addToast('嵌入服务未启用，无法同步（请先在设置中配置嵌入）', 'error');
          return;
        }
      } catch (e) {
        // 诊断失败不阻塞同步，交给后端返回更具体错误
        console.error(e);
      }

      const res = await novelsApi.ingestAllRagData(id, true);
      if (res.success) addToast('RAG 同步完成', 'success');
      else addToast('RAG 同步失败（请查看后端日志/结果详情）', 'error');
    } catch (e) {
      console.error(e);
      addToast('RAG 同步失败', 'error');
    } finally {
      setRagSyncing(false);
    }
  }, [addToast, id, ragSyncing]);

  return {
    ragSyncing,
    handleRagSync,
  };
};
