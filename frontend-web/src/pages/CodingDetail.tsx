import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { codingApi } from '../api/coding';
import { DirectoryTree } from '../components/coding/DirectoryTree';
import { Editor } from '../components/business/Editor'; // Reuse Editor for now
import { ArrowLeft, Layout, Code } from 'lucide-react';
import { BookButton } from '../components/ui/BookButton';
import { useSSE } from '../hooks/useSSE';
import { useToast } from '../components/feedback/Toast';
import { Modal } from '../components/ui/Modal';
import { BookCard } from '../components/ui/BookCard';

export const CodingDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  const [project, setProject] = useState<any>(null);
  const [treeData, setTreeData] = useState<any>(null);
  const [currentFile, setCurrentFile] = useState<any>(null);
  const [content, setContent] = useState('');
  const [versions, setVersions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isBlueprintModalOpen, setIsBlueprintModalOpen] = useState(false);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
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
  };

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
    await connect(codingApi.generateFilePromptStream(id, currentFile.id), {});
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

  const { connect } = useSSE((event, data) => {
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

  if (loading) return <div className="flex h-screen items-center justify-center">加载中...</div>;

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
            <BookButton size="sm" variant="ghost" onClick={() => setIsBlueprintModalOpen(true)}>
              查看蓝图
            </BookButton>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
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

      <Modal
        isOpen={isBlueprintModalOpen}
        onClose={() => setIsBlueprintModalOpen(false)}
        title="架构蓝图"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={() => setIsBlueprintModalOpen(false)}>关闭</BookButton>
            <BookButton variant="primary" onClick={handleGenerateBlueprint}>
              {project?.blueprint ? '重新生成' : '生成蓝图'}
            </BookButton>
          </div>
        }
      >
        {project?.blueprint ? (
          <div className="space-y-4">
            <div className="text-sm text-book-text-muted">
              {project.blueprint.one_sentence_summary || '暂无一句话概要'}
            </div>
            <BookCard variant="flat" className="p-4 bg-book-bg/40 border-book-border/40">
              <div className="text-xs text-book-text-muted mb-2">架构概述</div>
              <div className="text-sm text-book-text-main whitespace-pre-wrap leading-relaxed">
                {project.blueprint.architecture_synopsis || '暂无内容'}
              </div>
            </BookCard>
            {project.blueprint.tech_stack && (
              <BookCard variant="flat" className="p-4 bg-book-bg/40 border-book-border/40">
                <div className="text-xs text-book-text-muted mb-2">技术栈</div>
                <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed">
                  {JSON.stringify(project.blueprint.tech_stack, null, 2)}
                </pre>
              </BookCard>
            )}
          </div>
        ) : (
          <div className="text-sm text-book-text-muted">
            当前项目尚未生成蓝图。完成“需求分析”对话后可生成，或直接点击下方“生成蓝图”。
          </div>
        )}
      </Modal>
    </div>
  );
};
