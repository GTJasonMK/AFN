import { useCallback, useState } from 'react';

type EditingOutlineChapter = {
  chapter_number: number;
  title: string;
  summary: string;
  generation_status: 'not_generated';
};

type UseNovelDetailOutlineEditorParams = {
  setIsOutlineModalOpen: (open: boolean) => void;
};

export const useNovelDetailOutlineEditor = ({
  setIsOutlineModalOpen,
}: UseNovelDetailOutlineEditorParams) => {
  const [editingChapter, setEditingChapter] = useState<EditingOutlineChapter | null>(null);

  const openOutlineEditor = useCallback((outline: any) => {
    const chapterNumber = Number(outline?.chapter_number || 0);
    if (!chapterNumber) return;

    setEditingChapter({
      chapter_number: chapterNumber,
      title: String(outline?.title || `第${chapterNumber}章`),
      summary: String(outline?.summary || ''),
      generation_status: 'not_generated',
    });
    setIsOutlineModalOpen(true);
  }, [setIsOutlineModalOpen]);

  return {
    editingChapter,
    openOutlineEditor,
  };
};
