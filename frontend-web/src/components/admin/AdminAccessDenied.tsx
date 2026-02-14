import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield } from 'lucide-react';
import { BookButton } from '../ui/BookButton';
import { BookCard } from '../ui/BookCard';

export const AdminAccessDenied: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="flex-1 p-6">
      <BookCard className="max-w-2xl mx-auto space-y-4">
        <div className="flex items-center gap-2 text-book-text-main">
          <Shield size={18} className="text-book-accent" />
          <h2 className="font-serif text-lg font-bold">无管理员权限</h2>
        </div>
        <p className="text-sm text-book-text-muted leading-relaxed">
          当前账号没有权限访问管理员页面。请使用拥有管理员权限的账号登录后重试（默认管理员为 desktop_user）。
        </p>
        <div className="flex justify-end">
          <BookButton variant="secondary" onClick={() => navigate('/')}>
            返回首页
          </BookButton>
        </div>
      </BookCard>
    </div>
  );
};
