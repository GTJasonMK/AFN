import { useCallback } from 'react';
import { sanitizeFilenamePart } from '../../utils/sanitizeFilename';
import { downloadBlob } from '../../utils/downloadFile';

type UseNovelDetailChapterExportParams = {
  id: string | undefined;
  projectTitle: unknown;
  selectedCompletedChapterNumber: number | null;
  selectedCompletedChapter: any | null;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailChapterExport = ({
  id,
  projectTitle,
  selectedCompletedChapterNumber,
  selectedCompletedChapter,
  addToast,
}: UseNovelDetailChapterExportParams) => {
  const exportSelectedChapter = useCallback((format: 'txt' | 'markdown') => {
    if (!id) return;
    const chapterNo = Number(selectedCompletedChapterNumber || 0);
    if (!chapterNo) {
      addToast('请先选择章节', 'info');
      return;
    }

    const titleRaw = String(selectedCompletedChapter?.title || `第${chapterNo}章`).trim();
    const filenameTitle = sanitizeFilenamePart(titleRaw ? `第${chapterNo}章_${titleRaw}` : `第${chapterNo}章`);
    const baseTitle = sanitizeFilenamePart(String(projectTitle || 'novel').trim()) || 'novel';

    const body = String(selectedCompletedChapter?.content || '').trimEnd();
    const ext = format === 'markdown' ? 'md' : 'txt';
    const prefix = format === 'markdown' ? `# 第${chapterNo}章 ${titleRaw}\n\n` : `第${chapterNo}章  ${titleRaw}\n\n`;
    const text = `${prefix}${body}\n`;

    try {
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      downloadBlob(blob, `${baseTitle}_${filenameTitle || `chapter_${chapterNo}`}.${ext}`);
      addToast('已导出本章', 'success');
    } catch (e) {
      console.error(e);
      addToast('导出失败', 'error');
    }
  }, [addToast, id, projectTitle, selectedCompletedChapter?.content, selectedCompletedChapter?.title, selectedCompletedChapterNumber]);

  return {
    exportSelectedChapter,
  };
};
