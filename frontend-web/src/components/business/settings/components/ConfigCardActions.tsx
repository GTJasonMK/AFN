import React from 'react';
import { FlaskConical, Pencil, Trash2 } from 'lucide-react';
import { BookButton } from '../../../ui/BookButton';

interface ConfigCardActionsProps {
  isActive: boolean;
  isTesting: boolean;
  onActivate?: () => void;
  onTest: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export const ConfigCardActions: React.FC<ConfigCardActionsProps> = ({
  isActive,
  isTesting,
  onActivate,
  onTest,
  onEdit,
  onDelete,
}) => {
  return (
    <div className="flex flex-col gap-2 shrink-0">
      {!isActive && onActivate && (
        <BookButton variant="primary" size="sm" onClick={onActivate}>
          设为激活
        </BookButton>
      )}
      <BookButton variant="ghost" size="sm" onClick={onTest} disabled={isTesting}>
        <FlaskConical size={14} className={`mr-1 ${isTesting ? 'animate-pulse' : ''}`} />
        {isTesting ? '测试中…' : '测试'}
      </BookButton>
      <BookButton variant="ghost" size="sm" onClick={onEdit}>
        <Pencil size={14} className="mr-1" />
        编辑
      </BookButton>
      <BookButton variant="ghost" size="sm" onClick={onDelete} className="text-book-accent">
        <Trash2 size={14} className="mr-1" />
        删除
      </BookButton>
    </div>
  );
};

