import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, BarChart3, FolderKanban, Settings2, Users } from 'lucide-react';
import { BookButton } from '../ui/BookButton';

type AdminTabKey = 'overview' | 'users' | 'projects' | 'configs';

interface AdminPanelHeaderProps {
  current: AdminTabKey;
  title: string;
  description: string;
  onRefresh?: () => void;
  refreshing?: boolean;
  extraActions?: React.ReactNode;
}

const tabs: Array<{ key: AdminTabKey; to: string; label: string; icon: React.ReactNode }> = [
  { key: 'overview', to: '/admin/overview', label: '总览', icon: <BarChart3 size={14} /> },
  { key: 'users', to: '/admin/users', label: '用户', icon: <Users size={14} /> },
  { key: 'projects', to: '/admin/projects', label: '项目', icon: <FolderKanban size={14} /> },
  { key: 'configs', to: '/admin/configs', label: '配置', icon: <Settings2 size={14} /> },
];

export const AdminPanelHeader: React.FC<AdminPanelHeaderProps> = ({
  current,
  title,
  description,
  onRefresh,
  refreshing = false,
  extraActions,
}) => {
  const navigate = useNavigate();

  return (
    <div className="dramatic-surface rounded-[30px] p-5 sm:p-6">
      <div className="relative z-[1] space-y-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="eyebrow">Admin Control</div>
            <div className="flex flex-wrap items-center gap-3">
              <BookButton variant="ghost" size="sm" onClick={() => navigate('/')}>
                <ArrowLeft size={14} />
                返回首页
              </BookButton>
            </div>
            <div>
              <h1 className="font-serif text-3xl font-bold text-book-text-main sm:text-4xl">{title}</h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-book-text-sub">{description}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {extraActions}
            {onRefresh ? (
              <BookButton variant="secondary" size="sm" onClick={onRefresh} disabled={refreshing}>
                {refreshing ? '刷新中…' : '刷新数据'}
              </BookButton>
            ) : null}
          </div>
        </div>

        <div className="inline-flex flex-wrap gap-2 rounded-[22px] border border-book-border/50 bg-book-bg-paper/72 p-2">
          {tabs.map((tab) => (
            <Link
              key={tab.key}
              to={tab.to}
              className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-all ${
                tab.key === current
                  ? 'bg-book-primary text-white shadow-[0_18px_38px_-24px_rgba(87,44,17,0.96)]'
                  : 'text-book-text-sub hover:bg-book-bg hover:text-book-text-main'
              }`}
            >
              {tab.icon}
              {tab.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};
