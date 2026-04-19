import {
  Activity,
  Camera,
  GitCompare,
  ScrollText,
  Sparkles,
  Trash2,
  User,
  type LucideIcon,
} from 'lucide-react';

export type DetailTab =
  | 'attributes'
  | 'history'
  | 'behaviors'
  | 'deletions'
  | 'snapshots'
  | 'diff'
  | 'implicit';

export const DETAIL_TABS: Array<{
  id: DetailTab;
  label: string;
  description: string;
  icon: LucideIcon;
}> = [
  {
    id: 'attributes',
    label: '属性',
    description: '查看角色当前的显性、隐性和社会属性快照。',
    icon: User,
  },
  {
    id: 'history',
    label: '历史',
    description: '筛选属性变更历史，追踪每次更新的章节来源和证据。',
    icon: ScrollText,
  },
  {
    id: 'behaviors',
    label: '行为',
    description: '回看被抽取出的行为记录、标签和原文证据。',
    icon: Activity,
  },
  {
    id: 'deletions',
    label: '删除',
    description: '核对删除候选的累计标记、执行情况和重置状态。',
    icon: Trash2,
  },
  {
    id: 'snapshots',
    label: '快照',
    description: '浏览按章节沉淀的状态快照，并对具体章节快照做抽样检查。',
    icon: Camera,
  },
  {
    id: 'diff',
    label: 'Diff/回滚',
    description: '执行冲突检测、章节间状态对比，并在必要时回滚快照。',
    icon: GitCompare,
  },
  {
    id: 'implicit',
    label: '隐性',
    description: '评估隐性属性是否达到更新阈值，并请求 LLM 给出修订建议。',
    icon: Sparkles,
  },
];

export const selectClassName = `
  book-control book-select mt-1 w-full rounded-2xl border px-4 py-3
  text-sm text-book-text-main transition-all duration-200
  focus:border-book-primary/45 focus:outline-none focus:ring-2 focus:ring-book-primary/18
`;

export const codeBlockClassName = `
  max-h-[20rem] overflow-auto whitespace-pre-wrap rounded-[22px] border border-book-border/45
  bg-book-bg-paper/78 p-4 font-mono text-xs text-book-text-main
  shadow-[inset_0_1px_0_rgba(255,255,255,0.24)]
`;

export const formatDateTime = (value: string) => {
  if (!value) return '未知时间';
  const time = new Date(value);
  return Number.isNaN(time.getTime()) ? value : time.toLocaleString();
};

export const normalizeCharacterName = (value: any) => String(value ?? '').trim();

export const extractIdentityFromAttributes = (
  attrs: Record<string, any> | null | undefined,
): string | null => {
  if (!attrs || typeof attrs !== 'object') return null;
  const candidates = ['identity', '身份', '角色身份', '角色定位', '定位', 'role'];
  for (const key of candidates) {
    const raw = (attrs as any)[key];
    if (typeof raw === 'string') {
      const trimmed = raw.trim();
      if (trimmed) return trimmed;
    }
  }
  return null;
};
