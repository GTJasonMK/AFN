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
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <BookButton variant="ghost" size="sm" onClick={() => navigate('/')}>
            <ArrowLeft size={14} />
            返回首页
          </BookButton>
          <div>
            <h1 className="font-serif text-xl font-bold text-book-text-main">{title}</h1>
            <p className="text-xs text-book-text-muted mt-1">{description}</p>
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

      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <Link
            key={tab.key}
            to={tab.to}
            className={`inline-flex items-center gap-1 px-3 py-2 rounded-lg border text-xs font-bold transition-all ${
              tab.key === current
                ? 'bg-book-primary/10 border-book-primary/30 text-book-primary'
                : 'bg-book-bg-paper border-book-border/50 text-book-text-muted hover:text-book-text-main hover:border-book-primary/20'
            }`}
          >
            {tab.icon}
            {tab.label}
          </Link>
        ))}
      </div>
    </div>
  );
};
