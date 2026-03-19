import React from 'react';

type SettingsTabPanelProps = {
  header?: React.ReactNode;
  info?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
};

export const SettingsTabPanel: React.FC<SettingsTabPanelProps> = ({
  header,
  info,
  children,
  className = '',
  bodyClassName = '',
}) => {
  return (
    <div className={`flex min-h-0 min-w-0 flex-col gap-4 ${className}`}>
      {header ? <div className="shrink-0">{header}</div> : null}
      {info ? <div className="shrink-0">{info}</div> : null}
      <div className={`min-h-0 min-w-0 flex-1 ${bodyClassName}`}>{children}</div>
    </div>
  );
};
