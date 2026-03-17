import React, { type ComponentProps, type ReactNode } from 'react';
import { NovelDetailHeader } from './NovelDetailHeader';
import { NovelDetailTabBar, type NovelDetailTab } from './NovelDetailTabBar';
import { NovelDetailTabContent } from './NovelDetailTabContent';
import { TitleAndBlueprintModals } from './TitleAndBlueprintModals';
import { CharacterAndRelationshipModals } from './CharacterAndRelationshipModals';
import { NovelDetailLazyBusinessModals } from './NovelDetailLazyBusinessModals';
import { LatestPartOutlineModals } from './LatestPartOutlineModals';
import { LatestChapterOutlineModals } from './LatestChapterOutlineModals';
import { AppViewportFrame, AppViewportShell, SegmentPager } from '../../components/layout/AppViewport';

type NovelDetailPageLayoutProps = {
  headerProps: ComponentProps<typeof NovelDetailHeader>;
  activeTab: NovelDetailTab;
  onTabChange: (next: NovelDetailTab) => void;
  tabProps: ComponentProps<typeof NovelDetailTabContent>['tabProps'];
  optionalPromptModal: ReactNode;
  titleAndBlueprintModalProps: ComponentProps<typeof TitleAndBlueprintModals>;
  characterAndRelationshipModalProps: ComponentProps<typeof CharacterAndRelationshipModals>;
  projectId: string;
  onProjectRefresh: () => void | Promise<void>;
  lazyBusinessModalProps: Omit<
    ComponentProps<typeof NovelDetailLazyBusinessModals>,
    'projectId' | 'onProjectRefresh'
  >;
  latestPartOutlineModalProps: ComponentProps<typeof LatestPartOutlineModals>;
  latestChapterOutlineModalProps: ComponentProps<typeof LatestChapterOutlineModals>;
};

export const NovelDetailPageLayout: React.FC<NovelDetailPageLayoutProps> = ({
  headerProps,
  activeTab,
  onTabChange,
  tabProps,
  optionalPromptModal,
  titleAndBlueprintModalProps,
  characterAndRelationshipModalProps,
  projectId,
  onProjectRefresh,
  lazyBusinessModalProps,
  latestPartOutlineModalProps,
  latestChapterOutlineModalProps,
}) => {
  const [workspacePane, setWorkspacePane] = React.useState<'sections' | 'workspace'>('workspace');
  const paneItems = [
    {
      id: 'workspace',
      label: '工作区',
      hint: '聚焦当前章节、角色或世界观的编辑与查看。',
    },
    {
      id: 'sections',
      label: '分区导航',
      hint: '切换概览、世界观、角色、关系与章节内容。',
    },
  ] as const;

  return (
    <AppViewportShell>
      <div className="ambient-orb -left-16 top-0 h-72 w-72 bg-book-primary/14" />
      <div className="ambient-orb right-[-5rem] top-28 h-64 w-64 bg-book-primary-light/12" />

      <AppViewportFrame>
        <NovelDetailHeader {...headerProps} />

        <div className="xl:hidden">
          <div className="dramatic-surface rounded-[28px] px-4 py-4">
            <div className="relative z-[1]">
              <SegmentPager
                items={[...paneItems]}
                value={workspacePane}
                onChange={(next) => setWorkspacePane(next as 'sections' | 'workspace')}
              />
            </div>
          </div>
        </div>

        <div className="grid min-h-0 flex-1 gap-4 xl:grid-cols-[260px_minmax(0,1fr)]">
          <div className={`${workspacePane === 'sections' ? 'min-h-0' : 'hidden'} xl:block`}>
            <NovelDetailTabBar activeTab={activeTab} onChange={onTabChange} />
          </div>

          <div className={`${workspacePane === 'workspace' ? 'min-h-0' : 'hidden'} xl:block`}>
            <div className="dramatic-surface min-h-[32rem] h-full rounded-[32px]">
              <NovelDetailTabContent activeTab={activeTab} tabProps={tabProps} />
            </div>
          </div>
        </div>
      </AppViewportFrame>

      {optionalPromptModal}

      <TitleAndBlueprintModals {...titleAndBlueprintModalProps} />

      <CharacterAndRelationshipModals {...characterAndRelationshipModalProps} />

      <NovelDetailLazyBusinessModals
        projectId={projectId}
        onProjectRefresh={onProjectRefresh}
        {...lazyBusinessModalProps}
      />

      <LatestPartOutlineModals {...latestPartOutlineModalProps} />

      <LatestChapterOutlineModals {...latestChapterOutlineModalProps} />
    </AppViewportShell>
  );
};
