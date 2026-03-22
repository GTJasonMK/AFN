export type WorkflowRollbackImpact = {
  kind?: string;
  title?: string;
  tables?: string[];
  count?: number | null;
  chapter_start?: number | null;
  chapter_end?: number | null;
  part_start?: number | null;
  part_end?: number | null;
  note?: string | null;
};

export type WorkflowRollbackStep = {
  from_status?: string;
  to_status?: string;
  from_label?: string;
  to_label?: string;
  impacts?: WorkflowRollbackImpact[];
};

export type WorkflowRollbackPreview = {
  project_id?: string;
  from_status?: string;
  to_status?: string;
  path?: string[];
  steps?: WorkflowRollbackStep[];
  summary?: string;
};

const formatRange = (start?: number | null, end?: number | null, unit?: string) => {
  if (start == null || end == null) return '';
  const suffix = unit ? ` ${unit}` : '';
  if (start === end) return `第 ${start}${suffix}`.trim();
  return `第 ${start}-${end}${suffix}`.trim();
};

const formatTables = (tables?: string[]) => {
  const arr = Array.isArray(tables) ? tables.filter(Boolean) : [];
  if (!arr.length) return '';
  const preview = arr.length > 4 ? `${arr.slice(0, 4).join('、')} 等` : arr.join('、');
  return `涉及：${preview}`;
};

export const buildWorkflowRollbackConfirmMessage = (preview?: WorkflowRollbackPreview | null): string => {
  if (!preview) return '';

  const steps = Array.isArray(preview.steps) ? preview.steps : [];
  if (!steps.length) {
    const summary = String(preview.summary || '').trim();
    return summary || '无需回退。';
  }

  const lines: string[] = [];
  lines.push('将执行回退路径：');

  for (const step of steps) {
    const fromLabel = String(step?.from_label || step?.from_status || '').trim();
    const toLabel = String(step?.to_label || step?.to_status || '').trim();
    if (fromLabel && toLabel) lines.push(`- ${fromLabel} → ${toLabel}`);

    const impacts = Array.isArray(step?.impacts) ? step.impacts : [];
    if (!impacts.length) {
      lines.push('  - （无清理动作）');
      continue;
    }

    for (const impact of impacts) {
      const title = String(impact?.title || '').trim() || '清理数据';
      const kind = String(impact?.kind || '').trim();

      const meta: string[] = [];
      const tablesText = formatTables(impact?.tables);
      if (tablesText) meta.push(tablesText);

      let detail = title;
      if (kind === 'delete_chapters' && typeof impact?.count === 'number') {
        const range = formatRange(impact.chapter_start, impact.chapter_end, '章');
        if (range) meta.unshift(range);
        detail = `${detail}：${impact.count} 章`;
      } else if (kind === 'delete_chapter_outlines' && typeof impact?.count === 'number') {
        const range = formatRange(impact.chapter_start, impact.chapter_end, '章');
        if (range) meta.unshift(range);
        detail = `${detail}：${impact.count} 条`;
      } else if (kind === 'delete_part_outlines' && typeof impact?.count === 'number') {
        const range = formatRange(impact.part_start, impact.part_end, '部分');
        if (range) meta.unshift(range);
        detail = `${detail}：${impact.count} 条`;
      } else if (kind === 'delete_vector_store') {
        const range = formatRange(impact.chapter_start, impact.chapter_end, '章');
        if (range) meta.unshift(range);
      }

      if (meta.length) detail = `${detail}（${meta.join('；')}）`;
      lines.push(`  - ${detail}`);

      const note = String(impact?.note || '').trim();
      if (note) lines.push(`    - ${note}`);
    }
  }

  lines.push('');
  lines.push('注意：回退会删除依赖数据，此操作不可恢复。');
  return lines.join('\n');
};

export const inferWorkflowRollbackDialogType = (
  preview?: WorkflowRollbackPreview | null,
): 'warning' | 'danger' => {
  const steps = Array.isArray(preview?.steps) ? preview?.steps : [];
  const impacts = steps.flatMap((s) => (Array.isArray(s?.impacts) ? s.impacts : []));
  const hasChapterDeletion = impacts.some(
    (impact) => String(impact?.kind || '') === 'delete_chapters' && Number(impact?.count || 0) > 0,
  );
  if (hasChapterDeletion) return 'danger';

  const hasVectorStoreDeletion = impacts.some((impact) => String(impact?.kind || '') === 'delete_vector_store');
  if (hasVectorStoreDeletion) return 'danger';

  const hasAnyDeletion = impacts.some((impact) => String(impact?.kind || '').startsWith('delete_'));
  return hasAnyDeletion ? 'warning' : 'warning';
};
