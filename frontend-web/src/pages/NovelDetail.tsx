import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { novelsApi } from '../api/novels';
import { writerApi } from '../api/writer';
import { BookButton } from '../components/ui/BookButton';
import { BookCard } from '../components/ui/BookCard';
import { BookInput, BookTextarea } from '../components/ui/BookInput';
import { ArrowLeft, Save, Play, Sparkles, Map, Users, FileText, Share, Plus, Trash2, Download } from 'lucide-react';
import { useToast } from '../components/feedback/Toast';
import { Modal } from '../components/ui/Modal';

type Tab = 'overview' | 'world' | 'characters' | 'outlines';

export const NovelDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  const [project, setProject] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form states
  const [blueprintData, setBlueprintData] = useState<any>({});

  // Part outlines progress
  const [partProgress, setPartProgress] = useState<any | null>(null);
  const [partLoading, setPartLoading] = useState(false);
  
  // Character Edit State
  const [editingCharIndex, setEditingCharIndex] = useState<number | null>(null);
  const [charForm, setCharForm] = useState<any>({});
  const [isCharModalOpen, setIsCharModalOpen] = useState(false);

  // Blueprint Refine（优化蓝图）State
  const [isRefineModalOpen, setIsRefineModalOpen] = useState(false);
  const [refineInstruction, setRefineInstruction] = useState('');
  const [refineForce, setRefineForce] = useState(false);
  const [refining, setRefining] = useState(false);
  const [refineResult, setRefineResult] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      fetchProject();
    }
  }, [id]);

  useEffect(() => {
    if (id && activeTab === 'outlines') {
      fetchPartProgress();
    }
  }, [id, activeTab]);

  const fetchProject = async () => {
    try {
      const data = await novelsApi.get(id!);
      setProject(data);
      if (data.blueprint) {
        setBlueprintData(data.blueprint);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!id) return;
    setSaving(true);
    try {
      await novelsApi.updateBlueprint(id, blueprintData);
      addToast('蓝图已保存', 'success');
    } catch (e) {
      console.error(e);
      addToast('保存失败', 'error');
    } finally {
      setSaving(false);
    }
  };

  const openRefineModal = () => {
    setRefineInstruction('');
    setRefineForce(false);
    setRefineResult(null);
    setIsRefineModalOpen(true);
  };

  const handleRefineBlueprint = async () => {
    if (!id) return;
    const instruction = refineInstruction.trim();
    if (!instruction) {
      addToast('请输入优化指令', 'error');
      return;
    }

    setRefining(true);
    setRefineResult(null);

    const run = async (force: boolean) => {
      const result = await novelsApi.refineBlueprint(id, instruction, force);
      if (result?.blueprint) setBlueprintData(result.blueprint);
      setRefineResult(result?.ai_message || null);
      addToast('蓝图优化完成', 'success');
      await fetchProject();
    };

    try {
      await run(refineForce);
    } catch (e: any) {
      const status = e?.response?.status;
      const detail = e?.response?.data?.detail;

      // 后端会在存在章节大纲/章节内容时返回 409，提示需要用户确认 force
      if (status === 409 && !refineForce) {
        const ok = confirm(
          `${detail || '检测到已有后续数据，优化蓝图会清空这些数据。'}\n\n是否强制优化？`
        );
        if (ok) {
          try {
            setRefineForce(true);
            await run(true);
          } catch (e2) {
            console.error(e2);
          }
        }
        return;
      }

      console.error(e);
    } finally {
      setRefining(false);
    }
  };

  const handleExport = async () => {
    if (!id) return;
    try {
      const response = await novelsApi.exportNovel(id, 'txt');
      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      // Content-Disposition header usually has filename, but we can fallback
      const filename = `${project.title || 'novel'}.txt`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      addToast('导出成功', 'success');
    } catch (e) {
      console.error(e);
      addToast('导出失败', 'error');
    }
  };

  const fetchPartProgress = async () => {
    if (!id) return;
    setPartLoading(true);
    try {
      const data = await writerApi.getPartOutlines(id);
      setPartProgress(data);
    } catch (e) {
      // 可能尚未生成部分大纲，忽略即可
      setPartProgress(null);
    } finally {
      setPartLoading(false);
    }
  };

  const handleEditChar = (index: number) => {
    setEditingCharIndex(index);
    setCharForm({ ...blueprintData.characters[index] });
    setIsCharModalOpen(true);
  };

  const handleAddChar = () => {
    setEditingCharIndex(null); // null means adding
    setCharForm({ name: '', identity: '', personality: '', goal: '' });
    setIsCharModalOpen(true);
  };

  const handleSaveChar = () => {
    const newChars = [...(blueprintData.characters || [])];
    if (editingCharIndex !== null) {
      newChars[editingCharIndex] = charForm;
    } else {
      newChars.push(charForm);
    }
    setBlueprintData({ ...blueprintData, characters: newChars });
    setIsCharModalOpen(false);
  };

  const handleDeleteChar = (index: number) => {
    if (confirm('确定要删除这个角色吗？')) {
      const newChars = [...blueprintData.characters];
      newChars.splice(index, 1);
      setBlueprintData({ ...blueprintData, characters: newChars });
    }
  };

  if (loading) return <div className="flex h-screen items-center justify-center text-book-text-muted">加载中...</div>;
  if (!project) return <div className="flex h-screen items-center justify-center text-book-text-muted">项目不存在</div>;

  return (
    <div className="min-h-screen bg-book-bg flex flex-col">
      {/* Header */}
      <div className="h-16 border-b border-book-border/40 bg-book-bg-paper/80 backdrop-blur-md flex items-center justify-between px-8 sticky top-0 z-20">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate('/')}
            className="flex items-center text-book-text-sub hover:text-book-primary transition-colors group"
          >
            <div className="p-1.5 rounded-full bg-book-bg border border-book-border group-hover:border-book-primary/50 shadow-sm transition-colors">
              <ArrowLeft size={16} />
            </div>
          </button>
          
          <div>
            <h1 className="font-serif font-bold text-lg text-book-text-main">{project.title}</h1>
            <div className="flex items-center gap-2 text-xs text-book-text-muted">
              <span className="px-1.5 py-0.5 rounded bg-book-bg border border-book-border">{blueprintData.genre || '未分类'}</span>
              <span>•</span>
              <span>{project.status}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <BookButton variant="ghost" size="sm" onClick={handleExport}>
            <Download size={16} className="mr-2" />
            导出
          </BookButton>
          <BookButton variant="ghost" size="sm" onClick={handleSave} disabled={saving}>
            <Save size={16} className="mr-2" />
            {saving ? '保存中...' : '保存修改'}
          </BookButton>
          <BookButton variant="secondary" size="sm" onClick={openRefineModal}>
            <Sparkles size={16} className="mr-2" />
            优化蓝图
          </BookButton>
          <BookButton variant="primary" size="sm" onClick={() => navigate(`/write/${id}`)}>
            <Play size={16} className="mr-2 fill-current" />
            进入写作
          </BookButton>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-book-border/40 bg-book-bg-paper px-8">
        <div className="flex gap-8">
          {[
            { id: 'overview', label: '概览', icon: FileText },
            { id: 'world', label: '世界观', icon: Map },
            { id: 'characters', label: '角色', icon: Users },
            { id: 'outlines', label: '大纲', icon: Share },
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`
                  flex items-center gap-2 py-4 text-sm font-bold transition-all relative
                  ${isActive ? 'text-book-primary' : 'text-book-text-sub hover:text-book-text-main'}
                `}
              >
                <Icon size={16} />
                {tab.label}
                {isActive && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-book-primary rounded-t-full" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-8 max-w-5xl mx-auto w-full custom-scrollbar">
        {activeTab === 'overview' && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <div className="grid grid-cols-3 gap-6">
              <div className="col-span-2 space-y-6">
                <BookCard className="p-6 space-y-4">
                  <h3 className="font-serif font-bold text-lg text-book-text-main border-b border-book-border/40 pb-2">
                    一句话梗概
                  </h3>
                  <BookTextarea 
                    value={blueprintData.one_sentence_summary || ''}
                    onChange={(e) => setBlueprintData({...blueprintData, one_sentence_summary: e.target.value})}
                    className="min-h-[80px] text-base font-serif leading-relaxed"
                  />
                </BookCard>

                <BookCard className="p-6 space-y-4">
                  <h3 className="font-serif font-bold text-lg text-book-text-main border-b border-book-border/40 pb-2">
                    故事全貌
                  </h3>
                  <BookTextarea 
                    value={blueprintData.full_synopsis || ''}
                    onChange={(e) => setBlueprintData({...blueprintData, full_synopsis: e.target.value})}
                    className="min-h-[300px] text-base font-serif leading-relaxed"
                  />
                </BookCard>
              </div>

              <div className="space-y-6">
                <BookCard className="p-5 space-y-4 sticky top-4">
                  <h3 className="font-bold text-sm text-book-text-main">基础设定</h3>
                  <div className="space-y-3">
                    <BookInput 
                      label="作品类型" 
                      value={blueprintData.genre || ''}
                      onChange={(e) => setBlueprintData({...blueprintData, genre: e.target.value})}
                    />
                    <BookInput 
                      label="目标读者" 
                      value={blueprintData.target_audience || ''}
                      onChange={(e) => setBlueprintData({...blueprintData, target_audience: e.target.value})}
                    />
                    <BookInput 
                      label="叙事风格" 
                      value={blueprintData.style || ''}
                      onChange={(e) => setBlueprintData({...blueprintData, style: e.target.value})}
                    />
                    <BookInput 
                      label="情感基调" 
                      value={blueprintData.tone || ''}
                      onChange={(e) => setBlueprintData({...blueprintData, tone: e.target.value})}
                    />
                  </div>
                </BookCard>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'world' && (
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
                <BookCard className="p-6 space-y-4">
                  <h3 className="font-serif font-bold text-lg text-book-text-main border-b border-book-border/40 pb-2">
                    世界观设定
                  </h3>
                  <BookTextarea 
                    value={
                      typeof blueprintData.world_setting === 'string' 
                        ? blueprintData.world_setting 
                        : JSON.stringify(blueprintData.world_setting, null, 2)
                    }
                    onChange={(e) => setBlueprintData({...blueprintData, world_setting: e.target.value})}
                    className="min-h-[500px] text-base font-serif leading-relaxed font-mono"
                    placeholder="输入世界观设定..."
                  />
                </BookCard>
            </div>
        )}

        {activeTab === 'characters' && (
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="font-serif font-bold text-lg text-book-text-main">角色列表 ({blueprintData.characters?.length || 0})</h3>
                    <BookButton size="sm" onClick={handleAddChar}>
                        <Plus size={16} className="mr-1" /> 添加角色
                    </BookButton>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {blueprintData.characters?.map((char: any, idx: number) => (
                        <BookCard key={idx} className="p-5 hover:shadow-md transition-shadow group relative">
                            <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                                <button onClick={() => handleEditChar(idx)} className="p-1.5 rounded-full bg-book-bg hover:text-book-primary">
                                    <FileText size={14} />
                                </button>
                                <button onClick={() => handleDeleteChar(idx)} className="p-1.5 rounded-full bg-book-bg hover:text-red-500">
                                    <Trash2 size={14} />
                                </button>
                            </div>
                            
                            <div className="flex justify-between items-start mb-3 border-b border-book-border/30 pb-2">
                                <h4 className="font-serif font-bold text-lg text-book-text-main">{char.name}</h4>
                                <span className="text-xs bg-book-bg px-2 py-1 rounded text-book-text-sub">{char.identity}</span>
                            </div>
                            <div className="space-y-2 text-sm text-book-text-secondary">
                                <p className="line-clamp-2"><span className="font-bold text-book-text-muted">性格：</span>{char.personality}</p>
                                <p className="line-clamp-2"><span className="font-bold text-book-text-muted">目标：</span>{char.goal}</p>
                            </div>
                        </BookCard>
                    ))}
                </div>
            </div>
        )}
        
        {activeTab === 'outlines' && (
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 space-y-6">
                <div className="flex justify-between items-center">
                    <h3 className="font-serif font-bold text-lg text-book-text-main">部分大纲</h3>
                    <BookButton size="sm" onClick={async () => {
                        try {
                            // 默认生成逻辑：20章一个部分
                            await writerApi.generatePartOutlines(id!, blueprintData.total_chapters || 100, 20);
                            addToast('部分大纲生成任务已启动', 'success');
                            fetchPartProgress();
                        } catch (e) {
                            addToast('生成失败', 'error');
                        }
                    }}>
                        <Sparkles size={16} className="mr-1" /> 生成部分大纲
                    </BookButton>
                </div>

                {partLoading ? (
                  <div className="text-center py-20 text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30">
                    加载中...
                  </div>
                ) : partProgress?.parts?.length ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between text-sm text-book-text-muted">
                      <span>进度：{partProgress.completed_parts}/{partProgress.total_parts}</span>
                      <button
                        onClick={() => navigate(`/write/${id}`)}
                        className="text-book-primary hover:text-book-primary-light transition-colors font-bold"
                      >
                        前往写作台 →
                      </button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {partProgress.parts.map((p: any) => (
                        <BookCard key={p.part_number} className="p-5 hover:shadow-md transition-shadow">
                          <div className="flex items-start justify-between gap-3 mb-2">
                            <div className="min-w-0">
                              <div className="font-serif font-bold text-book-text-main truncate">
                                第{p.part_number}部分：{p.title}
                              </div>
                              <div className="text-xs text-book-text-muted mt-1">
                                章节 {p.start_chapter}–{p.end_chapter} · 状态 {p.generation_status} · {p.progress ?? 0}%
                              </div>
                            </div>
                            <span className="text-xs bg-book-bg px-2 py-1 rounded text-book-text-sub whitespace-nowrap">
                              {p.theme || '主题'}
                            </span>
                          </div>
                          <div className="text-sm text-book-text-secondary leading-relaxed line-clamp-4 whitespace-pre-wrap">
                            {p.summary}
                          </div>
                        </BookCard>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-20 text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30">
                      <Share size={48} className="mx-auto mb-4 opacity-50" />
                      <p>尚未生成部分大纲。生成后可在此查看进度与内容。</p>
                  </div>
                )}
            </div>
        )}
      </div>

      {/* Blueprint Refine Modal */}
      <Modal
        isOpen={isRefineModalOpen}
        onClose={() => setIsRefineModalOpen(false)}
        title="优化蓝图"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={() => setIsRefineModalOpen(false)}>关闭</BookButton>
            <BookButton
              variant="primary"
              onClick={handleRefineBlueprint}
              disabled={refining || !refineInstruction.trim()}
            >
              {refining ? '优化中...' : '开始优化'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
            说明：优化蓝图会重置已生成的章节大纲、章节内容以及向量库等后续数据。建议先导出/备份再执行。
          </div>

          <BookTextarea
            label="优化指令"
            value={refineInstruction}
            onChange={(e) => setRefineInstruction(e.target.value)}
            rows={6}
            placeholder="例如：把世界观从现代都市改为架空蒸汽朋克，并强化主角动机与成长线…"
          />

          <label className="flex items-center gap-2 text-sm text-book-text-main">
            <input
              type="checkbox"
              className="rounded border-book-border text-book-primary focus:ring-book-primary"
              checked={refineForce}
              onChange={(e) => setRefineForce(e.target.checked)}
            />
            <span className="font-bold">强制优化（存在后续数据时也继续）</span>
          </label>

          {refineResult && (
            <BookCard className="p-4">
              <div className="text-xs text-book-text-muted mb-2">AI 说明</div>
              <div className="text-sm text-book-text-main whitespace-pre-wrap leading-relaxed">
                {refineResult}
              </div>
            </BookCard>
          )}
        </div>
      </Modal>

      {/* Character Edit Modal */}
      <Modal
        isOpen={isCharModalOpen}
        onClose={() => setIsCharModalOpen(false)}
        title={editingCharIndex !== null ? "编辑角色" : "添加新角色"}
        footer={
            <div className="flex justify-end gap-2">
                <BookButton variant="ghost" onClick={() => setIsCharModalOpen(false)}>取消</BookButton>
                <BookButton variant="primary" onClick={handleSaveChar}>保存</BookButton>
            </div>
        }
      >
        <div className="space-y-4">
            <BookInput 
                label="姓名" 
                value={charForm.name} 
                onChange={e => setCharForm({...charForm, name: e.target.value})}
            />
            <BookInput 
                label="身份" 
                value={charForm.identity} 
                onChange={e => setCharForm({...charForm, identity: e.target.value})}
            />
            <BookTextarea 
                label="性格特征" 
                value={charForm.personality} 
                onChange={e => setCharForm({...charForm, personality: e.target.value})}
            />
            <BookTextarea 
                label="目标与动机" 
                value={charForm.goal} 
                onChange={e => setCharForm({...charForm, goal: e.target.value})}
            />
        </div>
      </Modal>
    </div>
  );
};
