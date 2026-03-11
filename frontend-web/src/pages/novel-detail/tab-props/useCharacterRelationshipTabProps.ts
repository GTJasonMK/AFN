import { useMemo } from 'react';
import type { NovelDetailTabProps, NovelDetailTabSources } from './types';

type UseCharacterRelationshipTabPropsResult = Pick<
  NovelDetailTabProps,
  'charactersTabProps' | 'relationshipsTabProps'
>;

type UseCharacterRelationshipTabPropsParams = {
  projectId: string;
  characterRelationship: NovelDetailTabSources['characterRelationship'];
};

export const useCharacterRelationshipTabProps = ({
  projectId,
  characterRelationship,
}: UseCharacterRelationshipTabPropsParams): UseCharacterRelationshipTabPropsResult => {
  const {
    charactersList,
    visibleCharacters,
    remainingCharacters,
    charactersView,
    setCharactersView,
    handleAddChar,
    handleEditChar,
    handleDeleteChar,
    setCharactersRenderLimit,
    characterNames,
    characterProfiles,
    relationshipsList,
    visibleRelationships,
    remainingRelationships,
    handleAddRel,
    handleEditRel,
    handleDeleteRel,
    setRelationshipsRenderLimit,
  } = characterRelationship;

  const charactersTabProps = useMemo(() => ({
    projectId,
    charactersList,
    visibleCharacters,
    remainingCharacters,
    charactersView,
    setCharactersView,
    handleAddChar,
    handleEditChar,
    handleDeleteChar,
    setCharactersRenderLimit,
    characterNames,
    characterProfiles,
  }), [
    characterNames,
    characterProfiles,
    charactersList,
    charactersView,
    handleAddChar,
    handleDeleteChar,
    handleEditChar,
    projectId,
    remainingCharacters,
    setCharactersRenderLimit,
    setCharactersView,
    visibleCharacters,
  ]);

  const relationshipsTabProps = useMemo(() => ({
    relationshipsList,
    visibleRelationships,
    remainingRelationships,
    handleAddRel,
    handleEditRel,
    handleDeleteRel,
    setRelationshipsRenderLimit,
  }), [
    handleAddRel,
    handleDeleteRel,
    handleEditRel,
    relationshipsList,
    remainingRelationships,
    setRelationshipsRenderLimit,
    visibleRelationships,
  ]);

  return {
    charactersTabProps,
    relationshipsTabProps,
  };
};
