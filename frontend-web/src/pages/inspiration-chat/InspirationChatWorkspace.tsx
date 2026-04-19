import React from 'react';
import { SegmentPager } from '../../components/layout/AppViewport';
import { WORKSPACE_PANE_ITEMS, WorkspacePane } from './shared';

type InspirationChatWorkspaceProps = {
  isElectronRuntime: boolean;
  workspacePane: WorkspacePane;
  onWorkspacePaneChange: (pane: WorkspacePane) => void;
  guidePanel: React.ReactNode;
  conversationPanel: React.ReactNode;
};

export const InspirationChatWorkspace: React.FC<InspirationChatWorkspaceProps> = ({
  isElectronRuntime,
  workspacePane,
  onWorkspacePaneChange,
  guidePanel,
  conversationPanel,
}) => {
  return (
    <>
      <div className={isElectronRuntime ? 'hidden' : 'xl:hidden'}>
        <div className="relative overflow-hidden rounded-xl border border-book-border/55 bg-book-bg-paper/95 px-4 py-4 shadow-surface">
          <div className="relative z-[1]">
            <SegmentPager
              items={WORKSPACE_PANE_ITEMS}
              value={workspacePane}
              onChange={(next) => onWorkspacePaneChange(next as WorkspacePane)}
            />
          </div>
        </div>
      </div>

      <section
        className={`grid min-h-0 flex-1 gap-4 ${
          isElectronRuntime ? 'contents' : 'xl:grid-cols-[320px_minmax(0,1fr)]'
        }`}
      >
        <div
          className={
            isElectronRuntime
              ? 'col-start-1 row-start-2 flex min-h-0 h-full flex-col'
              : `${workspacePane === 'guide' ? 'min-h-0' : 'hidden'} xl:block`
          }
        >
          <div className={isElectronRuntime ? 'flex min-h-0 h-full flex-col pr-2' : ''}>
            {guidePanel}
          </div>
        </div>

        <div
          className={
            isElectronRuntime
              ? 'col-start-2 row-start-1 row-span-2 min-h-0'
              : `${workspacePane === 'conversation' ? 'min-h-0' : 'hidden'} xl:block`
          }
        >
          {conversationPanel}
        </div>
      </section>
    </>
  );
};
