import React from 'react';
import { BookCard } from '../ui/BookCard';
import { User } from 'lucide-react';

interface BlueprintCardProps {
  title?: string;
  summary?: string;
  style?: string;
  progress?: { current: number; total: number };
  portraitUrl?: string | null;
  portraitName?: string | null;
}

export const BlueprintCard: React.FC<BlueprintCardProps> = ({ 
  title = "小说项目", 
  summary = "暂无概要", 
  style = "未设定",
  progress,
  portraitUrl,
  portraitName,
}) => {
  return (
    <div className="relative group perspective-1000 h-40 w-full cursor-pointer">
      <div className="relative w-full h-full transition-all duration-500 transform-style-3d group-hover:rotate-y-180">
        {/* Front Face */}
        <div className="absolute inset-0 backface-hidden">
          <BookCard className="h-full flex flex-col justify-between bg-gradient-to-br from-book-primary/10 to-book-bg-paper border-book-primary/20">
            <div>
              <div className="flex justify-between items-start mb-2">
                <span className="text-sm font-bold text-book-text-main truncate max-w-[140px]">
                  {title}
                </span>
                <span className="text-xs font-bold text-book-primary px-2 py-0.5 rounded-full bg-book-primary/10 border border-book-primary/20">
                  {style}
                </span>
              </div>
              <p className="text-xs text-book-text-sub line-clamp-3 leading-relaxed">
                {summary}
              </p>
            </div>
            
            {progress && (
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-book-text-muted">
                  <span>创作进度</span>
                  <span>{progress.current}/{progress.total} 章</span>
                </div>
                <div className="h-1.5 w-full bg-book-border/30 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-book-primary transition-all duration-500"
                    style={{ width: `${(progress.current / Math.max(progress.total, 1)) * 100}%` }}
                  />
                </div>
              </div>
            )}
          </BookCard>
        </div>

        {/* Back Face */}
        <div className="absolute inset-0 h-full w-full backface-hidden rotate-y-180">
          <BookCard className="h-full bg-book-bg-paper border-book-border text-center overflow-hidden relative">
            {portraitUrl ? (
              <>
                <img
                  src={portraitUrl}
                  alt={portraitName || '主角立绘'}
                  className="absolute inset-0 w-full h-full object-cover"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/10 to-transparent" />
                <div className="absolute bottom-0 left-0 right-0 p-3 text-left">
                  <div className="text-sm font-bold text-white drop-shadow">
                    {portraitName ? `主角：${portraitName}` : '主角立绘'}
                  </div>
                  <div className="text-xs text-white/80 mt-0.5 drop-shadow">
                    点击打开主角档案
                  </div>
                </div>
              </>
            ) : (
              <div className="h-full flex flex-col items-center justify-center">
                <div className="w-12 h-12 rounded-full bg-book-bg flex items-center justify-center mb-2 text-book-text-sub">
                  <User size={24} />
                </div>
                <span className="text-sm font-bold text-book-text-main">主角档案</span>
                <span className="text-xs text-book-text-muted mt-1">点击查看详情</span>
              </div>
            )}
          </BookCard>
        </div>
      </div>
    </div>
  );
};
