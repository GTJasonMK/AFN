import type { BuildNovelDetailModalInputParamsArgs } from './buildNovelDetailModalInputParams';
import type { useNovelDetailDerivedData } from './useNovelDetailDerivedData';
import type { useNovelDetailModalStates } from './useNovelDetailModalStates';

type DerivedDataState = ReturnType<typeof useNovelDetailDerivedData>;
type ModalStates = ReturnType<typeof useNovelDetailModalStates>;

type BuildNovelDetailModalInputArgs = {
  businessBase: Omit<
    BuildNovelDetailModalInputParamsArgs['modal']['business'],
    keyof DerivedDataState | keyof ModalStates
  >;
  derivedData: DerivedDataState;
  modalStates: ModalStates;
};

export const buildNovelDetailModalInput = ({
  businessBase,
  derivedData,
  modalStates,
}: BuildNovelDetailModalInputArgs): BuildNovelDetailModalInputParamsArgs['modal'] => {
  return {
    business: {
      ...businessBase,
      ...derivedData,
      ...modalStates,
    },
    latestPart: {
      ...derivedData,
      ...modalStates,
    },
    latestChapter: {
      ...derivedData,
      ...modalStates,
    },
  };
};
