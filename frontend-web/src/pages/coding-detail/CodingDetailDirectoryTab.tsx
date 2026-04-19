import React, { lazy, Suspense } from 'react';
import { RefreshCw, Wand2 } from 'lucide-react';
import { BookCard } from '../../components/ui/BookCard';
import { BookButton } from '../../components/ui/BookButton';

const DirectoryTreeLazy = lazy(() =>
  import('../../components/coding/DirectoryTree').then((module) => ({ default: module.DirectoryTree }))
);
const EditorLazy = lazy(() =>
  import('../../components/business/Editor').then((module) => ({ default: module.Editor }))
);

type CodingDetailDirectoryTabProps = {
  treeData: any;
  loading: boolean;
  treeExpandAllToken: number;
  treeCollapseAllToken: number;
  selectedDirectory: any;
  currentFile: any;
  content: string;
  editorVersions: any[];
  isCurrentFileDirty: boolean;
  isSaving: boolean;
  isGenerating: boolean;
  onExpandAll: () => void;
  onCollapseAll: () => void;
  onRefreshTreeData: () => void | Promise<void>;
  onSelectFile: (fileId: number) => void | Promise<void>;
  onSelectDirectory: (directory: any) => void;
  onEditDirectoryInfo: () => void;
  onEditFileInfo: () => void;
  onOpenCodingDesk: (fileId?: number) => void;
  onGenerate: () => void | Promise<void>;
  onSave: () => void | Promise<void>;
  onChangeContent: (value: string) => void;
  onSelectVersion: (index: number) => void | Promise<void>;
};

export const CodingDetailDirectoryTab: React.FC<CodingDetailDirectoryTabProps> = ({
  treeData,
  loading,
  treeExpandAllToken,
  treeCollapseAllToken,
  selectedDirectory,
  currentFile,
  content,
  editorVersions,
  isCurrentFileDirty,
  isSaving,
  isGenerating,
  onExpandAll,
  onCollapseAll,
  onRefreshTreeData,
  onSelectFile,
  onSelectDirectory,
  onEditDirectoryInfo,
  onEditFileInfo,
  onOpenCodingDesk,
  onGenerate,
  onSave,
  onChangeContent,
  onSelectVersion,
}) => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="text-base font-bold text-book-text-main">目录结构</div>
          <span className="text-sm text-book-text-muted">
            总计 {treeData?.total_directories || 0} 目录 / {treeData?.total_files || 0} 文件
          </span>
        </div>
        <div className="flex items-center gap-2">
          <BookButton
            size="sm"
            variant="ghost"
            onClick={onExpandAll}
            disabled={!treeData?.root_nodes?.length}
          >
            展开全部
          </BookButton>
          <BookButton
            size="sm"
            variant="ghost"
            onClick={onCollapseAll}
            disabled={!treeData?.root_nodes?.length}
          >
            折叠全部
          </BookButton>
          <BookButton size="sm" variant="ghost" onClick={onRefreshTreeData} disabled={loading}>
            <RefreshCw size={16} className={`mr-1 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </BookButton>
        </div>
      </div>

      <BookCard className="p-4">
        {!treeData?.root_nodes?.length ? (
          <div className="py-8 text-center text-sm text-book-text-muted">
            暂无目录结构，请在工作台中使用 Agent 生成
          </div>
        ) : (
          <div className="custom-scrollbar max-h-[600px] overflow-y-auto">
            <Suspense fallback={<div className="py-6 text-xs text-book-text-muted">目录树加载中…</div>}>
              <DirectoryTreeLazy
                data={treeData}
                onSelectFile={onSelectFile}
                onSelectDirectory={onSelectDirectory}
                expandAllToken={treeExpandAllToken}
                collapseAllToken={treeCollapseAllToken}
              />
            </Suspense>
          </div>
        )}
      </BookCard>

      {selectedDirectory && (
        <BookCard className="p-4">
          <div className="mb-2 flex items-center justify-between">
            <div className="min-w-0">
              <div className="truncate text-sm font-bold text-book-text-main">
                {selectedDirectory.name || '目录'}
              </div>
              <div className="truncate text-xs text-book-text-muted">
                {selectedDirectory.path || ''}
              </div>
            </div>
            <BookButton size="sm" variant="ghost" onClick={onEditDirectoryInfo}>
              编辑目录描述
            </BookButton>
          </div>
          <div className="whitespace-pre-wrap text-sm text-book-text-sub">
            {selectedDirectory.description || '暂无描述'}
          </div>
        </BookCard>
      )}

      {currentFile && (
        <BookCard className="p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-bold text-book-text-main">
              {currentFile.filename || currentFile.file_path}
            </div>
            <div className="flex items-center gap-2">
              <BookButton size="sm" variant="ghost" onClick={onEditFileInfo} disabled={!currentFile}>
                编辑信息
              </BookButton>
              <BookButton
                size="sm"
                variant="ghost"
                onClick={() => onOpenCodingDesk(typeof currentFile?.id === 'number' ? currentFile.id : undefined)}
                disabled={!currentFile}
                title="在工作台中打开并定位到该文件"
              >
                在工作台打开
              </BookButton>
              <BookButton size="sm" variant="ghost" onClick={onGenerate} disabled={isGenerating}>
                <Wand2 size={16} className={`mr-1 ${isGenerating ? 'animate-spin' : ''}`} />
                生成
              </BookButton>
              <BookButton size="sm" variant="primary" onClick={onSave} disabled={isSaving}>
                {isSaving ? '保存中...' : '保存'}
              </BookButton>
            </div>
          </div>
          <Suspense fallback={<div className="py-6 text-xs text-book-text-muted">编辑器加载中…</div>}>
            <EditorLazy
              content={content}
              versions={editorVersions}
              isDirty={isCurrentFileDirty}
              isSaving={isSaving}
              isGenerating={isGenerating}
              onChange={onChangeContent}
              onSave={onSave}
              onGenerate={onGenerate}
              onSelectVersion={onSelectVersion}
            />
          </Suspense>
        </BookCard>
      )}
    </div>
  );
};
