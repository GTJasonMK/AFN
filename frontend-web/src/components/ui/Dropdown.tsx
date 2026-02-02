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
      setMenuPosition({
        top: rect.bottom + 4,
        left: rect.right,
      });
    }
  }, [isOpen]);

  const menuContent = isOpen && (
    <div
      ref={menuRef}
      className="fixed pointer-events-auto min-w-[8rem] bg-book-bg-paper border border-book-border rounded-lg shadow-xl py-1 animate-in fade-in zoom-in-95 duration-100"
      style={{
        top: menuPosition.top,
        right: window.innerWidth - menuPosition.left,
        zIndex: 9999,
      }}
    >
      {items.map((item, idx) => {
        if ('type' in item && item.type === 'divider') {
          return <div key={`divider-${idx}`} className="my-1 border-t border-book-border/50" />;
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
              w-full text-left px-3 py-2 text-xs flex items-center gap-2 whitespace-nowrap
              ${menuItem.danger
                ? 'text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20'
                : 'text-book-text-main hover:bg-book-bg'}
            `}
          >
            {menuItem.icon}
            {menuItem.label}
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
          onClick={(e) => {
            e.stopPropagation();
            setIsOpen(!isOpen);
          }}
          className="px-2 py-1 rounded-md text-xs text-book-text-muted hover:bg-book-bg hover:text-book-text-main transition-colors flex items-center gap-1"
        >
          {label}
          <ChevronDown size={12} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      ) : (
        <button
          ref={buttonRef}
          onClick={(e) => {
            e.stopPropagation();
            setIsOpen(!isOpen);
          }}
          className="p-1 rounded-md text-book-text-muted hover:bg-book-bg hover:text-book-text-main transition-colors"
        >
          <MoreVertical size={14} />
        </button>
      )}

      {isOpen && portalContainer ? createPortal(menuContent, portalContainer) : null}
    </div>
  );
};
