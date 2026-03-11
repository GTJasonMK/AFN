import { useMemo } from 'react';
import type { NovelDetailTabProps, NovelDetailTabSources } from './types';

type UseOverviewWorldTabPropsResult = Pick<NovelDetailTabProps, 'overviewTabProps' | 'worldTabProps'>;

export const useOverviewWorldTabProps = (
  overviewWorld: NovelDetailTabSources['overviewWorld'],
): UseOverviewWorldTabPropsResult => {
  const {
    blueprintData,
    setBlueprintData,
    project,
    importStatus,
    importStatusLoading,
    importStarting,
    startImportAnalysis,
    refreshImportStatus,
    cancelImportAnalysis,
    worldEditMode,
    setWorldEditMode,
    worldSettingObj,
    worldListToText,
    worldTextToList,
    updateWorldSettingDraft,
    worldSettingDraft,
    setWorldSettingDraft,
    worldSettingError,
  } = overviewWorld;

  const overviewTabProps = useMemo(() => ({
    blueprintData,
    setBlueprintData,
    project,
    importStatus,
    importStatusLoading,
    importStarting,
    startImportAnalysis,
    refreshImportStatus,
    cancelImportAnalysis,
  }), [
    blueprintData,
    cancelImportAnalysis,
    importStarting,
    importStatus,
    importStatusLoading,
    project,
    refreshImportStatus,
    setBlueprintData,
    startImportAnalysis,
  ]);

  const worldTabProps = useMemo(() => ({
    worldEditMode,
    setWorldEditMode,
    worldSettingObj,
    worldListToText,
    worldTextToList,
    updateWorldSettingDraft,
    worldSettingDraft,
    setWorldSettingDraft,
    worldSettingError,
  }), [
    setWorldEditMode,
    setWorldSettingDraft,
    updateWorldSettingDraft,
    worldEditMode,
    worldListToText,
    worldSettingDraft,
    worldSettingError,
    worldSettingObj,
    worldTextToList,
  ]);

  return {
    overviewTabProps,
    worldTabProps,
  };
};
