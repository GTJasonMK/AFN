/** 首页名言：[正文, 出处] */
export const CREATIVE_QUOTES: [string, string][] = [
  ['写小说就是跟自己的灵魂下一盘很长的棋。', '—— 余华'],
  ['一切伟大的行动和思想，都有一个微不足道的开始。', '—— 加缪'],
  ['故事是人类对抗遗忘的最古老的武器。', '—— 本雅明'],
  ['你不是在写故事，是故事在借你的手说话。', '—— 斯蒂芬·金'],
  ['世界上只有一种英雄主义，就是在认清生活真相之后依然热爱生活。', '—— 罗曼·罗兰'],
  ['灵感是风，而持续的写作是帆。', '—— 杰克·伦敦'],
  ['每一个不曾起舞的日子，都是对生命的辜负。', '—— 尼采'],
  ['真正的发现之旅不在于寻找新风景，而在于拥有新眼光。', '—— 普鲁斯特'],
  ['所有坚韧不拔的努力迟早会取得报酬的。', '—— 安格尔'],
  ['我写作不是因为我有话要说，而是因为我有需要被说出的话。', '—— 菲茨杰拉德'],
];

export const PROJECT_STATUS_MAP: Record<string, string> = {
  'draft': '草稿',
  'inspiration': '灵感构思',
  'blueprint_ready': '蓝图就绪',
  'part_outlines_ready': '分部大纲就绪',
  'chapter_outlines_ready': '章节大纲就绪',
  'writing': '连载中',
  'completed': '已完结',

  // Coding 项目状态（后端可能返回大写）
  'draft_coding': '草稿',
  'blueprint_generated': '架构蓝图已生成',
  'blueprint_ready_coding': '架构蓝图就绪',
  'directory_planned': '目录结构已规划',
  'files_generated': '文件清单已生成',
};

export const getStatusText = (status: string) => {
  const normalized = (status || '').trim();
  const lower = normalized.toLowerCase();
  if (PROJECT_STATUS_MAP[lower]) return PROJECT_STATUS_MAP[lower];
  if (PROJECT_STATUS_MAP[`${lower}_coding`]) return PROJECT_STATUS_MAP[`${lower}_coding`];
  return normalized;
};
