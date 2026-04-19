import React from 'react';
import { Wand2 } from 'lucide-react';
import { CodingModule, CodingSystem } from '../../api/coding';
import { BookCard } from '../../components/ui/BookCard';
import { BookButton } from '../../components/ui/BookButton';

type CodingDetailArchitectureTabProps = {
  project: any;
  systems: CodingSystem[];
  modules: CodingModule[];
  genAllLogs: string[];
  genAllRunning: boolean;
  tabLoading: boolean;
  onGenerateBlueprint: () => void | Promise<void>;
  onGenerateAllModules: () => void | Promise<void>;
  onGenerateSystems: () => void | Promise<void>;
  onGenerateModulesForSystem: (systemNumber: number) => void | Promise<void>;
  onEditSystem: (system: CodingSystem) => void;
  onDeleteSystem: (system: CodingSystem) => void | Promise<void>;
  onEditModule: (module: CodingModule) => void;
  onDeleteModule: (module: CodingModule) => void | Promise<void>;
};

export const CodingDetailArchitectureTab: React.FC<CodingDetailArchitectureTabProps> = ({
  project,
  systems,
  modules,
  genAllLogs,
  genAllRunning,
  tabLoading,
  onGenerateBlueprint,
  onGenerateAllModules,
  onGenerateSystems,
  onGenerateModulesForSystem,
  onEditSystem,
  onDeleteSystem,
  onEditModule,
  onDeleteModule,
}) => {
  return (
    <div className="space-y-6">
      <BookCard className="p-5">
        <div className="mb-4 flex items-center justify-between">
          <div className="text-sm font-bold text-book-text-main">蓝图概要</div>
          <BookButton size="sm" variant="primary" onClick={onGenerateBlueprint}>
            <Wand2 size={16} className="mr-1" />
            {project?.blueprint ? '重新生成' : '生成蓝图'}
          </BookButton>
        </div>
        {project?.blueprint?.tech_stack && (
          <div className="mb-4 rounded border border-book-border/40 bg-book-bg p-3">
            <div className="mb-2 text-xs font-bold text-book-text-main">技术栈</div>
            <div className="flex flex-wrap gap-2">
              {(project.blueprint.tech_stack.components || []).slice(0, 6).map((comp: any, idx: number) => (
                <span key={idx} className="rounded bg-book-primary/10 px-2 py-0.5 text-xs text-book-primary">
                  {typeof comp === 'string' ? comp : comp?.name || ''}
                </span>
              ))}
            </div>
            {project.blueprint.tech_stack.core_constraints && (
              <div className="mt-2 text-xs text-book-text-sub">
                约束: {project.blueprint.tech_stack.core_constraints}
              </div>
            )}
          </div>
        )}
        {Array.isArray(project?.blueprint?.core_requirements) && project.blueprint.core_requirements.length > 0 && (
          <div className="mb-4 rounded border border-book-border/40 bg-book-bg p-3">
            <div className="mb-2 text-xs font-bold text-book-text-main">
              核心需求 ({project.blueprint.core_requirements.length})
            </div>
            {project.blueprint.core_requirements.slice(0, 3).map((item: any, idx: number) => (
              <div key={idx} className="text-xs text-book-text-sub">
                - {(item.requirement || '').slice(0, 80)}
                {(item.requirement || '').length > 80 ? '...' : ''}
              </div>
            ))}
            {project.blueprint.core_requirements.length > 3 && (
              <div className="text-xs italic text-book-text-muted">
                ... 还有 {project.blueprint.core_requirements.length - 3} 项
              </div>
            )}
          </div>
        )}
        {Array.isArray(project?.blueprint?.technical_challenges) &&
          project.blueprint.technical_challenges.length > 0 && (
            <div className="rounded border border-book-border/40 bg-book-bg p-3">
              <div className="mb-2 text-xs font-bold text-book-text-main">
                技术挑战 ({project.blueprint.technical_challenges.length})
              </div>
              {project.blueprint.technical_challenges.slice(0, 3).map((item: any, idx: number) => (
                <div key={idx} className="text-xs text-book-text-sub">
                  - {(item.challenge || '').slice(0, 80)}
                  {(item.challenge || '').length > 80 ? '...' : ''}
                </div>
              ))}
              {project.blueprint.technical_challenges.length > 3 && (
                <div className="text-xs italic text-book-text-muted">
                  ... 还有 {project.blueprint.technical_challenges.length - 3} 项
                </div>
              )}
            </div>
          )}
      </BookCard>

      <div>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-base font-bold text-book-text-main">项目结构</div>
            <span className="text-sm text-book-text-muted">
              {systems.length} 系统 / {modules.length} 模块
            </span>
          </div>
          <div className="flex items-center gap-2">
            <BookButton size="sm" variant="ghost" onClick={onGenerateAllModules} disabled={genAllRunning || tabLoading}>
              <Wand2 size={16} className="mr-1" />
              一键生成所有模块
            </BookButton>
            <BookButton size="sm" variant="primary" onClick={onGenerateSystems} disabled={tabLoading}>
              <Wand2 size={16} className="mr-1" />
              生成系统划分
            </BookButton>
          </div>
        </div>

        {genAllLogs.length > 0 && (
          <BookCard className="mb-4 p-4">
            <div className="mb-2 text-xs text-book-text-muted">生成进度</div>
            <div className="custom-scrollbar max-h-32 space-y-1 overflow-y-auto font-mono text-xs text-book-text-main">
              {genAllLogs.map((line, idx) => (
                <div key={idx}>{line}</div>
              ))}
            </div>
          </BookCard>
        )}

        {systems.length === 0 ? (
          <BookCard className="p-8 text-center">
            <div className="text-sm text-book-text-muted">
              暂无系统划分
              <br />
              <br />
              点击「生成系统划分」按钮，AI将自动将项目划分为多个子系统
            </div>
          </BookCard>
        ) : (
          <div className="space-y-4">
            {systems.map((system) => {
              const systemModules = modules.filter((module) => module.system_number === system.system_number);
              return (
                <BookCard key={system.system_number} className="p-4">
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div>
                      <div className="font-bold text-book-text-main">
                        #{system.system_number} · {system.name}
                      </div>
                      <div className="mt-1 text-xs text-book-text-muted">
                        {systemModules.length} 模块 · {system.generation_status}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <BookButton
                        size="sm"
                        variant="ghost"
                        onClick={() => onGenerateModulesForSystem(system.system_number)}
                        disabled={tabLoading || genAllRunning}
                      >
                        <Wand2 size={14} className="mr-1" />
                        生成模块
                      </BookButton>
                      <button
                        type="button"
                        className="text-xs font-bold text-book-primary hover:underline"
                        onClick={() => onEditSystem(system)}
                      >
                        编辑
                      </button>
                      <button
                        type="button"
                        className="text-xs font-bold text-red-600 hover:underline"
                        onClick={() => onDeleteSystem(system)}
                      >
                        删除
                      </button>
                    </div>
                  </div>
                  {system.description && (
                    <div className="mb-3 text-sm text-book-text-sub">{system.description}</div>
                  )}
                  {Array.isArray(system.responsibilities) && system.responsibilities.length > 0 && (
                    <div className="mb-3 flex flex-wrap gap-2">
                      {system.responsibilities.slice(0, 6).map((responsibility, idx) => (
                        <span
                          key={idx}
                          className="rounded-full border border-book-border/40 bg-book-bg px-2 py-0.5 text-[11px] text-book-text-sub"
                        >
                          {responsibility}
                        </span>
                      ))}
                    </div>
                  )}
                  {systemModules.length > 0 && (
                    <div className="space-y-2 border-t border-book-border/30 pt-3">
                      {systemModules.map((module) => (
                        <div key={module.module_number} className="flex items-center justify-between rounded bg-book-bg/50 p-2">
                          <div>
                            <span className="text-sm text-book-text-main">
                              #{module.module_number} · {module.name}
                            </span>
                            <span className="ml-2 text-xs text-book-text-muted">{module.type}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              className="text-xs font-bold text-book-primary hover:underline"
                              onClick={() => onEditModule(module)}
                            >
                              编辑
                            </button>
                            <button
                              type="button"
                              className="text-xs font-bold text-red-600 hover:underline"
                              onClick={() => onDeleteModule(module)}
                            >
                              删除
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </BookCard>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
