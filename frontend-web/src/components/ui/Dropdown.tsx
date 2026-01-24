import React, { useState, useRef, useEffect } from 'react';
import { MoreVertical } from 'lucide-react';

interface DropdownProps {
  items: {
    label: string;
    onClick: () => void;
    danger?: boolean;
    icon?: React.ReactNode;
  }[];
}

export const Dropdown: React.FC<DropdownProps> = ({ items }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button 
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        className="p-1 rounded-md text-book-text-muted hover:bg-book-bg hover:text-book-text-main transition-colors"
      >
        <MoreVertical size={14} />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-1 w-32 bg-book-bg-paper border border-book-border rounded-lg shadow-lg z-50 py-1 animate-in fade-in zoom-in-95 duration-100">
          {items.map((item, idx) => (
            <button
              key={idx}
              onClick={(e) => {
                e.stopPropagation();
                item.onClick();
                setIsOpen(false);
              }}
              className={`
                w-full text-left px-3 py-2 text-xs flex items-center gap-2
                ${item.danger 
                  ? 'text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20' 
                  : 'text-book-text-main hover:bg-book-bg'}
              `}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};