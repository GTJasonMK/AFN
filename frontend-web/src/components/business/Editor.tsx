import React, { useState, useEffect, useRef } from 'react';
import { BookButton } from '../ui/BookButton';
import { ChapterVersion } from '../../api/writer';
import { Save, RefreshCw, Maximize2, Minimize2, Check } from 'lucide-react';

interface EditorProps {
  content: string;
  versions?: ChapterVersion[];
  isSaving?: boolean;
  isGenerating?: boolean;
  onChange: (value: string) => void;
  onSave: () => void;
  onGenerate: () => void;
  onSelectVersion: (index: number) => void;
}

export const Editor: React.FC<EditorProps> = ({
  content,
  versions = [],
  isSaving,
  isGenerating,
  onChange,
  onSave,
  onGenerate,
  onSelectVersion
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isFocusMode, setIsFocusMode] = useState(false);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [content]);

  return (
    <div className={`flex-1 flex flex-col h-full bg-book-bg relative transition-all duration-500 ease-in-out ${isFocusMode ? 'z-50 fixed inset-0' : ''}`}>
      {/* Toolbar */}
      <div className={`
        h-14 border-b border-book-border/40 flex items-center justify-between px-6 
        bg-book-bg-paper/90 backdrop-blur-md sticky top-0 z-20 shadow-sm transition-all duration-300
        ${isFocusMode ? 'opacity-0 hover:opacity-100 -translate-y-full hover:translate-y-0' : ''}
      `}>
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar mask-gradient-right">
          {/* Version Tabs - Pill Style */}
          {versions.length > 0 && (
            <div className="flex items-center gap-1 bg-book-bg p-1 rounded-lg border border-book-border/50 shadow-inner">
              {versions.map((v, idx) => {
                const isSelected = content === v.content;
                const key = v.id ? `version-${String(v.id)}` : `version-idx-${idx}-${v.version_label || 'unknown'}`;
                return (
                  <button
                    key={key}
                    onClick={() => onSelectVersion(idx)}
                    className={`
                      px-3 py-1 text-xs font-medium rounded-md transition-all duration-300 relative overflow-hidden
                      ${isSelected 
                        ? 'bg-book-bg-paper text-book-primary shadow-sm border border-book-border/50 scale-105' 
                        : 'text-book-text-muted hover:text-book-text-main hover:bg-book-bg-paper/50'}
                    `}
                  >
                    <span className="relative z-10 flex items-center gap-1">
                      {v.version_label}
                      {isSelected && <Check size={10} className="stroke-[3]" />}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 pl-4 border-l border-book-border/30">
          <BookButton 
            variant="ghost" 
            size="sm"
            onClick={() => setIsFocusMode(!isFocusMode)}
            title={isFocusMode ? "退出专注 (Esc)" : "专注模式"}
            className="text-book-text-sub hover:text-book-primary"
          >
            {isFocusMode ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </BookButton>

          <div className="w-px h-4 bg-book-border mx-1" />

          <BookButton 
            variant="ghost" 
            size="sm" 
            onClick={onGenerate}
            disabled={isGenerating}
            className={`
              text-book-accent hover:text-book-accent hover:bg-book-accent/10 border border-transparent hover:border-book-accent/20
              ${isGenerating ? "animate-pulse cursor-wait" : ""}
            `}
          >
            <RefreshCw size={16} className={`mr-2 ${isGenerating ? "animate-spin" : ""}`} />
            {isGenerating ? "生成中..." : "AI 续写"}
          </BookButton>
          
          <BookButton 
            variant="primary" 
            size="sm" 
            onClick={onSave}
            disabled={isSaving}
            className="shadow-md hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0 transition-all"
          >
            <Save size={16} className="mr-2" />
            {isSaving ? "保存中..." : "保存"}
          </BookButton>
        </div>
      </div>

      {/* Editing Area - Paper Style */}
      <div className="flex-1 overflow-y-auto custom-scrollbar bg-book-bg scroll-smooth">
        <div className={`
          mx-auto my-8 bg-book-bg-paper shadow-book-card rounded-lg border border-book-border/20
          transition-all duration-700 ease-out min-h-[calc(100%-6rem)] relative
          ${isFocusMode ? 'max-w-4xl py-20 px-16 my-0 rounded-none border-y-0 min-h-full' : 'max-w-3xl py-16 px-12'}
        `}>
          {/* Paper Texture Overlay (Optional, subtle noise) */}
          <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[url('https://www.transparenttextures.com/patterns/cream-paper.png')] mix-blend-multiply" />

          <textarea
            ref={textareaRef}
            value={content}
            onChange={(e) => onChange(e.target.value)}
            className={`
              w-full h-full bg-transparent resize-none focus:outline-none 
              text-lg leading-loose text-book-text-main font-serif tracking-wide
              placeholder:text-book-text-muted/40 selection:bg-book-primary/20
              transition-all duration-300
            `}
            placeholder="在这里开始你的故事..."
            spellCheck={false}
            style={{ 
              minHeight: '60vh',
              textIndent: '2em',
              textAlign: 'justify'
            }}
          />
        </div>
        
        {!isFocusMode && <div className="h-16 flex items-center justify-center text-book-text-muted text-xs opacity-50">
          - 终 -
        </div>}
      </div>
    </div>
  );
};
