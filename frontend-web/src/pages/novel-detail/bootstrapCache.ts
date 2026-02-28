import { readBootstrapCache, writeBootstrapCache } from '../../utils/bootstrapCache';

export type NovelDetailBootstrapSnapshot = {
  project: any;
};

export type NovelDetailImportStatusSnapshot = {
  importStatus: any | null;
};

export type NovelDetailPartProgressSnapshot = {
  partProgress: any | null;
};

export type NovelDetailChapterDetailSnapshot = {
  chapterDetail: any | null;
};

export type NovelDetailChapterSelectionSnapshot = {
  chapterNumber: number | null;
  chapterDetail: any | null;
};

const NOVEL_DETAIL_BOOTSTRAP_TTL_MS = 4 * 60 * 1000;
const NOVEL_DETAIL_SECTION_TTL_MS = 4 * 60 * 1000;
const NOVEL_DETAIL_CHAPTER_DETAIL_TTL_MS = 10 * 60 * 1000;

const getNovelDetailBootstrapKey = (projectId: string) => `afn:web:novel-detail:${projectId}:bootstrap:v1`;
const getNovelDetailImportStatusKey = (projectId: string) => `afn:web:novel-detail:${projectId}:import-status:v1`;
const getNovelDetailPartProgressKey = (projectId: string) => `afn:web:novel-detail:${projectId}:part-progress:v1`;
const getNovelDetailChapterDetailKey = (projectId: string, chapterNo: number) =>
  `afn:web:novel-detail:${projectId}:chapter-detail:${chapterNo}:v1`;
const getNovelDetailChapterSelectionKey = (projectId: string) => `afn:web:novel-detail:${projectId}:chapter-selection:v1`;

export const readNovelDetailBootstrap = (projectId: string) =>
  readBootstrapCache<NovelDetailBootstrapSnapshot>(
    getNovelDetailBootstrapKey(projectId),
    NOVEL_DETAIL_BOOTSTRAP_TTL_MS,
  );

export const writeNovelDetailBootstrap = (projectId: string, project: any) =>
  writeBootstrapCache<NovelDetailBootstrapSnapshot>(getNovelDetailBootstrapKey(projectId), { project });

export const readNovelDetailImportStatus = (projectId: string) =>
  readBootstrapCache<NovelDetailImportStatusSnapshot>(
    getNovelDetailImportStatusKey(projectId),
    NOVEL_DETAIL_SECTION_TTL_MS,
  );

export const writeNovelDetailImportStatus = (projectId: string, importStatus: any | null) =>
  writeBootstrapCache<NovelDetailImportStatusSnapshot>(getNovelDetailImportStatusKey(projectId), {
    importStatus: importStatus ?? null,
  });

export const readNovelDetailPartProgress = (projectId: string) =>
  readBootstrapCache<NovelDetailPartProgressSnapshot>(
    getNovelDetailPartProgressKey(projectId),
    NOVEL_DETAIL_SECTION_TTL_MS,
  );

export const writeNovelDetailPartProgress = (projectId: string, partProgress: any | null) =>
  writeBootstrapCache<NovelDetailPartProgressSnapshot>(getNovelDetailPartProgressKey(projectId), {
    partProgress: partProgress ?? null,
  });

export const readNovelDetailChapterSelection = (projectId: string) =>
  readBootstrapCache<NovelDetailChapterSelectionSnapshot>(
    getNovelDetailChapterSelectionKey(projectId),
    NOVEL_DETAIL_CHAPTER_DETAIL_TTL_MS,
  );

export const writeNovelDetailChapterSelection = (
  projectId: string,
  chapterNumber: number | null,
  chapterDetail: any | null,
) =>
  writeBootstrapCache<NovelDetailChapterSelectionSnapshot>(getNovelDetailChapterSelectionKey(projectId), {
    chapterNumber: chapterNumber ?? null,
    chapterDetail: chapterDetail ?? null,
  });

export const readNovelDetailChapterDetail = (projectId: string, chapterNo: number) =>
  readBootstrapCache<NovelDetailChapterDetailSnapshot>(
    getNovelDetailChapterDetailKey(projectId, chapterNo),
    NOVEL_DETAIL_CHAPTER_DETAIL_TTL_MS,
  );

export const writeNovelDetailChapterDetail = (projectId: string, chapterNo: number, chapterDetail: any | null) =>
  writeBootstrapCache<NovelDetailChapterDetailSnapshot>(getNovelDetailChapterDetailKey(projectId, chapterNo), {
    chapterDetail: chapterDetail ?? null,
  });
