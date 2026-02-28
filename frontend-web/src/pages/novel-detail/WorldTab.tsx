import React from 'react';
import { BookButton } from '../../components/ui/BookButton';
import { BookCard } from '../../components/ui/BookCard';
import { BookTextarea } from '../../components/ui/BookInput';

export type WorldEditMode = 'structured' | 'json';

export type WorldTabProps = {
  worldEditMode: WorldEditMode;
  setWorldEditMode: (mode: WorldEditMode) => void;
  worldSettingObj: any | null;
  worldListToText: (value: any) => string;
  worldTextToList: (text: string) => any;
  updateWorldSettingDraft: (patch: (obj: any) => void) => void;
  worldSettingDraft: string;
  setWorldSettingDraft: (text: string) => void;
  worldSettingError: string;
};

export const WorldTab: React.FC<WorldTabProps> = ({
  worldEditMode,
  setWorldEditMode,
  worldSettingObj,
  worldListToText,
  worldTextToList,
  updateWorldSettingDraft,
  worldSettingDraft,
  setWorldSettingDraft,
  worldSettingError,
}) => {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 space-y-6">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-serif font-bold text-lg text-book-text-main">世界观设定</h3>
        <div className="flex items-center gap-2">
          <BookButton
            size="sm"
            variant={worldEditMode === 'structured' ? 'primary' : 'ghost'}
            onClick={() => setWorldEditMode('structured')}
          >
            结构化
          </BookButton>
          <BookButton
            size="sm"
            variant={worldEditMode === 'json' ? 'primary' : 'ghost'}
            onClick={() => setWorldEditMode('json')}
          >
            JSON
          </BookButton>
        </div>
      </div>

      {worldEditMode === 'structured' ? (
        worldSettingObj ? (
          <>
            <BookCard className="p-6 space-y-4">
              <h4 className="font-serif font-bold text-base text-book-text-main border-b border-book-border/40 pb-2">
                核心规则
              </h4>
              <BookTextarea
                value={String(worldSettingObj.core_rules || '')}
                onChange={(e) => updateWorldSettingDraft((obj) => { obj.core_rules = e.target.value; })}
                className="min-h-[140px] text-base font-serif leading-relaxed"
                placeholder="例如：魔法来源/限制、社会规则、科技水平、禁忌与代价…"
              />
            </BookCard>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <BookCard className="p-6 space-y-4">
                <h4 className="font-serif font-bold text-base text-book-text-main border-b border-book-border/40 pb-2">
                  关键地点
                </h4>
                <div className="text-xs text-book-text-muted">
                  每行一条；可写“名称｜描述”（支持中文竖线或英文 |）。
                </div>
                <BookTextarea
                  value={worldListToText(worldSettingObj.key_locations)}
                  onChange={(e) => updateWorldSettingDraft((obj) => { obj.key_locations = worldTextToList(e.target.value); })}
                  className="min-h-[220px] text-sm font-mono leading-relaxed"
                  placeholder="王都｜政治中心，暗流涌动\n灰港｜走私与情报交易之城\n禁林"
                />
              </BookCard>

              <BookCard className="p-6 space-y-4">
                <h4 className="font-serif font-bold text-base text-book-text-main border-b border-book-border/40 pb-2">
                  主要阵营
                </h4>
                <div className="text-xs text-book-text-muted">
                  每行一条；可写“名称｜描述”（支持中文竖线或英文 |）。
                </div>
                <BookTextarea
                  value={worldListToText(worldSettingObj.factions)}
                  onChange={(e) => updateWorldSettingDraft((obj) => { obj.factions = worldTextToList(e.target.value); })}
                  className="min-h-[220px] text-sm font-mono leading-relaxed"
                  placeholder="学院派｜重视秩序与传承\n流亡者｜被放逐的旧贵族残党"
                />
              </BookCard>
            </div>

            <div className="text-xs text-book-text-muted bg-book-bg-paper rounded-lg border border-book-border/30 p-4 leading-relaxed">
              提示：结构化编辑只覆盖常用字段（core_rules/key_locations/factions）。如需编辑更多字段，可切换到 JSON 模式。
            </div>
          </>
        ) : (
          <BookCard className="p-6 space-y-3">
            <div className="font-bold text-book-text-main">世界观 JSON 无效</div>
            <div className="text-sm text-book-text-muted leading-relaxed">
              当前 world_setting 不是合法 JSON 对象，无法进行结构化编辑。请先切换到 JSON 模式修复格式。
            </div>
            <div className="flex justify-end">
              <BookButton size="sm" variant="primary" onClick={() => setWorldEditMode('json')}>
                切到 JSON
              </BookButton>
            </div>
          </BookCard>
        )
      ) : (
        <BookCard className="p-6 space-y-4">
          <h4 className="font-serif font-bold text-base text-book-text-main border-b border-book-border/40 pb-2">
            JSON（高级）
          </h4>
          <BookTextarea
            value={worldSettingDraft}
            onChange={(e) => setWorldSettingDraft(e.target.value)}
            error={worldSettingError || undefined}
            className="min-h-[520px] text-sm font-mono leading-relaxed"
            placeholder="请输入 JSON 对象（保存时会合并更新 world_setting）"
          />
        </BookCard>
      )}
    </div>
  );
};
