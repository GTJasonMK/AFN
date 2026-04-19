import type { Chapter } from '../../api/writer';

export const DEFAULT_VERSION_CREATED_AT = '1970-01-01T00:00:00.000Z';
export const WRITING_DESK_BOOTSTRAP_TTL_MS = 4 * 60 * 1000;

export type WritingDeskBootstrapSnapshot = {
  chapters: Chapter[];
  projectInfo: any;
  projectStatus?: string;
  outlineChapterNumbers?: number[];
  needsPartOutlines?: boolean;
  partOutlineCount?: number;
  partOutlineCoverMax?: number | null;
  selectedChapterNumber: number | null;
};

export const getWritingDeskBootstrapKey = (projectId: string) =>
  `afn:web:writing-desk:${projectId}:bootstrap:v1`;

export type WritingDeskBatchModalPreset = {
  count: number;
  startFrom: number | '';
};

export type WritingDeskCompactPane = 'chapters' | 'editor' | 'assistant';

export const WRITING_DESK_COMPACT_PANE_ITEMS: Array<{
  id: WritingDeskCompactPane;
  label: string;
  hint: string;
}> = [
  {
    id: 'chapters',
    label: '章节导航',
    hint: '锁定章节、创建章节、编辑大纲和批量生成。',
  },
  {
    id: 'editor',
    label: '编辑区',
    hint: '正文、版本切换和空态操作都收束在主工作区。',
  },
  {
    id: 'assistant',
    label: '写作助手',
    hint: 'RAG 检索和正文优化切到独立切面，不再用抽屉覆盖正文。',
  },
];
