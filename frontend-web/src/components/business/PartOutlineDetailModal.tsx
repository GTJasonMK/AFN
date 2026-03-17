import React, { useMemo } from 'react';
import { Modal } from '../ui/Modal';
import { BookButton } from '../ui/BookButton';
import { useToast } from '../feedback/Toast';
import {
  NovelDialogIntro,
  NovelDialogMetric,
  NovelDialogMetricGrid,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from './novel/NovelDialogPrimitives';

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
  const theme = String(part?.theme || '').trim();
  const summary = String(part?.summary || '').trim();

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
      {!part ? (
        <NovelDialogIntro
          eyebrow="Part Outline"
          title="暂无可展示的部分大纲"
          tone="warning"
          description="当前没有选中的部分数据，或数据尚未加载完成。返回列表后重新选择一个部分即可查看详情。"
        />
      ) : (
        <NovelDialogStack>
          <NovelDialogIntro
            eyebrow="Part Outline"
            title={partNumber ? `第 ${partNumber} 部分详情` : '部分大纲详情'}
            description="这里展示当前部分的主题、摘要、关键事件、角色推进与冲突结构，适合在重写前快速核对结构完整性。"
          >
            <div className="flex flex-wrap gap-2">
              {startChapter && endChapter ? <span className="story-pill">章节 {startChapter} - {endChapter}</span> : null}
              <span className="story-pill">{statusLabel}</span>
            </div>
          </NovelDialogIntro>

          <NovelDialogMetricGrid>
            <NovelDialogMetric
              label="章节范围"
              value={startChapter && endChapter ? `${startChapter}-${endChapter}` : '未标注'}
              note="用于确认该部分覆盖的叙事区间是否与预期一致。"
            />
            <NovelDialogMetric
              label="结构状态"
              value={statusLabel}
              note={status === 'generating' ? `当前进度 ${progress}%` : '可复制 JSON 以便归档或排查。'}
            />
          </NovelDialogMetricGrid>

          <NovelDialogSection
            eyebrow="Overview"
            title="部分概览"
            description="先从主题和摘要快速判断这一部分的叙事重心。"
            actions={(
              <BookButton variant="ghost" size="sm" onClick={handleCopy}>
                复制JSON
              </BookButton>
            )}
          >
            {theme || summary ? (
              <div className="grid gap-3 md:grid-cols-2">
                {theme ? (
                  <NovelDialogSurface>
                    <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">Theme</div>
                    <div className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-book-text-main">{theme}</div>
                  </NovelDialogSurface>
                ) : null}
                {summary ? (
                  <NovelDialogSurface>
                    <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">Summary</div>
                    <div className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-book-text-main">{summary}</div>
                  </NovelDialogSurface>
                ) : null}
              </div>
            ) : (
              <NovelDialogSurface className="text-sm text-book-text-muted">
                当前部分尚未生成主题与剧情摘要。
              </NovelDialogSurface>
            )}
          </NovelDialogSection>

          {keyEvents.length ? (
            <NovelDialogSection
              eyebrow="Key Events"
              title="关键事件"
              description="按事件粒度查看这一部分的主要推进节点。"
            >
              <div className="space-y-3">
                {keyEvents.map((evt, idx) => (
                  <NovelDialogSurface key={`${idx}-${evt.title || evt.desc || 'evt'}`}>
                    <div className="text-sm font-semibold text-book-text-main">
                      {evt.chapter ? <span className="mr-2 text-book-text-muted">[{evt.chapter}]</span> : null}
                      {evt.title || evt.desc || '（未命名事件）'}
                    </div>
                    {evt.desc && evt.title ? (
                      <div className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-book-text-sub">{evt.desc}</div>
                    ) : null}
                  </NovelDialogSurface>
                ))}
              </div>
            </NovelDialogSection>
          ) : null}

          {(characterArcs.length || conflicts.length) ? (
            <NovelDialogSection
              eyebrow="Dynamics"
              title="人物推进与冲突"
              description="这两组信息决定了部分内部的人物变化密度和情节张力。"
            >
              <div className="grid gap-3 lg:grid-cols-2">
                <NovelDialogSurface>
                  <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">Character Arcs</div>
                  {characterArcs.length ? (
                    <div className="mt-3 space-y-3">
                      {characterArcs.map((arc) => (
                        <div key={arc.name}>
                          <div className="text-sm font-semibold text-book-text-main">{arc.name}</div>
                          <div className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-book-text-sub">{arc.desc}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="mt-3 text-sm text-book-text-muted">当前没有记录角色发展线。</div>
                  )}
                </NovelDialogSurface>

                <NovelDialogSurface>
                  <div className="text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">Conflicts</div>
                  {conflicts.length ? (
                    <div className="mt-3 space-y-3">
                      {conflicts.map((conflictItem, idx) => (
                        <div key={`${idx}-${conflictItem.type || conflictItem.description}`}>
                          <div className="text-sm font-semibold text-book-text-main">
                            {conflictItem.type ? <span className="mr-2 text-book-text-muted">{conflictItem.type}</span> : null}
                            {conflictItem.description}
                          </div>
                          {conflictItem.characters.length ? (
                            <div className="mt-1 text-xs leading-relaxed text-book-text-muted">
                              涉及角色：{conflictItem.characters.join('、')}
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="mt-3 text-sm text-book-text-muted">当前没有记录冲突结构。</div>
                  )}
                </NovelDialogSurface>
              </div>
            </NovelDialogSection>
          ) : null}

          {endingHook ? (
            <NovelDialogSection
              eyebrow="Next Hook"
              title="与下一部分衔接点"
              description="检查这一部分结尾是否为下一部分留下了明确的情绪、事件或悬念接口。"
            >
              <NovelDialogSurface className="whitespace-pre-wrap text-sm leading-relaxed text-book-text-main">
                {endingHook}
              </NovelDialogSurface>
            </NovelDialogSection>
          ) : null}
        </NovelDialogStack>
      )}
    </Modal>
  );
};
