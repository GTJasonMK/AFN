import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChapterList } from '../components/business/ChapterList';
import { Editor } from '../components/business/Editor';
import { AssistantPanel } from '../components/business/AssistantPanel';
import { OutlineEditModal } from '../components/business/OutlineEditModal';
import { BatchGenerateModal } from '../components/business/BatchGenerateModal';
import { writerApi, Chapter } from '../api/writer';
import { useSSE } from '../hooks/useSSE';
import { useToast } from '../components/feedback/Toast';
import { ArrowLeft } from 'lucide-react';

export const WritingDesk: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [currentChapter, setCurrentChapter] = useState<Chapter | null>(null);
  const [content, setContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [projectInfo, setProjectInfo] = useState<any>(null);

  // Modal States
  const [editingChapter, setEditingChapter] = useState<Chapter | null>(null);
  const [isOutlineModalOpen, setIsOutlineModalOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);

  useEffect(() => {
    if (id) {
      loadProjectData();
    }
  }, [id]);

  const loadProjectData = async () => {
    if (!id) return;
    try {
        const project = await writerApi.getProject(id);
        setChapters(project.chapters || []);
        
        setProjectInfo({
            title: project.title,
            summary: project.blueprint?.one_sentence_summary || "暂无概要",
            style: project.blueprint?.style || "自由创作"
        });

        // If no current chapter but we have chapters, select first
        if (!currentChapter && project.chapters && project.chapters.length > 0) {
            handleSelectChapter(project.chapters[0].chapter_number);
        }
    } catch (e) {
        console.error(e);
    }
  };

  const handleSelectChapter = async (chapterNumber: number) => {
    if (!id) return;
    try {
      const chapter = await writerApi.getChapter(id, chapterNumber);
      setCurrentChapter(chapter);
      
      if (chapter.selected_version_id && chapter.versions) {
        const selected = chapter.versions.find(v => v.id === chapter.selected_version_id);
        if (selected) setContent(selected.content);
      } else if (chapter.versions && chapter.versions.length > 0) {
        setContent(chapter.versions[0].content);
      } else {
        setContent('');
      }
    } catch (e) {
      console.error("Failed to load chapter", e);
    }
  };

  const handleCreateChapter = async () => {
    if (!id) return;
    const nextChapterNum = chapters.length > 0 
      ? Math.max(...chapters.map(c => c.chapter_number)) + 1 
      : 1;
    
    // Optimistic update
    const newChapterStub = {
      id: `temp-${Date.now()}`,
      project_id: id,
      chapter_number: nextChapterNum,
      title: `第${nextChapterNum}章`,
      status: 'pending'
    } as Chapter;
    
    setChapters([...chapters, newChapterStub]);
    
    try {
        await writerApi.createChapter(id, nextChapterNum);
        loadProjectData();
        handleSelectChapter(nextChapterNum);
    } catch (e) {
        console.error("Failed to create chapter", e);
    }
  };

  const handleSave = async () => {
    if (!id || !currentChapter) return;
    setIsSaving(true);
    try {
      await writerApi.updateChapter(id, currentChapter.chapter_number, content);
      await handleSelectChapter(currentChapter.chapter_number);
      addToast('保存成功', 'success');
    } catch (e) {
      console.error("Save failed", e);
      addToast('保存失败', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const { connect } = useSSE((event, data) => {
    if (event === 'progress' && data.stage === 'generating') {
       // Handle progress
    } else if (event === 'complete') {
       setIsGenerating(false);
       addToast('生成完成', 'success');
       if (id && currentChapter) handleSelectChapter(currentChapter.chapter_number);
    } else if (event === 'error') {
       setIsGenerating(false);
       addToast(data.message, 'error');
    }
  });

  const handleGenerate = async () => {
    if (!id || !currentChapter) return;
    setIsGenerating(true);
    await connect(`/writer/novels/${id}/chapters/generate-stream`, {
        chapter_number: currentChapter.chapter_number
    });
  };

  const handleVersionSelect = async (index: number) => {
    if (!id || !currentChapter || !currentChapter.versions) return;
    const version = currentChapter.versions[index];
    if (!version) return;
    
    setContent(version.content);
    await writerApi.selectVersion(id, currentChapter.chapter_number, index);
  };

  // Chapter Actions
  const handleEditOutline = (chapter: Chapter) => {
    setEditingChapter(chapter);
    setIsOutlineModalOpen(true);
  };

  const handleResetChapter = async (chapter: Chapter) => {
    if (!id) return;
    if (confirm(`确定要清空第 ${chapter.chapter_number} 章的内容吗？这将删除所有已生成的版本。`)) {
        try {
            await writerApi.resetChapter(id, chapter.chapter_number);
            addToast('章节已重置', 'success');
            loadProjectData();
            if (currentChapter?.chapter_number === chapter.chapter_number) {
                handleSelectChapter(chapter.chapter_number);
            }
        } catch (e) {
            addToast('操作失败', 'error');
        }
    }
  };

  const handleDeleteChapter = async (chapter: Chapter) => {
    if (!id) return;
    if (confirm(`确定要删除第 ${chapter.chapter_number} 章吗？此操作不可恢复。`)) {
        try {
            await writerApi.deleteChapters(id, [chapter.chapter_number]);
            addToast('章节已删除', 'success');
            loadProjectData();
            if (currentChapter?.chapter_number === chapter.chapter_number) {
                setCurrentChapter(null);
                setContent('');
            }
        } catch (e) {
            addToast('删除失败', 'error');
        }
    }
  };

  if (!id) return null;

  return (
    <div className="flex flex-col h-screen bg-book-bg">
      <div className="h-12 border-b border-book-border bg-book-bg-paper flex items-center px-4 justify-between shrink-0 z-30 shadow-sm">
        <button 
          onClick={() => navigate('/')}
          className="flex items-center text-book-text-sub hover:text-book-primary transition-colors text-sm font-medium"
        >
          <ArrowLeft size={16} className="mr-1" />
          返回列表
        </button>
        <div className="font-serif font-bold text-book-text-main text-base tracking-wide">
            {projectInfo?.title} · {currentChapter ? `第${currentChapter.chapter_number}章` : '写作台'}
        </div>
        <div className="w-20" />
      </div>

      <div className="flex-1 flex overflow-hidden">
        <ChapterList 
          chapters={chapters} 
          currentChapterNumber={currentChapter?.chapter_number}
          projectInfo={projectInfo}
          onSelectChapter={handleSelectChapter}
          onCreateChapter={handleCreateChapter}
          onEditOutline={handleEditOutline}
          onResetChapter={handleResetChapter}
          onDeleteChapter={handleDeleteChapter}
          onBatchGenerate={() => setIsBatchModalOpen(true)}
        />

        <div className="flex-1 min-w-0 bg-book-bg">
          <Editor 
            content={content}
            versions={currentChapter?.versions}
            isSaving={isSaving}
            isGenerating={isGenerating}
            onChange={setContent}
            onSave={handleSave}
            onGenerate={handleGenerate}
            onSelectVersion={handleVersionSelect}
          />
        </div>

        <AssistantPanel 
            projectId={id}
            chapterNumber={currentChapter?.chapter_number}
            summary={currentChapter?.summary}
            outline={currentChapter ? chapters.find(c => c.chapter_number === currentChapter.chapter_number)?.summary : undefined} // Pass outline from list data
        />
      </div>

      {/* Modals */}
      <OutlineEditModal 
        isOpen={isOutlineModalOpen}
        onClose={() => setIsOutlineModalOpen(false)}
        chapter={editingChapter}
        projectId={id}
        onSuccess={loadProjectData}
      />

      <BatchGenerateModal
        isOpen={isBatchModalOpen}
        onClose={() => setIsBatchModalOpen(false)}
        projectId={id}
        onSuccess={loadProjectData}
      />
    </div>
  );
};
