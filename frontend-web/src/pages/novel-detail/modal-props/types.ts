import type { ComponentProps } from 'react';
import { NovelDetailLazyBusinessModals } from '../NovelDetailLazyBusinessModals';
import { LatestPartOutlineModals } from '../LatestPartOutlineModals';
import { LatestChapterOutlineModals } from '../LatestChapterOutlineModals';

export type LazyBusinessModalProps = Omit<
  ComponentProps<typeof NovelDetailLazyBusinessModals>,
  'projectId' | 'onProjectRefresh'
>;

export type LatestPartOutlineModalProps = ComponentProps<typeof LatestPartOutlineModals>;
export type LatestChapterOutlineModalProps = ComponentProps<typeof LatestChapterOutlineModals>;

export type BusinessModalInput = {
  blueprintData: any;
  partOutlines: any[];
  partTotalChapters: number;
  latestChapterNumber: number;
  partCoveredChapters: number;
  partGenerateMode: 'generate' | 'continue';
  isOutlineModalOpen: boolean;
  setIsOutlineModalOpen: (open: boolean) => void;
  editingChapter: any | null;
  isBatchModalOpen: boolean;
  setIsBatchModalOpen: (open: boolean) => void;
  isProtagonistModalOpen: boolean;
  setIsProtagonistModalOpen: (open: boolean) => void;
  isPartGenerateModalOpen: boolean;
  setIsPartGenerateModalOpen: (open: boolean) => void;
  detailPart: any | null;
  setDetailPart: (part: any | null) => void;
  refreshProjectAndPartProgress: () => Promise<void>;
};

export type LatestPartModalInput = {
  partOutlines: any[];
  isDeleteLatestPartsModalOpen: boolean;
  setIsDeleteLatestPartsModalOpen: (open: boolean) => void;
  deletingLatestParts: boolean;
  maxDeletablePartCount: number;
  deleteLatestPartsCount: number;
  setDeleteLatestPartsCount: (value: number) => void;
  handleDeleteLatestPartOutlines: () => void | Promise<void>;
  isRegenerateLatestPartsModalOpen: boolean;
  setIsRegenerateLatestPartsModalOpen: (open: boolean) => void;
  regeneratingLatestParts: boolean;
  regenerateLatestPartsCount: number;
  setRegenerateLatestPartsCount: (value: number) => void;
  regenerateLatestPartsPrompt: string;
  setRegenerateLatestPartsPrompt: (value: string) => void;
  handleRegenerateLatestPartOutlines: () => void | Promise<void>;
};

export type LatestChapterModalInput = {
  chapterOutlines: any[];
  isRegenerateLatestModalOpen: boolean;
  setIsRegenerateLatestModalOpen: (open: boolean) => void;
  regeneratingLatest: boolean;
  regenerateLatestCount: number;
  setRegenerateLatestCount: (value: number) => void;
  regenerateLatestPrompt: string;
  setRegenerateLatestPrompt: (value: string) => void;
  handleRegenerateLatestOutlines: () => void | Promise<void>;
  isDeleteLatestModalOpen: boolean;
  setIsDeleteLatestModalOpen: (open: boolean) => void;
  deletingLatest: boolean;
  deleteLatestCount: number;
  setDeleteLatestCount: (value: number) => void;
  handleDeleteLatestOutlines: () => void | Promise<void>;
};

export type UseNovelDetailModalPropsParams = {
  business: BusinessModalInput;
  latestPart: LatestPartModalInput;
  latestChapter: LatestChapterModalInput;
};

export type UseNovelDetailModalPropsResult = {
  lazyBusinessModalProps: LazyBusinessModalProps;
  latestPartOutlineModalProps: LatestPartOutlineModalProps;
  latestChapterOutlineModalProps: LatestChapterOutlineModalProps;
};
