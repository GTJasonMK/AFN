import React from 'react';
import { Map as MapIcon, Users, FileText, Share, Link2, type LucideIcon } from 'lucide-react';

export type NovelDetailTab = 'overview' | 'world' | 'characters' | 'relationships' | 'outlines' | 'chapters';

type TabItem = {
  id: NovelDetailTab;
  label: string;
  icon: LucideIcon;
};

const TABS: readonly TabItem[] = [
  { id: 'overview', label: '概览', icon: FileText },
  { id: 'world', label: '世界观', icon: MapIcon },
  { id: 'characters', label: '角色', icon: Users },
  { id: 'relationships', label: '关系', icon: Link2 },
  { id: 'outlines', label: '章节大纲', icon: Share },
  { id: 'chapters', label: '已生成章节', icon: FileText },
];

export const NovelDetailTabBar: React.FC<{
  activeTab: NovelDetailTab;
  onChange: (nextTab: NovelDetailTab) => void;
}> = ({ activeTab, onChange }) => {
  return (
    <div className="border-b border-book-border/40 bg-book-bg-paper px-8">
      <div className="flex gap-8">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onChange(tab.id)}
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
  );
};
