import React from 'react';
import { Copy, Info } from 'lucide-react';
import { BookCard } from '../../ui/BookCard';
import { BookButton } from '../../ui/BookButton';
import { safeJson } from './shared';

type CharacterProfileItem = {
  name: string;
  desc: string;
};

type MangaDetailsTabProps = {
  sortedCharacterProfiles: CharacterProfileItem[];
  analysisData: any;
  chapterInfo: any;
  pagePlan: any;
  onCopyText: (text: string, label: string) => void | Promise<void>;
};

export const MangaDetailsTab: React.FC<MangaDetailsTabProps> = ({
  sortedCharacterProfiles,
  analysisData,
  chapterInfo,
  pagePlan,
  onCopyText,
}) => {
  return (
    <div className="space-y-4">
      {sortedCharacterProfiles.length > 0 && (
        <BookCard className="p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <div className="font-bold text-book-text-main">角色外观（提示词）</div>
            <BookButton
              variant="ghost"
              size="sm"
              onClick={() =>
                onCopyText(
                  safeJson(Object.fromEntries(sortedCharacterProfiles.map((item) => [item.name, item.desc]))),
                  '角色外观JSON',
                )
              }
            >
              <Copy size={14} className="mr-1" />
              复制JSON
            </BookButton>
          </div>
          <div className="space-y-3">
            {sortedCharacterProfiles.map((item) => (
              <div key={item.name} className="rounded-lg border border-book-border/40 bg-book-bg p-3">
                <div className="font-bold text-book-primary">{item.name}</div>
                <div className="mt-2 whitespace-pre-wrap font-mono text-xs leading-relaxed text-book-text-main">
                  {item.desc}
                </div>
              </div>
            ))}
          </div>
        </BookCard>
      )}

      {!analysisData && (
        <BookCard className="p-4">
          <div className="flex items-start gap-2 text-xs leading-relaxed text-book-text-muted">
            <Info size={16} className="mt-0.5 flex-none" />
            <div>
              暂无详细信息（analysis_data）。生成分镜后，如果后端返回分析数据，这里会展示“信息提取/页面规划”等结构化结果。
            </div>
          </div>
        </BookCard>
      )}

      {analysisData && (
        <div className="space-y-3">
          <details className="group rounded-lg border border-book-border/40 bg-book-bg-paper">
            <summary className="cursor-pointer select-none px-4 py-3 font-bold text-book-text-main">
              步骤1：信息提取
            </summary>
            <div className="space-y-3 px-4 pb-4">
              {chapterInfo?.chapter_summary ? (
                <BookCard className="border-book-border/50 bg-book-bg/50 p-3">
                  <div className="mb-1 text-xs font-bold text-book-text-sub">章节摘要</div>
                  <div className="whitespace-pre-wrap text-sm leading-relaxed text-book-text-main">
                    {String(chapterInfo.chapter_summary)}
                  </div>
                </BookCard>
              ) : null}

              {chapterInfo?.characters && typeof chapterInfo.characters === 'object' && !Array.isArray(chapterInfo.characters) ? (
                <BookCard className="border-book-border/50 bg-book-bg/50 p-3">
                  <div className="mb-2 text-xs font-bold text-book-text-sub">角色信息</div>
                  <div className="space-y-2">
                    {Object.entries(chapterInfo.characters as Record<string, any>).map(([name, value]) => (
                      <div key={name} className="rounded-lg border border-book-border/40 bg-book-bg p-2">
                        <div className="text-sm font-bold text-book-primary">{name}</div>
                        <div className="mt-1 whitespace-pre-wrap text-xs leading-relaxed text-book-text-main">
                          {typeof value === 'string' ? value : safeJson(value)}
                        </div>
                      </div>
                    ))}
                  </div>
                </BookCard>
              ) : null}

              {Array.isArray(chapterInfo?.events) && chapterInfo.events.length > 0 ? (
                <BookCard className="border-book-border/50 bg-book-bg/50 p-3">
                  <div className="mb-2 text-xs font-bold text-book-text-sub">事件列表</div>
                  <ul className="list-inside list-decimal space-y-1 text-xs text-book-text-main">
                    {chapterInfo.events.map((event: any, idx: number) => (
                      <li key={`evt-${idx}`} className="whitespace-pre-wrap">
                        {typeof event === 'string' ? event : safeJson(event)}
                      </li>
                    ))}
                  </ul>
                </BookCard>
              ) : null}

              {Array.isArray(chapterInfo?.dialogues) && chapterInfo.dialogues.length > 0 ? (
                <BookCard className="border-book-border/50 bg-book-bg/50 p-3">
                  <div className="mb-2 text-xs font-bold text-book-text-sub">对话列表</div>
                  <div className="space-y-2">
                    {chapterInfo.dialogues.map((dialogue: any, idx: number) => {
                      const speaker = String(dialogue?.speaker || dialogue?.character || '').trim();
                      const text = String(dialogue?.text || dialogue?.content || '').trim();
                      return (
                        <div key={`dlg-${idx}`} className="rounded-lg border border-book-border/40 bg-book-bg p-2">
                          <div className="font-mono text-[11px] text-book-text-muted">
                            {speaker ? `speaker: ${speaker}` : 'speaker: —'}
                          </div>
                          <div className="mt-1 whitespace-pre-wrap text-xs leading-relaxed text-book-text-main">
                            {text || (typeof dialogue === 'string' ? dialogue : safeJson(dialogue))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </BookCard>
              ) : null}

              {Array.isArray(chapterInfo?.scenes) && chapterInfo.scenes.length > 0 ? (
                <BookCard className="border-book-border/50 bg-book-bg/50 p-3">
                  <div className="mb-2 text-xs font-bold text-book-text-sub">场景列表</div>
                  <ul className="list-inside list-disc space-y-1 text-xs text-book-text-main">
                    {chapterInfo.scenes.map((scene: any, idx: number) => (
                      <li key={`scene-${idx}`} className="whitespace-pre-wrap">
                        {typeof scene === 'string' ? scene : safeJson(scene)}
                      </li>
                    ))}
                  </ul>
                </BookCard>
              ) : null}
            </div>
          </details>

          <details className="group rounded-lg border border-book-border/40 bg-book-bg-paper">
            <summary className="cursor-pointer select-none px-4 py-3 font-bold text-book-text-main">
              步骤2：页面规划
            </summary>
            <div className="space-y-3 px-4 pb-4">
              {Array.isArray(pagePlan?.pages) && pagePlan.pages.length > 0 ? (
                <BookCard className="border-book-border/50 bg-book-bg/50 p-3">
                  <div className="mb-2 text-xs font-bold text-book-text-sub">页面分配</div>
                  <div className="space-y-2">
                    {pagePlan.pages.map((page: any, idx: number) => (
                      <div key={`pp-${idx}`} className="rounded-lg border border-book-border/40 bg-book-bg p-2">
                        <div className="text-xs font-bold text-book-primary">
                          第 {page?.page_number ?? idx + 1} 页
                        </div>
                        <div className="mt-1 whitespace-pre-wrap text-xs leading-relaxed text-book-text-main">
                          {page?.layout_description ? String(page.layout_description) : safeJson(page)}
                        </div>
                      </div>
                    ))}
                  </div>
                </BookCard>
              ) : (
                <BookCard className="border-book-border/50 bg-book-bg/50 p-3">
                  <div className="text-xs text-book-text-muted">无页面规划数据（page_plan.pages）。</div>
                </BookCard>
              )}
            </div>
          </details>

          <details className="group rounded-lg border border-book-border/40 bg-book-bg-paper">
            <summary className="cursor-pointer select-none px-4 py-3 font-bold text-book-text-main">
              原始数据（JSON）
            </summary>
            <div className="space-y-2 px-4 pb-4">
              <div className="flex justify-end">
                <BookButton
                  variant="secondary"
                  size="sm"
                  onClick={() => onCopyText(safeJson(analysisData), 'analysis_data')}
                >
                  <Copy size={14} className="mr-1" />
                  复制
                </BookButton>
              </div>
              <pre className="overflow-auto rounded-lg border border-book-border/40 bg-book-bg p-3 font-mono text-xs leading-relaxed text-book-text-main whitespace-pre-wrap">
                {safeJson(analysisData)}
              </pre>
            </div>
          </details>
        </div>
      )}
    </div>
  );
};
