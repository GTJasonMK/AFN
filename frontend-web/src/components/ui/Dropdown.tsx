import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { MoreVertical, ChevronDown } from 'lucide-react';

type DropdownItem = {
  label: string;
  onClick: () => void;
  danger?: boolean;
  icon?: React.ReactNode;
} | {
  type: 'divider';
};

interface DropdownProps {
  items: DropdownItem[];
  label?: string;
}

export const Dropdown: React.FC<DropdownProps> = ({ items, label }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const portalContainer =
    typeof document !== 'undefined'
      ? document.getElementById('afn-portal-root') || document.body
      : null;

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        buttonRef.current && !buttonRef.current.contains(event.target as Node) &&
        menuRef.current && !menuRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (isOpen && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      const estimatedWidth = 240;
      const left = Math.max(12, Math.min(rect.right - estimatedWidth, window.innerWidth - estimatedWidth - 12));
      setMenuPosition({
        top: rect.bottom + 8,
        left,
      });
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return undefined;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsOpen(false);
    };
    const handleReposition = () => {
      if (!buttonRef.current) return;
      const rect = buttonRef.current.getBoundingClientRect();
      const estimatedWidth = 240;
      const left = Math.max(12, Math.min(rect.right - estimatedWidth, window.innerWidth - estimatedWidth - 12));
      setMenuPosition({
        top: rect.bottom + 8,
        left,
      });
    };

    window.addEventListener('keydown', handleEscape);
    window.addEventListener('resize', handleReposition);
    window.addEventListener('scroll', handleReposition, true);
    return () => {
      window.removeEventListener('keydown', handleEscape);
      window.removeEventListener('resize', handleReposition);
      window.removeEventListener('scroll', handleReposition, true);
    };
  }, [isOpen]);

  const menuContent = isOpen && (
    <div
      ref={menuRef}
      className="fixed pointer-events-auto min-w-[15rem] overflow-hidden rounded-[20px] border border-book-border/60 bg-book-bg-paper/94 p-1.5 shadow-[0_28px_68px_-36px_rgba(36,18,6,0.96)] backdrop-blur-xl"
      style={{
        top: menuPosition.top,
        left: menuPosition.left,
        zIndex: 9999,
      }}
    >
      {items.map((item, idx) => {
        if ('type' in item && item.type === 'divider') {
          return <div key={`divider-${idx}`} className="my-1.5 border-t border-book-border/45" />;
        }
        const menuItem = item as { label: string; onClick: () => void; danger?: boolean; icon?: React.ReactNode };
        return (
          <button
            key={`action-${menuItem.label}-${idx}`}
            onClick={(e) => {
              e.stopPropagation();
              menuItem.onClick();
              setIsOpen(false);
            }}
            className={`
              flex w-full items-center gap-3 rounded-2xl px-3.5 py-2.5 text-left text-sm transition-all duration-200
              ${menuItem.danger
                ? 'text-red-500 hover:bg-red-50/80 dark:hover:bg-red-900/20'
                : 'text-book-text-main hover:bg-book-bg'}
            `}
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-full border border-book-border/45 bg-book-bg/70 text-book-text-muted">
              {menuItem.icon}
            </span>
            <span className="flex-1 whitespace-nowrap">{menuItem.label}</span>
          </button>
        );
      })}
    </div>
  );

  return (
    <div className="relative">
      {label ? (
        <button
          ref={buttonRef}
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setIsOpen(!isOpen);
          }}
          aria-expanded={isOpen}
          aria-haspopup="menu"
          className="inline-flex items-center gap-1 rounded-full border border-book-border/45 bg-book-bg-paper/72 px-2.5 py-1.5 text-xs font-semibold text-book-text-muted transition-all duration-200 hover:border-book-primary/25 hover:text-book-primary"
        >
          {label}
          <ChevronDown size={12} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      ) : (
        <button
          ref={buttonRef}
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setIsOpen(!isOpen);
          }}
          aria-expanded={isOpen}
          aria-haspopup="menu"
          className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-book-border/45 bg-book-bg-paper/72 text-book-text-muted transition-all duration-200 hover:border-book-primary/25 hover:text-book-primary"
        >
          <MoreVertical size={14} />
        </button>
      )}

      {isOpen && portalContainer ? createPortal(menuContent, portalContainer) : null}
    </div>
  );
};
