import type { UseNovelDetailModalPropsParams } from './modal-props/types';

type LatestPartOutlineInputForModal = Pick<
  UseNovelDetailModalPropsParams['latestPart'],
  | 'deletingLatestParts'
  | 'deleteLatestPartsCount'
  | 'setDeleteLatestPartsCount'
  | 'handleDeleteLatestPartOutlines'
  | 'regeneratingLatestParts'
  | 'regenerateLatestPartsCount'
  | 'setRegenerateLatestPartsCount'
  | 'regenerateLatestPartsPrompt'
  | 'setRegenerateLatestPartsPrompt'
  | 'handleRegenerateLatestPartOutlines'
>;

type LatestChapterOutlineInputForModal = Pick<
  UseNovelDetailModalPropsParams['latestChapter'],
  | 'regeneratingLatest'
  | 'regenerateLatestCount'
  | 'setRegenerateLatestCount'
  | 'regenerateLatestPrompt'
  | 'setRegenerateLatestPrompt'
  | 'handleRegenerateLatestOutlines'
  | 'deletingLatest'
  | 'deleteLatestCount'
  | 'setDeleteLatestCount'
  | 'handleDeleteLatestOutlines'
>;

export type BuildNovelDetailModalInputParamsArgs = {
  modal: {
    business: UseNovelDetailModalPropsParams['business'];
    latestPart: Omit<
      UseNovelDetailModalPropsParams['latestPart'],
      keyof LatestPartOutlineInputForModal
    >;
    latestChapter: Omit<
      UseNovelDetailModalPropsParams['latestChapter'],
      keyof LatestChapterOutlineInputForModal
    >;
  };
  latestPartOutlineInput: LatestPartOutlineInputForModal;
  latestChapterOutlineInput: LatestChapterOutlineInputForModal;
};

export const buildNovelDetailModalInputParams = ({
  modal,
  latestPartOutlineInput,
  latestChapterOutlineInput,
}: BuildNovelDetailModalInputParamsArgs): UseNovelDetailModalPropsParams => {
  return {
    business: modal.business,
    latestPart: {
      ...modal.latestPart,
      ...latestPartOutlineInput,
    },
    latestChapter: {
      ...modal.latestChapter,
      ...latestChapterOutlineInput,
    },
  };
};
