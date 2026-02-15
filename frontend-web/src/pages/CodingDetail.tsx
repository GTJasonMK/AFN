import React, { lazy, Suspense, useEffect, useMemo, useCallback, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { codingApi, CodingDependency, CodingFilePriority, CodingModule, CodingSystem } from '../api/coding';
import { FileCode, GitBranch, RefreshCw, Wand2, Sparkles, Database, Search, Layout } from 'lucide-react';
import { BookButton } from '../components/ui/BookButton';
import { useSSE } from '../hooks/useSSE';
import { useToast } from '../components/feedback/Toast';
import { confirmDialog } from '../components/feedback/ConfirmDialog';
import { Modal } from '../components/ui/Modal';
import { BookCard } from '../components/ui/BookCard';
import { BookInput, BookTextarea } from '../components/ui/BookInput';
import { readBootstrapCache, writeBootstrapCache } from '../utils/bootstrapCache';

const DirectoryTreeLazy = lazy(() =>
  import('../components/coding/DirectoryTree').then((m) => ({ default: m.DirectoryTree }))
);
const EditorLazy = lazy(() =>
  import('../components/business/Editor').then((m) => ({ default: m.Editor }))
);

// 照抄桌面端 coding_detail/mixins/tab_manager.py 的Tab配置
type CodingTab = 'overview' | 'architecture' | 'directory' | 'generation';

const DEFAULT_VERSION_CREATED_AT = '1970-01-01T00:00:00.000Z';
const CODING_DETAIL_BOOTSTRAP_TTL_MS = 4 * 60 * 1000;
const getCodingDetailBootstrapKey = (projectId: string) => `afn:web:coding-detail:${projectId}:bootstrap:v1`;

type CodingDetailBootstrapSnapshot = {
  project: any | null;
  treeData: any | null;
  systems: CodingSystem[];
  modules: CodingModule[];
  dependencies: CodingDependency[];
  ragCompleteness: any | null;
};

export const CodingDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const hasBootstrapRef = useRef(false);

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

  const [activeTab, setActiveTab] = useState<CodingTab>('overview');
  const activeTabStorageKey = useMemo(() => (id ? `afn:coding_detail:active_tab:${id}` : ''), [id]);

  // 对齐桌面端“页缓存”体验：Web 侧记忆上次停留的 Tab（避免路由重建后总回到 overview）
  useEffect(() => {
    if (!activeTabStorageKey) return;
    try {
      const saved = localStorage.getItem(activeTabStorageKey) || '';
      if (saved === 'overview' || saved === 'architecture' || saved === 'directory' || saved === 'generation') {
        setActiveTab(saved);
      }
    } catch {
      // ignore
    }
  }, [activeTabStorageKey]);

  useEffect(() => {
    if (!activeTabStorageKey) return;
    try {
      localStorage.setItem(activeTabStorageKey, activeTab);
    } catch {
      // ignore
    }
  }, [activeTab, activeTabStorageKey]);

  const [project, setProject] = useState<any>(null);
  const [treeData, setTreeData] = useState<any>(null);
  const [treeExpandAllToken, setTreeExpandAllToken] = useState(0);
  const [treeCollapseAllToken, setTreeCollapseAllToken] = useState(0);
  const [selectedDirectory, setSelectedDirectory] = useState<any>(null);
  const [currentFile, setCurrentFile] = useState<any>(null);
  const [content, setContent] = useState('');
  const fileTokensRef = useRef<string[]>([]);
  const fileTokenFlushTimerRef = useRef<number | null>(null);
  const resetFileTokenBuffer = useCallback(() => {
    fileTokensRef.current = [];
    if (fileTokenFlushTimerRef.current !== null) {
      window.clearTimeout(fileTokenFlushTimerRef.current);
      fileTokenFlushTimerRef.current = null;
    }
  }, []);

  const flushFileTokens = useCallback(() => {
    if (fileTokensRef.current.length === 0) return;
    const text = fileTokensRef.current.join('');
    fileTokensRef.current = [];
    setContent((prev) => prev + text);
  }, []);

  const scheduleFileTokenFlush = useCallback(() => {
    if (fileTokenFlushTimerRef.current !== null) return;
    fileTokenFlushTimerRef.current = window.setTimeout(() => {
      fileTokenFlushTimerRef.current = null;
      flushFileTokens();
    }, 48);
  }, [flushFileTokens]);
  const [versions, setVersions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // File info modal（对齐桌面端 DirectorySection 的“编辑文件信息”能力）
  const [isFileInfoModalOpen, setIsFileInfoModalOpen] = useState(false);
  const [fileInfoForm, setFileInfoForm] = useState<{
    description: string;
    purpose: string;
    priority: CodingFilePriority;
  }>({
    description: '',
    purpose: '',
    priority: 'medium',
  });
  const [fileInfoSaving, setFileInfoSaving] = useState(false);

  // Directory info modal（对齐桌面端 DirectorySection 的“编辑目录信息”能力）
  const [isDirectoryInfoModalOpen, setIsDirectoryInfoModalOpen] = useState(false);
  const [directoryInfoForm, setDirectoryInfoForm] = useState<{ description: string }>({ description: '' });
  const [directoryInfoSaving, setDirectoryInfoSaving] = useState(false);

  const [systems, setSystems] = useState<CodingSystem[]>([]);
  const [modules, setModules] = useState<CodingModule[]>([]);
  const [dependencies, setDependencies] = useState<CodingDependency[]>([]);
  const [tabLoading, setTabLoading] = useState(false);

  // System modal
  const [isSystemModalOpen, setIsSystemModalOpen] = useState(false);
  const [editingSystem, setEditingSystem] = useState<CodingSystem | null>(null);
  const [systemForm, setSystemForm] = useState({
    name: '',
    description: '',
    responsibilitiesText: '',
    techRequirements: '',
  });
  const [systemSaving, setSystemSaving] = useState(false);

  // Module modal
  const [isModuleModalOpen, setIsModuleModalOpen] = useState(false);
  const [editingModule, setEditingModule] = useState<CodingModule | null>(null);
  const [moduleForm, setModuleForm] = useState({
    systemNumber: '' as number | '',
    name: '',
    type: 'service',
    description: '',
    iface: '',
    dependenciesText: '',
  });
  const [moduleSaving, setModuleSaving] = useState(false);

  // Generate modules
  const [targetSystemNumber, setTargetSystemNumber] = useState<number | ''>('');
  const [genAllRunning, setGenAllRunning] = useState(false);
  const [genAllLogs, setGenAllLogs] = useState<string[]>([]);

  // RAG
  const [ragCompleteness, setRagCompleteness] = useState<any | null>(null);
  const [ragLoading, setRagLoading] = useState(false);
  const [ragIngesting, setRagIngesting] = useState(false);
  const [ragQuery, setRagQuery] = useState('');
  const [ragQueryLoading, setRagQueryLoading] = useState(false);
  const [ragResult, setRagResult] = useState<any | null>(null);

  useEffect(() => {
    if (!id) return;

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
      setLoading(true);
      return;
    }

    setProject(cached.project ?? null);
    setTreeData(cached.treeData ?? null);
    setSystems(Array.isArray(cached.systems) ? cached.systems : []);
    setModules(Array.isArray(cached.modules) ? cached.modules : []);
    setDependencies(Array.isArray(cached.dependencies) ? cached.dependencies : []);
    setRagCompleteness(cached.ragCompleteness ?? null);

    hasBootstrapRef.current = Boolean(cached.project);
    setLoading(!cached.project);
  }, [id]);

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

  const refreshTreeData = useCallback(async () => {
    if (!id) return;
    try {
      const tree = await codingApi.getDirectoryTree(id);
      setTreeData(tree);
    } catch (e) {
      console.error(e);
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
    });
  }, [dependencies, id, modules, project, ragCompleteness, systems, treeData]);

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

  const refreshSystems = useCallback(async () => {
    if (!id) return;
    setTabLoading(true);
    try {
      const list = await codingApi.listSystems(id);
      setSystems(list);
    } catch (e) {
      console.error(e);
      addToast('加载系统列表失败', 'error');
      setSystems([]);
    } finally {
      setTabLoading(false);
    }
  }, [addToast, id]);

  const refreshModules = useCallback(async () => {
    if (!id) return;
    setTabLoading(true);
    try {
      const list = await codingApi.listModules(id);
      setModules(list);
    } catch (e) {
      console.error(e);
      addToast('加载模块列表失败', 'error');
      setModules([]);
    } finally {
      setTabLoading(false);
    }
  }, [addToast, id]);

  const refreshDependencies = useCallback(async () => {
    if (!id) return;
    setTabLoading(true);
    try {
      const list = await codingApi.listDependencies(id);
      setDependencies(list);
    } catch (e) {
      console.error(e);
      addToast('加载依赖列表失败', 'error');
      setDependencies([]);
    } finally {
      setTabLoading(false);
    }
  }, [addToast, id]);

  const refreshRagCompleteness = useCallback(async () => {
    if (!id) return;
    setRagLoading(true);
    try {
      const data = await codingApi.getRagCompleteness(id);
      setRagCompleteness(data);
    } catch (e) {
      console.error(e);
      addToast('RAG 完整性检查失败', 'error');
      setRagCompleteness(null);
    } finally {
      setRagLoading(false);
    }
  }, [addToast, id]);

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
    // 概览Tab需要加载系统和模块数据
    if (activeTab === 'overview') {
      Promise.allSettled([refreshSystems(), refreshModules()]);
    }
    // 架构设计Tab需要加载系统和模块数据
    if (activeTab === 'architecture') {
      Promise.allSettled([refreshSystems(), refreshModules()]);
    }
    // 目录结构Tab只在进入时加载目录树（减少详情页首屏阻塞）
    if (activeTab === 'directory' && treeData === null) {
      refreshTreeData();
    }
    // 生成管理Tab需要RAG和依赖数据
    if (activeTab === 'generation') {
      Promise.allSettled([refreshModules(), refreshDependencies(), refreshRagCompleteness()]);
    }
  }, [activeTab, id, refreshDependencies, refreshModules, refreshRagCompleteness, refreshSystems, refreshTreeData, treeData]);

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

  useEffect(() => {
    if (targetSystemNumber !== '' || sortedSystemNumbers.length === 0) return;
    setTargetSystemNumber(sortedSystemNumbers[0]);
  }, [sortedSystemNumbers, targetSystemNumber]);

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
	      await Promise.allSettled([refreshSystems(), refreshModules()]);
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
            setTabLoading(true);
            const list = await codingApi.generateSystems(id, { preference: preference || undefined });
            setSystems(list);
            setModules([]);
            addToast('系统划分已生成', 'success');
          } catch (e) {
            console.error(e);
            addToast('生成失败', 'error');
          } finally {
            setTabLoading(false);
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
      await Promise.allSettled([refreshModules(), refreshSystems()]);
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
	      await Promise.allSettled([refreshModules(), refreshSystems(), refreshDependencies()]);
    } catch (e) {
      console.error(e);
      addToast('删除失败', 'error');
    }
  };

		  const generateModulesForSystem = async () => {
		    if (!id) return;
		    const sysNo = Number(targetSystemNumber || 0);
		    if (!sysNo) {
		      addToast('请选择系统', 'error');
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
            setTabLoading(true);
            await codingApi.generateModules(id, { systemNumber: sysNo, preference: preference || undefined });
            addToast('模块已生成', 'success');
            await Promise.allSettled([refreshModules(), refreshSystems(), refreshDependencies()]);
          } catch (e) {
            console.error(e);
            addToast('生成失败', 'error');
          } finally {
            setTabLoading(false);
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
      Promise.allSettled([refreshModules(), refreshSystems(), refreshDependencies()]);
      return;
    }
    if (event === 'error') {
      setGenAllRunning(false);
      setGenAllLogs((prev) => [...prev, `错误：${data?.message || 'unknown'}`]);
      return;
    }
  }, [refreshDependencies, refreshModules, refreshSystems]);

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
      await Promise.allSettled([refreshDependencies(), refreshModules()]);
    } catch (e) {
      console.error(e);
      addToast('删除失败', 'error');
    }
  };

  const handleSelectFile = async (fileId: number) => {
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
  };

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
      fileTokensRef.current.push(String(data.token));
      scheduleFileTokenFlush();
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

  if (loading) return <div className="flex h-screen items-center justify-center">加载中...</div>;

  // 照抄桌面端 coding_detail/mixins/tab_manager.py 的Tab配置
  const tabs = [
    { id: 'overview', label: '概览', icon: FileCode },
    { id: 'architecture', label: '架构设计', icon: Layout },
    { id: 'directory', label: '目录结构', icon: GitBranch },
    { id: 'generation', label: '生成管理', icon: Database },
  ] as const;

  return (
    <div className="flex flex-col h-screen bg-book-bg">
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

      {/* 照抄桌面端 coding_detail 的4个Tab内容区域 */}
      <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
        {/* Tab 1: 概览 - 照抄 overview.py */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* 项目进度Section */}
            <BookCard className="p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="text-sm font-bold text-book-text-main">项目进度</div>
                <div className="text-sm font-bold text-book-primary">
                  {(() => {
                    let completed = 0;
                    if (project?.blueprint?.one_sentence_summary || project?.blueprint?.architecture_synopsis) completed++;
                    if (systems.length > 0) completed++;
                    if (modules.length > 0) completed++;
                    if (treeData?.root_nodes?.length > 0) completed++;
                    return Math.round((completed / 4) * 100);
                  })()}%
                </div>
              </div>
              <div className="h-2 bg-book-border rounded-full mb-4">
                <div
                  className="h-full bg-book-primary rounded-full transition-all"
                  style={{
                    width: `${(() => {
                      let completed = 0;
                      if (project?.blueprint?.one_sentence_summary || project?.blueprint?.architecture_synopsis) completed++;
                      if (systems.length > 0) completed++;
                      if (modules.length > 0) completed++;
                      if (treeData?.root_nodes?.length > 0) completed++;
                      return Math.round((completed / 4) * 100);
                    })()}%`,
                  }}
                />
              </div>
              <div className="flex justify-between text-xs text-book-text-muted">
                <span className={project?.blueprint ? 'text-green-600' : ''}>1.蓝图</span>
                <span>--</span>
                <span className={systems.length > 0 ? 'text-green-600' : ''}>2.系统</span>
                <span>--</span>
                <span className={modules.length > 0 ? 'text-green-600' : ''}>3.模块</span>
                <span>--</span>
                <span className={treeData?.root_nodes?.length > 0 ? 'text-green-600' : ''}>4.目录</span>
              </div>
            </BookCard>

            {/* 项目摘要Section */}
            <BookCard className="p-5">
              <div className="text-sm font-bold text-book-text-main mb-3">项目摘要</div>
              <div className="text-sm text-book-text-main mb-4">
                {project?.blueprint?.one_sentence_summary || '暂无摘要，请先生成蓝图'}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-book-text-muted">项目类型</div>
                  <div className="text-sm text-book-text-sub">{project?.blueprint?.project_type_desc || '未定义'}</div>
                </div>
                <div>
                  <div className="text-xs text-book-text-muted">目标受众</div>
                  <div className="text-sm text-book-text-sub">{project?.blueprint?.target_audience || '未定义'}</div>
                </div>
                <div>
                  <div className="text-xs text-book-text-muted">技术风格</div>
                  <div className="text-sm text-book-text-sub">{project?.blueprint?.tech_style || '未定义'}</div>
                </div>
                <div>
                  <div className="text-xs text-book-text-muted">项目调性</div>
                  <div className="text-sm text-book-text-sub">{project?.blueprint?.project_tone || '未定义'}</div>
                </div>
              </div>
              {project?.blueprint?.architecture_synopsis && (
                <div className="mt-4">
                  <div className="text-xs text-book-text-muted mb-1">架构概述</div>
                  <div className="text-sm text-book-text-sub whitespace-pre-wrap">{project.blueprint.architecture_synopsis}</div>
                </div>
              )}
            </BookCard>

            {/* 技术栈Section */}
            <BookCard className="p-5">
              <div className="text-sm font-bold text-book-text-main mb-3">技术栈</div>
              {!project?.blueprint?.tech_stack ? (
                <div className="text-sm text-book-text-muted">暂无技术栈信息，请先生成蓝图</div>
              ) : (
                <>
                  {project.blueprint.tech_stack.core_constraints && (
                    <div className="text-sm text-book-text-sub mb-3">
                      核心约束: {project.blueprint.tech_stack.core_constraints}
                    </div>
                  )}
                  {Array.isArray(project.blueprint.tech_stack.components) && project.blueprint.tech_stack.components.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {project.blueprint.tech_stack.components.slice(0, 8).map((comp: any, idx: number) => {
                        const name = typeof comp === 'string' ? comp : comp?.name || '';
                        return (
                          <span key={idx} className="px-2 py-1 text-xs bg-book-primary/10 text-book-primary rounded border border-book-primary/30">
                            {name}
                          </span>
                        );
                      })}
                      {project.blueprint.tech_stack.components.length > 8 && (
                        <span className="text-xs text-book-text-muted">+{project.blueprint.tech_stack.components.length - 8}</span>
                      )}
                    </div>
                  )}
                </>
              )}
            </BookCard>
          </div>
        )}

        {/* Tab 2: 架构设计 - 照抄 architecture.py */}
        {activeTab === 'architecture' && (
          <div className="space-y-6">
            {/* 蓝图概要Section */}
            <BookCard className="p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="text-sm font-bold text-book-text-main">蓝图概要</div>
                <BookButton size="sm" variant="primary" onClick={handleGenerateBlueprint}>
                  <Wand2 size={16} className="mr-1" />
                  {project?.blueprint ? '重新生成' : '生成蓝图'}
                </BookButton>
              </div>
              {project?.blueprint?.tech_stack && (
                <div className="p-3 rounded bg-book-bg border border-book-border/40 mb-4">
                  <div className="text-xs font-bold text-book-text-main mb-2">技术栈</div>
                  <div className="flex flex-wrap gap-2">
                    {(project.blueprint.tech_stack.components || []).slice(0, 6).map((comp: any, idx: number) => (
                      <span key={idx} className="px-2 py-0.5 text-xs bg-book-primary/10 text-book-primary rounded">
                        {typeof comp === 'string' ? comp : comp?.name || ''}
                      </span>
                    ))}
                  </div>
                  {project.blueprint.tech_stack.core_constraints && (
                    <div className="text-xs text-book-text-sub mt-2">约束: {project.blueprint.tech_stack.core_constraints}</div>
                  )}
                </div>
              )}
              {Array.isArray(project?.blueprint?.core_requirements) && project.blueprint.core_requirements.length > 0 && (
                <div className="p-3 rounded bg-book-bg border border-book-border/40 mb-4">
                  <div className="text-xs font-bold text-book-text-main mb-2">核心需求 ({project.blueprint.core_requirements.length})</div>
                  {project.blueprint.core_requirements.slice(0, 3).map((r: any, idx: number) => (
                    <div key={idx} className="text-xs text-book-text-sub">- {(r.requirement || '').slice(0, 80)}{(r.requirement || '').length > 80 ? '...' : ''}</div>
                  ))}
                  {project.blueprint.core_requirements.length > 3 && (
                    <div className="text-xs text-book-text-muted italic">... 还有 {project.blueprint.core_requirements.length - 3} 项</div>
                  )}
                </div>
              )}
              {Array.isArray(project?.blueprint?.technical_challenges) && project.blueprint.technical_challenges.length > 0 && (
                <div className="p-3 rounded bg-book-bg border border-book-border/40">
                  <div className="text-xs font-bold text-book-text-main mb-2">技术挑战 ({project.blueprint.technical_challenges.length})</div>
                  {project.blueprint.technical_challenges.slice(0, 3).map((c: any, idx: number) => (
                    <div key={idx} className="text-xs text-book-text-sub">- {(c.challenge || '').slice(0, 80)}{(c.challenge || '').length > 80 ? '...' : ''}</div>
                  ))}
                  {project.blueprint.technical_challenges.length > 3 && (
                    <div className="text-xs text-book-text-muted italic">... 还有 {project.blueprint.technical_challenges.length - 3} 项</div>
                  )}
                </div>
              )}
            </BookCard>

            {/* 项目结构Section */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="text-base font-bold text-book-text-main">项目结构</div>
                  <span className="text-sm text-book-text-muted">{systems.length} 系统 / {modules.length} 模块</span>
                </div>
                <div className="flex items-center gap-2">
                  <BookButton size="sm" variant="ghost" onClick={startGenerateAllModules} disabled={genAllRunning || tabLoading}>
                    <Wand2 size={16} className="mr-1" />
                    一键生成所有模块
                  </BookButton>
                  <BookButton size="sm" variant="primary" onClick={generateSystems} disabled={tabLoading}>
                    <Wand2 size={16} className="mr-1" />
                    生成系统划分
                  </BookButton>
                </div>
              </div>

              {genAllLogs.length > 0 && (
                <BookCard className="p-4 mb-4">
                  <div className="text-xs text-book-text-muted mb-2">生成进度</div>
                  <div className="max-h-32 overflow-y-auto custom-scrollbar space-y-1 text-xs text-book-text-main font-mono">
                    {genAllLogs.map((line, idx) => (
                      <div key={idx}>{line}</div>
                    ))}
                  </div>
                </BookCard>
              )}

              {systems.length === 0 ? (
                <BookCard className="p-8 text-center">
                  <div className="text-sm text-book-text-muted">
                    暂无系统划分<br /><br />
                    点击「生成系统划分」按钮，AI将自动将项目划分为多个子系统
                  </div>
                </BookCard>
              ) : (
                <div className="space-y-4">
                  {systems.map((sys) => {
                    const sysModules = modules.filter((m) => m.system_number === sys.system_number);
                    return (
                      <BookCard key={sys.system_number} className="p-4">
                        <div className="flex items-start justify-between gap-3 mb-3">
                          <div>
                            <div className="font-bold text-book-text-main">#{sys.system_number} · {sys.name}</div>
                            <div className="text-xs text-book-text-muted mt-1">{sysModules.length} 模块 · {sys.generation_status}</div>
                          </div>
                          <div className="flex items-center gap-2">
                            <BookButton size="sm" variant="ghost" onClick={() => generateModulesForSystem()} disabled={tabLoading || genAllRunning}>
                              <Wand2 size={14} className="mr-1" />
                              生成模块
                            </BookButton>
                            <button className="text-xs text-book-primary font-bold hover:underline" onClick={() => openEditSystem(sys)}>编辑</button>
                            <button className="text-xs text-red-600 font-bold hover:underline" onClick={() => deleteSystem(sys)}>删除</button>
                          </div>
                        </div>
                        {sys.description && (
                          <div className="text-sm text-book-text-sub mb-3">{sys.description}</div>
                        )}
                        {Array.isArray(sys.responsibilities) && sys.responsibilities.length > 0 && (
                          <div className="flex flex-wrap gap-2 mb-3">
                            {sys.responsibilities.slice(0, 6).map((r, idx) => (
                              <span key={idx} className="text-[11px] px-2 py-0.5 rounded-full bg-book-bg border border-book-border/40 text-book-text-sub">{r}</span>
                            ))}
                          </div>
                        )}
                        {sysModules.length > 0 && (
                          <div className="border-t border-book-border/30 pt-3 space-y-2">
                            {sysModules.map((m) => (
                              <div key={m.module_number} className="flex items-center justify-between p-2 rounded bg-book-bg/50">
                                <div>
                                  <span className="text-sm text-book-text-main">#{m.module_number} · {m.name}</span>
                                  <span className="text-xs text-book-text-muted ml-2">{m.type}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <button className="text-xs text-book-primary font-bold hover:underline" onClick={() => openEditModule(m)}>编辑</button>
                                  <button className="text-xs text-red-600 font-bold hover:underline" onClick={() => deleteModule(m)}>删除</button>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </BookCard>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 3: 目录结构 - 照抄 directory.py */}
        {activeTab === 'directory' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="text-base font-bold text-book-text-main">目录结构</div>
                <span className="text-sm text-book-text-muted">
                  总计 {treeData?.total_directories || 0} 目录 / {treeData?.total_files || 0} 文件
                </span>
              </div>
              <div className="flex items-center gap-2">
                <BookButton
                  size="sm"
                  variant="ghost"
                  onClick={() => setTreeExpandAllToken((v) => v + 1)}
                  disabled={!treeData?.root_nodes?.length}
                >
                  展开全部
                </BookButton>
                <BookButton
                  size="sm"
                  variant="ghost"
                  onClick={() => setTreeCollapseAllToken((v) => v + 1)}
                  disabled={!treeData?.root_nodes?.length}
                >
                  折叠全部
                </BookButton>
                <BookButton size="sm" variant="ghost" onClick={refreshTreeData} disabled={loading}>
                  <RefreshCw size={16} className={`mr-1 ${loading ? 'animate-spin' : ''}`} />
                  刷新
                </BookButton>
              </div>
            </div>

            <BookCard className="p-4">
              {!treeData?.root_nodes?.length ? (
                <div className="py-8 text-center text-sm text-book-text-muted">
                  暂无目录结构，请在工作台中使用 Agent 生成
                </div>
              ) : (
                <div className="max-h-[600px] overflow-y-auto custom-scrollbar">
                  <Suspense fallback={<div className="py-6 text-xs text-book-text-muted">目录树加载中…</div>}>
                    <DirectoryTreeLazy
                      data={treeData}
                      onSelectFile={handleSelectFile}
                      onSelectDirectory={setSelectedDirectory}
                      expandAllToken={treeExpandAllToken}
                      collapseAllToken={treeCollapseAllToken}
                    />
                  </Suspense>
                </div>
              )}
            </BookCard>

            {selectedDirectory && (
              <BookCard className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="min-w-0">
                    <div className="text-sm font-bold text-book-text-main truncate">
                      {selectedDirectory.name || '目录'}
                    </div>
                    <div className="text-xs text-book-text-muted truncate">
                      {selectedDirectory.path || ''}
                    </div>
                  </div>
                  <BookButton size="sm" variant="ghost" onClick={openDirectoryInfoModal}>
                    编辑目录描述
                  </BookButton>
                </div>
                <div className="text-sm text-book-text-sub whitespace-pre-wrap">
                  {selectedDirectory.description || '暂无描述'}
                </div>
              </BookCard>
            )}

            {currentFile && (
              <BookCard className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-sm font-bold text-book-text-main">{currentFile.filename || currentFile.file_path}</div>
                  <div className="flex items-center gap-2">
                    <BookButton size="sm" variant="ghost" onClick={openFileInfoModal} disabled={!currentFile}>
                      编辑信息
                    </BookButton>
                    <BookButton
                      size="sm"
                      variant="ghost"
                      onClick={() => openCodingDesk(typeof currentFile?.id === 'number' ? currentFile.id : undefined)}
                      disabled={!currentFile}
                      title="在工作台中打开并定位到该文件"
                    >
                      在工作台打开
                    </BookButton>
                    <BookButton size="sm" variant="ghost" onClick={handleGenerate} disabled={isGenerating}>
                      <Wand2 size={16} className={`mr-1 ${isGenerating ? 'animate-spin' : ''}`} />
                      生成
                    </BookButton>
                    <BookButton size="sm" variant="primary" onClick={handleSave} disabled={isSaving}>
                      {isSaving ? '保存中...' : '保存'}
                    </BookButton>
                  </div>
                </div>
                <Suspense fallback={<div className="py-6 text-xs text-book-text-muted">编辑器加载中…</div>}>
                  <EditorLazy
                    content={content}
                    versions={editorVersions}
                    isDirty={isCurrentFileDirty}
                    isSaving={isSaving}
                    isGenerating={isGenerating}
                    onChange={setContent}
                    onSave={handleSave}
                    onGenerate={handleGenerate}
                    onSelectVersion={handleSelectVersion}
                  />
                </Suspense>
              </BookCard>
            )}
          </div>
        )}

        {/* Tab 4: 生成管理 - 照抄 generation.py */}
        {activeTab === 'generation' && (
          <div className="space-y-6">
            {/* RAG状态Section */}
            <BookCard className="p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="text-sm font-bold text-book-text-main">RAG状态</div>
                <div className="flex items-center gap-2">
                  <BookButton size="sm" variant="ghost" onClick={() => ingestRag(false)} disabled={ragLoading || ragIngesting}>
                    <Database size={16} className={`mr-1 ${ragIngesting ? 'animate-pulse' : ''}`} />
                    {ragIngesting ? '入库中...' : '同步RAG'}
                  </BookButton>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-6">
                <div>
                  <div className="text-xs text-book-text-muted mb-1">数据完整性</div>
                  <div className="h-2 bg-book-border rounded-full mb-1">
                    <div
                      className={`h-full rounded-full ${ragCompleteness?.complete ? 'bg-green-500' : 'bg-yellow-500'}`}
                      style={{ width: ragCompleteness?.complete ? '100%' : '50%' }}
                    />
                  </div>
                  <div className="text-xs text-book-text-sub">
                    {ragCompleteness?.total_vector_count ?? '--'} / {ragCompleteness?.total_db_count ?? '--'}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-book-text-muted mb-1">已入库</div>
                  <div className="text-xl font-bold text-green-600">{ragCompleteness?.total_vector_count ?? 0}</div>
                </div>
                <div>
                  <div className="text-xs text-book-text-muted mb-1">待入库</div>
                  <div className="text-xl font-bold text-yellow-600">
                    {Math.max(0, (ragCompleteness?.total_db_count ?? 0) - (ragCompleteness?.total_vector_count ?? 0))}
                  </div>
                </div>
              </div>
            </BookCard>

            {/* 依赖关系Section */}
            <BookCard className="p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="text-sm font-bold text-book-text-main">依赖关系</div>
                  <span className="text-xs text-book-text-muted">({dependencies.length})</span>
                </div>
                <BookButton
                  size="sm"
                  variant="ghost"
                  onClick={async () => {
                    if (!id) return;
                    try {
                      const res = await codingApi.syncDependencies(id);
                      addToast(res?.message || '已同步', 'success');
                      await refreshDependencies();
                    } catch (e) {
                      console.error(e);
                      addToast('同步失败', 'error');
                    }
                  }}
                  disabled={tabLoading}
                >
                  <RefreshCw size={16} className="mr-1" />
                  同步依赖
                </BookButton>
              </div>
              {dependencies.length === 0 ? (
                <div className="text-sm text-book-text-muted text-center py-4">暂无依赖关系</div>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto custom-scrollbar">
                  {dependencies.slice(0, 10).map((d, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 rounded bg-book-bg/50">
                      <span className="text-sm text-book-text-main">{d.from_module} → {d.to_module}</span>
                      <button className="text-xs text-red-600 font-bold hover:underline" onClick={() => deleteDependency(d)}>删除</button>
                    </div>
                  ))}
                  {dependencies.length > 10 && (
                    <div className="text-xs text-book-text-muted text-center">... 还有 {dependencies.length - 10} 条</div>
                  )}
                </div>
              )}
            </BookCard>

            {/* 已生成内容Section - 对齐桌面端 generation.py */}
            <BookCard className="p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="text-sm font-bold text-book-text-main">已生成内容</div>
                  <span className="text-xs text-book-text-muted">({generatedSourceFiles.length})</span>
                  {generatedTotalVersions > 0 && (
                    <span className="text-xs text-book-text-muted">{generatedTotalVersions} 版本</span>
                  )}
                </div>
                <BookButton size="sm" variant="ghost" onClick={loadData} disabled={loading}>
                  <RefreshCw size={16} className={`mr-1 ${loading ? 'animate-spin' : ''}`} />
                  刷新
                </BookButton>
              </div>
              {generatedSourceFiles.length === 0 ? (
                <div className="text-sm text-book-text-muted text-center py-4">暂无已生成内容</div>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
                  {generatedSourceFiles.slice(0, 20).map((f: any) => (
                    <div key={f.id} className="flex items-center justify-between p-2 rounded bg-book-bg/50 border border-book-border/40">
                      <div className="min-w-0">
                        <div className="text-sm font-bold text-book-text-main truncate">{f.filename || f.file_path}</div>
                        <div className="text-xs text-book-text-muted truncate">{f.file_path || ''}</div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <span className="text-xs text-book-text-muted">{Number(f.version_count || 0)} 版本</span>
                        <button
                          type="button"
                          className="text-xs text-book-primary font-bold hover:underline"
                          onClick={() => {
                            setActiveTab('directory');
                            if (typeof f.id === 'number') handleSelectFile(f.id);
                          }}
                        >
                          打开
                        </button>
                        <button
                          type="button"
                          className="text-xs text-book-primary font-bold hover:underline"
                          onClick={() => {
                            if (typeof f.id === 'number') openCodingDesk(f.id);
                          }}
                        >
                          工作台
                        </button>
                      </div>
                    </div>
                  ))}
                  {generatedSourceFiles.length > 20 && (
                    <div className="text-xs text-book-text-muted text-center">... 还有 {generatedSourceFiles.length - 20} 个</div>
                  )}
                </div>
              )}
            </BookCard>

            {/* RAG检索Section */}
            <BookCard className="p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="text-sm font-bold text-book-text-main">检索查询</div>
                <BookButton size="sm" variant="ghost" onClick={runRagQuery} disabled={ragQueryLoading || !ragQuery?.trim()}>
                  <Search size={16} className={`mr-1 ${ragQueryLoading ? 'animate-spin' : ''}`} />
                  查询
                </BookButton>
              </div>
              <input
                className="w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main mb-4"
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                placeholder="输入问题，例如：模块职责/依赖关系/异常处理..."
                onKeyDown={(e) => { if (e.key === 'Enter') runRagQuery(); }}
              />
              {ragResult ? (
                <div className="space-y-3 max-h-64 overflow-y-auto custom-scrollbar">
                  {Array.isArray((ragResult as any).chunks) && (ragResult as any).chunks.map((c: any, idx: number) => (
                    <div key={idx} className="p-3 rounded bg-book-bg/50 border border-book-border/40">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold text-book-text-main">{c?.source || 'unknown'}</span>
                        <span className="text-[10px] text-book-text-muted font-mono">{c?.score?.toFixed(3) || ''}</span>
                      </div>
                      <div className="text-xs text-book-text-sub whitespace-pre-wrap">{c?.content || ''}</div>
                    </div>
                  ))}
                  {(!(ragResult as any).chunks?.length) && (
                    <div className="text-sm text-book-text-muted text-center py-4">未命中结果</div>
                  )}
                </div>
              ) : (
                <div className="text-sm text-book-text-muted text-center py-8">
                  <Sparkles size={24} className="mx-auto mb-2 opacity-50" />
                  输入问题以检索已入库的项目知识
                </div>
              )}
            </BookCard>
          </div>
        )}
      </div>

      <Modal
        isOpen={isPreferenceModalOpen}
        onClose={() => {
          pendingPreferenceActionRef.current = null;
          setIsPreferenceModalOpen(false);
        }}
        title={preferenceModalTitle}
        maxWidthClassName="max-w-2xl"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton
              variant="ghost"
              onClick={() => {
                pendingPreferenceActionRef.current = null;
                setIsPreferenceModalOpen(false);
              }}
            >
              取消
            </BookButton>
            <BookButton variant="primary" onClick={confirmPreferenceModal}>
              确定
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          {preferenceModalHint ? (
            <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
              {preferenceModalHint}
            </div>
          ) : null}
          <BookTextarea
            label="偏好指导（可选）"
            rows={6}
            value={preferenceModalValue}
            onChange={(e) => setPreferenceModalValue(e.target.value)}
            placeholder="例如：优先领域层/应用层分层；命名用驼峰；尽量少引入新依赖…"
          />
        </div>
      </Modal>

      <Modal
        isOpen={isDirectoryInfoModalOpen}
        onClose={() => setIsDirectoryInfoModalOpen(false)}
        title="编辑目录信息"
        maxWidthClassName="max-w-2xl"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton
              variant="ghost"
              onClick={() => setIsDirectoryInfoModalOpen(false)}
              disabled={directoryInfoSaving}
            >
              取消
            </BookButton>
            <BookButton variant="primary" onClick={saveDirectoryInfo} disabled={directoryInfoSaving}>
              {directoryInfoSaving ? '保存中…' : '保存'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="text-xs text-book-text-muted break-all">
            {selectedDirectory?.path || selectedDirectory?.name || ''}
          </div>
          <BookTextarea
            label="描述"
            rows={6}
            value={directoryInfoForm.description}
            onChange={(e) => setDirectoryInfoForm({ description: e.target.value })}
            placeholder="例如：该目录用于…"
          />
        </div>
      </Modal>

      <Modal
        isOpen={isFileInfoModalOpen}
        onClose={() => setIsFileInfoModalOpen(false)}
        title="编辑文件信息"
        maxWidthClassName="max-w-2xl"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={() => setIsFileInfoModalOpen(false)} disabled={fileInfoSaving}>
              取消
            </BookButton>
            <BookButton variant="primary" onClick={saveFileInfo} disabled={fileInfoSaving}>
              {fileInfoSaving ? '保存中…' : '保存'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="text-xs text-book-text-muted break-all">
            {currentFile?.file_path || currentFile?.filename || ''}
          </div>

          <BookTextarea
            label="描述"
            rows={4}
            value={fileInfoForm.description}
            onChange={(e) => setFileInfoForm({ ...fileInfoForm, description: e.target.value })}
            placeholder="例如：该文件负责…"
          />

          <BookTextarea
            label="用途"
            rows={4}
            value={fileInfoForm.purpose}
            onChange={(e) => setFileInfoForm({ ...fileInfoForm, purpose: e.target.value })}
            placeholder="例如：提供…接口/实现…逻辑"
          />

          <label className="text-xs font-bold text-book-text-sub">
            优先级
            <select
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
              value={fileInfoForm.priority}
              onChange={(e) => setFileInfoForm({ ...fileInfoForm, priority: e.target.value as CodingFilePriority })}
            >
              <option value="high">高</option>
              <option value="medium">中</option>
              <option value="low">低</option>
            </select>
          </label>
        </div>
      </Modal>

	      {/* System Modal */}
	      <Modal
	        isOpen={isSystemModalOpen}
	        onClose={() => setIsSystemModalOpen(false)}
        title={editingSystem ? `编辑系统 #${editingSystem.system_number}` : '新增系统'}
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={() => setIsSystemModalOpen(false)} disabled={systemSaving}>
              取消
            </BookButton>
            <BookButton variant="primary" onClick={saveSystem} disabled={systemSaving}>
              {systemSaving ? '保存中…' : '保存'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <BookInput label="系统名称" value={systemForm.name} onChange={(e) => setSystemForm({ ...systemForm, name: e.target.value })} />
          <BookTextarea
            label="系统描述"
            rows={3}
            value={systemForm.description}
            onChange={(e) => setSystemForm({ ...systemForm, description: e.target.value })}
          />
          <BookTextarea
            label="系统职责（每行一条）"
            rows={4}
            value={systemForm.responsibilitiesText}
            onChange={(e) => setSystemForm({ ...systemForm, responsibilitiesText: e.target.value })}
          />
          <BookTextarea
            label="技术要求"
            rows={4}
            value={systemForm.techRequirements}
            onChange={(e) => setSystemForm({ ...systemForm, techRequirements: e.target.value })}
          />
        </div>
      </Modal>

      {/* Module Modal */}
      <Modal
        isOpen={isModuleModalOpen}
        onClose={() => setIsModuleModalOpen(false)}
        title={editingModule ? `编辑模块 #${editingModule.module_number}` : '新增模块'}
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={() => setIsModuleModalOpen(false)} disabled={moduleSaving}>
              取消
            </BookButton>
            <BookButton variant="primary" onClick={saveModule} disabled={moduleSaving}>
              {moduleSaving ? '保存中…' : '保存'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <label className="text-xs font-bold text-book-text-sub">
            所属系统
            <select
              className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
              value={moduleForm.systemNumber}
              onChange={(e) => setModuleForm({ ...moduleForm, systemNumber: e.target.value ? Number(e.target.value) : '' })}
              disabled={Boolean(editingModule)}
            >
              <option value="">请选择</option>
              {sortedSystemNumbers.map((n) => (
                <option key={`sys-${n}`} value={n}>
                  系统 #{n}
                </option>
              ))}
            </select>
          </label>

          <BookInput label="模块名称" value={moduleForm.name} onChange={(e) => setModuleForm({ ...moduleForm, name: e.target.value })} />
          <BookInput label="模块类型" value={moduleForm.type} onChange={(e) => setModuleForm({ ...moduleForm, type: e.target.value })} />
          <BookTextarea
            label="模块描述"
            rows={3}
            value={moduleForm.description}
            onChange={(e) => setModuleForm({ ...moduleForm, description: e.target.value })}
          />
          <BookTextarea
            label="接口说明"
            rows={3}
            value={moduleForm.iface}
            onChange={(e) => setModuleForm({ ...moduleForm, iface: e.target.value })}
          />
          <BookTextarea
            label="依赖模块（每行一个模块名）"
            rows={4}
            value={moduleForm.dependenciesText}
            onChange={(e) => setModuleForm({ ...moduleForm, dependenciesText: e.target.value })}
          />
        </div>
      </Modal>
    </div>
  );
};
