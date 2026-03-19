import React from 'react';

interface SettingsInfoBoxProps {
  children: React.ReactNode;
}

export const SettingsInfoBox: React.FC<SettingsInfoBoxProps> = ({ children }) => {
  return (
    <div className="text-xs text-book-text-sub bg-book-bg-paper/70 p-3 rounded-2xl border border-book-border/50 leading-relaxed">
      {children}
    </div>
  );
};
