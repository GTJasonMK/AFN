import { useCallback } from 'react';
import { writerApi } from '../../api/writer';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';

type OptionalPromptOptions = {
  title?: string;
  hint?: string;
  initialValue?: string;
  onConfirm: (promptText?: string) => void | Promise<void>;
};

type UseNovelDetailChapterOutlineRegenerateParams = {
  id: string | undefined;
  chapterOutlines: any[];
  fetchProject: () => Promise<void>;
  openOptionalPromptModal: (opts: OptionalPromptOptions) => void;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailChapterOutlineRegenerate = ({
  id,
  chapterOutlines,
  fetchProject,
  openOptionalPromptModal,
  addToast,
}: UseNovelDetailChapterOutlineRegenerateParams) => {
  const handleRegenerateOutline = useCallback(async (chapterNumber: number) => {
    if (!id) return;
    const max = chapterOutlines.length
      ? Number(chapterOutlines[chapterOutlines.length - 1]?.chapter_number || 0)
      : chapterNumber;
    const isLast = chapterNumber === max;

    let cascadeDelete = false;
    if (!isLast && max > 0) {
      const ok = await confirmDialog({
        title: '串行生成原则',
        message:
          `串行生成原则：只能直接重生成最后一章（当前最后一章为第${max}章）。\n\n` +
          `若要重生成第${chapterNumber}章，必须级联删除第${chapterNumber + 1}-${max}章的大纲/章节内容/向量数据。\n\n是否继续？`,
        confirmText: '继续',
        dialogType: 'danger',
      });
      if (!ok) return;
      cascadeDelete = true;
    }

    openOptionalPromptModal({
      title: '输入优化提示词（可选）',
      hint: '留空则按默认策略重生成；填写则会作为优化方向参与生成。',
      onConfirm: async (promptText?: string) => {
        try {
          const result = await writerApi.regenerateChapterOutline(id, chapterNumber, {
            prompt: promptText,
            cascadeDelete,
          });
          addToast(result?.message || '已重新生成章节大纲', 'success');
          if (result?.cascade_deleted?.message) {
            addToast(String(result.cascade_deleted.message), 'info');
          }
          await fetchProject();
        } catch (e) {
          console.error(e);
          addToast('重生成失败', 'error');
        }
      },
    });
  }, [addToast, chapterOutlines, fetchProject, id, openOptionalPromptModal]);

  return {
    handleRegenerateOutline,
  };
};
