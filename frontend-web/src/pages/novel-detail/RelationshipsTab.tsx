import React from 'react';
import { Link2, Plus, FileText, Trash2 } from 'lucide-react';
import { BookButton } from '../../components/ui/BookButton';
import { BookCard } from '../../components/ui/BookCard';

export type RelationshipsTabProps = {
  relationshipsList: any[];
  visibleRelationships: any[];
  remainingRelationships: number;
  handleAddRel: () => void | Promise<void>;
  handleEditRel: (index: number) => void | Promise<void>;
  handleDeleteRel: (index: number) => void | Promise<void>;
  setRelationshipsRenderLimit: React.Dispatch<React.SetStateAction<number>>;
  renderBatchSize: number;
};

export const RelationshipsTab: React.FC<RelationshipsTabProps> = ({
  relationshipsList,
  visibleRelationships,
  remainingRelationships,
  handleAddRel,
  handleEditRel,
  handleDeleteRel,
  setRelationshipsRenderLimit,
  renderBatchSize,
}) => {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-serif font-bold text-lg text-book-text-main">
          关系网 ({relationshipsList.length})
        </h3>
        <BookButton size="sm" onClick={handleAddRel}>
          <Plus size={16} className="mr-1" /> 添加关系
        </BookButton>
      </div>

      {relationshipsList.length > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {visibleRelationships.map((rel: any, idx: number) => (
              <BookCard key={idx} className="p-5 hover:shadow-md transition-shadow group relative">
                <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                  <button onClick={() => handleEditRel(idx)} className="p-1.5 rounded-full bg-book-bg hover:text-book-primary">
                    <FileText size={14} />
                  </button>
                  <button onClick={() => handleDeleteRel(idx)} className="p-1.5 rounded-full bg-book-bg hover:text-red-500">
                    <Trash2 size={14} />
                  </button>
                </div>

                <div className="flex items-center gap-2 font-bold text-book-text-main">
                  <span className="truncate">{rel.character_from}</span>
                  <span className="text-book-text-muted">→</span>
                  <span className="truncate">{rel.character_to}</span>
                </div>
                <div className="mt-2 text-sm text-book-text-secondary whitespace-pre-wrap leading-relaxed">
                  {rel.description || '（无描述）'}
                </div>
              </BookCard>
            ))}
          </div>

          {remainingRelationships > 0 ? (
            <div className="flex justify-center">
              <BookButton
                size="sm"
                variant="ghost"
                onClick={() => setRelationshipsRenderLimit((prev) => prev + renderBatchSize)}
              >
                加载更多关系（剩余 {remainingRelationships}）
              </BookButton>
            </div>
          ) : null}
        </>
      ) : (
        <div className="text-center py-20 text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30">
          <Link2 size={48} className="mx-auto mb-4 opacity-50" />
          <p>尚未添加角色关系。你可以先从“角色”里补齐人物，再在此建立关系网。</p>
        </div>
      )}
    </div>
  );
};
