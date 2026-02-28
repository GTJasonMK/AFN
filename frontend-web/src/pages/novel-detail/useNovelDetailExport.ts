import { useCallback } from 'react';
import { novelsApi } from '../../api/novels';
import { sanitizeFilenamePart } from '../../utils/sanitizeFilename';
import { downloadBlob } from '../../utils/downloadFile';

type UseNovelDetailExportParams = {
  id: string | undefined;
  projectTitle: string | undefined;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailExport = ({
  id,
  projectTitle,
  addToast,
}: UseNovelDetailExportParams) => {
  const handleExport = useCallback(async () => {
    if (!id) return;
    try {
      const response = await novelsApi.exportNovel(id, 'txt');
      const titleRaw = String(projectTitle || 'novel').trim() || 'novel';
      const title = sanitizeFilenamePart(titleRaw) || 'novel';
      downloadBlob(new Blob([response.data]), `${title}.txt`);
      addToast('导出成功', 'success');
    } catch (e) {
      console.error(e);
      addToast('导出失败', 'error');
    }
  }, [addToast, id, projectTitle]);

  return {
    handleExport,
  };
};
