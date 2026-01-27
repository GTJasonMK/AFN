import React, { useMemo } from 'react';
import { Modal } from '../ui/Modal';
import { BookButton } from '../ui/BookButton';
import { BookCard } from '../ui/BookCard';
import { useToast } from '../feedback/Toast';

interface PartOutlineDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  part: any | null;
}

const safeJson = (value: any) => {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value ?? '');
  }
};

export const PartOutlineDetailModal: React.FC<PartOutlineDetailModalProps> = ({ isOpen, onClose, part }) => {
  const { addToast } = useToast();

  const partNumber = Number(part?.part_number || 0);
  const startChapter = Number(part?.start_chapter || 0);
  const endChapter = Number(part?.end_chapter || 0);

  const status = String(part?.generation_status || '');
  const progress = Number(part?.progress ?? 0);
  const statusLabel = useMemo(() => {
    if (status === 'completed') return '已完成';
    if (status === 'generating') return `生成中 ${progress}%`;
    if (status === 'failed') return '失败';
    if (status === 'cancelled') return '已取消';
    if (status === 'cancelling') return '取消中';
    return '待生成';
  }, [progress, status]);

  const keyEvents = useMemo(() => {
    const list = Array.isArray(part?.key_events) ? part.key_events : [];
    return list
      .map((item: any) => {
        if (typeof item === 'string') {
          const text = item.trim();
          return text ? { title: text } : null;
        }
        if (!item || typeof item !== 'object') return null;
        const chapter = typeof item.chapter === 'string' ? item.chapter.trim() : '';
        const title = typeof item.event === 'string' ? item.event.trim() : '';
        const desc = typeof item.description === 'string' ? item.description.trim() : '';
        if (!chapter && !title && !desc) return null;
        return { chapter, title, desc };
      })
      .filter(Boolean) as Array<{ chapter?: string; title?: string; desc?: string }>;
  }, [part]);

  const conflicts = useMemo(() => {
    const list = Array.isArray(part?.conflicts) ? part.conflicts : [];
    return list
      .map((item: any) => {
        if (typeof item === 'string') {
          const text = item.trim();
          return text ? { type: '', description: text, characters: [] as string[] } : null;
        }
        if (!item || typeof item !== 'object') return null;
        const type = typeof item.type === 'string' ? item.type.trim() : '';
        const description = typeof item.description === 'string' ? item.description.trim() : '';
        const characters = Array.isArray(item.characters)
          ? item.characters.map((c: any) => String(c || '').trim()).filter(Boolean)
          : [];
        if (!type && !description && characters.length === 0) return null;
        return { type, description, characters };
      })
      .filter(Boolean) as Array<{ type: string; description: string; characters: string[] }>;
  }, [part]);

  const characterArcs = useMemo(() => {
    const arcs = part?.character_arcs && typeof part.character_arcs === 'object' ? part.character_arcs : {};
    return Object.entries(arcs as Record<string, any>)
      .map(([name, desc]) => ({ name: String(name || '').trim(), desc: String(desc || '').trim() }))
      .filter((it) => it.name && it.desc);
  }, [part]);

  const endingHook = String(part?.ending_hook || '').trim();

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(safeJson(part));
      addToast('已复制 JSON', 'success');
    } catch (e) {
      console.error(e);
      addToast('复制失败（可能被浏览器限制）', 'error');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={partNumber ? `部分大纲详情 - 第${partNumber}部分` : '部分大纲详情'}
      maxWidthClassName="max-w-3xl"
      footer={
        <div className="flex justify-end gap-2">
          <BookButton variant="ghost" onClick={onClose}>关闭</BookButton>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-2">
          <div className="text-xs text-book-text-muted">
            {startChapter && endChapter ? (
              <span>章节 {startChapter}–{endChapter} · {statusLabel}</span>
            ) : (
              <span>{statusLabel}</span>
            )}
          </div>
          <BookButton variant="ghost" size="sm" onClick={handleCopy}>复制JSON</BookButton>
        </div>

        {String(part?.theme || '').trim() ? (
          <BookCard className="p-4">
            <div className="text-sm font-bold text-book-text-main mb-2">主题</div>
            <div className="text-sm text-book-text-secondary whitespace-pre-wrap leading-relaxed">
              {String(part.theme || '').trim()}
            </div>
          </BookCard>
        ) : null}

        {String(part?.summary || '').trim() ? (
          <BookCard className="p-4">
            <div className="text-sm font-bold text-book-text-main mb-2">剧情摘要</div>
            <div className="text-sm text-book-text-secondary whitespace-pre-wrap leading-relaxed">
              {String(part.summary || '').trim()}
            </div>
          </BookCard>
        ) : null}

        {keyEvents.length ? (
          <BookCard className="p-4">
            <div className="text-sm font-bold text-book-text-main mb-2">关键事件</div>
            <div className="space-y-2">
              {keyEvents.map((evt, idx) => (
                <div key={`${idx}-${evt.title || evt.desc || 'evt'}`} className="text-sm text-book-text-secondary">
                  <div className="font-bold">
                    {evt.chapter ? <span className="mr-2 text-book-text-muted">[{evt.chapter}]</span> : null}
                    {evt.title || evt.desc || '（未命名事件）'}
                  </div>
                  {evt.desc && evt.title ? (
                    <div className="mt-1 whitespace-pre-wrap leading-relaxed">{evt.desc}</div>
                  ) : null}
                </div>
              ))}
            </div>
          </BookCard>
        ) : null}

        {characterArcs.length ? (
          <BookCard className="p-4">
            <div className="text-sm font-bold text-book-text-main mb-2">角色发展</div>
            <div className="space-y-2">
              {characterArcs.map((a) => (
                <div key={a.name} className="text-sm text-book-text-secondary">
                  <div className="font-bold text-book-text-main">{a.name}</div>
                  <div className="mt-1 whitespace-pre-wrap leading-relaxed">{a.desc}</div>
                </div>
              ))}
            </div>
          </BookCard>
        ) : null}

        {conflicts.length ? (
          <BookCard className="p-4">
            <div className="text-sm font-bold text-book-text-main mb-2">冲突</div>
            <div className="space-y-2">
              {conflicts.map((c, idx) => (
                <div key={`${idx}-${c.type || c.description}`} className="text-sm text-book-text-secondary">
                  <div className="font-bold">
                    {c.type ? <span className="mr-2 text-book-text-main">{c.type}</span> : null}
                    {c.description}
                  </div>
                  {c.characters.length ? (
                    <div className="mt-1 text-xs text-book-text-muted">
                      涉及角色：{c.characters.join('、')}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </BookCard>
        ) : null}

        {endingHook ? (
          <BookCard className="p-4">
            <div className="text-sm font-bold text-book-text-main mb-2">与下一部分衔接点</div>
            <div className="text-sm text-book-text-secondary whitespace-pre-wrap leading-relaxed">
              {endingHook}
            </div>
          </BookCard>
        ) : null}
      </div>
    </Modal>
  );
};

