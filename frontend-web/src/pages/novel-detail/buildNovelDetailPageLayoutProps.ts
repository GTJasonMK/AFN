import type { ComponentProps } from 'react';
import type { NovelDetailHeader } from './NovelDetailHeader';
import type { TitleAndBlueprintModals } from './TitleAndBlueprintModals';
import type { CharacterAndRelationshipModals } from './CharacterAndRelationshipModals';
import type { useNovelDetailCharacterRelationshipEditor } from './useNovelDetailCharacterRelationshipEditor';

type HeaderProps = ComponentProps<typeof NovelDetailHeader>;
type TitleAndBlueprintModalProps = ComponentProps<typeof TitleAndBlueprintModals>;
type CharacterAndRelationshipModalProps = ComponentProps<typeof CharacterAndRelationshipModals>;
type CharacterRelationshipEditorState = ReturnType<typeof useNovelDetailCharacterRelationshipEditor>;

type CharacterRelationshipEditorForLayout = Pick<
  CharacterRelationshipEditorState,
  | 'isCharModalOpen'
  | 'setIsCharModalOpen'
  | 'editingCharIndex'
  | 'handleSaveChar'
  | 'charForm'
  | 'setCharForm'
  | 'isRelModalOpen'
  | 'setIsRelModalOpen'
  | 'editingRelIndex'
  | 'handleSaveRel'
  | 'relForm'
  | 'setRelForm'
>;

type BuildNovelDetailPageLayoutPropsArgs = {
  project: HeaderProps['project'];
  projectId: HeaderProps['projectId'];
  blueprintData: HeaderProps['blueprintData'];
  avatarManager: Pick<HeaderProps, 'avatarLoading' | 'handleAvatarClick' | 'handleDeleteAvatar'>;
  openEditTitleModal: HeaderProps['openEditTitleModal'];
  isBlueprintDirty: HeaderProps['isBlueprintDirty'];
  dirtySummary: HeaderProps['dirtySummary'];
  saving: HeaderProps['saving'];
  worldSettingError: HeaderProps['worldSettingError'];
  handleSave: HeaderProps['handleSave'];
  safeNavigate: HeaderProps['safeNavigate'];
  handleExport: HeaderProps['handleExport'];
  ragSync: Pick<HeaderProps, 'ragSyncing' | 'handleRagSync'>;
  openRefineModal: HeaderProps['openRefineModal'];
  blueprintRefineModalProps: Omit<
    TitleAndBlueprintModalProps,
    | 'isEditTitleModalOpen'
    | 'closeEditTitleModal'
    | 'editTitleSaving'
    | 'saveProjectTitle'
    | 'editTitleValue'
    | 'setEditTitleValue'
  >;
  titleEditorModalProps: Pick<
    TitleAndBlueprintModalProps,
    | 'isEditTitleModalOpen'
    | 'closeEditTitleModal'
    | 'editTitleSaving'
    | 'saveProjectTitle'
    | 'editTitleValue'
    | 'setEditTitleValue'
  >;
  characterRelationshipEditor: CharacterRelationshipEditorForLayout;
  characterNames: CharacterAndRelationshipModalProps['relationshipModal']['characterNames'];
};

type BuildNovelDetailPageLayoutPropsResult = {
  headerProps: HeaderProps;
  titleAndBlueprintModalProps: TitleAndBlueprintModalProps;
  characterAndRelationshipModalProps: CharacterAndRelationshipModalProps;
};

export const buildNovelDetailPageLayoutProps = ({
  project,
  projectId,
  blueprintData,
  avatarManager,
  openEditTitleModal,
  isBlueprintDirty,
  dirtySummary,
  saving,
  worldSettingError,
  handleSave,
  safeNavigate,
  handleExport,
  ragSync,
  openRefineModal,
  blueprintRefineModalProps,
  titleEditorModalProps,
  characterRelationshipEditor,
  characterNames,
}: BuildNovelDetailPageLayoutPropsArgs): BuildNovelDetailPageLayoutPropsResult => {
  return {
    headerProps: {
      project,
      projectId,
      blueprintData,
      ...avatarManager,
      openEditTitleModal,
      isBlueprintDirty,
      dirtySummary,
      saving,
      worldSettingError,
      handleSave,
      safeNavigate,
      handleExport,
      ...ragSync,
      openRefineModal,
    },
    titleAndBlueprintModalProps: {
      ...blueprintRefineModalProps,
      ...titleEditorModalProps,
    },
    characterAndRelationshipModalProps: {
      characterModal: {
        isOpen: characterRelationshipEditor.isCharModalOpen,
        setOpen: characterRelationshipEditor.setIsCharModalOpen,
        editingIndex: characterRelationshipEditor.editingCharIndex,
        onSave: characterRelationshipEditor.handleSaveChar,
        charForm: characterRelationshipEditor.charForm,
        setCharForm: characterRelationshipEditor.setCharForm,
      },
      relationshipModal: {
        isOpen: characterRelationshipEditor.isRelModalOpen,
        setOpen: characterRelationshipEditor.setIsRelModalOpen,
        editingIndex: characterRelationshipEditor.editingRelIndex,
        onSave: characterRelationshipEditor.handleSaveRel,
        characterNames,
        relForm: characterRelationshipEditor.relForm,
        setRelForm: characterRelationshipEditor.setRelForm,
      },
    },
  };
};
