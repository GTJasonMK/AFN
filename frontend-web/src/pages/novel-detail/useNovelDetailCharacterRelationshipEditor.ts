import { useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { useNovelDetailCharacterEditor } from './useNovelDetailCharacterEditor';
import { useNovelDetailRelationshipEditor } from './useNovelDetailRelationshipEditor';

type UseNovelDetailCharacterRelationshipEditorParams = {
  blueprintData: any;
  setBlueprintData: Dispatch<SetStateAction<any>>;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailCharacterRelationshipEditor = ({
  blueprintData,
  setBlueprintData,
  addToast,
}: UseNovelDetailCharacterRelationshipEditorParams) => {
  const [isProtagonistModalOpen, setIsProtagonistModalOpen] = useState(false);

  const characterEditor = useNovelDetailCharacterEditor({
    blueprintData,
    setBlueprintData,
  });

  const relationshipEditor = useNovelDetailRelationshipEditor({
    blueprintData,
    setBlueprintData,
    addToast,
  });

  return {
    ...characterEditor,
    isProtagonistModalOpen,
    setIsProtagonistModalOpen,
    ...relationshipEditor,
  };
};
