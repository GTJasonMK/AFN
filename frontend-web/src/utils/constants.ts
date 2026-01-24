export const CREATIVE_QUOTES = [
  ["写书不是为了名利，而是为了安放那个躁动不安的灵魂。", "Writing is not for fame or fortune, but to settle that restless soul."],
  ["每一个字符，都是通向另一个世界的钥匙。", "Every character is a key to another world."],
  ["灵感是风，而持续的写作是帆。", "Inspiration is the wind, but consistent writing is the sail."],
  ["不要等待完美的时刻，抓住这一刻让它变完美。", "Don't wait for the perfect moment, take the moment and make it perfect."],
  ["伟大的故事往往源于一个微小的念头。", "Great stories often start with a tiny thought."],
  ["写作是孤独者的狂欢。", "Writing is a carnival for the lonely."],
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
