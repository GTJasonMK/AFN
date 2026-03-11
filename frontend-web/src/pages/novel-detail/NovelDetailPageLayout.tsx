import React, { type ComponentProps, type ReactNode } from 'react';
import { NovelDetailHeader } from './NovelDetailHeader';
import { NovelDetailTabBar, type NovelDetailTab } from './NovelDetailTabBar';
import { NovelDetailTabContent } from './NovelDetailTabContent';
import { TitleAndBlueprintModals } from './TitleAndBlueprintModals';
import { CharacterAndRelationshipModals } from './CharacterAndRelationshipModals';
import { NovelDetailLazyBusinessModals } from './NovelDetailLazyBusinessModals';
import { LatestPartOutlineModals } from './LatestPartOutlineModals';
import { LatestChapterOutlineModals } from './LatestChapterOutlineModals';

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
  return (
    <div className="page-shell min-h-screen overflow-hidden">
      <div className="ambient-orb -left-16 top-0 h-72 w-72 bg-book-primary/14" />
      <div className="ambient-orb right-[-5rem] top-28 h-64 w-64 bg-book-primary-light/12" />

      <div className="relative mx-auto flex min-h-screen w-full max-w-[1600px] flex-col gap-4 px-3 py-3 sm:px-5 sm:py-5">
        <NovelDetailHeader {...headerProps} />

        <div className="grid min-h-0 flex-1 gap-4 xl:grid-cols-[260px_minmax(0,1fr)]">
          <NovelDetailTabBar activeTab={activeTab} onChange={onTabChange} />

          <div className="dramatic-surface min-h-[32rem] rounded-[32px]">
            <NovelDetailTabContent activeTab={activeTab} tabProps={tabProps} />
          </div>
        </div>
      </div>

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
    </div>
  );
};
