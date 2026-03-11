import React from 'react';
import { Map as MapIcon, Users, FileText, Share, Link2, type LucideIcon } from 'lucide-react';

export type NovelDetailTab = 'overview' | 'world' | 'characters' | 'relationships' | 'outlines' | 'chapters';

export type NovelDetailTabItem = {
  id: NovelDetailTab;
  label: string;
  description: string;
  icon: LucideIcon;
};

export const NOVEL_DETAIL_TAB_ITEMS: readonly NovelDetailTabItem[] = [
  { id: 'overview', label: '概览', description: '总览作品定位、风格和全局摘要。', icon: FileText },
  { id: 'world', label: '世界观', description: '整理设定、规则与场景基础。', icon: MapIcon },
  { id: 'characters', label: '角色', description: '维护角色档案、动机与身份。', icon: Users },
  { id: 'relationships', label: '关系', description: '梳理人物关系网和冲突线。', icon: Link2 },
  { id: 'outlines', label: '章节大纲', description: '推进章节和分部结构。', icon: Share },
  { id: 'chapters', label: '已生成章节', description: '查看已完成正文与导出入口。', icon: FileText },
];

export const NovelDetailTabBar: React.FC<{
  activeTab: NovelDetailTab;
  onChange: (nextTab: NovelDetailTab) => void;
}> = ({ activeTab, onChange }) => {
  return (
    <aside className="xl:sticky xl:top-4 xl:self-start">
      <div className="dramatic-surface rounded-[28px] p-3">
        <div className="relative z-[1]">
          <div className="hidden px-2 pb-3 xl:block">
            <div className="eyebrow">Story Sections</div>
            <p className="mt-3 text-sm leading-relaxed text-book-text-sub">
              把蓝图拆成明确的工作区，避免所有信息堆进一个大页面。
            </p>
          </div>

          <div className="no-scrollbar flex gap-2 overflow-x-auto xl:flex-col xl:overflow-visible">
            {NOVEL_DETAIL_TAB_ITEMS.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => onChange(tab.id)}
                  className={`
                    min-w-[11rem] rounded-[22px] border px-4 py-3 text-left transition-all duration-300 xl:min-w-0
                    ${isActive
                      ? 'border-book-primary/35 bg-book-primary text-white shadow-[0_24px_48px_-30px_rgba(87,44,17,0.96)]'
                      : 'border-book-border/50 bg-book-bg-paper/72 text-book-text-main hover:-translate-y-0.5 hover:border-book-primary/25 hover:text-book-primary'}
                  `}
                >
                  <div className="flex items-center gap-2 text-sm font-bold">
                    <Icon size={16} />
                    {tab.label}
                  </div>
                  <div className={`mt-2 text-xs leading-relaxed ${isActive ? 'text-white/82' : 'text-book-text-muted'}`}>
                    {tab.description}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </aside>
  );
};
