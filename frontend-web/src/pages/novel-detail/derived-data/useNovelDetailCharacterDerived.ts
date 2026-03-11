import { useMemo } from 'react';

const CHARACTER_PROFILE_KEYS = [
  'appearance',
  'appearance_description',
  'looks',
  'look',
  'visual',
  'portrait',
  'portrait_prompt',
  'image_prompt',
  'description',
  'desc',
  'profile',
  '外貌',
  '外观',
  '形象',
  '描述',
] as const;

type UseNovelDetailCharacterDerivedParams = {
  blueprintData: any;
  charactersRenderLimit: number;
  relationshipsRenderLimit: number;
};

export const useNovelDetailCharacterDerived = ({
  blueprintData,
  charactersRenderLimit,
  relationshipsRenderLimit,
}: UseNovelDetailCharacterDerivedParams) => {
  const charactersList = useMemo(() => {
    return Array.isArray(blueprintData?.characters) ? blueprintData.characters : [];
  }, [blueprintData]);

  const relationshipsList = useMemo(() => {
    return Array.isArray(blueprintData?.relationships) ? blueprintData.relationships : [];
  }, [blueprintData]);

  const characterNames = useMemo(() => {
    const set = new Set<string>();
    charactersList.forEach((character: any) => {
      const name = String(character?.name || '').trim();
      if (name) set.add(name);
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'zh-CN'));
  }, [charactersList]);

  const characterProfiles = useMemo(() => {
    const map: Record<string, string> = {};
    for (const character of charactersList) {
      const name = String((character as any)?.name || '').trim();
      if (!name) continue;

      let desc = '';
      for (const key of CHARACTER_PROFILE_KEYS) {
        const value = (character as any)?.[key];
        if (typeof value === 'string' && value.trim()) {
          desc = value.trim();
          break;
        }
      }

      if (!desc) {
        const parts: string[] = [];
        for (const [key, value] of Object.entries(character || {})) {
          if (key === 'name') continue;
          if (typeof value === 'string' && value.trim()) parts.push(value.trim());
        }
        desc = parts.join('；').trim();
      }

      if (desc) map[name] = desc.length > 600 ? desc.slice(0, 600) : desc;
    }
    return map;
  }, [charactersList]);

  const visibleCharacters = useMemo(() => {
    return charactersList.slice(0, charactersRenderLimit);
  }, [charactersList, charactersRenderLimit]);

  const visibleRelationships = useMemo(() => {
    return relationshipsList.slice(0, relationshipsRenderLimit);
  }, [relationshipsList, relationshipsRenderLimit]);

  const remainingCharacters = Math.max(0, charactersList.length - visibleCharacters.length);
  const remainingRelationships = Math.max(0, relationshipsList.length - visibleRelationships.length);

  return {
    charactersList,
    relationshipsList,
    characterNames,
    characterProfiles,
    visibleCharacters,
    visibleRelationships,
    remainingCharacters,
    remainingRelationships,
  };
};
