import React, { useEffect, useState } from 'react';
import { Folder, FileCode, ChevronRight, ChevronDown } from 'lucide-react';

interface TreeNode {
  id: string | number;
  name: string;
  type: 'dir' | 'file';
  raw?: any;
  children?: TreeNode[];
}

interface DirectoryTreeProps {
  data: any; // Raw API response
  onSelectFile: (fileId: number) => void;
  onSelectDirectory?: (dir: any) => void;
  expandAllToken?: number;
  collapseAllToken?: number;
}

const TreeItem: React.FC<{
  node: TreeNode;
  level: number;
  onSelectFile: (id: number) => void;
  onSelectDirectory?: (dir: any) => void;
  expandAllToken?: number;
  collapseAllToken?: number;
}> = ({ node, level, onSelectFile, onSelectDirectory, expandAllToken, collapseAllToken }) => {
  // 与桌面端一致：默认展开第一层目录
  const [isOpen, setIsOpen] = useState(level === 0);
  const isDir = node.type === 'dir';

  useEffect(() => {
    if (!isDir) return;
    if (typeof expandAllToken !== 'number') return;
    setIsOpen(true);
  }, [expandAllToken, isDir]);

  useEffect(() => {
    if (!isDir) return;
    if (typeof collapseAllToken !== 'number') return;
    setIsOpen(level === 0);
  }, [collapseAllToken, isDir, level]);
  
  const handleClick = () => {
    if (isDir) {
      onSelectDirectory?.(node.raw);
      setIsOpen(!isOpen);
    } else {
      const rawId = node.id;
      const fileId = typeof rawId === 'number' ? rawId : Number(rawId);
      if (!Number.isFinite(fileId) || fileId <= 0) return;
      onSelectFile(fileId);
    }
  };

  return (
    <div>
      <div 
        className={`
          flex items-center gap-1.5 py-1 px-2 rounded cursor-pointer transition-colors
          hover:bg-book-bg text-sm
        `}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onClick={handleClick}
      >
        <span className="opacity-50 w-4 h-4 flex items-center justify-center">
          {isDir && (
            isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />
          )}
        </span>
        
        {isDir ? (
          <Folder size={14} className="text-book-accent" />
        ) : (
          <FileCode size={14} className="text-book-text-sub" />
        )}
        
        <span className={`${isDir ? 'font-medium text-book-text-main' : 'text-book-text-secondary'}`}>
          {node.name}
        </span>
      </div>
      
      {isDir && isOpen && node.children && (
        <div>
          {node.children.map(child => (
            <TreeItem
              key={`${child.type}-${child.id}`}
              node={child}
              level={level + 1}
              onSelectFile={onSelectFile}
              onSelectDirectory={onSelectDirectory}
              expandAllToken={expandAllToken}
              collapseAllToken={collapseAllToken}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const DirectoryTree: React.FC<DirectoryTreeProps> = ({
  data,
  onSelectFile,
  onSelectDirectory,
  expandAllToken,
  collapseAllToken,
}) => {
  // 后端返回 DirectoryTreeResponse：
  // - root_nodes: DirectoryNodeResponse[]
  // - total_directories/total_files

  const transform = (node: any): TreeNode => {
    const children: TreeNode[] = [];
    if (node.children) {
      children.push(...node.children.map((c: any) => transform(c)));
    }
    if (node.files) {
      children.push(...node.files.map((f: any) => ({
        id: f.id,
        name: f.filename,
        type: 'file',
        raw: f,
      })));
    }
    
    return {
      id: node.id,
      name: node.name,
      type: 'dir',
      raw: node,
      children
    };
  };

  const rootDirs = Array.isArray(data?.root_nodes)
    ? data.root_nodes
    : (Array.isArray(data?.directories) ? data.directories : []);

  if (!data || rootDirs.length === 0) return <div className="p-4 text-xs text-book-text-muted">无文件结构</div>;
  
  return (
    <div className="py-2">
      {rootDirs.map((dir: any) => (
        <TreeItem 
          key={`dir-${dir.id}`} 
          node={transform(dir)} 
          level={0} 
          onSelectFile={onSelectFile}
          onSelectDirectory={onSelectDirectory}
          expandAllToken={expandAllToken}
          collapseAllToken={collapseAllToken}
        />
      ))}
    </div>
  );
};
