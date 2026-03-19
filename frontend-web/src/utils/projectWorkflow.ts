import { getStatusText } from './constants';

/**
 * 项目工作流（前端视角）
 *
 * 目标：
 * - 把“每一步依赖上一步”的约束从后端错误提示，提前变成前端可解释的禁用/引导
 * - 统一各页面对 status 的解释，避免入口分流与按钮权限各说各话
 *
 * 注意：
 * - 后端 novel 的状态值来自 ProjectStatus（state_machine.py）
 * - 前端历史上存在 inspiration/draft 混用，这里做归一化兼容
 */

export type WorkflowStage =
  | 'draft'
  | 'blueprint_ready'
  | 'part_outlines_ready'
  | 'chapter_outlines_ready'
  | 'writing'
  | 'completed'
  | 'unknown';

export type WorkflowCapabilities = {
  canGenerateBlueprint: boolean;
  canEditBlueprint: boolean;
  canGeneratePartOutlines: boolean;
  canGenerateChapterOutlines: boolean;
  canGenerateChapterContent: boolean;
};

export const normalizeProjectStatus = (raw: unknown): string => {
  const text = String(raw ?? '').trim();
  if (!text) return '';
  return text.toLowerCase();
};

export const resolveWorkflowStage = (rawStatus: unknown): WorkflowStage => {
  const status = normalizeProjectStatus(rawStatus);
  if (!status) return 'unknown';

  // 兼容历史值：inspiration 等价于 draft
  if (status === 'draft' || status === 'inspiration') return 'draft';

  if (status === 'blueprint_ready') return 'blueprint_ready';
  if (status === 'part_outlines_ready') return 'part_outlines_ready';
  if (status === 'chapter_outlines_ready') return 'chapter_outlines_ready';
  if (status === 'writing') return 'writing';
  if (status === 'completed') return 'completed';

  return 'unknown';
};

/**
 * 小说项目能力计算（对齐后端 state_validators.py）
 */
export const getNovelCapabilities = (stage: WorkflowStage): WorkflowCapabilities => {
  const canGenerateBlueprint = stage === 'draft' || stage === 'blueprint_ready';
  const canEditBlueprint = stage === 'draft' || stage === 'blueprint_ready';
  const canGeneratePartOutlines = stage === 'blueprint_ready';
  const canGenerateChapterOutlines =
    stage === 'blueprint_ready' ||
    stage === 'part_outlines_ready' ||
    stage === 'chapter_outlines_ready' ||
    stage === 'writing';
  const canGenerateChapterContent =
    stage === 'chapter_outlines_ready' ||
    stage === 'writing' ||
    stage === 'completed';

  return {
    canGenerateBlueprint,
    canEditBlueprint,
    canGeneratePartOutlines,
    canGenerateChapterOutlines,
    canGenerateChapterContent,
  };
};

export const getWorkflowStatusLabel = (rawStatus: unknown): string => {
  const normalized = normalizeProjectStatus(rawStatus);
  return normalized ? getStatusText(normalized) : '未知状态';
};

