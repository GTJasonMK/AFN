import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { novelsApi, Novel } from '../api/novels';
import { codingApi, CodingProjectSummary } from '../api/coding';
import { settingsApi } from '../api/settings';
import { CreateProjectModal } from '../components/business/CreateProjectModal';
import { ProjectListItem, ProjectListItemModel } from '../components/business/ProjectListItem';
import { useNavigate } from 'react-router-dom';
import { Plus, Settings, Code, FolderOpen, Upload } from 'lucide-react';
import { CREATIVE_QUOTES } from '../utils/constants';
import { ParticleBackground } from '../components/ui/ParticleBackground';
import { ImportModal } from '../components/business/ImportModal';
import { useUIStore } from '../store/ui';
import { confirmDialog } from '../components/feedback/ConfirmDialog';

export const NovelList: React.FC = () => {
  const [novels, setNovels] = useState<Novel[]>([]);
  const [codingProjects, setCodingProjects] = useState<CodingProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'recent' | 'all'>('recent');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createDefaultType, setCreateDefaultType] = useState<'novel' | 'coding'>('novel');
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [projectKind, setProjectKind] = useState<'novel' | 'coding'>('novel');
  const [codingEnabled, setCodingEnabled] = useState(false);
  const navigate = useNavigate();
  const { openSettings } = useUIStore();

  // Random quote
  const quote = useMemo(() => {
    return CREATIVE_QUOTES[Math.floor(Math.random() * CREATIVE_QUOTES.length)];
  }, []);

  const fetchNovels = useCallback(async () => {
    setLoading(true);
    try {
      // 获取高级配置，检查编程项目是否启用
      const advancedConfig = await settingsApi.getAdvancedConfig();
      const isCodingEnabled = advancedConfig.coding_project_enabled ?? false;
      setCodingEnabled(isCodingEnabled);

      // 如果编程项目功能关闭且当前选中的是编程项目，切换回小说
      setProjectKind((prev) => (!isCodingEnabled && prev === 'coding' ? 'novel' : prev));

      const [novelList, codingList] = await Promise.all([
        novelsApi.list(),
        // 仅在编程项目功能启用时获取编程项目列表
        isCodingEnabled ? codingApi.list() : Promise.resolve([]),
      ]);
      setNovels(novelList);
      setCodingProjects(codingList);
    } catch (err) {
      console.error("Failed to fetch novels", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNovels();
  }, [fetchNovels]);

  const handleProjectClick = (project: ProjectListItemModel) => {
    if (project.kind === 'coding') {
      const status = (project.status || '').toLowerCase();
      if (status.includes('draft')) {
        navigate(`/coding/inspiration/${project.id}`);
      } else {
        navigate(`/coding/detail/${project.id}`);
      }
      return;
    }

    // 桌面端（HOME）对齐：draft 表示“灵感对话中”，应继续进入对话；
    // 其余状态（blueprint_ready/part_outlines_ready/chapter_outlines_ready/writing/completed）默认进入写作台。
    const status = String(project.status || '').toLowerCase();
    if (status === 'draft' || status === 'inspiration') {
      navigate(`/inspiration/${project.id}`);
      return;
    }
    navigate(`/write/${project.id}`);
  };

  const handleDelete = async (project: ProjectListItemModel) => {
    const ok = await confirmDialog({
      title: '删除项目',
      message: `确定要删除项目「${project.title}」吗？`,
      confirmText: '删除',
      dialogType: 'danger',
    });
    if (!ok) return;
    try {
      if (project.kind === 'coding') {
        await codingApi.deleteProject(project.id);
      } else {
        await novelsApi.delete([project.id]);
      }
      fetchNovels();
    } catch (e) {
      console.error(e);
    }
  };

  const currentProjects = useMemo<ProjectListItemModel[]>(() => {
    if (projectKind === 'coding') {
      return codingProjects.map((p) => ({
        kind: 'coding',
        id: p.id,
        title: p.title,
        description: p.project_type_desc || 'Prompt工程',
        status: (p.status || '').toLowerCase(),
        updated_at: p.last_edited,
      }));
    }
    return novels.map((n) => ({
      kind: 'novel',
      id: n.id,
      title: n.title,
      description: n.is_imported
        ? `导入分析：${n.import_analysis_status || 'pending'}${n.genre ? ` · 类型：${n.genre}` : ''}`
        : (n.description || (n.genre ? `类型：${n.genre}` : undefined)),
      status: n.status,
      updated_at: n.last_edited || n.updated_at || n.created_at || new Date().toISOString(),
    }));
  }, [projectKind, codingProjects, novels]);

  const recentProjects = useMemo(() => {
    return [...currentProjects]
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, 10);
  }, [currentProjects]);

  const displayedProjects = activeTab === 'recent' ? recentProjects : currentProjects;

  return (
    <div className="flex h-screen w-full bg-book-bg overflow-hidden relative">
      <ParticleBackground />
      {/* Background decoration (Simplified particle effect) */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-30">
        <div className="absolute -top-20 -left-20 w-96 h-96 bg-book-primary/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute top-1/2 right-0 w-64 h-64 bg-book-accent/10 rounded-full blur-3xl animate-pulse delay-700" />
      </div>

      {/* LEFT COLUMN: Actions & Branding */}
      <div className="w-[380px] flex flex-col justify-between px-12 py-20 z-10">
        
        {/* 右上角设置按钮 - 照抄桌面端位置 */}
        <div className="absolute top-8 right-8">
	            <button
	                onClick={openSettings}
	                className="text-book-text-muted hover:text-book-accent flex items-center gap-2 text-sm transition-colors"
	            >
	                <Settings size={16} /> 设置
	            </button>
	        </div>

        <div className="space-y-10 animate-in fade-in slide-in-from-left-4 duration-700 my-auto">
          {/* Branding */}
          <div className="space-y-4">
            <h1 className="font-serif text-6xl font-bold text-book-text-main tracking-wider">
              AFN
            </h1>
            <p className="font-sans text-lg text-book-text-sub tracking-wide">
              AI 驱动的长篇小说创作助手
            </p>
          </div>

          {/* Quote */}
          <div className="space-y-2 border-l-4 border-book-primary/30 pl-4 py-1">
            <p className="font-serif text-lg italic text-book-text-secondary leading-relaxed">
              {quote[0]}
            </p>
            <p className="font-serif text-xs italic text-book-text-muted">
              {quote[1]}
            </p>
          </div>

          <div className="h-4" />

          {/* Action Buttons */}
          <div className="space-y-4 w-full max-w-xs">
            <button
              onClick={() => { setCreateDefaultType('novel'); setIsCreateModalOpen(true); }}
              className="w-full py-3.5 px-6 rounded-xl bg-book-accent text-white font-medium shadow-lg shadow-book-accent/20 hover:bg-book-text-main hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300 flex items-center justify-center gap-2 group"
            >
              <Plus size={20} className="group-hover:rotate-90 transition-transform duration-300" />
              创建小说
            </button>

            {codingEnabled && (
              <button
                onClick={() => { setCreateDefaultType('coding'); setIsCreateModalOpen(true); }}
                className="w-full py-3.5 px-6 rounded-xl bg-book-bg-paper border-2 border-book-accent text-book-accent font-medium hover:bg-book-accent hover:text-white transition-all duration-300 flex items-center justify-center gap-2"
              >
                <Code size={20} />
                创建Prompt工程
              </button>
            )}

            <button 
              onClick={() => setActiveTab('all')}
              className="w-full py-3.5 px-6 rounded-xl bg-transparent border border-book-border text-book-text-main hover:border-book-accent hover:text-book-accent transition-all duration-300 flex items-center justify-center gap-2"
            >
              <FolderOpen size={20} />
              查看全部项目
            </button>

            <button 
              onClick={() => setIsImportOpen(true)}
              className="w-full py-3.5 px-6 rounded-xl bg-book-bg-paper border border-book-border text-book-text-main hover:border-book-primary hover:text-book-primary transition-all duration-300 flex items-center justify-center gap-2"
              title="导入 TXT 小说并自动分析（桌面版同款流程）"
            >
              <Upload size={20} />
              导入 TXT 小说
            </button>
          </div>
        </div>
      </div>

	      {/* RIGHT COLUMN: Project List */}
	      <div className="flex-1 bg-book-bg-paper border-l border-book-border/40 p-12 flex flex-col z-10">
          {/* Project Kind Toggle */}
          {codingEnabled && (
            <div className="flex gap-2 mb-6">
              <button
                onClick={() => setProjectKind('novel')}
                className={`px-4 py-2 rounded-lg text-sm font-bold border transition-all ${
                  projectKind === 'novel'
                    ? 'bg-book-bg-paper border-book-border text-book-text-main'
                    : 'bg-transparent border-book-border/40 text-book-text-muted hover:text-book-text-main hover:border-book-border'
                }`}
              >
                小说
              </button>
              <button
                onClick={() => setProjectKind('coding')}
                className={`px-4 py-2 rounded-lg text-sm font-bold border transition-all ${
                  projectKind === 'coding'
                    ? 'bg-book-bg-paper border-book-border text-book-text-main'
                    : 'bg-transparent border-book-border/40 text-book-text-muted hover:text-book-text-main hover:border-book-border'
                }`}
              >
                Prompt工程
              </button>
            </div>
          )}
	        
	        {/* Tabs */}
	        <div className="flex gap-6 border-b border-book-border/30 pb-4 mb-6">
	          <button
            onClick={() => setActiveTab('recent')}
            className={`text-lg font-medium transition-colors pb-1 relative ${activeTab === 'recent' ? 'text-book-accent' : 'text-book-text-muted hover:text-book-text-main'}`}
          >
            最近项目
            {activeTab === 'recent' && <div className="absolute bottom-[-17px] left-0 right-0 h-0.5 bg-book-accent" />}
          </button>
          
          <button
            onClick={() => setActiveTab('all')}
            className={`text-lg font-medium transition-colors pb-1 relative ${activeTab === 'all' ? 'text-book-accent' : 'text-book-text-muted hover:text-book-text-main'}`}
          >
            全部项目
            {activeTab === 'all' && <div className="absolute bottom-[-17px] left-0 right-0 h-0.5 bg-book-accent" />}
          </button>
        </div>

	        {/* List Content */}
	        <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-3">
	          {loading ? (
            // Skeleton
            [1, 2, 3, 4].map(i => (
              <div key={i} className="h-20 w-full bg-book-bg-paper/40 rounded-lg animate-pulse" />
            ))
	          ) : displayedProjects.length > 0 ? (
	            displayedProjects.map(project => (
	              <ProjectListItem 
	                key={project.id} 
	                project={project} 
	                onClick={handleProjectClick}
	                onDelete={handleDelete}
	              />
	            ))
	          ) : (
            <div className="h-full flex flex-col items-center justify-center text-book-text-muted opacity-60">
              <FolderOpen size={48} className="mb-4 stroke-1" />
              <p className="text-center whitespace-pre-line">
                {activeTab === 'recent'
                  ? '暂无最近项目\n点击"创建小说"开始您的创作之旅'
                  : '暂无项目\n点击"创建小说"开始您的创作之旅'}
              </p>
            </div>
          )}
        </div>
      </div>

	      <CreateProjectModal
	        isOpen={isCreateModalOpen}
	        onClose={() => setIsCreateModalOpen(false)}
	        onSuccess={fetchNovels}
          defaultType={createDefaultType}
          codingEnabled={codingEnabled}
	      />
      
	        <ImportModal
	          isOpen={isImportOpen}
	          onClose={() => setIsImportOpen(false)}
	          onSuccess={fetchNovels}
	        />
	    </div>
	  );
};
