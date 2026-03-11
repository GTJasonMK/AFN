import React, { useState, useMemo, useRef, useDeferredValue } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useToast, type ToastType } from '../components/feedback/Toast';
import { useConfirmTextModal } from '../hooks/useConfirmTextModal';
import { usePersistedTab } from '../hooks/usePersistedTab';
import { type NovelDetailTab } from './novel-detail/NovelDetailTabBar';
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
import { useNovelDetailDerivedData } from './novel-detail/useNovelDetailDerivedData';
import { useNovelDetailModalStates } from './novel-detail/useNovelDetailModalStates';
import { useNovelDetailOutlineActions } from './novel-detail/useNovelDetailOutlineActions';
import { useNovelDetailOutlineEditor } from './novel-detail/useNovelDetailOutlineEditor';
import { useNovelDetailPartProgressSync } from './novel-detail/useNovelDetailPartProgressSync';
import { useNovelDetailProjectSync } from './novel-detail/useNovelDetailProjectSync';
import { useNovelDetailModalProps } from './novel-detail/useNovelDetailModalProps';
import { useNovelDetailTabProps } from './novel-detail/useNovelDetailTabProps';
import { NovelDetailPageLayout } from './novel-detail/NovelDetailPageLayout';
import { buildNovelDetailModalInput } from './novel-detail/buildNovelDetailModalInput';
import { buildNovelDetailPageLayoutProps } from './novel-detail/buildNovelDetailPageLayoutProps';
import { buildNovelDetailModalInputParams } from './novel-detail/buildNovelDetailModalInputParams';
import { buildNovelDetailTabInput } from './novel-detail/buildNovelDetailTabInput';
import { buildNovelDetailTabSources } from './novel-detail/buildNovelDetailTabSources';

const NOVEL_DETAIL_TABS: readonly NovelDetailTab[] = ['overview', 'world', 'characters', 'relationships', 'outlines', 'chapters'];

type NovelDetailPageProps = {
  projectId: string;
};

const NovelDetailPage: React.FC<NovelDetailPageProps> = ({ projectId }) => {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const addLegacyToast = React.useCallback((message: string, type?: string) => {
    const normalizedType: ToastType =
      type === 'success' || type === 'error' || type === 'info' ? type : 'info';
    addToast(message, normalizedType);
  }, [addToast]);
  
  const [project, setProject] = useState<any>(null);
  const activeTabStorageKey = useMemo(() => `afn:novel_detail:active_tab:${projectId}`, [projectId]);
  const [activeTab, setActiveTab] = usePersistedTab(activeTabStorageKey, 'overview', NOVEL_DETAIL_TABS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form states
  const [blueprintData, setBlueprintData] = useState<any>({});
  const [worldEditMode, setWorldEditMode] = useState<'structured' | 'json'>('structured');

  // Part outlines progress
  const [partProgress, setPartProgress] = useState<any | null>(null);
  const [partLoading, setPartLoading] = useState(false);
  const [detailPart, setDetailPart] = useState<any | null>(null);

  const modalStates = useNovelDetailModalStates();
  const {
    setIsOutlineModalOpen,
    setIsDeleteLatestModalOpen,
    setIsRegenerateLatestModalOpen,
    setIsPartGenerateModalOpen,
    setPartGenerateMode,
    setIsDeleteLatestPartsModalOpen,
    setIsRegenerateLatestPartsModalOpen,
  } = modalStates;

  // 导入分析进度（导入小说专用）
  const [importStatus, setImportStatus] = useState<any | null>(null);
  const [importStatusLoading, setImportStatusLoading] = useState(false);
  const [importStarting, setImportStarting] = useState(false);

  // 已完成章节（项目详情页展示，桌面端 ChaptersSection 对齐）
  const [chaptersSearch, setChaptersSearch] = useState('');
  const [selectedCompletedChapterNumber, setSelectedCompletedChapterNumber] = useState<number | null>(null);
  const [selectedCompletedChapter, setSelectedCompletedChapter] = useState<any | null>(null);
  const [selectedCompletedChapterLoading, setSelectedCompletedChapterLoading] = useState(false);

  const blueprintDraftState = useNovelDetailBlueprintDraft({
    blueprintData,
    setBlueprintData,
  });
  const {
    worldSettingDraft,
    worldSettingError,
    isBlueprintDirty,
    dirtySummary,
    applyProjectBlueprint,
    markBlueprintSaved,
  } = blueprintDraftState;

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

  const renderLimitState = useNovelDetailRenderLimits({
    id: projectId,
    activeTab,
    deferredChaptersSearch,
  });
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
  } = renderLimitState;

  const derivedData = useNovelDetailDerivedData({
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
  const {
    chapterOutlines,
    partOutlines,
    partTotalChapters,
    maxDeletablePartCount,
    completedChapters,
    characterNames,
  } = derivedData;

  const {
    editingChapter,
    openOutlineEditor,
  } = useNovelDetailOutlineEditor({
    setIsOutlineModalOpen,
  });

  const {
    fetchProject,
    fetchProjectButton,
    refreshImportStatus,
    cancelImportAnalysis,
    startImportAnalysis,
  } = useNovelDetailProjectSync({
    projectId,
    isBlueprintDirty,
    dirtySummary,
    applyProjectBlueprint,
    setProject,
    setLoading,
    importStatus,
    projectImportAnalysisStatus: project?.import_analysis_status,
    setImportStatus,
    setImportStatusLoading,
    setImportStarting,
    setPartProgress,
    setSelectedCompletedChapterNumber,
    setSelectedCompletedChapter,
    hasImportStatusBootstrapRef,
    hasPartProgressBootstrapRef,
    addToast: addLegacyToast,
  });

  useNovelDetailChapterSelection({
    id: projectId,
    activeTab,
    completedChapters,
    selectedCompletedChapterNumber,
    selectedCompletedChapter,
    setSelectedCompletedChapterNumber,
    setSelectedCompletedChapter,
    setSelectedCompletedChapterLoading,
  });

  const { exportSelectedChapter } = useNovelDetailChapterExport({
    id: projectId,
    projectTitle: project?.title,
    selectedCompletedChapterNumber,
    selectedCompletedChapter,
    addToast: addLegacyToast,
  });

  const characterRelationshipEditor = useNovelDetailCharacterRelationshipEditor({
    blueprintData,
    setBlueprintData,
    addToast: addLegacyToast,
  });
  const {
    isProtagonistModalOpen,
    setIsProtagonistModalOpen,
  } = characterRelationshipEditor;

  const { handleSave } = useNovelDetailBlueprintSave({
    id: projectId,
    blueprintData,
    worldSettingDraft,
    setBlueprintData,
    markBlueprintSaved,
    setSaving,
    setActiveTab,
    addToast: addLegacyToast,
  });

  const blueprintRefine = useNovelDetailBlueprintRefine({
    id: projectId,
    fetchProject,
    setBlueprintData,
    addToast: addLegacyToast,
  });
  const { openRefineModal, ...blueprintRefineModalProps } = blueprintRefine;

  const ragSync = useNovelDetailRagSync({
    id: projectId,
    addToast: addLegacyToast,
  });

  const avatarManager = useNovelDetailAvatarManager({
    id: projectId,
    projectHasBlueprint: Boolean(project?.blueprint),
    hasAvatar: Boolean(blueprintData?.avatar_svg),
    setBlueprintData,
    addToast: addLegacyToast,
  });

  const titleEditor = useNovelDetailTitleEditor({
    id: projectId,
    projectTitle: project?.title,
    fetchProject,
    addToast: addLegacyToast,
  });
  const { openEditTitleModal, ...titleEditorModalProps } = titleEditor;

  const { handleExport } = useNovelDetailExport({
    id: projectId,
    projectTitle: project?.title,
    addToast: addLegacyToast,
  });

  const {
    fetchPartProgress,
    refreshProjectAndPartProgress,
  } = useNovelDetailPartProgressSync({
    projectId,
    activeTab,
    partProgress,
    setPartProgress,
    setPartLoading,
    hasPartProgressBootstrapRef,
    fetchProject,
  });

  const {
    handleRegenerateOutline,
    latestOutlineInputParams,
    openPartOutlinesModal,
    regeneratingPartKey,
    handleRegenerateAllPartOutlines,
    handleRegenerateLastPartOutline,
    handleRegeneratePartOutline,
    generatingPartChapters,
    handleGeneratePartChapters,
  } = useNovelDetailOutlineActions({
    projectId,
    chapterOutlines,
    partOutlines,
    partProgress,
    partTotalChapters,
    maxDeletablePartCount,
    setPartProgress,
    fetchProject,
    fetchPartProgress,
    setIsDeleteLatestModalOpen,
    setIsRegenerateLatestModalOpen,
    setIsDeleteLatestPartsModalOpen,
    setIsRegenerateLatestPartsModalOpen,
    setPartGenerateMode,
    setIsPartGenerateModalOpen,
    openOptionalPromptModal,
    addToast: addLegacyToast,
  });

  const tabInput = buildNovelDetailTabInput({
    overviewWorldBase: {
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
    },
    characterRelationshipBase: {
      setCharactersRenderLimit,
      setRelationshipsRenderLimit,
    },
    outlinesBase: {
      blueprintData,
      loading,
      safeNavigate,
      fetchProjectButton,
      partLoading,
      partProgress,
      openOutlineEditor,
      handleRegenerateOutline,
      setChapterOutlinesRenderLimit,
      regeneratingPartKey,
      generatingPartChapters,
      openPartOutlinesModal,
      handleRegenerateLastPartOutline,
      handleRegenerateAllPartOutlines,
      handleRegeneratePartOutline,
      handleGeneratePartChapters,
      setDetailPart,
      setPartOutlinesRenderLimit,
    },
    chaptersBase: {
      chaptersSearch,
      setChaptersSearch,
      selectedCompletedChapterNumber,
      setSelectedCompletedChapterNumber,
      selectedCompletedChapter,
      selectedCompletedChapterLoading,
      setCompletedChaptersRenderLimit,
      exportSelectedChapter,
      fetchProject,
      safeNavigate,
    },
    blueprintDraftState,
    characterRelationshipEditor,
    derivedData,
    modalStates,
  });

  const tabSources = buildNovelDetailTabSources({
    tab: tabInput,
    ...latestOutlineInputParams,
  });

  const modalInput = buildNovelDetailModalInput({
    businessBase: {
      blueprintData,
      editingChapter,
      isProtagonistModalOpen,
      setIsProtagonistModalOpen,
      detailPart,
      setDetailPart,
      refreshProjectAndPartProgress,
    },
    derivedData,
    modalStates,
  });

  const modalInputParamsArgs = buildNovelDetailModalInputParams({
    modal: modalInput,
    ...latestOutlineInputParams,
  });

  const tabProps = useNovelDetailTabProps({
    projectId,
    sources: tabSources,
  });

  const {
    lazyBusinessModalProps,
    latestPartOutlineModalProps,
    latestChapterOutlineModalProps,
  } = useNovelDetailModalProps(modalInputParamsArgs);

  const {
    headerProps,
    titleAndBlueprintModalProps,
    characterAndRelationshipModalProps,
  } = buildNovelDetailPageLayoutProps({
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
  });

  if (loading) return <div className="flex h-screen items-center justify-center text-book-text-muted">加载中...</div>;
  if (!project) return <div className="flex h-screen items-center justify-center text-book-text-muted">项目不存在</div>;

  return (
    <NovelDetailPageLayout
      headerProps={headerProps}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      tabProps={tabProps}
      optionalPromptModal={optionalPromptModal}
      titleAndBlueprintModalProps={titleAndBlueprintModalProps}
      characterAndRelationshipModalProps={characterAndRelationshipModalProps}
      projectId={projectId}
      onProjectRefresh={fetchProject}
      lazyBusinessModalProps={lazyBusinessModalProps}
      latestPartOutlineModalProps={latestPartOutlineModalProps}
      latestChapterOutlineModalProps={latestChapterOutlineModalProps}
    />
  );
};

export const NovelDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  if (!id) return <div className="flex h-screen items-center justify-center text-book-text-muted">项目不存在</div>;
  return <NovelDetailPage projectId={id} />;
};
