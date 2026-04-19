import React from 'react';
import { CodingFileDetail, CodingFileVersion } from '../../api/coding';
import { BookButton } from '../../components/ui/BookButton';
import { BookCard } from '../../components/ui/BookCard';
import { BookInput } from '../../components/ui/BookInput';
import { Save, Square, Wand2 } from 'lucide-react';

type CodingDeskEditorPanelProps = {
  currentFile: CodingFileDetail | null;
  content: string;
  reviewPrompt: string;
  reviewNotes: string;
  versions: CodingFileVersion[];
  selectedVersionId: number | null;
  isGenerating: boolean;
  isSaving: boolean;
  isDirty: boolean;
  isGeneratingReview: boolean;
  isSavingReview: boolean;
  isReviewDirty: boolean;
  genStage: string | null;
  genMessage: string | null;
  onChangeContent: (value: string) => void;
  onChangeReviewPrompt: (value: string) => void;
  onChangeReviewNotes: (value: string) => void;
  onStopPrompt: () => void;
  onGeneratePrompt: () => void | Promise<void>;
  onSavePrompt: () => void | Promise<void>;
  onSelectVersion: (version: CodingFileVersion) => void | Promise<void>;
  onStopReview: () => void;
  onGenerateReview: () => void | Promise<void>;
  onSaveReview: () => void | Promise<void>;
};

export const CodingDeskEditorPanel: React.FC<CodingDeskEditorPanelProps> = ({
  currentFile,
  content,
  reviewPrompt,
  reviewNotes,
  versions,
  selectedVersionId,
  isGenerating,
  isSaving,
  isDirty,
  isGeneratingReview,
  isSavingReview,
  isReviewDirty,
  genStage,
  genMessage,
  onChangeContent,
  onChangeReviewPrompt,
  onChangeReviewNotes,
  onStopPrompt,
  onGeneratePrompt,
  onSavePrompt,
  onSelectVersion,
  onStopReview,
  onGenerateReview,
  onSaveReview,
}) => {
  return (
    <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-book-bg">
      {!currentFile ? (
        <div className="flex h-full items-center justify-center text-book-text-muted">
          请选择一个文件开始编辑
        </div>
      ) : (
        <div className="custom-scrollbar flex-1 min-h-0 overflow-y-auto space-y-4 p-6">
          <BookCard className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="font-bold text-book-text-main">{currentFile.filename}</div>
                <div className="mt-1 whitespace-pre-wrap text-xs text-book-text-muted">
                  {currentFile.description || currentFile.purpose || currentFile.file_path}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {isGenerating ? (
                  <BookButton
                    size="sm"
                    variant="ghost"
                    onClick={onStopPrompt}
                    title="仅断开 SSE 连接（不保证取消后台任务）"
                  >
                    <Square size={16} className="mr-1" />
                    停止
                  </BookButton>
                ) : (
                  <BookButton size="sm" variant="primary" onClick={onGeneratePrompt} disabled={isGenerating || isSaving}>
                    <Wand2 size={16} className="mr-1" />
                    生成 Prompt
                  </BookButton>
                )}
                <BookButton
                  size="sm"
                  variant="secondary"
                  onClick={onSavePrompt}
                  disabled={isSaving || isGenerating}
                  title="保存为新版本"
                >
                  <Save size={16} className="mr-1" />
                  {isSaving ? '保存中…' : (isDirty ? '保存*' : '保存')}
                </BookButton>
              </div>
            </div>

            {(genStage || genMessage) ? (
              <div className="mt-3 rounded border border-book-border/40 bg-book-bg p-2 text-xs text-book-text-muted">
                {genStage ? <span className="mr-2 font-mono">{genStage}</span> : null}
                {genMessage}
              </div>
            ) : null}

            {versions.length > 0 ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {versions.map((version, idx) => {
                  const isSelected = selectedVersionId ? selectedVersionId === version.id : idx === 0;
                  return (
                    <button
                      key={`ver-${version.id}-${idx}`}
                      className={`rounded-lg border px-3 py-1 text-xs font-bold transition-all ${
                        isSelected
                          ? 'border-book-primary/30 bg-book-primary/10 text-book-primary'
                          : 'border-book-border/40 bg-book-bg text-book-text-muted hover:text-book-text-main'
                      }`}
                      onClick={() => onSelectVersion(version)}
                      disabled={isGenerating || isSaving}
                      type="button"
                    >
                      {version.version_label || `v${idx + 1}`}
                    </button>
                  );
                })}
              </div>
            ) : null}
          </BookCard>

          <BookCard className="p-4">
            <div className="mb-2 text-xs font-bold text-book-text-sub">实现 Prompt</div>
            <textarea
              value={content}
              onChange={(e) => onChangeContent(e.target.value)}
              className="min-h-[380px] w-full resize-y rounded-lg border border-book-border/40 bg-book-bg px-3 py-3 font-mono text-sm leading-relaxed text-book-text-main focus:outline-none focus:ring-2 focus:ring-book-primary/30"
              placeholder="选择一个文件后点击「生成 Prompt」开始生成，或直接编辑后保存。"
              spellCheck={false}
              readOnly={isGenerating}
            />
          </BookCard>

          <BookCard className="p-4">
            <div className="mb-2 flex items-center justify-between gap-3">
              <div className="text-xs font-bold text-book-text-sub">审查 Prompt</div>
              <div className="flex items-center gap-2">
                {isGeneratingReview ? (
                  <BookButton size="sm" variant="ghost" onClick={onStopReview}>
                    <Square size={16} className="mr-1" />
                    停止
                  </BookButton>
                ) : (
                  <BookButton size="sm" variant="ghost" onClick={onGenerateReview} disabled={!content.trim()}>
                    <Wand2 size={16} className="mr-1" />
                    生成审查
                  </BookButton>
                )}
                <BookButton
                  size="sm"
                  variant="secondary"
                  onClick={onSaveReview}
                  disabled={isSavingReview || isGeneratingReview}
                  title="保存审查 Prompt"
                >
                  <Save size={16} className="mr-1" />
                  {isSavingReview ? '保存中…' : (isReviewDirty ? '保存*' : '保存')}
                </BookButton>
              </div>
            </div>

            <div className="mb-3 grid grid-cols-1 gap-3 md:grid-cols-2">
              <BookInput
                label="审查偏好（可选）"
                placeholder="例如：更关注安全/性能/可测试性…"
                value={reviewNotes}
                onChange={(e) => onChangeReviewNotes(e.target.value)}
              />
            </div>

            <textarea
              value={reviewPrompt}
              onChange={(e) => onChangeReviewPrompt(e.target.value)}
              className="min-h-[180px] w-full resize-y rounded-lg border border-book-border/40 bg-book-bg px-3 py-3 font-mono text-sm leading-relaxed text-book-text-main focus:outline-none focus:ring-2 focus:ring-book-primary/30"
              placeholder="生成实现 Prompt 后可生成审查 Prompt…"
              spellCheck={false}
              readOnly={isGeneratingReview}
            />
          </BookCard>
        </div>
      )}
    </div>
  );
};
