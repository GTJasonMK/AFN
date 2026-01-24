import React, { useState } from 'react';
import { Folder, FileCode, ChevronRight, ChevronDown } from 'lucide-react';

interface TreeNode {
  id: string | number;
  name: string;
  type: 'dir' | 'file';
  children?: TreeNode[];
}

interface DirectoryTreeProps {
  data: any; // Raw API response
  onSelectFile: (fileId: number) => void;
}

const TreeItem: React.FC<{ node: TreeNode; level: number; onSelect: (id: number) => void }> = ({ node, level, onSelect }) => {
  const [isOpen, setIsOpen] = useState(false);
  const isDir = node.type === 'dir';
  
  const handleClick = () => {
    if (isDir) {
      setIsOpen(!isOpen);
    } else {
      onSelect(node.id as number);
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
            <TreeItem key={`${child.type}-${child.id}`} node={child} level={level + 1} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  );
};

export const DirectoryTree: React.FC<DirectoryTreeProps> = ({ data, onSelectFile }) => {
  // Transform backend data to TreeNode if needed
  // Backend returns: { root: { ... } } or list
  // Let's assume we receive the raw tree from `getDirectoryTree` API
  
  const transform = (node: any): TreeNode => {
    const children: TreeNode[] = [];
    if (node.children) {
      children.push(...node.children.map((c: any) => transform(c)));
    }
    if (node.files) {
      children.push(...node.files.map((f: any) => ({
        id: f.id,
        name: f.filename,
        type: 'file'
      })));
    }
    
    return {
      id: node.id,
      name: node.name,
      type: 'dir',
      children
    };
  };

  if (!data || !data.directories) return <div className="p-4 text-xs text-book-text-muted">无文件结构</div>;

  // The API returns { directories: [...], files: [...] } usually for flat list or nested
  // Let's assume `data` is the `DirectoryTreeResponse` which has a list of root directories
  
  return (
    <div className="py-2">
      {data.directories.map((dir: any) => (
        <TreeItem 
          key={`dir-${dir.id}`} 
          node={transform(dir)} 
          level={0} 
          onSelect={onSelectFile} 
        />
      ))}
    </div>
  );
};
