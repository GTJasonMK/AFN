import React, { useEffect, useMemo, useCallback, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { codingApi, CodingDependency, CodingModule, CodingSystem } from '../api/coding';
import { DirectoryTree } from '../components/coding/DirectoryTree';
import { Editor } from '../components/business/Editor'; // Reuse Editor for now
import { ArrowLeft, Layout, Code, FileCode, Boxes, Layers, GitBranch, RefreshCw, Plus, Wand2, Sparkles, Database, Search } from 'lucide-react';
import { BookButton } from '../components/ui/BookButton';
import { useSSE } from '../hooks/useSSE';
import { useToast } from '../components/feedback/Toast';
import { Modal } from '../components/ui/Modal';
import { BookCard } from '../components/ui/BookCard';
import { BookInput, BookTextarea } from '../components/ui/BookInput';

type CodingTab = 'files' | 'blueprint' | 'systems' | 'modules' | 'dependencies' | 'rag';

export const CodingDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  // 可选偏好弹窗：替代浏览器 prompt()，统一交互体验
  const pendingPreferenceActionRef = useRef<((preference?: string) => void | Promise<void>) | null>(null);
  const [isPreferenceModalOpen, setIsPreferenceModalOpen] = useState(false);
  const [preferenceModalTitle, setPreferenceModalTitle] = useState('偏好指导（可选）');
  const [preferenceModalHint, setPreferenceModalHint] = useState<string | null>(null);
  const [preferenceModalValue, setPreferenceModalValue] = useState('');

  const [activeTab, setActiveTab] = useState<CodingTab>('files');

  const [project, setProject] = useState<any>(null);
  const [treeData, setTreeData] = useState<any>(null);
  const [currentFile, setCurrentFile] = useState<any>(null);
  const [content, setContent] = useState('');
  const [versions, setVersions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

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

  // Dependencies add form
  const [depFrom, setDepFrom] = useState('');
  const [depTo, setDepTo] = useState('');
  const [depDesc, setDepDesc] = useState('');

  // RAG
  const [ragCompleteness, setRagCompleteness] = useState<any | null>(null);
  const [ragLoading, setRagLoading] = useState(false);
  const [ragIngesting, setRagIngesting] = useState(false);
  const [ragQuery, setRagQuery] = useState('');
  const [ragQueryLoading, setRagQueryLoading] = useState(false);
  const [ragResult, setRagResult] = useState<any | null>(null);

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
    try {
      const [proj, tree] = await Promise.all([
        codingApi.get(id),
        codingApi.getDirectoryTree(id)
      ]);
      setProject(proj);
      setTreeData(tree);
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
      const ok = confirm('强制全量入库会对所有类型重新入库，耗时更长。是否继续？');
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
    if (activeTab === 'systems') {
      refreshSystems();
    }
    if (activeTab === 'modules') {
      Promise.allSettled([refreshSystems(), refreshModules()]);
    }
    if (activeTab === 'dependencies') {
      Promise.allSettled([refreshModules(), refreshDependencies()]);
    }
    if (activeTab === 'rag') {
      refreshRagCompleteness();
    }
  }, [activeTab, id, refreshDependencies, refreshModules, refreshRagCompleteness, refreshSystems]);

  const sortedSystemNumbers = useMemo(() => {
    return [...new Set(systems.map((s) => Number(s.system_number || 0)).filter((n) => n > 0))].sort((a, b) => a - b);
  }, [systems]);

  useEffect(() => {
    if (targetSystemNumber !== '' || sortedSystemNumbers.length === 0) return;
    setTargetSystemNumber(sortedSystemNumbers[0]);
  }, [sortedSystemNumbers, targetSystemNumber]);

  const moduleNameOptions = useMemo(() => {
    return [...new Set(modules.map((m) => String(m.name || '')).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  }, [modules]);

  const openCreateSystem = () => {
    setEditingSystem(null);
    setSystemForm({ name: '', description: '', responsibilitiesText: '', techRequirements: '' });
    setIsSystemModalOpen(true);
  };

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
    const ok = confirm(`确定要删除系统「${sys.name}」吗？（会同时删除关联模块）`);
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
	    const ok = confirm('自动生成系统将删除当前所有系统/模块数据并重建。是否继续？');
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

  const openCreateModule = () => {
    setEditingModule(null);
    setModuleForm({
      systemNumber: targetSystemNumber === '' ? '' : targetSystemNumber,
      name: '',
      type: 'service',
      description: '',
      iface: '',
      dependenciesText: '',
    });
    setIsModuleModalOpen(true);
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
    const ok = confirm(`确定要删除模块「${m.name}」吗？`);
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
	    const ok = confirm(`为系统 #${sysNo} 生成模块？（会覆盖该系统下旧模块）`);
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
	    const ok = confirm('为所有系统批量生成模块（SSE流式）？这会逐个系统覆盖其旧模块。');
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

  const addDependency = async () => {
    if (!id) return;
    const from = depFrom.trim();
    const to = depTo.trim();
    if (!from || !to) {
      addToast('请选择源模块与目标模块', 'error');
      return;
    }
    if (from === to) {
      addToast('源模块与目标模块不能相同', 'error');
      return;
    }
    try {
      await codingApi.createDependency(id, { from_module: from, to_module: to, description: depDesc || undefined });
      addToast('依赖已添加', 'success');
      setDepDesc('');
      await Promise.allSettled([refreshDependencies(), refreshModules()]);
    } catch (e) {
      console.error(e);
      addToast('添加失败', 'error');
    }
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

  const handleGenerate = async () => {
    if (!id || !currentFile) return;
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
    } catch (e) {
      console.error(e);
      addToast('保存失败', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSelectVersion = async (index: number) => {
    if (!id || !currentFile) return;
    const target = versions[index];
    if (!target) return;
    try {
      await codingApi.selectFileVersion(id, currentFile.id, target.id);
      setContent(target.content);
      addToast('已切换版本', 'success');
    } catch (e) {
      console.error(e);
      addToast('切换失败', 'error');
    }
  };

  const { connect: connectFileStream, disconnect: disconnectFileStream } = useSSE((event, data) => {
    if (event === 'token' && data?.token) {
      setContent((prev) => prev + data.token);
      return;
    }
    if (event === 'complete') {
      setIsGenerating(false);
      addToast('生成完成', 'success');
      if (id && currentFile?.id) {
        handleSelectFile(currentFile.id);
      }
      return;
    }
    if (event === 'error') {
      setIsGenerating(false);
      addToast(data?.message || '生成失败', 'error');
    }
  });

  useEffect(() => {
    return () => disconnectFileStream();
  }, [disconnectFileStream]);

  if (loading) return <div className="flex h-screen items-center justify-center">加载中...</div>;

  const tabs = [
    { id: 'files', label: '文件', icon: FileCode },
    { id: 'blueprint', label: '蓝图', icon: Layout },
    { id: 'systems', label: '系统', icon: Boxes },
    { id: 'modules', label: '模块', icon: Layers },
    { id: 'dependencies', label: '依赖', icon: GitBranch },
    { id: 'rag', label: 'RAG', icon: Database },
  ] as const;

  return (
    <div className="flex flex-col h-screen bg-book-bg">
      {/* Header */}
      <div className="h-12 border-b border-book-border bg-book-bg-paper flex items-center px-4 justify-between shrink-0 z-30 shadow-sm">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate('/')}
            className="flex items-center text-book-text-sub hover:text-book-primary transition-colors text-sm font-medium"
          >
            <ArrowLeft size={16} className="mr-1" />
            返回列表
          </button>
          <div className="font-serif font-bold text-book-text-main text-base tracking-wide flex items-center gap-2">
            <Code size={16} className="text-book-accent" />
            {project?.title}
          </div>
        </div>
        
        <div className="flex gap-2">
          <BookButton size="sm" variant="ghost" onClick={() => navigate(`/coding/inspiration/${id}`)}>
            <Layout size={16} className="mr-1" /> 架构设计
          </BookButton>
          <BookButton size="sm" variant="ghost" onClick={() => navigate(`/coding/desk/${id}`)} title="进入编程工作台（文件级 Prompt 编辑/审查/目录规划）">
            <FileCode size={16} className="mr-1" /> 工作台
          </BookButton>
          {isGenerating && (
            <BookButton
              size="sm"
              variant="ghost"
              onClick={() => {
                disconnectFileStream();
                setIsGenerating(false);
                addToast('已断开生成流（后台任务可能仍在运行）', 'info');
              }}
              title="仅断开 SSE 连接（不保证取消后台任务）"
            >
              停止生成
            </BookButton>
          )}
          <BookButton size="sm" variant="ghost" onClick={() => setActiveTab('blueprint')}>
            查看蓝图
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

      <div className="flex-1 overflow-hidden">
        {activeTab === 'files' ? (
          <div className="flex h-full overflow-hidden">
            {/* Sidebar: File Tree */}
            <div className="w-64 bg-book-bg-paper border-r border-book-border/60 flex flex-col">
              <div className="p-3 border-b border-book-border/30 text-xs font-bold text-book-text-sub uppercase tracking-wider">
                Explorer
              </div>
              <div className="flex-1 overflow-y-auto custom-scrollbar">
                <DirectoryTree data={treeData} onSelectFile={handleSelectFile} />
              </div>
            </div>

            {/* Main: Editor */}
            <div className="flex-1 min-w-0 bg-book-bg">
              {currentFile ? (
                <Editor
                  content={content}
                  versions={versions.map((v, idx) => ({
                    id: String(v.id),
                    chapter_id: String(v.file_id ?? currentFile.id),
                    version_label: v.version_label || `v${idx + 1}`,
                    content: v.content,
                    created_at: v.created_at || new Date().toISOString(),
                    provider: v.provider || 'local',
                  }))}
                  isSaving={isSaving}
                  isGenerating={isGenerating}
                  onChange={setContent}
                  onSave={handleSave}
                  onGenerate={handleGenerate}
                  onSelectVersion={handleSelectVersion}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-book-text-muted">
                  选择一个文件查看详情
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="h-full overflow-y-auto p-6 custom-scrollbar">
            {activeTab === 'blueprint' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-serif font-bold text-lg text-book-text-main flex items-center gap-2">
                    <Layout size={18} className="text-book-accent" />
                    架构蓝图
                  </div>
                  <BookButton size="sm" variant="primary" onClick={handleGenerateBlueprint}>
                    <Wand2 size={16} className="mr-1" />
                    {project?.blueprint ? '重新生成蓝图' : '生成蓝图'}
                  </BookButton>
                </div>

                {!project?.blueprint ? (
                  <BookCard className="p-5">
                    <div className="text-sm text-book-text-muted leading-relaxed">
                      当前项目尚未生成蓝图。请先完成“架构设计”对话，或直接点击右上角“生成蓝图”。
                    </div>
                  </BookCard>
                ) : (
                  <>
                    <BookCard className="p-5 space-y-2">
                      <div className="text-sm text-book-text-muted">{project.blueprint.project_type_desc || '（未设置项目类型）'}</div>
                      <div className="text-lg font-bold text-book-text-main">{project.blueprint.one_sentence_summary || '（暂无一句话概要）'}</div>
                    </BookCard>

                    <BookCard className="p-5">
                      <div className="text-xs text-book-text-muted mb-2">架构概述</div>
                      <div className="text-sm text-book-text-main whitespace-pre-wrap leading-relaxed">
                        {project.blueprint.architecture_synopsis || '暂无内容'}
                      </div>
                    </BookCard>

                    {project.blueprint.tech_stack && (
                      <BookCard className="p-5">
                        <div className="text-xs text-book-text-muted mb-2">技术栈</div>
                        <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed">
                          {JSON.stringify(project.blueprint.tech_stack, null, 2)}
                        </pre>
                      </BookCard>
                    )}

                    {Array.isArray(project.blueprint.core_requirements) && project.blueprint.core_requirements.length > 0 && (
                      <BookCard className="p-5">
                        <div className="text-xs text-book-text-muted mb-3">核心需求</div>
                        <div className="space-y-2">
                          {project.blueprint.core_requirements.map((r: any, idx: number) => (
                            <div key={`req-${idx}`} className="p-3 rounded border border-book-border/40 bg-book-bg">
                              <div className="text-xs text-book-text-muted">{r.category} · {r.priority}</div>
                              <div className="text-sm text-book-text-main mt-1">{r.requirement}</div>
                            </div>
                          ))}
                        </div>
                      </BookCard>
                    )}

                    {Array.isArray(project.blueprint.technical_challenges) && project.blueprint.technical_challenges.length > 0 && (
                      <BookCard className="p-5">
                        <div className="text-xs text-book-text-muted mb-3">技术挑战</div>
                        <div className="space-y-2">
                          {project.blueprint.technical_challenges.map((c: any, idx: number) => (
                            <div key={`ch-${idx}`} className="p-3 rounded border border-book-border/40 bg-book-bg">
                              <div className="text-xs text-book-text-muted">影响：{c.impact || 'medium'}</div>
                              <div className="text-sm text-book-text-main mt-1">{c.challenge}</div>
                              {c.solution_direction ? (
                                <div className="text-xs text-book-text-muted mt-2 whitespace-pre-wrap">方向：{c.solution_direction}</div>
                              ) : null}
                            </div>
                          ))}
                        </div>
                      </BookCard>
                    )}
                  </>
                )}
              </div>
            )}

            {activeTab === 'systems' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-serif font-bold text-lg text-book-text-main flex items-center gap-2">
                    <Boxes size={18} className="text-book-primary" />
                    系统划分
                  </div>
                  <div className="flex items-center gap-2">
                    <BookButton size="sm" variant="ghost" onClick={refreshSystems} disabled={tabLoading}>
                      <RefreshCw size={16} className={`mr-1 ${tabLoading ? 'animate-spin' : ''}`} />
                      刷新
                    </BookButton>
                    <BookButton size="sm" variant="ghost" onClick={generateSystems} disabled={tabLoading}>
                      <Wand2 size={16} className="mr-1" />
                      生成系统
                    </BookButton>
                    <BookButton size="sm" variant="primary" onClick={openCreateSystem} disabled={tabLoading}>
                      <Plus size={16} className="mr-1" />
                      新增系统
                    </BookButton>
                  </div>
                </div>

                {systems.length === 0 ? (
                  <BookCard className="p-5">
                    <div className="text-sm text-book-text-muted">暂无系统。可先生成蓝图，再点击“生成系统”。</div>
                  </BookCard>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {systems.map((s) => (
                      <BookCard key={s.system_number} className="p-5">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="font-bold text-book-text-main truncate">
                              #{s.system_number} · {s.name}
                            </div>
                            <div className="text-xs text-book-text-muted mt-1">
                              模块数：{s.module_count || 0} · 状态：{s.generation_status} · 进度：{s.progress ?? 0}%
                            </div>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <button className="text-xs text-book-primary font-bold hover:underline" onClick={() => openEditSystem(s)}>
                              编辑
                            </button>
                            <button className="text-xs text-red-600 font-bold hover:underline" onClick={() => deleteSystem(s)}>
                              删除
                            </button>
                          </div>
                        </div>

                        {s.description ? (
                          <div className="mt-3 text-sm text-book-text-secondary whitespace-pre-wrap leading-relaxed">
                            {s.description}
                          </div>
                        ) : null}

                        {Array.isArray(s.responsibilities) && s.responsibilities.length > 0 ? (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {s.responsibilities.slice(0, 8).map((r, idx) => (
                              <span key={`r-${s.system_number}-${idx}`} className="text-[11px] px-2 py-0.5 rounded-full bg-book-bg border border-book-border/40 text-book-text-sub">
                                {r}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </BookCard>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'modules' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-serif font-bold text-lg text-book-text-main flex items-center gap-2">
                    <Layers size={18} className="text-book-primary" />
                    模块列表
                  </div>
                  <div className="flex items-center gap-2">
                    <BookButton size="sm" variant="ghost" onClick={() => Promise.allSettled([refreshSystems(), refreshModules()])} disabled={tabLoading}>
                      <RefreshCw size={16} className={`mr-1 ${tabLoading ? 'animate-spin' : ''}`} />
                      刷新
                    </BookButton>
                    <BookButton size="sm" variant="ghost" onClick={startGenerateAllModules} disabled={genAllRunning || tabLoading}>
                      <Wand2 size={16} className="mr-1" />
                      生成全部模块
                    </BookButton>
                    <BookButton size="sm" variant="primary" onClick={openCreateModule} disabled={tabLoading}>
                      <Plus size={16} className="mr-1" />
                      新增模块
                    </BookButton>
                  </div>
                </div>

                <BookCard className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="text-xs font-bold text-book-text-sub">目标系统</div>
                    <select
                      className="px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                      value={targetSystemNumber}
                      onChange={(e) => setTargetSystemNumber(e.target.value ? Number(e.target.value) : '')}
                      disabled={tabLoading || genAllRunning}
                    >
                      <option value="">请选择</option>
                      {sortedSystemNumbers.map((n) => (
                        <option key={n} value={n}>
                          系统 #{n}
                        </option>
                      ))}
                    </select>
                    <BookButton size="sm" variant="secondary" onClick={generateModulesForSystem} disabled={tabLoading || genAllRunning}>
                      <Wand2 size={16} className="mr-1" />
                      生成该系统模块
                    </BookButton>
                    {genAllRunning && (
                      <button
                        className="text-xs text-book-text-muted font-bold hover:underline"
                        onClick={() => {
                          disconnectModulesStream();
                          setGenAllRunning(false);
                          addToast('已停止模块生成流（后台可能仍在运行）', 'info');
                        }}
                      >
                        停止
                      </button>
                    )}
                  </div>
                </BookCard>

                {genAllLogs.length > 0 && (
                  <BookCard className="p-4">
                    <div className="text-xs text-book-text-muted mb-2">生成进度</div>
                    <div className="max-h-48 overflow-y-auto custom-scrollbar space-y-1 text-xs text-book-text-main">
                      {genAllLogs.map((line, idx) => (
                        <div key={`log-${idx}`} className="font-mono whitespace-pre-wrap">
                          {line}
                        </div>
                      ))}
                    </div>
                  </BookCard>
                )}

                {modules.length === 0 ? (
                  <BookCard className="p-5">
                    <div className="text-sm text-book-text-muted">暂无模块。可先生成系统，再生成模块。</div>
                  </BookCard>
                ) : (
                  <div className="space-y-3">
                    {modules
                      .slice()
                      .sort((a, b) => Number(a.module_number || 0) - Number(b.module_number || 0))
                      .map((m) => (
                        <BookCard key={m.module_number} className="p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="font-bold text-book-text-main truncate">
                                #{m.module_number} · {m.name}
                              </div>
                              <div className="text-xs text-book-text-muted mt-1">
                                系统 #{m.system_number} · 类型 {m.type} · 状态 {m.generation_status}
                              </div>
                              {m.description ? (
                                <div className="mt-2 text-sm text-book-text-secondary whitespace-pre-wrap leading-relaxed">
                                  {m.description}
                                </div>
                              ) : null}
                              {Array.isArray(m.dependencies) && m.dependencies.length > 0 ? (
                                <div className="mt-2 text-xs text-book-text-muted">
                                  依赖：{m.dependencies.join('、')}
                                </div>
                              ) : null}
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              <button className="text-xs text-book-primary font-bold hover:underline" onClick={() => openEditModule(m)}>
                                编辑
                              </button>
                              <button className="text-xs text-red-600 font-bold hover:underline" onClick={() => deleteModule(m)}>
                                删除
                              </button>
                            </div>
                          </div>
                        </BookCard>
                      ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'dependencies' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-serif font-bold text-lg text-book-text-main flex items-center gap-2">
                    <GitBranch size={18} className="text-book-primary" />
                    模块依赖
                  </div>
                  <div className="flex items-center gap-2">
                    <BookButton size="sm" variant="ghost" onClick={() => Promise.allSettled([refreshModules(), refreshDependencies()])} disabled={tabLoading}>
                      <RefreshCw size={16} className={`mr-1 ${tabLoading ? 'animate-spin' : ''}`} />
                      刷新
                    </BookButton>
                    <BookButton
                      size="sm"
                      variant="ghost"
                      onClick={async () => {
                        if (!id) return;
                        try {
                          const res = await codingApi.syncDependencies(id);
                          addToast(res?.message || '已同步依赖关系统计', 'success');
                          await refreshDependencies();
                        } catch (e) {
                          console.error(e);
                          addToast('同步失败', 'error');
                        }
                      }}
                      disabled={tabLoading}
                    >
                      <RefreshCw size={16} className="mr-1" />
                      同步
                    </BookButton>
                  </div>
                </div>

                <BookCard className="p-4 space-y-3">
                  <div className="text-xs font-bold text-book-text-sub">新增依赖</div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <label className="text-xs font-bold text-book-text-sub">
                      源模块
                      <select
                        className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                        value={depFrom}
                        onChange={(e) => setDepFrom(e.target.value)}
                      >
                        <option value="">请选择</option>
                        {moduleNameOptions.map((n) => (
                          <option key={`from-${n}`} value={n}>
                            {n}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="text-xs font-bold text-book-text-sub">
                      目标模块
                      <select
                        className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                        value={depTo}
                        onChange={(e) => setDepTo(e.target.value)}
                      >
                        <option value="">请选择</option>
                        {moduleNameOptions.map((n) => (
                          <option key={`to-${n}`} value={n}>
                            {n}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="text-xs font-bold text-book-text-sub">
                      描述（可选）
                      <input
                        className="mt-1 w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                        value={depDesc}
                        onChange={(e) => setDepDesc(e.target.value)}
                        placeholder="例如：调用/事件/共享数据"
                      />
                    </label>
                  </div>
                  <div className="flex justify-end">
                    <BookButton size="sm" variant="primary" onClick={addDependency}>
                      <Plus size={16} className="mr-1" />
                      添加
                    </BookButton>
                  </div>
                </BookCard>

                {dependencies.length === 0 ? (
                  <BookCard className="p-5">
                    <div className="text-sm text-book-text-muted">暂无依赖关系。</div>
                  </BookCard>
                ) : (
                  <div className="space-y-3">
                    {dependencies.map((d) => (
                      <BookCard key={`${d.from_module}->${d.to_module}-${d.position}`} className="p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="font-bold text-book-text-main">
                              {d.from_module} → {d.to_module}
                            </div>
                            <div className="text-xs text-book-text-muted mt-1 whitespace-pre-wrap">
                              {d.description || ''}
                            </div>
                          </div>
                          <button className="text-xs text-red-600 font-bold hover:underline" onClick={() => deleteDependency(d)}>
                            删除
                          </button>
                        </div>
                      </BookCard>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'rag' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-serif font-bold text-lg text-book-text-main flex items-center gap-2">
                    <Database size={18} className="text-book-primary" />
                    RAG / 知识库
                  </div>
                  <div className="flex items-center gap-2">
                    <BookButton size="sm" variant="ghost" onClick={refreshRagCompleteness} disabled={ragLoading || ragIngesting}>
                      <RefreshCw size={16} className={`mr-1 ${ragLoading ? 'animate-spin' : ''}`} />
                      刷新
                    </BookButton>
                    <BookButton
                      size="sm"
                      variant="ghost"
                      onClick={() => ingestRag(false)}
                      disabled={ragLoading || ragIngesting}
                    >
                      <Database size={16} className={`mr-1 ${ragIngesting ? 'animate-pulse' : ''}`} />
                      {ragIngesting ? '入库中…' : '入库'}
                    </BookButton>
                    <BookButton
                      size="sm"
                      variant="primary"
                      onClick={() => ingestRag(true)}
                      disabled={ragLoading || ragIngesting}
                    >
                      强制重建
                    </BookButton>
                  </div>
                </div>

                {ragLoading && (
                  <BookCard className="p-5">
                    <div className="text-sm text-book-text-muted">RAG 状态加载中…</div>
                  </BookCard>
                )}

                {!ragLoading && ragCompleteness && (
                  <>
                    <BookCard className="p-4 space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="text-sm font-bold text-book-text-main">完整性</div>
                        <div className={`text-sm font-bold ${ragCompleteness.complete ? 'text-book-primary' : 'text-book-accent'}`}>
                          {ragCompleteness.complete ? '已完成' : '未完成'}
                        </div>
                      </div>
                      <div className="text-xs text-book-text-muted">
                        DB：{ragCompleteness.total_db_count} · 向量：{ragCompleteness.total_vector_count}
                      </div>
                    </BookCard>

                    <BookCard className="p-4">
                      <div className="text-xs font-bold text-book-text-sub mb-3">类型明细</div>
                      <div className="space-y-2">
                        {Object.entries(ragCompleteness.types || {}).map(([k, v]: any) => {
                          const complete = Boolean(v?.complete);
                          const missing = typeof v?.missing === 'number' ? v.missing : null;
                          const displayName = String(v?.display_name || k);
                          return (
                            <div key={k} className="p-3 rounded border border-book-border/40 bg-book-bg">
                              <div className="flex items-center justify-between gap-2">
                                <div className="font-bold text-book-text-main text-sm truncate">{displayName}</div>
                                <div className={`text-xs font-bold ${complete ? 'text-book-primary' : 'text-book-accent'}`}>
                                  {complete ? '完成' : (missing !== null ? `缺 ${missing}` : '未完成')}
                                </div>
                              </div>
                              <div className="text-xs text-book-text-muted mt-1">
                                DB：{v?.db_count ?? 0} · 向量：{v?.vector_count ?? 0}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </BookCard>
                  </>
                )}

                {!ragLoading && !ragCompleteness && (
                  <BookCard className="p-5">
                    <div className="text-sm text-book-text-muted leading-relaxed">
                      暂无法获取 RAG 完整性信息。若后端未启用向量库/嵌入服务，请先在设置中完成配置后再重试。
                    </div>
                  </BookCard>
                )}

                <BookCard className="p-4 space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-xs font-bold text-book-text-sub">检索查询</div>
                    <BookButton
                      size="sm"
                      variant="ghost"
                      onClick={runRagQuery}
                      disabled={ragQueryLoading || !(ragQuery || '').trim()}
                    >
                      <Search size={16} className={`mr-1 ${ragQueryLoading ? 'animate-spin' : ''}`} />
                      查询
                    </BookButton>
                  </div>

                  <input
                    className="w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main"
                    value={ragQuery}
                    onChange={(e) => setRagQuery(e.target.value)}
                    placeholder="输入问题，例如：模块职责/依赖关系/异常处理..."
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') runRagQuery();
                    }}
                  />

                  {ragResult ? (
                    <div className="space-y-4">
                      {Array.isArray((ragResult as any).summaries) && (ragResult as any).summaries.length > 0 && (
                        <div>
                          <div className="text-xs font-bold text-book-text-sub mb-2">摘要</div>
                          <div className="space-y-2">
                            {(ragResult as any).summaries.map((s: any, idx: number) => (
                              <BookCard key={`s-${s?.chapter_number ?? 'unknown'}-${idx}`} className="p-3 bg-book-bg/50 border-book-border/50">
                                <div className="flex items-center justify-between gap-2">
                                  <div className="text-xs font-bold text-book-text-main truncate">{s?.title || `条目 ${idx + 1}`}</div>
                                  <div className="text-[10px] text-book-text-muted font-mono">
                                    {typeof s?.score === 'number' ? s.score.toFixed(3) : ''}
                                  </div>
                                </div>
                                <div className="text-xs text-book-text-muted mt-2 whitespace-pre-wrap leading-relaxed">{s?.summary || ''}</div>
                              </BookCard>
                            ))}
                          </div>
                        </div>
                      )}

                      {Array.isArray((ragResult as any).chunks) && (ragResult as any).chunks.length > 0 && (
                        <div>
                          <div className="text-xs font-bold text-book-text-sub mb-2">片段</div>
                          <div className="space-y-2">
                            {(ragResult as any).chunks.map((c: any, idx: number) => (
                              <BookCard key={`c-${c?.chapter_number ?? 'unknown'}-${idx}`} className="p-3 bg-book-bg/50 border-book-border/50">
                                <div className="flex items-center justify-between gap-2">
                                  <div className="text-xs font-bold text-book-text-main truncate">
                                    {c?.data_type ? `[${c.data_type}] ` : ''}{c?.source || 'unknown'}
                                  </div>
                                  <div className="text-[10px] text-book-text-muted font-mono">
                                    {typeof c?.score === 'number' ? c.score.toFixed(3) : ''}
                                  </div>
                                </div>
                                <div className="text-xs text-book-text-muted mt-2 whitespace-pre-wrap leading-relaxed">{c?.content || ''}</div>
                              </BookCard>
                            ))}
                          </div>
                        </div>
                      )}

                      {(!(ragResult as any).summaries?.length && !(ragResult as any).chunks?.length) && (
                        <div className="py-10 text-center text-book-text-muted text-sm">未命中结果</div>
                      )}
                    </div>
                  ) : (
                    <div className="py-10 text-center text-book-text-muted text-xs">
                      <Sparkles size={22} className="mx-auto mb-2 opacity-70" />
                      输入问题以检索已入库的项目知识
                    </div>
                  )}
                </BookCard>
              </div>
            )}
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
