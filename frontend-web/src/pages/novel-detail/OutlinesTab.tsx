import React, { useMemo } from 'react';
import { Share } from 'lucide-react';
import {
  OutlinesChapterSection,
  type OutlinesChapterSectionProps,
} from './OutlinesChapterSection';
import {
  OutlinesPartSection,
  type OutlinesPartSectionProps,
} from './OutlinesPartSection';
import { SegmentPager } from '../../components/layout/AppViewport';
import { usePersistedTab } from '../../hooks/usePersistedTab';

export type OutlinesTabProps = OutlinesChapterSectionProps & OutlinesPartSectionProps;

export const OutlinesTab: React.FC<OutlinesTabProps> = (props) => {
  type OutlineSubTab = 'chapters' | 'parts';
  const subTabStorageKey = useMemo(() => `afn:novel_detail:outlines:sub_tab:${props.projectId}`, [props.projectId]);
  const [subTab, setSubTab] = usePersistedTab<OutlineSubTab>(
    subTabStorageKey,
    'chapters',
    ['chapters', 'parts'] as const,
  );

  const needsPartOutlines = Boolean(props.blueprintData?.needs_part_outlines);
  const subTabItems = useMemo(() => ([
    {
      id: 'chapters',
      label: '章节大纲',
      hint: '按章节推进：编辑标题/摘要，批量生成后续章节大纲。',
    },
    {
      id: 'parts',
      label: '部分大纲',
      hint: needsPartOutlines
        ? '按部分推进：先生成分部结构，再覆盖到对应章节范围。'
        : '本项目未启用分部大纲（章节数未超过阈值）。',
    },
  ] as const), [needsPartOutlines]);

  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 space-y-6">
      <div className="dramatic-surface rounded-[24px] p-4">
        <div className="relative z-[1]">
          <SegmentPager
            items={[...subTabItems]}
            value={subTab}
            onChange={(next) => setSubTab(next as OutlineSubTab)}
          />
        </div>
      </div>

      {subTab === 'chapters' ? (
        <OutlinesChapterSection {...props} />
      ) : needsPartOutlines ? (
        <OutlinesPartSection {...props} />
      ) : (
        <div className="text-center py-20 text-book-text-muted bg-book-bg-paper/80 rounded-2xl border border-book-border/40">
          <Share size={48} className="mx-auto mb-4 opacity-50" />
          <p className="text-sm font-semibold text-book-text-main">该项目不需要部分大纲</p>
          <p className="mt-2 text-sm leading-relaxed text-book-text-sub">
            当前蓝图判定为「无需分部结构」：你可以直接在「章节大纲」里按章推进。
          </p>
          <p className="mt-2 text-xs leading-relaxed text-book-text-muted">
            若你希望启用部分大纲，请先在蓝图中提高总章节数并重新生成/刷新大纲结构（使 needs_part_outlines 生效）。
          </p>
        </div>
      )}
    </div>
  );
};
