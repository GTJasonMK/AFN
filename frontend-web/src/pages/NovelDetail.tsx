import React, { useState, useEffect, useCallback, useMemo, useRef, useDeferredValue } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { writerApi } from '../api/writer';
import { useToast } from '../components/feedback/Toast';
import { confirmDialog } from '../components/feedback/ConfirmDialog';
import { useConfirmTextModal } from '../hooks/useConfirmTextModal';
import { usePersistedTab } from '../hooks/usePersistedTab';
import { NovelDetailTabBar, type NovelDetailTab } from './novel-detail/NovelDetailTabBar';
import { NovelDetailTabContent } from './novel-detail/NovelDetailTabContent';
import {
  writeNovelDetailPartProgress,
} from './novel-detail/bootstrapCache';
import { useNovelDetailBootstrap } from './novel-detail/useNovelDetailBootstrap';
import { useNovelDetailImportStatus } from './novel-detail/useNovelDetailImportStatus';
import { useNovelDetailChapterSelection } from './novel-detail/useNovelDetailChapterSelection';
import { useNovelDetailRenderLimits } from './novel-detail/useNovelDetailRenderLimits';
import { useNovelDetailChapterExport } from './novel-detail/useNovelDetailChapterExport';
import { useNovelDetailCharacterRelationshipEditor } from './novel-detail/useNovelDetailCharacterRelationshipEditor';
import { useNovelDetailBlueprintDraft } from './novel-detail/useNovelDetailBlueprintDraft';
import { useNovelDetailLeaveGuard } from './novel-detail/useNovelDetailLeaveGuard';
import { useNovelDetailBlueprintSave } from './novel-detail/useNovelDetailBlueprintSave';
import { useNovelDetailBlueprintRefine } from './novel-detail/useNovelDetailBlueprintRefine';
import { useNovelDetailRagSync } from './novel-detail/useNovelDetailRagSync';
import { useNovelDetailAvatarManager } from './novel-detail/useNovelDetailAvatarManager';
import { useNovelDetailTitleEditor } from './novel-detail/useNovelDetailTitleEditor';
import { useNovelDetailExport } from './novel-detail/useNovelDetailExport';
import { useNovelDetailChapterOutlineRegenerate } from './novel-detail/useNovelDetailChapterOutlineRegenerate';
import { useNovelDetailPartOutlineRegenerate } from './novel-detail/useNovelDetailPartOutlineRegenerate';
import { useNovelDetailPartOutlineChapterGenerate } from './novel-detail/useNovelDetailPartOutlineChapterGenerate';
import { useNovelDetailLatestChapterOutlineActions } from './novel-detail/useNovelDetailLatestChapterOutlineActions';
import { useNovelDetailLatestPartOutlineActions } from './novel-detail/useNovelDetailLatestPartOutlineActions';
import { useNovelDetailDerivedData } from './novel-detail/useNovelDetailDerivedData';
import { useNovelDetailTabProps, type NovelDetailTabSources } from './novel-detail/useNovelDetailTabProps';
import { LatestPartOutlineModals } from './novel-detail/LatestPartOutlineModals';
import { LatestChapterOutlineModals } from './novel-detail/LatestChapterOutlineModals';
import { CharacterAndRelationshipModals } from './novel-detail/CharacterAndRelationshipModals';
import { TitleAndBlueprintModals } from './novel-detail/TitleAndBlueprintModals';
import { NovelDetailLazyBusinessModals } from './novel-detail/NovelDetailLazyBusinessModals';
import { NovelDetailHeader } from './novel-detail/NovelDetailHeader';

const NOVEL_DETAIL_TABS: readonly NovelDetailTab[] = ['overview', 'world', 'characters', 'relationships', 'outlines', 'chapters'];

export const NovelDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  const [project, setProject] = useState<any>(null);
  const activeTabStorageKey = useMemo(() => (id ? `afn:novel_detail:active_tab:${id}` : ''), [id]);
  const [activeTab, setActiveTab] = usePersistedTab(activeTabStorageKey, 'overview', NOVEL_DETAIL_TABS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form states
  const [blueprintData, setBlueprintData] = useState<any>({});
  const [worldEditMode, setWorldEditMode] = useState<'structured' | 'json'>('structured');

  // Chapter outlines edit
  const [editingChapter, setEditingChapter] = useState<any | null>(null);
  const [isOutlineModalOpen, setIsOutlineModalOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [isDeleteLatestModalOpen, setIsDeleteLatestModalOpen] = useState(false);
  const [isRegenerateLatestModalOpen, setIsRegenerateLatestModalOpen] = useState(false);

  // Part outlines progress
  const [partProgress, setPartProgress] = useState<any | null>(null);
  const [partLoading, setPartLoading] = useState(false);
  const [isPartGenerateModalOpen, setIsPartGenerateModalOpen] = useState(false);
  const [partGenerateMode, setPartGenerateMode] = useState<'generate' | 'continue'>('generate');
  const [isDeleteLatestPartsModalOpen, setIsDeleteLatestPartsModalOpen] = useState(false);
  const [isRegenerateLatestPartsModalOpen, setIsRegenerateLatestPartsModalOpen] = useState(false);
  const [detailPart, setDetailPart] = useState<any | null>(null);

  // 导入分析进度（导入小说专用）
  const [importStatus, setImportStatus] = useState<any | null>(null);
  const [importStatusLoading, setImportStatusLoading] = useState(false);
  const [importStarting, setImportStarting] = useState(false);

  // 已完成章节（项目详情页展示，桌面端 ChaptersSection 对齐）
  const [chaptersSearch, setChaptersSearch] = useState('');
  const [selectedCompletedChapterNumber, setSelectedCompletedChapterNumber] = useState<number | null>(null);
  const [selectedCompletedChapter, setSelectedCompletedChapter] = useState<any | null>(null);
  const [selectedCompletedChapterLoading, setSelectedCompletedChapterLoading] = useState(false);

  const {
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
  } = useNovelDetailBlueprintDraft({
    blueprintData,
    setBlueprintData,
  });

  const { safeNavigate } = useNovelDetailLeaveGuard({
    isBlueprintDirty,
    dirtySummary,
    navigate,
  });

  // 输入优化提示词（可选）：替代浏览器 prompt()，统一为 Modal 交互
  const { open: openOptionalPromptModal, modal: optionalPromptModal } = useConfirmTextModal({
    addToast,
    defaultTitle: '输入优化提示词（可选）',
    defaultLabel: '优化提示词（可选）',
    defaultRows: 6,
    defaultPlaceholder: '例如：加强伏笔回收、提升冲突强度、强化人物动机、优化节奏…',
  });

  const hasImportStatusBootstrapRef = useRef(false);
  const hasPartProgressBootstrapRef = useRef(false);

  const deferredChaptersSearch = useDeferredValue(chaptersSearch);

  const {
    charactersRenderLimit,
    relationshipsRenderLimit,
    chapterOutlinesRenderLimit,
    partOutlinesRenderLimit,
    completedChaptersRenderLimit,
    setCharactersRenderLimit,
    setRelationshipsRenderLimit,
    setChapterOutlinesRenderLimit,
    setPartOutlinesRenderLimit,
    setCompletedChaptersRenderLimit,
  } = useNovelDetailRenderLimits({
    id,
    activeTab,
    deferredChaptersSearch,
  });

  const {
    chapterOutlines,
    partOutlines,
    partCoveredChapters,
    partTotalChapters,
    canContinuePartOutlines,
    maxDeletablePartCount,
    chaptersByNumber,
    completedChapters,
    charactersList,
    relationshipsList,
    characterNames,
    characterProfiles,
    countOutlinesInRange,
    visibleCharacters,
    visibleRelationships,
    visibleChapterOutlines,
    visiblePartOutlines,
    visibleCompletedChapters,
    remainingCharacters,
    remainingRelationships,
    remainingChapterOutlines,
    remainingPartOutlines,
    remainingCompletedChapters,
    latestChapterNumber,
  } = useNovelDetailDerivedData({
    blueprintData,
    partProgress,
    project,
    deferredChaptersSearch,
    charactersRenderLimit,
    relationshipsRenderLimit,
    chapterOutlinesRenderLimit,
    partOutlinesRenderLimit,
    completedChaptersRenderLimit,
  });

  const openOutlineEditor = useCallback((outline: any) => {
    const chapterNumber = Number(outline?.chapter_number || 0);
    if (!chapterNumber) return;
    setEditingChapter({
      chapter_number: chapterNumber,
      title: String(outline?.title || `第${chapterNumber}章`),
      summary: String(outline?.summary || ''),
      generation_status: 'not_generated',
    });
    setIsOutlineModalOpen(true);
  }, []);

  const applyProjectPayload = useCallback((data: any) => {
    setProject(data);
    applyProjectBlueprint(data?.blueprint);
  }, [applyProjectBlueprint]);

  const { fetchProject } = useNovelDetailBootstrap({
    id,
    applyProjectPayload,
    setProject,
    setLoading,
    setImportStatus,
    setImportStatusLoading,
    setPartProgress,
    setSelectedCompletedChapterNumber,
    setSelectedCompletedChapter,
    hasImportStatusBootstrapRef,
    hasPartProgressBootstrapRef,
  });

  const fetchProjectButton = useCallback(async () => {
    if (isBlueprintDirty) {
      const ok = await confirmDialog({
        title: '刷新确认',
        message: `${dirtySummary || '有未保存的修改'}。\n\n确定要刷新并丢弃本地修改吗？`,
        confirmText: '刷新并丢弃',
        dialogType: 'warning',
      });
      if (!ok) return;
    }
    await fetchProject();
  }, [dirtySummary, fetchProject, isBlueprintDirty]);

  const {
    refreshImportStatus,
    cancelImportAnalysis,
    startImportAnalysis,
  } = useNovelDetailImportStatus({
    id,
    importStatus,
    projectImportAnalysisStatus: project?.import_analysis_status,
    setImportStatus,
    setImportStatusLoading,
    setImportStarting,
    hasImportStatusBootstrapRef,
    fetchProject,
    addToast,
  });

  useNovelDetailChapterSelection({
    id,
    activeTab,
    completedChapters,
    selectedCompletedChapterNumber,
    selectedCompletedChapter,
    setSelectedCompletedChapterNumber,
    setSelectedCompletedChapter,
    setSelectedCompletedChapterLoading,
  });

  const { exportSelectedChapter } = useNovelDetailChapterExport({
    id,
    projectTitle: project?.title,
    selectedCompletedChapterNumber,
    selectedCompletedChapter,
    addToast,
  });

  const {
    editingCharIndex,
    charForm,
    isCharModalOpen,
    charactersView,
    isProtagonistModalOpen,
    editingRelIndex,
    relForm,
    isRelModalOpen,
    setCharForm,
    setIsCharModalOpen,
    setCharactersView,
    setIsProtagonistModalOpen,
    setRelForm,
    setIsRelModalOpen,
    handleEditChar,
    handleAddChar,
    handleSaveChar,
    handleDeleteChar,
    handleAddRel,
    handleEditRel,
    handleSaveRel,
    handleDeleteRel,
  } = useNovelDetailCharacterRelationshipEditor({
    blueprintData,
    setBlueprintData,
    addToast,
  });

  const { handleSave } = useNovelDetailBlueprintSave({
    id,
    blueprintData,
    worldSettingDraft,
    setBlueprintData,
    markBlueprintSaved,
    setSaving,
    setActiveTab,
    addToast,
  });

  const {
    isRefineModalOpen,
    refineInstruction,
    refineForce,
    refining,
    refineResult,
    setRefineInstruction,
    setRefineForce,
    closeRefineModal,
    openRefineModal,
    handleRefineBlueprint,
  } = useNovelDetailBlueprintRefine({
    id,
    fetchProject,
    setBlueprintData,
    addToast,
  });

  const {
    ragSyncing,
    handleRagSync,
  } = useNovelDetailRagSync({
    id,
    addToast,
  });

  const {
    avatarLoading,
    handleAvatarClick,
    handleDeleteAvatar,
  } = useNovelDetailAvatarManager({
    id,
    projectHasBlueprint: Boolean(project?.blueprint),
    hasAvatar: Boolean(blueprintData?.avatar_svg),
    setBlueprintData,
    addToast,
  });

  const {
    isEditTitleModalOpen,
    editTitleValue,
    editTitleSaving,
    setEditTitleValue,
    openEditTitleModal,
    closeEditTitleModal,
    saveProjectTitle,
  } = useNovelDetailTitleEditor({
    id,
    projectTitle: project?.title,
    fetchProject,
    addToast,
  });

  const { handleExport } = useNovelDetailExport({
    id,
    projectTitle: project?.title,
    addToast,
  });

  const { handleRegenerateOutline } = useNovelDetailChapterOutlineRegenerate({
    id,
    chapterOutlines,
    fetchProject,
    openOptionalPromptModal,
    addToast,
  });

  const {
    deleteLatestCount,
    setDeleteLatestCount,
    deletingLatest,
    regenerateLatestCount,
    setRegenerateLatestCount,
    regenerateLatestPrompt,
    setRegenerateLatestPrompt,
    regeneratingLatest,
    handleDeleteLatestOutlines,
    handleRegenerateLatestOutlines,
  } = useNovelDetailLatestChapterOutlineActions({
    id,
    chapterOutlines,
    fetchProject,
    setIsDeleteLatestModalOpen,
    setIsRegenerateLatestModalOpen,
    addToast,
  });

  useEffect(() => {
    if (!id) return;
    writeNovelDetailPartProgress(id, partProgress ?? null);
    hasPartProgressBootstrapRef.current = partProgress !== null;
  }, [id, partProgress]);

  const fetchPartProgress = useCallback(async () => {
    if (!id) return;
    const hadPartSnapshot = hasPartProgressBootstrapRef.current;
    if (!hadPartSnapshot) {
      setPartLoading(true);
    }
    try {
      const data = await writerApi.getPartOutlines(id);
      setPartProgress(data);
      hasPartProgressBootstrapRef.current = data !== null;
      writeNovelDetailPartProgress(id, data ?? null);
    } catch (e) {
      if (!hadPartSnapshot) {
        setPartProgress(null);
        hasPartProgressBootstrapRef.current = false;
      }
    } finally {
      setPartLoading(false);
    }
  }, [id]);

  const {
    deleteLatestPartsCount,
    setDeleteLatestPartsCount,
    deletingLatestParts,
    regenerateLatestPartsCount,
    setRegenerateLatestPartsCount,
    regenerateLatestPartsPrompt,
    setRegenerateLatestPartsPrompt,
    regeneratingLatestParts,
    handleDeleteLatestPartOutlines,
    handleRegenerateLatestPartOutlines,
  } = useNovelDetailLatestPartOutlineActions({
    id,
    partOutlines,
    maxDeletablePartCount,
    fetchProject,
    fetchPartProgress,
    setIsDeleteLatestPartsModalOpen,
    setIsRegenerateLatestPartsModalOpen,
    addToast,
  });

  const openPartOutlinesModal = useCallback((mode: 'generate' | 'continue') => {
    if (!id) return;
    if (!partTotalChapters) {
      addToast('无法获取总章节数，请先生成蓝图', 'error');
      return;
    }
    setPartGenerateMode(mode);
    setIsPartGenerateModalOpen(true);
  }, [addToast, id, partTotalChapters]);

  const {
    regeneratingPartKey,
    handleRegenerateAllPartOutlines,
    handleRegenerateLastPartOutline,
    handleRegeneratePartOutline,
  } = useNovelDetailPartOutlineRegenerate({
    id,
    partProgress,
    setPartProgress,
    fetchProject,
    fetchPartProgress,
    openOptionalPromptModal,
    addToast,
  });

  const {
    generatingPartChapters,
    handleGeneratePartChapters,
  } = useNovelDetailPartOutlineChapterGenerate({
    id,
    chapterOutlines,
    fetchProject,
    fetchPartProgress,
    addToast,
  });

  useEffect(() => {
    if (id) {
      fetchProject();
    }
  }, [id, fetchProject]);

  useEffect(() => {
    if (id && activeTab === 'outlines') {
      fetchPartProgress();
    }
  }, [id, activeTab, fetchPartProgress]);

  const tabInputSources: NovelDetailTabSources = {
    overviewWorld: {
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
    },
    characterRelationship: {
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
    },
    outlines: {
      blueprintData,
      loading,
      safeNavigate,
      fetchProjectButton,
      chapterOutlines,
      visibleChapterOutlines,
      remainingChapterOutlines,
      chaptersByNumber,
      openOutlineEditor,
      handleRegenerateOutline,
      setChapterOutlinesRenderLimit,
      setDeleteLatestCount,
      setIsDeleteLatestModalOpen,
      setRegenerateLatestCount,
      setRegenerateLatestPrompt,
      setIsRegenerateLatestModalOpen,
      setIsBatchModalOpen,
      partLoading,
      partOutlines,
      visiblePartOutlines,
      remainingPartOutlines,
      partProgress,
      canContinuePartOutlines,
      partCoveredChapters,
      maxDeletablePartCount,
      deletingLatestParts,
      regeneratingLatestParts,
      regeneratingPartKey,
      generatingPartChapters,
      setIsDeleteLatestPartsModalOpen,
      setIsRegenerateLatestPartsModalOpen,
      openPartOutlinesModal,
      handleRegenerateLastPartOutline,
      handleRegenerateAllPartOutlines,
      handleRegeneratePartOutline,
      handleGeneratePartChapters,
      setDetailPart,
      countOutlinesInRange,
      setPartOutlinesRenderLimit,
    },
    chapters: {
      completedChapters,
      visibleCompletedChapters,
      remainingCompletedChapters,
      setCompletedChaptersRenderLimit,
      chaptersSearch,
      setChaptersSearch,
      selectedCompletedChapterNumber,
      setSelectedCompletedChapterNumber,
      selectedCompletedChapter,
      selectedCompletedChapterLoading,
      exportSelectedChapter,
      latestChapterNumber,
      fetchProject,
      safeNavigate,
    },
  };

  const {
    overviewTabProps,
    worldTabProps,
    charactersTabProps,
    relationshipsTabProps,
    outlinesTabProps,
    chaptersTabProps,
  } = useNovelDetailTabProps({
    projectId: id!,
    sources: tabInputSources,
  });

  if (loading) return <div className="flex h-screen items-center justify-center text-book-text-muted">加载中...</div>;
  if (!project) return <div className="flex h-screen items-center justify-center text-book-text-muted">项目不存在</div>;

  return (
    <div className="min-h-screen bg-book-bg flex flex-col">
      <NovelDetailHeader
        project={project}
        projectId={id!}
        blueprintData={blueprintData}
        avatarLoading={avatarLoading}
        handleAvatarClick={handleAvatarClick}
        handleDeleteAvatar={handleDeleteAvatar}
        openEditTitleModal={openEditTitleModal}
        isBlueprintDirty={isBlueprintDirty}
        dirtySummary={dirtySummary}
        saving={saving}
        worldSettingError={worldSettingError}
        handleSave={handleSave}
        safeNavigate={safeNavigate}
        handleExport={handleExport}
        ragSyncing={ragSyncing}
        handleRagSync={handleRagSync}
        openRefineModal={openRefineModal}
      />

      {/* Tabs - 照抄桌面端 novel_detail/mixins/tab_manager.py */}
      <NovelDetailTabBar activeTab={activeTab} onChange={(next) => setActiveTab(next)} />

      <NovelDetailTabContent
        activeTab={activeTab}
        overviewTabProps={overviewTabProps}
        worldTabProps={worldTabProps}
        charactersTabProps={charactersTabProps}
        relationshipsTabProps={relationshipsTabProps}
        outlinesTabProps={outlinesTabProps}
        chaptersTabProps={chaptersTabProps}
      />

      {/* Optional Prompt Modal（用于“重生成”类操作的可选优化提示词） */}
      {optionalPromptModal}

      <TitleAndBlueprintModals
        isRefineModalOpen={isRefineModalOpen}
        closeRefineModal={closeRefineModal}
        handleRefineBlueprint={handleRefineBlueprint}
        refining={refining}
        refineInstruction={refineInstruction}
        setRefineInstruction={setRefineInstruction}
        refineForce={refineForce}
        setRefineForce={setRefineForce}
        refineResult={refineResult}
        isEditTitleModalOpen={isEditTitleModalOpen}
        closeEditTitleModal={closeEditTitleModal}
        editTitleSaving={editTitleSaving}
        saveProjectTitle={saveProjectTitle}
        editTitleValue={editTitleValue}
        setEditTitleValue={setEditTitleValue}
      />

      <CharacterAndRelationshipModals
        isCharModalOpen={isCharModalOpen}
        setIsCharModalOpen={setIsCharModalOpen}
        editingCharIndex={editingCharIndex}
        handleSaveChar={handleSaveChar}
        charForm={charForm}
        setCharForm={setCharForm}
        isRelModalOpen={isRelModalOpen}
        setIsRelModalOpen={setIsRelModalOpen}
        editingRelIndex={editingRelIndex}
        handleSaveRel={handleSaveRel}
        characterNames={characterNames}
        relForm={relForm}
        setRelForm={setRelForm}
      />

      <NovelDetailLazyBusinessModals
        projectId={id!}
        isOutlineModalOpen={isOutlineModalOpen}
        setIsOutlineModalOpen={setIsOutlineModalOpen}
        editingChapter={editingChapter}
        fetchProject={fetchProject}
        isBatchModalOpen={isBatchModalOpen}
        setIsBatchModalOpen={setIsBatchModalOpen}
        isProtagonistModalOpen={isProtagonistModalOpen}
        setIsProtagonistModalOpen={setIsProtagonistModalOpen}
        currentChapterNumber={latestChapterNumber}
        isPartGenerateModalOpen={isPartGenerateModalOpen}
        setIsPartGenerateModalOpen={setIsPartGenerateModalOpen}
        partGenerateMode={partGenerateMode}
        totalChapters={Math.max(10, partTotalChapters || 10)}
        chaptersPerPart={Number(blueprintData?.chapters_per_part || 25) || 25}
        currentCoveredChapters={partCoveredChapters || undefined}
        currentPartsCount={partOutlines.length || undefined}
        fetchPartProgress={fetchPartProgress}
        detailPart={detailPart}
        setDetailPart={setDetailPart}
      />

      <LatestPartOutlineModals
        isDeleteLatestPartsModalOpen={isDeleteLatestPartsModalOpen}
        setIsDeleteLatestPartsModalOpen={setIsDeleteLatestPartsModalOpen}
        deletingLatestParts={deletingLatestParts}
        maxDeletablePartCount={maxDeletablePartCount}
        handleDeleteLatestPartOutlines={handleDeleteLatestPartOutlines}
        deleteLatestPartsCount={deleteLatestPartsCount}
        setDeleteLatestPartsCount={setDeleteLatestPartsCount}
        isRegenerateLatestPartsModalOpen={isRegenerateLatestPartsModalOpen}
        setIsRegenerateLatestPartsModalOpen={setIsRegenerateLatestPartsModalOpen}
        regeneratingLatestParts={regeneratingLatestParts}
        partOutlines={partOutlines}
        handleRegenerateLatestPartOutlines={handleRegenerateLatestPartOutlines}
        regenerateLatestPartsCount={regenerateLatestPartsCount}
        setRegenerateLatestPartsCount={setRegenerateLatestPartsCount}
        regenerateLatestPartsPrompt={regenerateLatestPartsPrompt}
        setRegenerateLatestPartsPrompt={setRegenerateLatestPartsPrompt}
      />

      <LatestChapterOutlineModals
        isRegenerateLatestModalOpen={isRegenerateLatestModalOpen}
        setIsRegenerateLatestModalOpen={setIsRegenerateLatestModalOpen}
        regeneratingLatest={regeneratingLatest}
        chapterOutlines={chapterOutlines}
        handleRegenerateLatestOutlines={handleRegenerateLatestOutlines}
        regenerateLatestCount={regenerateLatestCount}
        setRegenerateLatestCount={setRegenerateLatestCount}
        regenerateLatestPrompt={regenerateLatestPrompt}
        setRegenerateLatestPrompt={setRegenerateLatestPrompt}
        isDeleteLatestModalOpen={isDeleteLatestModalOpen}
        setIsDeleteLatestModalOpen={setIsDeleteLatestModalOpen}
        deletingLatest={deletingLatest}
        handleDeleteLatestOutlines={handleDeleteLatestOutlines}
        deleteLatestCount={deleteLatestCount}
        setDeleteLatestCount={setDeleteLatestCount}
      />
    </div>
  );
};
