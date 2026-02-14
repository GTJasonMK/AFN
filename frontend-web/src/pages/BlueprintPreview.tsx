import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { novelsApi } from '../api/novels';
import { BookCard } from '../components/ui/BookCard';
import { BookButton } from '../components/ui/BookButton';
import { ArrowLeft, Map, Users, ScrollText, Play } from 'lucide-react';

interface BlueprintData {
  title?: string;
  one_sentence_summary?: string;
  world_setting?: any;
  characters?: Array<Record<string, any>>;
  full_synopsis?: string;
}

const INITIAL_PREVIEW_CHARACTER_LIMIT = 20;
const PREVIEW_CHARACTER_BATCH_SIZE = 20;

export const BlueprintPreview: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<BlueprintData | null>(null);
  const [loading, setLoading] = useState(true);
  const [characterRenderLimit, setCharacterRenderLimit] = useState(INITIAL_PREVIEW_CHARACTER_LIMIT);

  useEffect(() => {
    if (!id) {
      setLoading(false);
      setData(null);
      return;
    }

    let cancelled = false;
    setLoading(true);

    novelsApi
      .get(id)
      .then((project: any) => {
        if (cancelled) return;
        if (project?.blueprint) {
          setData(project.blueprint);
        } else {
          setData(null);
        }
      })
      .catch(() => {
        if (cancelled) return;
        setData(null);
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  const handleStartWriting = () => {
    navigate(`/write/${id}`);
  };

  const worldText = useMemo(() => {
    const raw = data?.world_setting;
    if (raw === null || raw === undefined) return '（空）';
    if (typeof raw === 'string') return raw;
    try {
      return JSON.stringify(raw, null, 2);
    } catch {
      return String(raw);
    }
  }, [data]);

  const synopsisText = useMemo(() => {
    const raw = data?.full_synopsis;
    if (raw === null || raw === undefined) return '（空）';
    return String(raw);
  }, [data]);

  const characters = useMemo(() => {
    return Array.isArray(data?.characters) ? data.characters : [];
  }, [data]);

  useEffect(() => {
    setCharacterRenderLimit(INITIAL_PREVIEW_CHARACTER_LIMIT);
  }, [id]);

  const visibleCharacters = useMemo(() => {
    return characters.slice(0, characterRenderLimit);
  }, [characterRenderLimit, characters]);

  const remainingCharacters = Math.max(0, characters.length - visibleCharacters.length);

  if (loading) return <div className="p-20 text-center text-book-text-muted">加载蓝图设定中...</div>;
  if (!data) return <div className="p-20 text-center text-book-text-muted">未找到蓝图数据</div>;

  return (
    <div className="max-w-5xl mx-auto p-8 space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex justify-between items-end border-b border-book-border pb-6">
        <div className="space-y-2">
          <button
            onClick={() => navigate(-1)}
            className="text-sm text-book-text-muted hover:text-book-primary flex items-center gap-1 transition-colors"
          >
            <ArrowLeft size={14} /> 返回
          </button>
          <h1 className="font-serif text-4xl font-bold text-book-text-main">{data.title || '未命名项目'}</h1>
          <p className="text-xl text-book-text-sub font-serif italic opacity-80">“{data.one_sentence_summary || '暂无一句话概要'}”</p>
        </div>
        <BookButton size="lg" onClick={handleStartWriting} className="mb-1">
          <Play size={18} className="mr-2 fill-current" /> 开始执笔
        </BookButton>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2 space-y-10">
          <section className="space-y-4">
            <h2 className="font-serif text-2xl font-bold text-book-text-main flex items-center gap-2">
              <Map className="text-book-primary" /> 世界观设定
            </h2>
            <BookCard variant="flat" className="bg-book-bg-paper/50 leading-relaxed text-book-text-secondary whitespace-pre-wrap">
              {worldText}
            </BookCard>
          </section>

          <section className="space-y-4">
            <h2 className="font-serif text-2xl font-bold text-book-text-main flex items-center gap-2">
              <ScrollText className="text-book-primary" /> 故事梗概
            </h2>
            <BookCard variant="flat" className="bg-book-bg-paper/50 leading-relaxed text-book-text-secondary whitespace-pre-wrap">
              {synopsisText}
            </BookCard>
          </section>
        </div>

        <div className="space-y-4">
          <h2 className="font-serif text-2xl font-bold text-book-text-main flex items-center gap-2">
            <Users className="text-book-primary" /> 登场角色
          </h2>
          <div className="space-y-4">
            {visibleCharacters.map((char, index) => (
              <BookCard key={String(char?.name || `char-${index}`)} className="hover:border-book-primary/30 transition-colors">
                <div className="font-bold text-book-text-main border-b border-book-border/30 pb-1 mb-2">
                  {String(char?.name || `角色 ${index + 1}`)}
                </div>
                <div className="text-xs space-y-1 text-book-text-sub">
                  {char?.identity ? <p><span className="font-semibold text-book-text-muted">身份：</span>{String(char.identity)}</p> : null}
                  {char?.personality ? <p><span className="font-semibold text-book-text-muted">性格：</span>{String(char.personality)}</p> : null}
                  {char?.goal ? <p><span className="font-semibold text-book-text-muted">目标：</span>{String(char.goal)}</p> : null}
                  {!char?.identity && !char?.personality && !char?.goal ? (
                    <pre className="whitespace-pre-wrap text-[11px] text-book-text-main leading-relaxed bg-book-bg p-2 rounded border border-book-border/40 overflow-auto">
                      {(() => {
                        try {
                          return JSON.stringify(char, null, 2);
                        } catch {
                          return String(char ?? '');
                        }
                      })()}
                    </pre>
                  ) : null}
                </div>
              </BookCard>
            ))}

            {remainingCharacters > 0 ? (
              <div className="flex justify-center pt-1">
                <BookButton
                  size="sm"
                  variant="ghost"
                  onClick={() => setCharacterRenderLimit((prev) => prev + PREVIEW_CHARACTER_BATCH_SIZE)}
                >
                  加载更多角色（剩余 {remainingCharacters}）
                </BookButton>
              </div>
            ) : null}

            {characters.length === 0 && (
              <BookCard className="p-4 text-xs text-book-text-muted">
                暂无角色信息。
              </BookCard>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
