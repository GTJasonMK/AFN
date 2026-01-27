import React from 'react';

interface SettingsInfoBoxProps {
  children: React.ReactNode;
}

export const SettingsInfoBox: React.FC<SettingsInfoBoxProps> = ({ children }) => {
  return (
    <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 leading-relaxed">
      {children}
    </div>
  );
};

