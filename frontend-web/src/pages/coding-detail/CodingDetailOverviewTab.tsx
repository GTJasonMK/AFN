import React from 'react';
import { BookCard } from '../../components/ui/BookCard';

type CodingDetailOverviewTabProps = {
  project: any;
  systems: any[];
  modules: any[];
  treeData: any;
};

const getProjectCompletionPercent = (
  project: any,
  systems: any[],
  modules: any[],
  treeData: any,
) => {
  let completed = 0;
  if (project?.blueprint?.one_sentence_summary || project?.blueprint?.architecture_synopsis) completed += 1;
  if (systems.length > 0) completed += 1;
  if (modules.length > 0) completed += 1;
  if (treeData?.root_nodes?.length > 0) completed += 1;
  return Math.round((completed / 4) * 100);
};

export const CodingDetailOverviewTab: React.FC<CodingDetailOverviewTabProps> = ({
  project,
  systems,
  modules,
  treeData,
}) => {
  const progressPercent = getProjectCompletionPercent(project, systems, modules, treeData);

  return (
    <div className="space-y-6">
      <BookCard className="p-5">
        <div className="mb-4 flex items-center justify-between">
          <div className="text-sm font-bold text-book-text-main">项目进度</div>
          <div className="text-sm font-bold text-book-primary">{progressPercent}%</div>
        </div>
        <div className="mb-4 h-2 rounded-full bg-book-border">
          <div
            className="h-full rounded-full bg-book-primary transition-all"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-book-text-muted">
          <span className={project?.blueprint ? 'text-green-600' : ''}>1.蓝图</span>
          <span>--</span>
          <span className={systems.length > 0 ? 'text-green-600' : ''}>2.系统</span>
          <span>--</span>
          <span className={modules.length > 0 ? 'text-green-600' : ''}>3.模块</span>
          <span>--</span>
          <span className={treeData?.root_nodes?.length > 0 ? 'text-green-600' : ''}>4.目录</span>
        </div>
      </BookCard>

      <BookCard className="p-5">
        <div className="mb-3 text-sm font-bold text-book-text-main">项目摘要</div>
        <div className="mb-4 text-sm text-book-text-main">
          {project?.blueprint?.one_sentence_summary || '暂无摘要，请先生成蓝图'}
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-book-text-muted">项目类型</div>
            <div className="text-sm text-book-text-sub">{project?.blueprint?.project_type_desc || '未定义'}</div>
          </div>
          <div>
            <div className="text-xs text-book-text-muted">目标受众</div>
            <div className="text-sm text-book-text-sub">{project?.blueprint?.target_audience || '未定义'}</div>
          </div>
          <div>
            <div className="text-xs text-book-text-muted">技术风格</div>
            <div className="text-sm text-book-text-sub">{project?.blueprint?.tech_style || '未定义'}</div>
          </div>
          <div>
            <div className="text-xs text-book-text-muted">项目调性</div>
            <div className="text-sm text-book-text-sub">{project?.blueprint?.project_tone || '未定义'}</div>
          </div>
        </div>
        {project?.blueprint?.architecture_synopsis && (
          <div className="mt-4">
            <div className="mb-1 text-xs text-book-text-muted">架构概述</div>
            <div className="whitespace-pre-wrap text-sm text-book-text-sub">
              {project.blueprint.architecture_synopsis}
            </div>
          </div>
        )}
      </BookCard>

      <BookCard className="p-5">
        <div className="mb-3 text-sm font-bold text-book-text-main">技术栈</div>
        {!project?.blueprint?.tech_stack ? (
          <div className="text-sm text-book-text-muted">暂无技术栈信息，请先生成蓝图</div>
        ) : (
          <>
            {project.blueprint.tech_stack.core_constraints && (
              <div className="mb-3 text-sm text-book-text-sub">
                核心约束: {project.blueprint.tech_stack.core_constraints}
              </div>
            )}
            {Array.isArray(project.blueprint.tech_stack.components) &&
              project.blueprint.tech_stack.components.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {project.blueprint.tech_stack.components.slice(0, 8).map((comp: any, idx: number) => {
                    const name = typeof comp === 'string' ? comp : comp?.name || '';
                    return (
                      <span
                        key={idx}
                        className="rounded border border-book-primary/30 bg-book-primary/10 px-2 py-1 text-xs text-book-primary"
                      >
                        {name}
                      </span>
                    );
                  })}
                  {project.blueprint.tech_stack.components.length > 8 && (
                    <span className="text-xs text-book-text-muted">
                      +{project.blueprint.tech_stack.components.length - 8}
                    </span>
                  )}
                </div>
              )}
          </>
        )}
      </BookCard>
    </div>
  );
};
