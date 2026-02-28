import { useCallback, useMemo, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

type UseNovelDetailBlueprintDraftParams = {
  blueprintData: any;
  setBlueprintData: Dispatch<SetStateAction<any>>;
};

const stableStringify = (value: any): string => {
  const seen = new WeakSet<object>();

  const normalize = (v: any): any => {
    if (v === null || v === undefined) return v;
    const t = typeof v;
    if (t === 'string' || t === 'number' || t === 'boolean') return v;
    if (Array.isArray(v)) return v.map(normalize);
    if (t !== 'object') return String(v);

    if (seen.has(v)) return null;
    seen.add(v);

    const out: Record<string, any> = {};
    for (const key of Object.keys(v).sort()) {
      const nv = normalize(v[key]);
      if (nv !== undefined) out[key] = nv;
    }
    return out;
  };

  try {
    return JSON.stringify(normalize(value));
  } catch {
    return JSON.stringify(String(value ?? ''));
  }
};

const buildNovelBlueprintSnapshot = (blueprint: any): string => {
  const bp = blueprint || {};
  return stableStringify({
    one_sentence_summary: String(bp.one_sentence_summary || ''),
    full_synopsis: String(bp.full_synopsis || ''),
    genre: String(bp.genre || ''),
    target_audience: String(bp.target_audience || ''),
    style: String(bp.style || ''),
    tone: String(bp.tone || ''),
    characters: Array.isArray(bp.characters) ? bp.characters : [],
    relationships: Array.isArray(bp.relationships) ? bp.relationships : [],
  });
};

const resolveWorldSettingDraft = (blueprint: any): string => {
  const raw = blueprint?.world_setting;
  let worldSetting = raw;
  if (typeof raw === 'string') {
    try {
      worldSetting = JSON.parse(raw);
    } catch {
      worldSetting = { text: raw };
    }
  }
  if (!worldSetting || typeof worldSetting !== 'object' || Array.isArray(worldSetting)) {
    worldSetting = {};
  }
  return JSON.stringify(worldSetting, null, 2);
};

export const useNovelDetailBlueprintDraft = ({
  blueprintData,
  setBlueprintData,
}: UseNovelDetailBlueprintDraftParams) => {
  const [worldSettingDraft, setWorldSettingDraft] = useState<string>('{}');
  const [savedBlueprintSnapshot, setSavedBlueprintSnapshot] = useState<string>('');
  const [savedWorldSettingDraft, setSavedWorldSettingDraft] = useState<string>('{}');

  const worldSettingError = useMemo(() => {
    try {
      const txt = (worldSettingDraft || '').trim();
      const parsed = txt ? JSON.parse(txt) : {};
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return '请输入合法 JSON 对象';
      return '';
    } catch {
      return '请输入合法 JSON 对象';
    }
  }, [worldSettingDraft]);

  const currentBlueprintSnapshot = useMemo(() => buildNovelBlueprintSnapshot(blueprintData), [blueprintData]);

  const isBlueprintDirty = useMemo(() => {
    if (!savedBlueprintSnapshot) return false;
    return currentBlueprintSnapshot !== savedBlueprintSnapshot || worldSettingDraft !== savedWorldSettingDraft;
  }, [currentBlueprintSnapshot, savedBlueprintSnapshot, savedWorldSettingDraft, worldSettingDraft]);

  const dirtySummary = useMemo(() => {
    if (!isBlueprintDirty) return '';

    const parts: string[] = [];
    try {
      const saved = savedBlueprintSnapshot ? JSON.parse(savedBlueprintSnapshot) : null;
      const cur = currentBlueprintSnapshot ? JSON.parse(currentBlueprintSnapshot) : null;
      if (saved && cur) {
        const overviewChanged =
          cur.one_sentence_summary !== saved.one_sentence_summary ||
          cur.full_synopsis !== saved.full_synopsis ||
          cur.genre !== saved.genre ||
          cur.target_audience !== saved.target_audience ||
          cur.style !== saved.style ||
          cur.tone !== saved.tone;
        if (overviewChanged) parts.push('概览');

        const charsChanged = stableStringify(cur.characters) !== stableStringify(saved.characters);
        if (charsChanged) parts.push('角色');

        const relChanged = stableStringify(cur.relationships) !== stableStringify(saved.relationships);
        if (relChanged) parts.push('关系');
      }
    } catch {
      // ignore
    }

    if (worldSettingDraft !== savedWorldSettingDraft) parts.push('世界观');

    if (!parts.length) return '有未保存的修改';
    return `有未保存的修改：${parts.join('、')}`;
  }, [currentBlueprintSnapshot, isBlueprintDirty, savedBlueprintSnapshot, savedWorldSettingDraft, worldSettingDraft]);

  const worldSettingObj = useMemo(() => {
    try {
      const txt = (worldSettingDraft || '').trim();
      const parsed = txt ? JSON.parse(txt) : {};
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
      return parsed as any;
    } catch {
      return null;
    }
  }, [worldSettingDraft]);

  const worldListToText = useCallback((value: any) => {
    if (!Array.isArray(value) || value.length === 0) return '';
    return value
      .map((it) => {
        if (typeof it === 'string') return it.trim();
        if (!it || typeof it !== 'object') return '';
        const title = String(it.title || it.name || '').trim();
        const desc = String(it.description || '').trim();
        if (!title && !desc) return '';
        if (!desc) return title || '';
        return `${title || '（未命名）'}｜${desc}`;
      })
      .filter(Boolean)
      .join('\n');
  }, []);

  const worldTextToList = useCallback((text: string) => {
    const lines = (text || '')
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);

    return lines.map((line) => {
      const sepIdx = line.includes('｜') ? line.indexOf('｜') : (line.includes('|') ? line.indexOf('|') : -1);
      if (sepIdx >= 0) {
        const title = line.slice(0, sepIdx).trim();
        const desc = line.slice(sepIdx + 1).trim();
        if (desc) return { title: title || '（未命名）', description: desc };
        return title;
      }
      return line;
    });
  }, []);

  const updateWorldSettingDraft = useCallback((patch: (obj: any) => void) => {
    if (!worldSettingObj) return;
    const next = { ...worldSettingObj };
    patch(next);
    setWorldSettingDraft(JSON.stringify(next, null, 2));
  }, [worldSettingObj]);

  const applyProjectBlueprint = useCallback((blueprint: any) => {
    if (blueprint) {
      setBlueprintData(blueprint);
      const pretty = resolveWorldSettingDraft(blueprint);
      setWorldSettingDraft(pretty);
      setSavedWorldSettingDraft(pretty);
      setSavedBlueprintSnapshot(buildNovelBlueprintSnapshot(blueprint));
    } else {
      setSavedBlueprintSnapshot(buildNovelBlueprintSnapshot({}));
      setSavedWorldSettingDraft('{}');
    }
  }, [setBlueprintData]);

  const markBlueprintSaved = useCallback((payload: any, prettyWorld: string) => {
    setWorldSettingDraft(prettyWorld);
    setSavedWorldSettingDraft(prettyWorld);
    setSavedBlueprintSnapshot(buildNovelBlueprintSnapshot(payload));
  }, []);

  return {
    worldSettingDraft,
    setWorldSettingDraft,
    worldSettingError,
    worldSettingObj,
    worldListToText,
    worldTextToList,
    updateWorldSettingDraft,
    isBlueprintDirty,
    dirtySummary,
    applyProjectBlueprint,
    markBlueprintSaved,
  };
};
