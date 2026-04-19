import React from 'react';
import { DirectoryAgentStateResponse } from '../../api/coding';
import { BookButton } from '../../components/ui/BookButton';
import { BookCard } from '../../components/ui/BookCard';
import { BookInput, BookTextarea } from '../../components/ui/BookInput';
import { Database, PauseCircle, PlayCircle, Search, Square, XCircle } from 'lucide-react';
import { AssistantTab, LOG_LABELS, safeJson, StreamLog } from './shared';

type CodingDeskAssistantPanelProps = {
  activeAssistantTab: AssistantTab;
  ragTopK: number;
  ragLoading: boolean;
  ragQuery: string;
  ragResult: any | null;
  agentDetailedMode: boolean;
  agentStateLoading: boolean;
  agentState: DirectoryAgentStateResponse | null;
  agentRunning: boolean;
  agentPreview: { directories?: any[]; files?: any[]; stats?: any } | null;
  agentPreviewText: string;
  agentLogs: StreamLog[];
  visibleAgentLogs: StreamLog[];
  hasMoreAgentLogs: boolean;
  remainingAgentLogs: number;
  agentLogRenderLimit: number;
  agentLogRef: React.RefObject<HTMLDivElement | null>;
  onChangeActiveAssistantTab: (tab: AssistantTab) => void;
  onChangeRagTopK: (value: number) => void;
  onRunRagQuery: () => void | Promise<void>;
  onChangeRagQuery: (value: string) => void;
  onChangeAgentDetailedMode: (checked: boolean) => void;
  onStartAgentPlanning: (opts: { clearExisting: boolean }) => void | Promise<void>;
  onContinueAgentPlanning: () => void | Promise<void>;
  onDiscardAgentState: () => void | Promise<void>;
  onStopAgentPlanning: () => void | Promise<void>;
  onClearAgentLogs: () => void;
  onExpandAgentLogs: () => void;
  onCollapseAgentLogs: () => void;
  onRefreshAgentState: () => void | Promise<void>;
};

export const CodingDeskAssistantPanel: React.FC<CodingDeskAssistantPanelProps> = ({
  activeAssistantTab,
  ragTopK,
  ragLoading,
  ragQuery,
  ragResult,
  agentDetailedMode,
  agentStateLoading,
  agentState,
  agentRunning,
  agentPreview,
  agentPreviewText,
  agentLogs,
  visibleAgentLogs,
  hasMoreAgentLogs,
  remainingAgentLogs,
  agentLogRenderLimit,
  agentLogRef,
  onChangeActiveAssistantTab,
  onChangeRagTopK,
  onRunRagQuery,
  onChangeRagQuery,
  onChangeAgentDetailedMode,
  onStartAgentPlanning,
  onContinueAgentPlanning,
  onDiscardAgentState,
  onStopAgentPlanning,
  onClearAgentLogs,
  onExpandAgentLogs,
  onCollapseAgentLogs,
  onRefreshAgentState,
}) => {
  return (
    <div className="flex w-[420px] flex-col border-l border-book-border/60 bg-book-bg-paper">
      <div className="flex items-center gap-2 border-b border-book-border/30 p-2">
        <button
          className={`flex-1 rounded-lg border px-3 py-2 text-xs font-bold transition-all ${
            activeAssistantTab === 'agent'
              ? 'border-book-primary/30 bg-book-primary/10 text-book-primary'
              : 'border-book-border/40 bg-book-bg text-book-text-muted hover:text-book-text-main'
          }`}
          onClick={() => onChangeActiveAssistantTab('agent')}
          type="button"
        >
          目录规划
        </button>
        <button
          className={`flex-1 rounded-lg border px-3 py-2 text-xs font-bold transition-all ${
            activeAssistantTab === 'rag'
              ? 'border-book-primary/30 bg-book-primary/10 text-book-primary'
              : 'border-book-border/40 bg-book-bg text-book-text-muted hover:text-book-text-main'
          }`}
          onClick={() => onChangeActiveAssistantTab('rag')}
          type="button"
        >
          RAG查询
        </button>
      </div>

      <div className="custom-scrollbar flex-1 min-h-0 space-y-4 overflow-y-auto p-4">
        {activeAssistantTab === 'rag' ? (
          <div className="space-y-3">
            <BookCard className="space-y-3 p-4">
              <div className="flex items-center gap-2 font-bold text-book-text-main">
                <Database size={16} className="text-book-primary" />
                RAG查询
              </div>
              <div className="grid grid-cols-2 gap-3">
                <BookInput
                  label="TopK"
                  type="number"
                  min={1}
                  max={30}
                  value={ragTopK}
                  onChange={(e) => onChangeRagTopK(Number(e.target.value || 8))}
                />
                <div className="flex items-end">
                  <BookButton
                    variant="primary"
                    size="sm"
                    onClick={onRunRagQuery}
                    disabled={ragLoading || !(ragQuery || '').trim()}
                    className="w-full"
                  >
                    <Search size={14} className={`mr-1 ${ragLoading ? 'animate-spin' : ''}`} />
                    查询
                  </BookButton>
                </div>
              </div>
              <label className="text-xs font-bold text-book-text-sub">
                查询内容
                <BookTextarea
                  rows={3}
                  value={ragQuery}
                  onChange={(e) => onChangeRagQuery(e.target.value)}
                  placeholder="输入查询，例如：鉴权、缓存、数据库迁移…"
                />
              </label>
            </BookCard>

            <BookCard className="p-4">
              <div className="mb-2 text-xs font-bold text-book-text-sub">结果</div>
              {!ragResult ? (
                <div className="text-xs text-book-text-muted">暂无结果</div>
              ) : (
                <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-book-text-main">
                  {safeJson(ragResult)}
                </pre>
              )}
            </BookCard>
          </div>
        ) : (
          <div className="space-y-3">
            <BookCard className="space-y-3 p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="font-bold text-book-text-main">目录规划</div>
                <div className="flex items-center gap-3">
                  <label className="flex cursor-pointer select-none items-center gap-2">
                    <input
                      type="checkbox"
                      className="rounded border-book-border text-book-primary focus:ring-book-primary"
                      checked={agentDetailedMode}
                      onChange={(e) => onChangeAgentDetailedMode(e.target.checked)}
                    />
                    <span className="text-[11px] font-bold text-book-text-sub">详细模式</span>
                  </label>
                  <div className="text-[11px] text-book-text-muted">
                    {agentStateLoading ? '状态加载中…' : (agentState?.has_paused_state ? '可恢复' : '无暂停状态')}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <BookButton
                  variant="primary"
                  size="sm"
                  onClick={() => onStartAgentPlanning({ clearExisting: true })}
                  disabled={agentRunning}
                >
                  {agentRunning ? <PauseCircle size={14} className="mr-1" /> : <PlayCircle size={14} className="mr-1" />}
                  规划全项目
                </BookButton>
                <BookButton
                  variant="ghost"
                  size="sm"
                  onClick={() => onStartAgentPlanning({ clearExisting: false })}
                  disabled={agentRunning}
                >
                  <PlayCircle size={14} className="mr-1" />
                  优化目录
                </BookButton>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <BookButton
                  variant="secondary"
                  size="sm"
                  onClick={onContinueAgentPlanning}
                  disabled={agentRunning || !agentState?.has_paused_state}
                  title="按桌面端逻辑尝试继续（取决于后端是否实现 resume）"
                >
                  <PlayCircle size={14} className="mr-1" />
                  继续规划
                </BookButton>
                <BookButton
                  variant="ghost"
                  size="sm"
                  onClick={onDiscardAgentState}
                  disabled={agentRunning || !agentState?.has_paused_state}
                >
                  <XCircle size={14} className="mr-1" />
                  放弃进度
                </BookButton>
              </div>

              <BookButton
                variant="secondary"
                size="sm"
                onClick={onStopAgentPlanning}
                disabled={!agentRunning}
                title="尽量调用后端 pause-agent；若不可用则仅断开连接"
              >
                <Square size={14} className="mr-1" />
                停止
              </BookButton>

              {agentState?.progress_message ? (
                <div className="rounded border border-book-border/40 bg-book-bg p-2 text-xs text-book-text-muted">
                  {agentState.progress_percent ? <span className="mr-2 font-mono">{agentState.progress_percent}%</span> : null}
                  {agentState.progress_message}
                </div>
              ) : null}
            </BookCard>

            {agentPreview ? (
              <BookCard className="p-4">
                <div className="mb-2 text-xs font-bold text-book-text-sub">结构预览</div>
                <div className="mb-2 text-xs text-book-text-muted">
                  目录 {agentPreview.directories?.length || 0} · 文件 {agentPreview.files?.length || 0}
                </div>
                <pre className="custom-scrollbar max-h-56 overflow-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-book-text-main">
                  {agentPreviewText}
                </pre>
              </BookCard>
            ) : null}

            <BookCard className="p-4">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-xs font-bold text-book-text-sub">过程输出</div>
                <div className="flex items-center gap-2">
                  <button
                    className="text-xs font-bold text-book-primary hover:underline"
                    type="button"
                    onClick={onClearAgentLogs}
                  >
                    清空
                  </button>
                  {hasMoreAgentLogs ? (
                    <button
                      className="text-xs text-book-text-muted hover:underline"
                      type="button"
                      onClick={onExpandAgentLogs}
                      title="为提升流式渲染性能，默认只渲染最近一部分日志"
                    >
                      显示更多（剩余 {remainingAgentLogs}）
                    </button>
                  ) : null}
                  {agentLogRenderLimit > 200 ? (
                    <button
                      className="text-xs text-book-text-muted hover:underline"
                      type="button"
                      onClick={onCollapseAgentLogs}
                    >
                      收起
                    </button>
                  ) : null}
                  <button
                    className="text-xs text-book-text-muted hover:underline"
                    type="button"
                    onClick={onRefreshAgentState}
                  >
                    {agentStateLoading ? '刷新中…' : '刷新状态'}
                  </button>
                </div>
              </div>

              {agentLogs.length === 0 ? (
                <div className="text-xs text-book-text-muted">
                  {agentRunning ? '等待输出…' : '点击“规划全项目/优化目录”开始。'}
                </div>
              ) : (
                <div ref={agentLogRef as React.Ref<HTMLDivElement>} className="custom-scrollbar max-h-[420px] space-y-2 overflow-y-auto pr-1">
                  {visibleAgentLogs.map((log) => {
                    const meta = LOG_LABELS[log.type] || { label: log.type, cls: 'text-book-text-muted' };
                    return (
                      <div key={log.id} className="rounded border border-book-border/40 bg-book-bg p-2">
                        <div className="flex items-center justify-between gap-2">
                          <div className={`text-[11px] font-bold ${meta.cls}`}>
                            {meta.label}
                            {log.title ? <span className="ml-2 font-normal text-book-text-muted">{log.title}</span> : null}
                          </div>
                          <div className="text-[10px] text-book-text-muted">
                            {log.timeText}
                          </div>
                        </div>
                        {log.content ? (
                          <pre className="mt-1 whitespace-pre-wrap font-mono text-xs leading-relaxed text-book-text-main">
                            {log.content}
                          </pre>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              )}
            </BookCard>
          </div>
        )}
      </div>
    </div>
  );
};
