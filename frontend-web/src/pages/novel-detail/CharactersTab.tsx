import React, { lazy, Suspense } from 'react';
import { Users, Plus, FileText, Trash2 } from 'lucide-react';
import { BookButton } from '../../components/ui/BookButton';
import { BookCard } from '../../components/ui/BookCard';

const CharacterPortraitGalleryLazy = lazy(() =>
  import('../../components/business/CharacterPortraitGallery').then((m) => ({ default: m.CharacterPortraitGallery }))
);

type CharactersView = 'info' | 'portraits';

export type CharactersTabProps = {
  projectId: string;
  charactersList: any[];
  visibleCharacters: any[];
  remainingCharacters: number;
  charactersView: CharactersView;
  setCharactersView: (view: CharactersView) => void;
  handleAddChar: () => void | Promise<void>;
  handleEditChar: (index: number) => void | Promise<void>;
  handleDeleteChar: (index: number) => void | Promise<void>;
  setCharactersRenderLimit: React.Dispatch<React.SetStateAction<number>>;
  renderBatchSize: number;
  characterNames: string[];
  characterProfiles: any;
};

export const CharactersTab: React.FC<CharactersTabProps> = ({
  projectId,
  charactersList,
  visibleCharacters,
  remainingCharacters,
  charactersView,
  setCharactersView,
  handleAddChar,
  handleEditChar,
  handleDeleteChar,
  setCharactersRenderLimit,
  renderBatchSize,
  characterNames,
  characterProfiles,
}) => {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h3 className="font-serif font-bold text-lg text-book-text-main">
            主要角色 ({charactersList.length})
          </h3>
          <div className="flex items-center gap-1 bg-book-bg-paper rounded-lg border border-book-border/40 p-1">
            <button
              className={`px-3 py-1 text-xs font-bold rounded-md transition-colors ${
                charactersView === 'info'
                  ? 'bg-book-bg text-book-primary'
                  : 'text-book-text-muted hover:text-book-text-main'
              }`}
              onClick={() => setCharactersView('info')}
            >
              基本信息
            </button>
            <button
              className={`px-3 py-1 text-xs font-bold rounded-md transition-colors ${
                charactersView === 'portraits'
                  ? 'bg-book-bg text-book-primary'
                  : 'text-book-text-muted hover:text-book-text-main'
              }`}
              onClick={() => setCharactersView('portraits')}
            >
              角色立绘
            </button>
          </div>
        </div>

        {charactersView === 'info' && (
          <BookButton size="sm" onClick={handleAddChar}>
            <Plus size={16} className="mr-1" /> 添加角色
          </BookButton>
        )}
      </div>

      {charactersView === 'portraits' ? (
        <Suspense fallback={<div className="text-sm text-book-text-muted">角色立绘加载中…</div>}>
          <CharacterPortraitGalleryLazy
            projectId={projectId}
            characterNames={characterNames}
            characterProfiles={characterProfiles}
          />
        </Suspense>
      ) : (
        <>
          {charactersList.length > 0 ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {visibleCharacters.map((char: any, idx: number) => (
                  <BookCard key={idx} className="p-5 hover:shadow-md transition-shadow group relative">
                    <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                      <button onClick={() => handleEditChar(idx)} className="p-1.5 rounded-full bg-book-bg hover:text-book-primary">
                        <FileText size={14} />
                      </button>
                      <button onClick={() => handleDeleteChar(idx)} className="p-1.5 rounded-full bg-book-bg hover:text-red-500">
                        <Trash2 size={14} />
                      </button>
                    </div>

                    <div className="flex justify-between items-start mb-3 border-b border-book-border/30 pb-2">
                      <h4 className="font-serif font-bold text-lg text-book-text-main truncate">{char.name || '（未命名）'}</h4>
                      {char.identity ? (
                        <span className="text-xs bg-book-bg px-2 py-1 rounded text-book-text-sub">{char.identity}</span>
                      ) : null}
                    </div>
                    <div className="space-y-2 text-sm text-book-text-secondary">
                      {char.personality ? (
                        <p className="line-clamp-2"><span className="font-bold text-book-text-muted">性格：</span>{char.personality}</p>
                      ) : null}
                      {char.goal ? (
                        <p className="line-clamp-2"><span className="font-bold text-book-text-muted">目标：</span>{char.goal}</p>
                      ) : null}
                      {char.ability ? (
                        <p className="line-clamp-2"><span className="font-bold text-book-text-muted">能力：</span>{char.ability}</p>
                      ) : null}
                    </div>
                  </BookCard>
                ))}
              </div>

              {remainingCharacters > 0 ? (
                <div className="flex justify-center">
                  <BookButton
                    size="sm"
                    variant="ghost"
                    onClick={() => setCharactersRenderLimit((prev) => prev + renderBatchSize)}
                  >
                    加载更多角色（剩余 {remainingCharacters}）
                  </BookButton>
                </div>
              ) : null}
            </>
          ) : (
            <div className="text-center py-20 text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30">
              <Users size={48} className="mx-auto mb-4 opacity-50" />
              <p>尚未添加角色。你可以点击右上角“添加角色”。</p>
            </div>
          )}
        </>
      )}
    </div>
  );
};
