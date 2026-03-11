import React from 'react';
import { CharacterEditModal } from './CharacterEditModal';
import { RelationshipEditModal } from './RelationshipEditModal';
import type { ComponentProps } from 'react';

export type CharacterModalProps = ComponentProps<typeof CharacterEditModal>;
export type RelationshipModalProps = ComponentProps<typeof RelationshipEditModal>;

type CharacterAndRelationshipModalsProps = {
  characterModal: CharacterModalProps;
  relationshipModal: RelationshipModalProps;
};

export const CharacterAndRelationshipModals: React.FC<CharacterAndRelationshipModalsProps> = ({
  characterModal,
  relationshipModal,
}) => {
  return (
    <>
      <CharacterEditModal {...characterModal} />

      <RelationshipEditModal {...relationshipModal} />
    </>
  );
};
