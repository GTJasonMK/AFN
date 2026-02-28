import { useCallback } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { novelsApi } from '../../api/novels';
import type { NovelDetailTab } from './NovelDetailTabBar';

type UseNovelDetailBlueprintSaveParams = {
  id: string | undefined;
  blueprintData: any;
  worldSettingDraft: string;
  setBlueprintData: Dispatch<SetStateAction<any>>;
  markBlueprintSaved: (payload: any, prettyWorld: string) => void;
  setSaving: Dispatch<SetStateAction<boolean>>;
  setActiveTab: Dispatch<SetStateAction<NovelDetailTab>>;
  addToast: (message: string, type?: string) => void;
};

const parseWorldSettingDraft = (worldSettingDraft: string): any => {
  const txt = (worldSettingDraft || '').trim();
  const parsed = txt ? JSON.parse(txt) : {};
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('world_setting must be an object');
  }
  return parsed;
};

export const useNovelDetailBlueprintSave = ({
  id,
  blueprintData,
  worldSettingDraft,
  setBlueprintData,
  markBlueprintSaved,
  setSaving,
  setActiveTab,
  addToast,
}: UseNovelDetailBlueprintSaveParams) => {
  const handleSave = useCallback(async () => {
    if (!id) return;

    setSaving(true);
    try {
      let parsedWorldSetting: any = {};
      try {
        parsedWorldSetting = parseWorldSettingDraft(worldSettingDraft);
      } catch {
        addToast('世界观格式无效：请填写合法的 JSON 对象', 'error');
        setActiveTab('world');
        return;
      }

      const prettyWorld = JSON.stringify(parsedWorldSetting, null, 2);
      const payload = { ...blueprintData, world_setting: parsedWorldSetting };
      await novelsApi.updateBlueprint(id, payload);
      setBlueprintData(payload);
      markBlueprintSaved(payload, prettyWorld);
      addToast('蓝图已保存', 'success');
    } catch (e) {
      console.error(e);
      addToast('保存失败', 'error');
    } finally {
      setSaving(false);
    }
  }, [
    addToast,
    blueprintData,
    id,
    markBlueprintSaved,
    setActiveTab,
    setBlueprintData,
    setSaving,
    worldSettingDraft,
  ]);

  return {
    handleSave,
  };
};
