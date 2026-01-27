import React, { useEffect, useMemo, useState } from 'react';
import { Chapter } from '../../api/writer';
import { Plus, Search, FileText, CheckCircle2, CircleDashed, Edit3, Trash2, RefreshCw, Sparkles } from 'lucide-react';
import { BlueprintCard } from './BlueprintCard';
import { Dropdown } from '../ui/Dropdown';
import { novelsApi } from '../../api/novels';
import { protagonistApi } from '../../api/protagonist';
import { API_BASE_URL } from '../../api/client';

interface ChapterListProps {
  chapters: Chapter[];
  projectId?: string;
  draftRevision?: number;
  currentChapterNumber?: number;
  projectInfo?: {
    title: string;
    summary: string;
    style: string;
  };
  onSelectChapter: (chapterNumber: number) => void;
  onCreateChapter: () => void;
  onOpenProtagonistProfiles?: () => void;
  // 新增操作回调
  onEditOutline: (chapter: Chapter) => void;
  onRegenerateOutline?: (chapter: Chapter) => void;
  onResetChapter: (chapter: Chapter) => void;
  onDeleteChapter: (chapter: Chapter) => void;
  onBatchGenerate: () => void;
}

export const ChapterList: React.FC<ChapterListProps> = ({
  chapters,
  projectId,
  draftRevision,
  currentChapterNumber,
  projectInfo,
  onSelectChapter,
  onCreateChapter,
  onOpenProtagonistProfiles,
  onEditOutline,
  onRegenerateOutline,
  onResetChapter,
  onDeleteChapter,
	onBatchGenerate,
	}) => {
	  const [searchTerm, setSearchTerm] = useState('');
    const [blueprintPortrait, setBlueprintPortrait] = useState<{ name: string | null; url: string } | null>(null);
	  
	  const sortedChapters = useMemo(() => {
	    return [...chapters].sort((a, b) => a.chapter_number - b.chapter_number);
	  }, [chapters]);

	  // 本地草稿标记：由 WritingDesk 触发的 revision 变化驱动刷新（避免每次输入都扫描 localStorage）
	  const draftSet = useMemo(() => {
	    const set = new Set<number>();
	    // draftRevision 仅用于触发刷新（草稿写入由 WritingDesk 驱动）
	    const _revision = typeof draftRevision === 'number' ? draftRevision : 0;
	    if (_revision < 0) return set;
	    if (!projectId) return set;
	    for (const c of sortedChapters) {
	      const key = `afn:writing_draft:${projectId}:${c.chapter_number}`;
	      try {
	        if (localStorage.getItem(key)) set.add(c.chapter_number);
      } catch {
        break;
      }
    }
    return set;
  }, [draftRevision, projectId, sortedChapters]);

  const toFullImageUrl = (url: string) => {
    const raw = String(url || '').trim();
    if (!raw) return '';
    if (raw.startsWith('http')) return raw;
    const baseUrl = API_BASE_URL.replace(/\/api$/, '');
    return `${baseUrl}${raw}`;
  };

  useEffect(() => {
    let cancelled = false;
    const fetchPortrait = async () => {
      if (!projectId) {
        setBlueprintPortrait(null);
        return;
      }
      try {
        const [profilesRes, portraitsRes] = await Promise.allSettled([
          protagonistApi.listProfiles(projectId),
          novelsApi.getPortraits(projectId),
        ]);
        const profiles = profilesRes.status === 'fulfilled' ? profilesRes.value : [];
        const portraits = portraitsRes.status === 'fulfilled' ? portraitsRes.value : [];

        const protagonistName = (() => {
          if (!profiles || profiles.length === 0) return null;
          const sorted = [...profiles].sort((a, b) => {
            const ta = Date.parse(a.created_at || '') || 0;
            const tb = Date.parse(b.created_at || '') || 0;
            return ta - tb;
          });
          const name = String(sorted[0]?.character_name || '').trim();
          return name || null;
        })();

        const byName = (name: string) => portraits.filter((p) => String(p.character_name || '').trim() === name);
        const pickPortrait = () => {
          if (protagonistName) {
            const list = byName(protagonistName);
            const active = list.find((p) => p.is_active && p.image_url);
            if (active) return active;
            const any = list.find((p) => p.image_url);
            if (any) return any;
          }
          const activeAny = portraits.find((p) => p.is_active && p.image_url);
          if (activeAny) return activeAny;
          const any = portraits.find((p) => p.image_url);
          return any || null;
        };

        const picked = pickPortrait();
        const url = picked?.image_url ? toFullImageUrl(picked.image_url) : '';
        const name = String(picked?.character_name || protagonistName || '').trim() || null;

        if (!cancelled) {
          setBlueprintPortrait(url ? { url, name } : null);
        }
      } catch (e) {
        console.error(e);
        if (!cancelled) setBlueprintPortrait(null);
      }
    };

    fetchPortrait();
    return () => {
      cancelled = true;
    };
  }, [projectId]);
  
  const filteredChapters = sortedChapters.filter(c => 
    c.title.includes(searchTerm) || 
    `第${c.chapter_number}章`.includes(searchTerm)
  );

  const completedCount = chapters.filter(c => c.generation_status === 'successful' || c.generation_status === 'completed').length;

  return (
    <div className="h-full flex flex-col bg-book-bg-paper border-r border-book-border/60 w-full transition-colors duration-300 shadow-sm relative z-20">
      <div className="p-4 space-y-4 bg-gradient-to-b from-book-bg-paper to-book-bg-paper/95">
        {/* Blueprint Card */}
        <div
          className="transform transition-transform hover:scale-[1.02] duration-300"
          onClick={() => onOpenProtagonistProfiles && onOpenProtagonistProfiles()}
          title="主角档案"
        >
          <BlueprintCard
            title={projectInfo?.title}
            summary={projectInfo?.summary}
            style={projectInfo?.style}
            progress={{ current: completedCount, total: Math.max(chapters.length, 10) }}
            portraitUrl={blueprintPortrait?.url || null}
            portraitName={blueprintPortrait?.name || null}
          />
        </div>

        {/* Action Bar & Search */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-serif font-bold text-sm text-book-text-main flex items-center gap-2">
              <span className="w-1 h-4 bg-book-primary rounded-full shadow-sm"/>
              章节列表
            </h3>
            <div className="flex gap-1">
              <button 
                onClick={onBatchGenerate}
                className="p-1.5 rounded-md hover:bg-book-bg text-book-text-sub hover:text-book-primary transition-all duration-200"
                title="批量生成大纲"
              >
                <RefreshCw size={16} />
              </button>
              <button 
                onClick={onCreateChapter}
                className="p-1.5 rounded-md hover:bg-book-bg text-book-text-sub hover:text-book-primary transition-all duration-200"
                title="新增章节"
              >
                <Plus size={16} />
              </button>
            </div>
          </div>

          <div className="relative group">
            <input
              type="text"
              placeholder="搜索..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-book-bg rounded-md border border-book-border/50 focus:border-book-primary/50 focus:ring-2 focus:ring-book-primary/10 outline-none transition-all placeholder:text-book-text-muted text-book-text-main"
            />
            <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-book-text-muted group-focus-within:text-book-primary transition-colors" />
          </div>
        </div>
      </div>
      
      {/* List */}
      <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-1.5 custom-scrollbar">
        {filteredChapters.map((chapter) => {
          const isActive = currentChapterNumber === chapter.chapter_number;
          const isCompleted = chapter.generation_status === 'successful' || chapter.generation_status === 'completed';
          const isGenerating = ['generating', 'evaluating', 'selecting', 'waiting_for_confirm'].includes(chapter.generation_status);
          const hasDraft = draftSet.has(chapter.chapter_number);

          return (
            <div
              key={chapter.chapter_number}
              onClick={() => onSelectChapter(chapter.chapter_number)}
              className={`
                relative flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-300 group
                border border-transparent pr-1
                ${isActive 
                  ? 'bg-book-bg shadow-sm border-book-border/40 translate-x-1' 
                  : 'hover:bg-book-bg/60 hover:border-book-border/20 hover:translate-x-0.5'}
              `}
            >
              {/* Active Indicator */}
              {isActive && (
                <div className="absolute left-0 top-2 bottom-2 w-0.5 bg-book-primary rounded-r-full shadow-[0_0_8px_rgb(var(--color-primary)_/_0.4)]" />
              )}

              {/* Status Icon */}
              <div className="flex-shrink-0 pt-0.5">
                {isCompleted ? (
                  <CheckCircle2 size={14} className="text-green-500/80" />
                ) : isGenerating ? (
                  <div className="w-3.5 h-3.5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
                ) : (
                  <CircleDashed size={14} className="text-book-border" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-baseline justify-between">
                  <span className={`text-sm font-medium truncate transition-colors ${isActive ? 'text-book-primary' : 'text-book-text-main group-hover:text-book-primary/80'}`}>
                    第{chapter.chapter_number}章{hasDraft ? <span className="ml-1 text-book-accent" title="存在本地草稿">*</span> : null}
                  </span>
                  {chapter.word_count ? (
                    <span className="text-[10px] text-book-text-muted opacity-60 font-mono">{chapter.word_count}</span>
                  ) : null}
                </div>
                <div className={`text-xs truncate mt-0.5 transition-colors ${isActive ? 'text-book-text-sub' : 'text-book-text-muted group-hover:text-book-text-sub'}`}>
                  {chapter.title || "未命名章节"}
                </div>
              </div>
              
              <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                <Dropdown items={[
                  { label: "编辑大纲", icon: <Edit3 size={12}/>, onClick: () => onEditOutline(chapter) },
                  ...(onRegenerateOutline ? [{ label: "重生成大纲", icon: <Sparkles size={12} />, onClick: () => onRegenerateOutline(chapter), danger: true }] : []),
                  { label: "重置内容", icon: <RefreshCw size={12}/>, onClick: () => onResetChapter(chapter), danger: true },
                  { label: "删除章节", icon: <Trash2 size={12}/>, onClick: () => onDeleteChapter(chapter), danger: true },
                ]} />
              </div>
            </div>
          );
        })}
        
        {filteredChapters.length === 0 && (
          <div className="text-center py-12 flex flex-col items-center">
            <div className="w-12 h-12 bg-book-bg rounded-full flex items-center justify-center mb-3">
              <FileText size={24} className="text-book-text-muted/40" />
            </div>
            <p className="text-xs text-book-text-muted">
              {searchTerm ? '无匹配结果' : '暂无章节'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
