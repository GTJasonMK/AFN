import React, { useEffect, useMemo, useCallback, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { codingApi, CodingDependency, CodingFilePriority, CodingModule, CodingSystem } from '../api/coding';
import { FileCode, GitBranch, Database, Layout } from 'lucide-react';
import { BookButton } from '../components/ui/BookButton';
import { useSSE } from '../hooks/useSSE';
import { useToast } from '../components/feedback/Toast';
import { confirmDialog } from '../components/feedback/ConfirmDialog';
import { usePersistedTab } from '../hooks/usePersistedTab';
import { useTokenBuffer } from '../hooks/useTokenBuffer';
import { readBootstrapCache, writeBootstrapCache } from '../utils/bootstrapCache';
import { CodingDetailArchitectureTab } from './coding-detail/CodingDetailArchitectureTab';
import { CodingDetailDirectoryTab } from './coding-detail/CodingDetailDirectoryTab';
import { CodingDetailGenerationTab } from './coding-detail/CodingDetailGenerationTab';
import { CodingDetailModals } from './coding-detail/CodingDetailModals';
import { CodingDetailOverviewTab } from './coding-detail/CodingDetailOverviewTab';
import {
  CODING_DETAIL_BOOTSTRAP_TTL_MS,
  CODING_DETAIL_TABS,
  DEFAULT_VERSION_CREATED_AT,
  DirectoryInfoFormState,
  FileInfoFormState,
  getCodingDetailBootstrapKey,
  ModuleFormState,
  ResourceKey,
  ResourceStatus,
  ResourceStatusMap,
  SystemFormState,
  CodingDetailBootstrapSnapshot,
  createEmptyResourceStatus,
  createInitialResourceStatus,
  serializeResourceStatus,
} from './coding-detail/shared';

export const CodingDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const hasBootstrapRef = useRef(false);
  const currentProjectIdRef = useRef<string | null>(null);
  const inflightResourceLoadsRef = useRef<Partial<Record<ResourceKey, Promise<void>>>>({});
  const resourceRequestVersionRef = useRef<Record<ResourceKey, number>>({
    systems: 0,
    modules: 0,
    dependencies: 0,
    ragCompleteness: 0,
    treeData: 0,
  });

  // 对齐桌面端：从 CodingDetail 可直达 CodingDesk，并可携带 fileId 定位到指定文件
  const openCodingDesk = useCallback(
    (fileId?: number) => {
      if (!id) return;
      const fid = typeof fileId === 'number' && Number.isFinite(fileId) && fileId > 0 ? fileId : null;
      navigate(fid ? `/coding/desk/${id}?fileId=${fid}` : `/coding/desk/${id}`);
    },
    [id, navigate]
  );
  
  // 可选偏好弹窗：替代浏览器 prompt()，统一交互体验
  const pendingPreferenceActionRef = useRef<((preference?: string) => void | Promise<void>) | null>(null);
  const [isPreferenceModalOpen, setIsPreferenceModalOpen] = useState(false);
  const [preferenceModalTitle, setPreferenceModalTitle] = useState('偏好指导（可选）');
  const [preferenceModalHint, setPreferenceModalHint] = useState<string | null>(null);
  const [preferenceModalValue, setPreferenceModalValue] = useState('');

  const activeTabStorageKey = id ? `afn:coding_detail:active_tab:${id}` : null;
  const [activeTab, setActiveTab] = usePersistedTab(activeTabStorageKey, 'overview', CODING_DETAIL_TABS);

  const [project, setProject] = useState<any>(null);
  const [treeData, setTreeData] = useState<any>(null);
  const [treeExpandAllToken, setTreeExpandAllToken] = useState(0);
  const [treeCollapseAllToken, setTreeCollapseAllToken] = useState(0);
  const [selectedDirectory, setSelectedDirectory] = useState<any>(null);
  const [currentFile, setCurrentFile] = useState<any>(null);
  const [content, setContent] = useState('');
  const appendFileTokens = useCallback((text: string) => {
    setContent((prev) => prev + text);
  }, []);
  const {
    pushToken: pushFileToken,
    flush: flushFileTokens,
    reset: resetFileTokenBuffer,
  } = useTokenBuffer(appendFileTokens, 48);
  const [versions, setVersions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // File info modal（对齐桌面端 DirectorySection 的“编辑文件信息”能力）
  const [isFileInfoModalOpen, setIsFileInfoModalOpen] = useState(false);
  const [fileInfoForm, setFileInfoForm] = useState<FileInfoFormState>({
    description: '',
    purpose: '',
    priority: 'medium',
  });
  const [fileInfoSaving, setFileInfoSaving] = useState(false);

  // Directory info modal（对齐桌面端 DirectorySection 的“编辑目录信息”能力）
  const [isDirectoryInfoModalOpen, setIsDirectoryInfoModalOpen] = useState(false);
  const [directoryInfoForm, setDirectoryInfoForm] = useState<DirectoryInfoFormState>({ description: '' });
  const [directoryInfoSaving, setDirectoryInfoSaving] = useState(false);

  const [systems, setSystems] = useState<CodingSystem[]>([]);
  const [modules, setModules] = useState<CodingModule[]>([]);
  const [dependencies, setDependencies] = useState<CodingDependency[]>([]);
  const [resourceState, setResourceState] = useState<ResourceStatusMap>(() => createEmptyResourceStatus());
  const resourceStateRef = useRef<ResourceStatusMap>(createEmptyResourceStatus());
  const [tabActionLoading, setTabActionLoading] = useState(false);

  // System modal
  const [isSystemModalOpen, setIsSystemModalOpen] = useState(false);
  const [editingSystem, setEditingSystem] = useState<CodingSystem | null>(null);
  const [systemForm, setSystemForm] = useState<SystemFormState>({
    name: '',
    description: '',
    responsibilitiesText: '',
    techRequirements: '',
  });
  const [systemSaving, setSystemSaving] = useState(false);

  // Module modal
  const [isModuleModalOpen, setIsModuleModalOpen] = useState(false);
  const [editingModule, setEditingModule] = useState<CodingModule | null>(null);
  const [moduleForm, setModuleForm] = useState<ModuleFormState>({
    systemNumber: '',
    name: '',
    type: 'service',
    description: '',
    iface: '',
    dependenciesText: '',
  });
  const [moduleSaving, setModuleSaving] = useState(false);

  const [genAllRunning, setGenAllRunning] = useState(false);
  const [genAllLogs, setGenAllLogs] = useState<string[]>([]);

  // RAG
  const [ragCompleteness, setRagCompleteness] = useState<any | null>(null);
  const [ragIngesting, setRagIngesting] = useState(false);
  const [ragQuery, setRagQuery] = useState('');
  const [ragQueryLoading, setRagQueryLoading] = useState(false);
  const [ragResult, setRagResult] = useState<any | null>(null);
  const tabLoading = tabActionLoading || Object.values(resourceState).some((item) => item.loading);
  const ragLoading = resourceState.ragCompleteness.loading;

  const replaceResourceState = useCallback((next: ResourceStatusMap) => {
    resourceStateRef.current = next;
    setResourceState(next);
  }, []);

  const patchResourceState = useCallback((key: ResourceKey, patch: Partial<ResourceStatus>) => {
    setResourceState((prev) => {
      const next = {
        ...prev,
        [key]: {
          ...prev[key],
          ...patch,
        },
      };
      resourceStateRef.current = next;
      return next;
    });
  }, []);

  const invalidateResources = useCallback((keys: ResourceKey[]) => {
    setResourceState((prev) => {
      const next = { ...prev };
      for (const key of keys) {
        next[key] = {
          ...prev[key],
          loaded: false,
          loading: false,
          error: null,
        };
      }
      resourceStateRef.current = next;
      return next;
    });
  }, []);

  useEffect(() => {
    if (!id) return;
    currentProjectIdRef.current = id;
    inflightResourceLoadsRef.current = {};
    resourceRequestVersionRef.current = {
      systems: 0,
      modules: 0,
      dependencies: 0,
      ragCompleteness: 0,
      treeData: 0,
    };

    setCurrentFile(null);
    setSelectedDirectory(null);
    setContent('');
    setVersions([]);
    setRagResult(null);

    const cached = readBootstrapCache<CodingDetailBootstrapSnapshot>(
      getCodingDetailBootstrapKey(id),
      CODING_DETAIL_BOOTSTRAP_TTL_MS,
    );

    if (!cached) {
      hasBootstrapRef.current = false;
      setProject(null);
      setTreeData(null);
      setSystems([]);
      setModules([]);
      setDependencies([]);
      setRagCompleteness(null);
      replaceResourceState(createEmptyResourceStatus());
      setLoading(true);
      return;
    }

    setProject(cached.project ?? null);
    setTreeData(cached.treeData ?? null);
    setSystems(Array.isArray(cached.systems) ? cached.systems : []);
    setModules(Array.isArray(cached.modules) ? cached.modules : []);
    setDependencies(Array.isArray(cached.dependencies) ? cached.dependencies : []);
    setRagCompleteness(cached.ragCompleteness ?? null);
    replaceResourceState(createInitialResourceStatus(cached));

    hasBootstrapRef.current = Boolean(cached.project);
    setLoading(!cached.project);
  }, [id, replaceResourceState]);

  const openPreferenceModal = useCallback((opts: {
    title?: string;
    hint?: string;
    initialValue?: string;
    onConfirm: (preference?: string) => void | Promise<void>;
  }) => {
    setPreferenceModalTitle(opts.title || '偏好指导（可选）');
    setPreferenceModalHint(opts.hint || null);
    setPreferenceModalValue(opts.initialValue || '');
    pendingPreferenceActionRef.current = opts.onConfirm;
    setIsPreferenceModalOpen(true);
  }, []);

  const confirmPreferenceModal = useCallback(async () => {
    const fn = pendingPreferenceActionRef.current;
    pendingPreferenceActionRef.current = null;
    setIsPreferenceModalOpen(false);
    const text = (preferenceModalValue || '').trim();
    try {
      await fn?.(text ? text : undefined);
    } catch (e) {
      console.error(e);
      addToast('操作失败', 'error');
    }
  }, [addToast, preferenceModalValue]);

  const loadData = useCallback(async () => {
    if (!id) return;
    if (!hasBootstrapRef.current) {
      setLoading(true);
    }
    try {
      const proj = await codingApi.get(id);
      setProject(proj);
      hasBootstrapRef.current = true;
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id, loadData]);

  useEffect(() => {
    if (!id) return;
    if (!project && !treeData && systems.length === 0 && modules.length === 0 && dependencies.length === 0 && !ragCompleteness) {
      return;
    }

    writeBootstrapCache<CodingDetailBootstrapSnapshot>(getCodingDetailBootstrapKey(id), {
      project,
      treeData,
      systems,
      modules,
      dependencies,
      ragCompleteness,
      resourceState: serializeResourceStatus(resourceState),
    });
  }, [dependencies, id, modules, project, ragCompleteness, resourceState, systems, treeData]);

  const handleGenerateBlueprint = async () => {
    if (!id) return;
    try {
      await codingApi.generateBlueprint(id);
      addToast('蓝图已生成', 'success');
      loadData();
    } catch (e) {
      console.error(e);
      addToast('蓝图生成失败', 'error');
    }
  };

  const ensureResource = useCallback(async (key: ResourceKey, opts: { force?: boolean } = {}) => {
    if (!id) return;

    const force = Boolean(opts.force);
    const currentState = resourceStateRef.current[key];
    const inflight = inflightResourceLoadsRef.current[key];
    if (!force) {
      if (currentState.loaded) return;
      if (inflight) return inflight;
    }

    const requestId = id;
    const requestVersion = resourceRequestVersionRef.current[key] + 1;
    resourceRequestVersionRef.current[key] = requestVersion;
    patchResourceState(key, { loading: true, error: null });

    const request = (async () => {
      try {
        switch (key) {
          case 'systems': {
            const list = await codingApi.listSystems(requestId);
            if (currentProjectIdRef.current !== requestId || resourceRequestVersionRef.current[key] !== requestVersion) return;
            setSystems(list);
            break;
          }
          case 'modules': {
            const list = await codingApi.listModules(requestId);
            if (currentProjectIdRef.current !== requestId || resourceRequestVersionRef.current[key] !== requestVersion) return;
            setModules(list);
            break;
          }
          case 'dependencies': {
            const list = await codingApi.listDependencies(requestId);
            if (currentProjectIdRef.current !== requestId || resourceRequestVersionRef.current[key] !== requestVersion) return;
            setDependencies(list);
            break;
          }
          case 'ragCompleteness': {
            const data = await codingApi.getRagCompleteness(requestId);
            if (currentProjectIdRef.current !== requestId || resourceRequestVersionRef.current[key] !== requestVersion) return;
            setRagCompleteness(data);
            break;
          }
          case 'treeData': {
            const tree = await codingApi.getDirectoryTree(requestId);
            if (currentProjectIdRef.current !== requestId || resourceRequestVersionRef.current[key] !== requestVersion) return;
            setTreeData(tree);
            break;
          }
        }

        patchResourceState(key, {
          loaded: true,
          loading: false,
          error: null,
          lastLoadedAt: Date.now(),
        });
      } catch (e) {
        console.error(e);
        if (currentProjectIdRef.current !== requestId || resourceRequestVersionRef.current[key] !== requestVersion) return;

        switch (key) {
          case 'systems':
            setSystems([]);
            addToast('加载系统列表失败', 'error');
            break;
          case 'modules':
            setModules([]);
            addToast('加载模块列表失败', 'error');
            break;
          case 'dependencies':
            setDependencies([]);
            addToast('加载依赖列表失败', 'error');
            break;
          case 'ragCompleteness':
            setRagCompleteness(null);
            addToast('RAG 完整性检查失败', 'error');
            break;
          case 'treeData':
            setTreeData(null);
            addToast('加载目录结构失败', 'error');
            break;
        }

        patchResourceState(key, {
          loaded: false,
          loading: false,
          error: e instanceof Error ? e.message : 'load_failed',
        });
      } finally {
        if (resourceRequestVersionRef.current[key] === requestVersion) {
          delete inflightResourceLoadsRef.current[key];
        }
      }
    })();

    inflightResourceLoadsRef.current[key] = request;
    return request;
  }, [addToast, id, patchResourceState]);

  const ensureResources = useCallback(async (keys: ResourceKey[], opts: { force?: boolean } = {}) => {
    await Promise.allSettled(keys.map((key) => ensureResource(key, opts)));
  }, [ensureResource]);

  const refreshSystems = useCallback(async () => {
    await ensureResources(['systems'], { force: true });
  }, [ensureResources]);

  const refreshDependencies = useCallback(async () => {
    await ensureResources(['dependencies'], { force: true });
  }, [ensureResources]);

  const refreshRagCompleteness = useCallback(async () => {
    await ensureResources(['ragCompleteness'], { force: true });
  }, [ensureResources]);

  const refreshTreeData = useCallback(async () => {
    await ensureResources(['treeData'], { force: true });
  }, [ensureResources]);

	  const ingestRag = useCallback(async (force: boolean) => {
	    if (!id) return;
	    if (force) {
	      const ok = await confirmDialog({
	        title: '确认入库',
	        message: '强制全量入库会对所有类型重新入库，耗时更长。是否继续？',
	        confirmText: '继续',
	        dialogType: 'warning',
	      });
	      if (!ok) return;
	    }
	    setRagIngesting(true);
	    try {
	      const res = await codingApi.ingestAllRagData(id, force);
      if (res.success) {
        addToast('RAG 入库完成', 'success');
      } else {
        addToast('RAG 入库失败（请查看后端日志）', 'error');
      }
      await refreshRagCompleteness();
    } catch (e) {
      console.error(e);
      addToast('RAG 入库失败', 'error');
    } finally {
      setRagIngesting(false);
    }
  }, [addToast, id, refreshRagCompleteness]);

  const runRagQuery = useCallback(async () => {
    if (!id) return;
    const q = (ragQuery || '').trim();
    if (!q) return;
    setRagQueryLoading(true);
    try {
      const res = await codingApi.queryRag(id, q, { topK: 8 });
      setRagResult(res);
    } catch (e) {
      console.error(e);
      addToast('RAG 查询失败', 'error');
      setRagResult(null);
    } finally {
      setRagQueryLoading(false);
    }
  }, [addToast, id, ragQuery]);

  useEffect(() => {
    if (!id) return;
    if (activeTab === 'overview') {
      void ensureResources(['systems', 'modules']);
      return;
    }
    if (activeTab === 'architecture') {
      void ensureResources(['systems', 'modules']);
      return;
    }
    if (activeTab === 'directory') {
      void ensureResources(['treeData']);
      return;
    }
    if (activeTab === 'generation') {
      void ensureResources(['modules', 'dependencies', 'ragCompleteness']);
    }
  }, [activeTab, ensureResources, id]);

  const sortedSystemNumbers = useMemo(() => {
    return [...new Set(systems.map((s) => Number(s.system_number || 0)).filter((n) => n > 0))].sort((a, b) => a - b);
  }, [systems]);

  const currentFileBaseContent = useMemo(() => {
    if (!currentFile) return '';
    return String((currentFile as any).content ?? (currentFile as any).description ?? '// 暂无内容');
  }, [currentFile]);

  const editorVersions = useMemo(() => {
    const fileId = typeof (currentFile as any)?.id === 'number' ? Number((currentFile as any).id) : null;
    return versions.map((v, idx) => ({
      id: String(v.id),
      chapter_id: String(v.file_id ?? fileId ?? ''),
      version_label: v.version_label || ('v' + (idx + 1)),
      content: v.content,
      created_at: v.created_at || DEFAULT_VERSION_CREATED_AT,
      provider: v.provider || 'local',
    }));
  }, [currentFile, versions]);

  const isCurrentFileDirty = useMemo(() => {
    if (!currentFile) return false;
    return content !== currentFileBaseContent;
  }, [content, currentFile, currentFileBaseContent]);

  const allSourceFiles = useMemo(() => {
    const out: any[] = [];
    const walk = (nodes: any[]) => {
      if (!Array.isArray(nodes)) return;
      for (const node of nodes) {
        if (!node || typeof node !== 'object') continue;
        const files = Array.isArray((node as any).files) ? (node as any).files : [];
        for (const f of files) out.push(f);
        const children = Array.isArray((node as any).children) ? (node as any).children : [];
        if (children.length > 0) walk(children);
      }
    };
    walk(Array.isArray(treeData?.root_nodes) ? treeData.root_nodes : []);
    return out;
  }, [treeData]);

  const generatedSourceFiles = useMemo(() => {
    return allSourceFiles
      .filter((f) => Boolean(f?.has_content))
      .sort((a, b) => String(a?.file_path || a?.filename || '').localeCompare(String(b?.file_path || b?.filename || '')));
  }, [allSourceFiles]);

  const generatedTotalVersions = useMemo(() => {
    return generatedSourceFiles.reduce((acc, f) => acc + Number(f?.version_count || 0), 0);
  }, [generatedSourceFiles]);

  const openEditSystem = (sys: CodingSystem) => {
    setEditingSystem(sys);
    setSystemForm({
      name: sys.name || '',
      description: sys.description || '',
      responsibilitiesText: Array.isArray(sys.responsibilities) ? sys.responsibilities.join('\n') : '',
      techRequirements: sys.tech_requirements || '',
    });
    setIsSystemModalOpen(true);
  };

  const saveSystem = async () => {
    if (!id) return;
    const name = systemForm.name.trim();
    if (!name) {
      addToast('请输入系统名称', 'error');
      return;
    }
    const responsibilities = (systemForm.responsibilitiesText || '')
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);

    setSystemSaving(true);
    try {
      if (editingSystem) {
        await codingApi.updateSystem(id, editingSystem.system_number, {
          name,
          description: systemForm.description || '',
          responsibilities,
          tech_requirements: systemForm.techRequirements || '',
        });
        addToast('系统已更新', 'success');
      } else {
        await codingApi.createSystem(id, {
          name,
          description: systemForm.description || '',
          responsibilities,
          tech_requirements: systemForm.techRequirements || '',
        });
        addToast('系统已创建', 'success');
      }
      setIsSystemModalOpen(false);
      await refreshSystems();
    } catch (e) {
      console.error(e);
      addToast('保存失败', 'error');
    } finally {
      setSystemSaving(false);
    }
  };

	  const deleteSystem = async (sys: CodingSystem) => {
	    if (!id) return;
	    const ok = await confirmDialog({
	      title: '删除系统',
	      message: `确定要删除系统「${sys.name}」吗？\n（会同时删除关联模块）`,
	      confirmText: '删除',
	      dialogType: 'danger',
	    });
	    if (!ok) return;
	    try {
	      await codingApi.deleteSystem(id, sys.system_number);
	      addToast('系统已删除', 'success');
	      invalidateResources(['systems', 'modules', 'dependencies']);
	      await ensureResources(['systems', 'modules', 'dependencies'], { force: true });
    } catch (e) {
      console.error(e);
      addToast('删除失败', 'error');
    }
  };

		  const generateSystems = async () => {
		    if (!id) return;
		    const ok = await confirmDialog({
		      title: '自动生成系统',
		      message: '自动生成系统将删除当前所有系统/模块数据并重建。\n是否继续？',
		      confirmText: '继续',
		      dialogType: 'danger',
		    });
	    if (!ok) return;
      openPreferenceModal({
	        title: '输入偏好指导（可选）',
	        hint: '留空则按默认策略生成；填写可指定技术栈/分层/命名习惯等偏好。',
	        onConfirm: async (preference?: string) => {
          try {
	            setTabActionLoading(true);
	            const list = await codingApi.generateSystems(id, { preference: preference || undefined });
	            setSystems(list);
	            setModules([]);
	            setDependencies([]);
	            patchResourceState('systems', {
	              loaded: true,
	              loading: false,
	              error: null,
	              lastLoadedAt: Date.now(),
	            });
	            invalidateResources(['modules', 'dependencies']);
	            addToast('系统划分已生成', 'success');
          } catch (e) {
            console.error(e);
            addToast('生成失败', 'error');
          } finally {
	            setTabActionLoading(false);
          }
        },
      });
	  };

  const openEditModule = (m: CodingModule) => {
    setEditingModule(m);
    setModuleForm({
      systemNumber: Number(m.system_number || 0) || '',
      name: m.name || '',
      type: m.type || 'service',
      description: m.description || '',
      iface: m.interface || '',
      dependenciesText: Array.isArray(m.dependencies) ? m.dependencies.join('\n') : '',
    });
    setIsModuleModalOpen(true);
  };

  const saveModule = async () => {
    if (!id) return;
    const name = moduleForm.name.trim();
    if (!name) {
      addToast('请输入模块名称', 'error');
      return;
    }
    const deps = (moduleForm.dependenciesText || '')
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);

    setModuleSaving(true);
    try {
      if (editingModule) {
        await codingApi.updateModule(id, editingModule.module_number, {
          name,
          type: moduleForm.type,
          description: moduleForm.description || '',
          interface: moduleForm.iface || '',
          dependencies: deps,
        });
        addToast('模块已更新', 'success');
      } else {
        const sysNo = Number(moduleForm.systemNumber || 0);
        if (!sysNo) {
          addToast('请选择所属系统', 'error');
          return;
        }
        await codingApi.createModule(id, {
          system_number: sysNo,
          name,
          type: moduleForm.type,
          description: moduleForm.description || '',
          interface: moduleForm.iface || '',
          dependencies: deps,
        });
        addToast('模块已创建', 'success');
      }
      setIsModuleModalOpen(false);
      invalidateResources(['modules', 'systems', 'dependencies']);
      await ensureResources(['modules', 'systems', 'dependencies'], { force: true });
    } catch (e) {
      console.error(e);
      addToast('保存失败', 'error');
    } finally {
      setModuleSaving(false);
    }
  };

	  const deleteModule = async (m: CodingModule) => {
	    if (!id) return;
	    const ok = await confirmDialog({
	      title: '删除模块',
	      message: `确定要删除模块「${m.name}」吗？`,
	      confirmText: '删除',
	      dialogType: 'danger',
	    });
	    if (!ok) return;
	    try {
	      await codingApi.deleteModule(id, m.module_number);
	      addToast('模块已删除', 'success');
	      invalidateResources(['modules', 'systems', 'dependencies']);
	      await ensureResources(['modules', 'systems', 'dependencies'], { force: true });
    } catch (e) {
      console.error(e);
      addToast('删除失败', 'error');
    }
  };

  const generateModulesForSystem = async (systemNumber: number) => {
    if (!id) return;
    const sysNo = Number(systemNumber || 0);
    if (!sysNo) {
      addToast('系统编号无效', 'error');
      return;
    }
    const ok = await confirmDialog({
      title: '生成模块',
      message: `为系统 #${sysNo} 生成模块？\n（会覆盖该系统下旧模块）`,
      confirmText: '覆盖生成',
      dialogType: 'warning',
    });
    if (!ok) return;
    openPreferenceModal({
      title: '输入偏好指导（可选）',
      hint: '留空则按默认策略生成；填写可指定模块边界/命名/依赖倾向等。',
      onConfirm: async (preference?: string) => {
        try {
          setTabActionLoading(true);
          await codingApi.generateModules(id, { systemNumber: sysNo, preference: preference || undefined });
          addToast('模块已生成', 'success');
          invalidateResources(['modules', 'systems', 'dependencies']);
          await ensureResources(['modules', 'systems', 'dependencies'], { force: true });
        } catch (e) {
          console.error(e);
          addToast('生成失败', 'error');
        } finally {
          setTabActionLoading(false);
        }
      },
    });
  };

  const handleModulesSseEvent = useCallback((event: string, data: any) => {
    if (event === 'start') {
      setGenAllRunning(true);
      setGenAllLogs([`开始批量生成模块：共 ${data?.total_systems || 0} 个系统`]);
      return;
    }
    if (event === 'system_start') {
      setGenAllLogs((prev) => [
        ...prev,
        `系统 #${data?.system_number}: ${data?.system_name || ''}（开始）`,
      ]);
      return;
    }
    if (event === 'system_complete') {
      setGenAllLogs((prev) => [
        ...prev,
        `系统 #${data?.system_number} 完成：新增 ${data?.modules_created || 0} 个模块`,
      ]);
      return;
    }
    if (event === 'system_error') {
      setGenAllLogs((prev) => [
        ...prev,
        `系统 #${data?.system_number} 失败：${data?.error || 'unknown'}`,
      ]);
      return;
    }
    if (event === 'complete') {
      setGenAllRunning(false);
      setGenAllLogs((prev) => [
        ...prev,
        `全部完成：系统 ${data?.systems_processed || 0}，模块 ${data?.total_modules || 0}`,
      ]);
      invalidateResources(['modules', 'systems', 'dependencies']);
      void ensureResources(['modules', 'systems', 'dependencies'], { force: true });
      return;
    }
    if (event === 'error') {
      setGenAllRunning(false);
      setGenAllLogs((prev) => [...prev, `错误：${data?.message || 'unknown'}`]);
      return;
    }
  }, [ensureResources, invalidateResources]);

  const { connect: connectModulesStream, disconnect: disconnectModulesStream } = useSSE(handleModulesSseEvent);

  useEffect(() => {
    return () => disconnectModulesStream();
  }, [disconnectModulesStream]);

		  const startGenerateAllModules = async () => {
		    if (!id) return;
		    const ok = await confirmDialog({
		      title: '批量生成模块',
		      message: '为所有系统批量生成模块（SSE流式）？\n这会逐个系统覆盖其旧模块。',
		      confirmText: '继续',
		      dialogType: 'warning',
		    });
		    if (!ok) return;
	      openPreferenceModal({
	        title: '输入偏好指导（可选）',
	        hint: '留空则按默认策略生成；填写可指定模块风格/依赖策略等偏好。',
	        onConfirm: async (preference?: string) => {
          const { endpoint, body } = codingApi.generateAllModulesStream(id, { preference: preference || undefined });
          setGenAllRunning(true);
          setGenAllLogs(['初始化…']);
          await connectModulesStream(endpoint, body);
        },
      });
	  };

  const deleteDependency = async (d: CodingDependency) => {
    if (!id) return;
    try {
      await codingApi.deleteDependency(id, { id: d.id, from: d.from_module, to: d.to_module });
      addToast('依赖已删除', 'success');
      invalidateResources(['dependencies', 'modules']);
      await ensureResources(['dependencies', 'modules'], { force: true });
    } catch (e) {
      console.error(e);
      addToast('删除失败', 'error');
    }
  };

  const handleSelectFile = useCallback(async (fileId: number) => {
    if (!id) return;
    setSelectedDirectory(null);
    try {
      const file = await codingApi.getFile(id, fileId);
      setCurrentFile(file);
      setContent(file.content || file.description || '// 暂无内容');

      const versionList = await codingApi.getFileVersions(id, fileId);
      setVersions(versionList.versions || []);
    } catch (e) {
      console.error(e);
    }
  }, [id]);

  const openFileInfoModal = useCallback(() => {
    if (!currentFile) return;
    const raw = String((currentFile as any).priority || '').toLowerCase();
    const priority: CodingFilePriority = raw === 'high' || raw === 'low' || raw === 'medium' ? raw : 'medium';
    setFileInfoForm({
      description: String((currentFile as any).description || ''),
      purpose: String((currentFile as any).purpose || ''),
      priority,
    });
    setIsFileInfoModalOpen(true);
  }, [currentFile]);

  const saveFileInfo = useCallback(async () => {
    if (!id || !currentFile) return;
    setFileInfoSaving(true);
    try {
      await codingApi.updateFileInfo(id, currentFile.id, {
        description: (fileInfoForm.description || '').trim() || undefined,
        purpose: (fileInfoForm.purpose || '').trim() || undefined,
        priority: fileInfoForm.priority,
      });
      addToast('文件信息已保存', 'success');
      setIsFileInfoModalOpen(false);

      // 刷新当前文件与目录树展示
      const file = await codingApi.getFile(id, currentFile.id);
      setCurrentFile(file);
      await refreshTreeData();
    } catch (e) {
      console.error(e);
      addToast('保存失败', 'error');
    } finally {
      setFileInfoSaving(false);
    }
  }, [addToast, currentFile, fileInfoForm.description, fileInfoForm.priority, fileInfoForm.purpose, id, refreshTreeData]);

  const openDirectoryInfoModal = useCallback(() => {
    if (!selectedDirectory) return;
    setDirectoryInfoForm({ description: String((selectedDirectory as any).description || '') });
    setIsDirectoryInfoModalOpen(true);
  }, [selectedDirectory]);

  const saveDirectoryInfo = useCallback(async () => {
    if (!id || !selectedDirectory) return;
    const nodeId = Number((selectedDirectory as any).id || 0);
    if (!nodeId) return;
    setDirectoryInfoSaving(true);
    try {
      const desc = (directoryInfoForm.description || '').trim();
      await codingApi.updateDirectoryInfo(id, nodeId, { description: desc || undefined });
      addToast('目录信息已保存', 'success');
      setIsDirectoryInfoModalOpen(false);
      setSelectedDirectory({ ...(selectedDirectory as any), description: desc });
      await refreshTreeData();
    } catch (e) {
      console.error(e);
      addToast('保存失败', 'error');
    } finally {
      setDirectoryInfoSaving(false);
    }
  }, [addToast, directoryInfoForm.description, id, refreshTreeData, selectedDirectory]);

  const handleGenerate = async () => {
    if (!id || !currentFile) return;
    resetFileTokenBuffer();
    setIsGenerating(true);
    setContent('');
    await connectFileStream(codingApi.generateFilePromptStream(id, currentFile.id), {});
  };

  const handleSave = async () => {
    if (!id || !currentFile) return;
    setIsSaving(true);
    try {
      await codingApi.saveFileContent(id, currentFile.id, content);
      addToast('已保存为新版本', 'success');

      const file = await codingApi.getFile(id, currentFile.id);
      setCurrentFile(file);
      setContent(file.content || content);

      const versionList = await codingApi.getFileVersions(id, currentFile.id);
      setVersions(versionList.versions || []);

      // 刷新目录树统计与“已生成内容”列表
      await refreshTreeData();
    } catch (e) {
      console.error(e);
      addToast('保存失败', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleHeaderSave = async () => {
    if (isSaving) return;
    if (!currentFile) {
      addToast('请先在“目录结构”里选择一个文件', 'info');
      return;
    }
    if (!isCurrentFileDirty) {
      addToast('没有需要保存的修改', 'info');
      return;
    }
    await handleSave();
  };

  const handleSelectVersion = async (index: number) => {
    if (!id || !currentFile) return;
    const target = versions[index];
    if (!target) return;
    try {
      await codingApi.selectFileVersion(id, currentFile.id, target.id);
      addToast('已切换版本', 'success');
      const file = await codingApi.getFile(id, currentFile.id);
      setCurrentFile(file);
      setContent(file.content || file.description || target.content);
      const versionList = await codingApi.getFileVersions(id, currentFile.id);
      setVersions(versionList.versions || []);
    } catch (e) {
      console.error(e);
      addToast('切换失败', 'error');
    }
  };

  const { connect: connectFileStream, disconnect: disconnectFileStream } = useSSE((event, data) => {
    if (event === 'token' && data?.token) {
      pushFileToken(String(data.token));
      return;
    }
    if (event === 'complete') {
      flushFileTokens();
      resetFileTokenBuffer();
      setIsGenerating(false);
      addToast('生成完成', 'success');
      if (id && currentFile?.id) {
        Promise.allSettled([handleSelectFile(currentFile.id), loadData()]);
      }
      return;
    }
    if (event === 'error') {
      flushFileTokens();
      resetFileTokenBuffer();
      setIsGenerating(false);
      addToast(data?.message || '生成失败', 'error');
    }
  });

  useEffect(() => {
    return () => {
      disconnectFileStream();
      resetFileTokenBuffer();
    };
  }, [disconnectFileStream, resetFileTokenBuffer]);

  const handleSyncDependencies = useCallback(async () => {
    if (!id) return;
    try {
      const res = await codingApi.syncDependencies(id);
      addToast(res?.message || '已同步', 'success');
      await refreshDependencies();
    } catch (e) {
      console.error(e);
      addToast('同步失败', 'error');
    }
  }, [addToast, id, refreshDependencies]);

  const handleOpenGeneratedFile = useCallback((fileId: number) => {
    if (typeof fileId !== 'number') return;
    setActiveTab('directory');
    void handleSelectFile(fileId);
  }, [handleSelectFile, setActiveTab]);

  if (loading) return <div className="flex h-full min-h-0 items-center justify-center">加载中...</div>;

  // 照抄桌面端 coding_detail/mixins/tab_manager.py 的Tab配置
  const tabs = [
    { id: 'overview', label: '概览', icon: FileCode },
    { id: 'architecture', label: '架构设计', icon: Layout },
    { id: 'directory', label: '目录结构', icon: GitBranch },
    { id: 'generation', label: '生成管理', icon: Database },
  ] as const;

  return (
    <div className="flex h-full min-h-0 flex-col bg-book-bg overflow-hidden">
      {/* Header - 完全照抄桌面端 coding_detail/mixins/header_manager.py */}
      <div className="h-[110px] border-b border-book-border bg-book-bg-paper flex items-center px-6 gap-4 shrink-0 z-30">
        {/* 左侧：项目图标 64x64 */}
        <div className="w-16 h-16 rounded-lg bg-book-primary flex items-center justify-center shrink-0">
          <span className="text-white text-3xl font-bold">C</span>
        </div>

        {/* 中间：项目信息区域 */}
        <div className="flex-1 min-w-0 flex flex-col gap-1">
          {/* 标题行 */}
          <div className="text-lg font-bold text-book-text-main truncate">
            {project?.title || '加载中...'}
          </div>
          {/* 元信息行：类型 | 状态 */}
          <div className="flex items-center gap-2 text-xs">
            <span className="px-2 py-0.5 bg-book-bg rounded text-book-text-sub">
              {project?.blueprint?.project_type_desc || '项目类型'}
            </span>
            <span className="text-book-text-muted">|</span>
            <span className="px-2 py-0.5 bg-book-bg rounded text-book-text-sub">
              {project?.status || '状态'}
            </span>
          </div>
          {/* 统计信息行 */}
          <div className="flex items-center gap-4 text-xs text-book-text-muted mt-1">
            <span>{systems.length} 系统</span>
            <span>{modules.length} 模块</span>
            <span>0 功能</span>
            <span>{Number(treeData?.total_files || 0)} 文件</span>
          </div>
        </div>

        {/* 右侧：操作按钮 - 照抄桌面端：保存、进入写作台、返回 */}
        <div className="flex items-center gap-2 shrink-0">
          <BookButton
            size="sm"
            variant={isCurrentFileDirty ? 'primary' : 'secondary'}
            onClick={handleHeaderSave}
            disabled={isSaving}
            title={
              !currentFile
                ? '请先在“目录结构”里选择一个文件'
                : (isCurrentFileDirty ? '有未保存的修改' : '没有需要保存的修改')
            }
          >
            {isSaving ? '保存中…' : (isCurrentFileDirty ? '保存*' : '保存')}
          </BookButton>
          <BookButton
            size="sm"
            variant="primary"
            onClick={() => openCodingDesk(typeof currentFile?.id === 'number' ? currentFile.id : undefined)}
          >
            进入写作台
          </BookButton>
          <BookButton size="sm" variant="secondary" onClick={() => navigate('/')}>
            返回
          </BookButton>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-book-border/40 bg-book-bg-paper px-4">
        <div className="flex gap-6">
          {tabs.map((t) => {
            const Icon = t.icon;
            const isActive = activeTab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`
                  flex items-center gap-2 py-3 text-sm font-bold transition-all relative
                  ${isActive ? 'text-book-primary' : 'text-book-text-sub hover:text-book-text-main'}
                `}
              >
                <Icon size={16} />
                {t.label}
                {isActive && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-book-primary rounded-t-full" />}
              </button>
            );
          })}
        </div>
      </div>

      <div className="perf-scroll-region flex-1 overflow-y-auto p-6 custom-scrollbar">
        {activeTab === 'overview' && (
          <CodingDetailOverviewTab
            project={project}
            systems={systems}
            modules={modules}
            treeData={treeData}
          />
        )}

        {activeTab === 'architecture' && (
          <CodingDetailArchitectureTab
            project={project}
            systems={systems}
            modules={modules}
            genAllLogs={genAllLogs}
            genAllRunning={genAllRunning}
            tabLoading={tabLoading}
            onGenerateBlueprint={handleGenerateBlueprint}
            onGenerateAllModules={startGenerateAllModules}
            onGenerateSystems={generateSystems}
            onGenerateModulesForSystem={generateModulesForSystem}
            onEditSystem={openEditSystem}
            onDeleteSystem={deleteSystem}
            onEditModule={openEditModule}
            onDeleteModule={deleteModule}
          />
        )}

        {activeTab === 'directory' && (
          <CodingDetailDirectoryTab
            treeData={treeData}
            loading={loading}
            treeExpandAllToken={treeExpandAllToken}
            treeCollapseAllToken={treeCollapseAllToken}
            selectedDirectory={selectedDirectory}
            currentFile={currentFile}
            content={content}
            editorVersions={editorVersions}
            isCurrentFileDirty={isCurrentFileDirty}
            isSaving={isSaving}
            isGenerating={isGenerating}
            onExpandAll={() => setTreeExpandAllToken((value) => value + 1)}
            onCollapseAll={() => setTreeCollapseAllToken((value) => value + 1)}
            onRefreshTreeData={refreshTreeData}
            onSelectFile={handleSelectFile}
            onSelectDirectory={setSelectedDirectory}
            onEditDirectoryInfo={openDirectoryInfoModal}
            onEditFileInfo={openFileInfoModal}
            onOpenCodingDesk={openCodingDesk}
            onGenerate={handleGenerate}
            onSave={handleSave}
            onChangeContent={setContent}
            onSelectVersion={handleSelectVersion}
          />
        )}

        {activeTab === 'generation' && (
          <CodingDetailGenerationTab
            dependencies={dependencies}
            tabLoading={tabLoading}
            onSyncDependencies={handleSyncDependencies}
            onDeleteDependency={deleteDependency}
            ragCompleteness={ragCompleteness}
            ragLoading={ragLoading}
            ragIngesting={ragIngesting}
            onIngestRag={ingestRag}
            generatedSourceFiles={generatedSourceFiles}
            generatedTotalVersions={generatedTotalVersions}
            loading={loading}
            onRefreshGeneratedContent={loadData}
            onOpenGeneratedFile={handleOpenGeneratedFile}
            onOpenCodingDesk={openCodingDesk}
            ragQuery={ragQuery}
            onRagQueryChange={setRagQuery}
            onRunRagQuery={runRagQuery}
            ragQueryLoading={ragQueryLoading}
            ragResult={ragResult}
          />
        )}
      </div>

      <CodingDetailModals
        preferenceModal={{
          isOpen: isPreferenceModalOpen,
          title: preferenceModalTitle,
          hint: preferenceModalHint,
          value: preferenceModalValue,
          onChange: (value) => setPreferenceModalValue(value),
          onClose: () => {
            pendingPreferenceActionRef.current = null;
            setIsPreferenceModalOpen(false);
          },
          onConfirm: confirmPreferenceModal,
        }}
        directoryInfoModal={{
          isOpen: isDirectoryInfoModalOpen,
          saving: directoryInfoSaving,
          selectedDirectory,
          form: directoryInfoForm,
          onChange: (next) => setDirectoryInfoForm(next),
          onClose: () => setIsDirectoryInfoModalOpen(false),
          onSave: saveDirectoryInfo,
        }}
        fileInfoModal={{
          isOpen: isFileInfoModalOpen,
          saving: fileInfoSaving,
          currentFile,
          form: fileInfoForm,
          onChange: (next) => setFileInfoForm(next),
          onClose: () => setIsFileInfoModalOpen(false),
          onSave: saveFileInfo,
        }}
        systemModal={{
          isOpen: isSystemModalOpen,
          saving: systemSaving,
          editingSystem,
          form: systemForm,
          onChange: (next) => setSystemForm(next),
          onClose: () => setIsSystemModalOpen(false),
          onSave: saveSystem,
        }}
        moduleModal={{
          isOpen: isModuleModalOpen,
          saving: moduleSaving,
          editingModule,
          sortedSystemNumbers,
          form: moduleForm,
          onChange: (next) => setModuleForm(next),
          onClose: () => setIsModuleModalOpen(false),
          onSave: saveModule,
        }}
      />
    </div>
  );
};
