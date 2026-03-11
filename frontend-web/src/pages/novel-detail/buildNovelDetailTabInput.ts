import type { BuildNovelDetailTabSourcesArgs } from './buildNovelDetailTabSources';
import type { useNovelDetailBlueprintDraft } from './useNovelDetailBlueprintDraft';
import type { useNovelDetailCharacterRelationshipEditor } from './useNovelDetailCharacterRelationshipEditor';
import type { useNovelDetailDerivedData } from './useNovelDetailDerivedData';
import type { useNovelDetailModalStates } from './useNovelDetailModalStates';

type BlueprintDraftState = ReturnType<typeof useNovelDetailBlueprintDraft>;
type CharacterRelationshipEditorState = ReturnType<typeof useNovelDetailCharacterRelationshipEditor>;
type DerivedDataState = ReturnType<typeof useNovelDetailDerivedData>;
type ModalStates = ReturnType<typeof useNovelDetailModalStates>;

type BuildNovelDetailTabInputArgs = {
  overviewWorldBase: Omit<BuildNovelDetailTabSourcesArgs['tab']['overviewWorld'], keyof BlueprintDraftState>;
  characterRelationshipBase: Pick<
    BuildNovelDetailTabSourcesArgs['tab']['characterRelationship'],
    'setCharactersRenderLimit' | 'setRelationshipsRenderLimit'
  >;
  outlinesBase: Omit<
    BuildNovelDetailTabSourcesArgs['tab']['outlines'],
    keyof DerivedDataState | keyof ModalStates
  >;
  chaptersBase: Omit<
    BuildNovelDetailTabSourcesArgs['tab']['chapters'],
    keyof DerivedDataState
  >;
  blueprintDraftState: BlueprintDraftState;
  characterRelationshipEditor: CharacterRelationshipEditorState;
  derivedData: DerivedDataState;
  modalStates: ModalStates;
};

export const buildNovelDetailTabInput = ({
  overviewWorldBase,
  characterRelationshipBase,
  outlinesBase,
  chaptersBase,
  blueprintDraftState,
  characterRelationshipEditor,
  derivedData,
  modalStates,
}: BuildNovelDetailTabInputArgs): BuildNovelDetailTabSourcesArgs['tab'] => {
  return {
    overviewWorld: {
      ...overviewWorldBase,
      ...blueprintDraftState,
    },
    characterRelationship: {
      ...derivedData,
      ...characterRelationshipEditor,
      ...characterRelationshipBase,
    },
    outlines: {
      ...outlinesBase,
      ...derivedData,
      ...modalStates,
    },
    chapters: {
      ...chaptersBase,
      ...derivedData,
    },
  };
};
