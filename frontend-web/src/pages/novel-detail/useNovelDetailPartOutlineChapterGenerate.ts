import { useCallback, useState } from 'react';
import { writerApi } from '../../api/writer';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';

type UseNovelDetailPartOutlineChapterGenerateParams = {
  id: string | undefined;
  chapterOutlines: any[];
  fetchProject: () => Promise<void>;
  fetchPartProgress: () => Promise<void>;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailPartOutlineChapterGenerate = ({
  id,
  chapterOutlines,
  fetchProject,
  fetchPartProgress,
  addToast,
}: UseNovelDetailPartOutlineChapterGenerateParams) => {
  const [generatingPartChapters, setGeneratingPartChapters] = useState<number | null>(null);

  const handleGeneratePartChapters = useCallback(async (part: any) => {
    if (!id) return;
    const partNumber = Number(part?.part_number || 0);
    const start = Number(part?.start_chapter || 0);
    const end = Number(part?.end_chapter || 0);
    if (!partNumber || !start || !end || end < start) {
      addToast('部分信息不完整，无法生成章节大纲', 'error');
      return;
    }

    const ok = await confirmDialog({
      title: '生成章节大纲',
      message: `为第${partNumber}部分生成章节大纲（第${start}-${end}章）？`,
      confirmText: '生成',
      dialogType: 'warning',
    });
    if (!ok) return;

    // 范围内已存在大纲时，允许用户选择“覆盖”或“仅补齐缺失”
    const hasExisting = chapterOutlines.some((outline: any) => {
      const number = Number(outline?.chapter_number || 0);
      return number >= start && number <= end;
    });
    let regenerate = false;
    if (hasExisting) {
      regenerate = await confirmDialog({
        title: '覆盖确认',
        message: '检测到该部分范围内已存在章节大纲，是否重新生成并覆盖？\n（不覆盖则仅补齐缺失章节）',
        confirmText: '重新生成并覆盖',
        cancelText: '仅补齐缺失',
        dialogType: 'warning',
      });
    }

    setGeneratingPartChapters(partNumber);
    try {
      await writerApi.generatePartChapters(id, partNumber, regenerate, { timeout: 0 });
      addToast(`第${partNumber}部分章节大纲生成完成`, 'success');
      await fetchProject();
      await fetchPartProgress();
    } catch (e) {
      console.error(e);
      addToast('生成失败', 'error');
    } finally {
      setGeneratingPartChapters(null);
    }
  }, [addToast, chapterOutlines, fetchPartProgress, fetchProject, id]);

  return {
    generatingPartChapters,
    handleGeneratePartChapters,
  };
};
