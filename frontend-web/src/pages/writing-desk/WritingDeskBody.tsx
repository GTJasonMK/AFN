import React from 'react';
import { SegmentPager } from '../../components/layout/AppViewport';
import { WRITING_DESK_COMPACT_PANE_ITEMS, type WritingDeskCompactPane } from './shared';

type WritingDeskBodyProps = {
  isCompactLayout: boolean;
  compactPane: WritingDeskCompactPane;
  onCompactPaneChange: (pane: WritingDeskCompactPane) => void;
  sidebarPane: React.ReactNode;
  editorWorkspace: React.ReactNode;
  assistantPane: React.ReactNode;
};

export const WritingDeskBody: React.FC<WritingDeskBodyProps> = ({
  isCompactLayout,
  compactPane,
  onCompactPaneChange,
  sidebarPane,
  editorWorkspace,
  assistantPane,
}) => {
  return (
    <>
      {isCompactLayout ? (
        <div className="relative overflow-hidden rounded-xl border border-book-border/55 bg-book-bg-paper/95 px-4 py-4 shadow-surface">
          <div className="relative z-[1]">
            <SegmentPager
              items={WRITING_DESK_COMPACT_PANE_ITEMS}
              value={compactPane}
              onChange={(next) => onCompactPaneChange(next as WritingDeskCompactPane)}
            />
          </div>
        </div>
      ) : null}

      <div className="relative min-h-0 flex-1 overflow-hidden rounded-2xl border border-book-border/55 bg-book-bg-paper/95 shadow-surface-strong">
        <div className="relative z-[1] flex h-full min-h-0">
          {isCompactLayout ? (
            <>
              {compactPane === 'chapters' ? sidebarPane : null}
              {compactPane === 'editor' ? (
                <div className="min-w-0 flex-1 bg-book-bg">
                  {editorWorkspace}
                </div>
              ) : null}
              {compactPane === 'assistant' ? assistantPane : null}
            </>
          ) : (
            <>
              {sidebarPane}
              <div className="min-w-0 flex-1 bg-book-bg">
                {editorWorkspace}
              </div>
              {assistantPane}
            </>
          )}
        </div>
      </div>
    </>
  );
};
