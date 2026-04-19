import React from 'react';
import { Edit3 } from 'lucide-react';
import type {
  ThemeConfigListItem,
  ThemeConfigUnifiedRead,
} from '../../../../api/themeConfigs';
import type { WebAppearanceConfig } from '../../../../theme/webAppearance';
import { BookButton } from '../../../ui/BookButton';
import { BookCard } from '../../../ui/BookCard';
import { BookInput } from '../../../ui/BookInput';
import { BookSlider } from '../../../ui/BookSlider';
import { Dropdown } from '../../../ui/Dropdown';
import {
  formatDate,
  formatThemeMode,
  formatTime,
  type ThemeActionMenuItem,
} from './shared';

interface ThemeTabDetailPanelProps {
  selectedItem: ThemeConfigListItem | null;
  selectedUnified: ThemeConfigUnifiedRead | null;
  selectedLoading: boolean;
  previewStyle?: React.CSSProperties;
  appearance: WebAppearanceConfig;
  appearanceDirty: boolean;
  activatingId: number | null;
  busyId: number | null;
  onActivate: (id: number) => void;
  onOpenEditor: (id: number) => void;
  onAppearanceEnabledChange: (enabled: boolean) => void;
  onAppearanceBackgroundImageUrlChange: (value: string) => void;
  onAppearanceBlurChange: (value: number) => void;
  onAppearanceOverlayChange: (value: number) => void;
  getThemeMenuItems: (cfg: ThemeConfigListItem) => ThemeActionMenuItem[];
}

export const ThemeTabDetailPanel: React.FC<ThemeTabDetailPanelProps> = ({
  selectedItem,
  selectedUnified,
  selectedLoading,
  previewStyle,
  appearance,
  appearanceDirty,
  activatingId,
  busyId,
  onActivate,
  onOpenEditor,
  onAppearanceEnabledChange,
  onAppearanceBackgroundImageUrlChange,
  onAppearanceBlurChange,
  onAppearanceOverlayChange,
  getThemeMenuItems,
}) => {
  return (
    <section className="min-h-0 flex flex-col">
      <div className="shrink-0 border-b border-book-border/45 bg-book-bg/40 p-4">
        {!selectedItem ? (
          <div className="text-sm text-book-text-muted">
            请选择一个主题配置
          </div>
        ) : (
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <div className="max-w-full truncate text-sm font-bold text-book-text-main">
                  {selectedItem.config_name}
                </div>
                <span className="inline-flex rounded-full border border-book-border/55 bg-book-bg-paper/80 px-2.5 py-1 text-[10px] font-bold text-book-text-muted">
                  {formatThemeMode(selectedItem.parent_mode)}
                </span>
                {selectedItem.is_active ? (
                  <span className="inline-flex rounded-full border border-book-primary/25 bg-book-primary/10 px-2.5 py-1 text-[10px] font-bold text-book-primary">
                    当前已激活
                  </span>
                ) : null}
              </div>
              <div className="mt-1 text-[11px] text-book-text-muted">
                创建：{formatDate(selectedItem.created_at)} · 更新：
                {formatDate(selectedItem.updated_at)}
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-end gap-2">
              {!selectedItem.is_active ? (
                <BookButton
                  variant="primary"
                  size="sm"
                  onClick={() => onActivate(selectedItem.id)}
                  disabled={
                    activatingId === selectedItem.id || busyId === selectedItem.id
                  }
                >
                  {activatingId === selectedItem.id ? '切换中…' : '激活'}
                </BookButton>
              ) : null}
              <BookButton
                variant="secondary"
                size="sm"
                onClick={() => onOpenEditor(selectedItem.id)}
                disabled={busyId === selectedItem.id}
              >
                <Edit3 size={14} className="mr-1" />
                编辑
              </BookButton>
              <Dropdown items={getThemeMenuItems(selectedItem)} label="更多" />
            </div>
          </div>
        )}
      </div>

      <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto p-4 pr-1">
        {!selectedItem ? (
          <div className="flex h-full items-center justify-center text-book-text-muted">
            从左侧选择一个主题
          </div>
        ) : selectedLoading ? (
          <div className="py-10 text-center text-sm text-book-text-muted">
            加载主题详情…
          </div>
        ) : selectedUnified ? (
          <div className="space-y-4">
            <div className="rounded-[24px] border border-book-border/45 bg-book-bg-paper/50 p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="text-xs font-bold text-book-text-sub">概览</div>
                <div className="text-[10px] text-book-text-muted">
                  V{selectedUnified.config_version || 1}
                </div>
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <div className="rounded-[22px] border border-book-border/45 bg-book-bg/50 px-4 py-3">
                  <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                    Mode
                  </div>
                  <div className="mt-2 text-sm font-bold text-book-text-main">
                    {selectedUnified.parent_mode === 'dark' ? 'Dark' : 'Light'}
                  </div>
                  <div className="mt-1 text-[11px] text-book-text-muted">
                    影响 {formatThemeMode(selectedUnified.parent_mode)}外观
                  </div>
                </div>
                <div className="rounded-[22px] border border-book-border/45 bg-book-bg/50 px-4 py-3">
                  <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                    Version
                  </div>
                  <div className="mt-2 text-sm font-bold text-book-text-main">
                    V{selectedUnified.config_version || 1}
                  </div>
                  <div className="mt-1 text-[11px] text-book-text-muted">
                    {Number(selectedUnified.config_version || 1) === 2
                      ? '组件/令牌结构'
                      : '传统字段结构'}
                  </div>
                </div>
                <div className="rounded-[22px] border border-book-border/45 bg-book-bg/50 px-4 py-3">
                  <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                    Created
                  </div>
                  <div className="mt-2 text-sm font-bold text-book-text-main">
                    {formatDate(selectedUnified.created_at)}
                  </div>
                  <div className="mt-1 text-[11px] text-book-text-muted">
                    {formatTime(selectedUnified.created_at)}
                  </div>
                </div>
                <div className="rounded-[22px] border border-book-border/45 bg-book-bg/50 px-4 py-3">
                  <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                    Updated
                  </div>
                  <div className="mt-2 text-sm font-bold text-book-text-main">
                    {formatDate(selectedUnified.updated_at)}
                  </div>
                  <div className="mt-1 text-[11px] text-book-text-muted">
                    {formatTime(selectedUnified.updated_at)}
                  </div>
                </div>
              </div>
            </div>

            <div
              className={`rounded-[24px] border border-book-border/45 bg-book-bg-paper/50 p-4 ${
                selectedUnified.parent_mode === 'dark' ? 'dark' : ''
              }`}
              style={previewStyle}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="text-xs font-bold text-book-text-sub">
                  预览（局部）
                </div>
                <div className="text-[10px] text-book-text-muted">
                  不会影响整体界面
                </div>
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <BookCard variant="glass" className="p-4">
                  <div className="text-xs font-bold text-book-text-main">
                    玻璃卡片
                  </div>
                  <div className="mt-1 text-[11px] leading-relaxed text-book-text-sub">
                    检查在当前主题下的对比度与层次。
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <BookButton size="sm" variant="primary">
                      主按钮
                    </BookButton>
                    <BookButton size="sm" variant="secondary">
                      次按钮
                    </BookButton>
                  </div>
                </BookCard>
                <div className="rounded-[24px] border border-book-border/45 bg-book-bg/55 p-4">
                  <div className="text-xs font-bold text-book-text-main">
                    控件
                  </div>
                  <div className="mt-3 space-y-3">
                    <BookInput
                      placeholder="输入框预览…"
                      className="py-2 text-xs"
                    />
                    <div className="flex flex-wrap gap-2">
                      <span className="inline-flex items-center rounded-full border border-book-border/55 bg-book-bg-paper/70 px-3 py-1 text-[10px] font-semibold text-book-text-muted">
                        tag
                      </span>
                      <span className="inline-flex items-center rounded-full border border-book-primary/25 bg-book-primary/10 px-3 py-1 text-[10px] font-bold text-book-primary">
                        active
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-[24px] border border-book-border/45 bg-book-bg-paper/50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="text-xs font-bold text-book-text-sub">
                    背景与玻璃效果
                  </div>
                  {appearanceDirty ? (
                    <span className="inline-flex rounded-full border border-book-primary/25 bg-book-primary/10 px-2.5 py-1 text-[10px] font-bold text-book-primary">
                      未应用
                    </span>
                  ) : (
                    <span className="inline-flex rounded-full border border-book-border/55 bg-book-bg-paper/70 px-2.5 py-1 text-[10px] font-semibold text-book-text-muted">
                      已应用
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-book-text-muted">
                  应用按钮在右下角
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <label className="flex items-center gap-2 text-xs font-bold text-book-text-sub">
                  <input
                    type="checkbox"
                    checked={Boolean(appearance.enabled)}
                    onChange={(event) =>
                      onAppearanceEnabledChange(event.target.checked)
                    }
                    className="book-check h-4 w-4 rounded border-book-border/60 bg-book-bg-paper/80"
                  />
                  启用背景图
                </label>

                <div className="sm:col-span-2">
                  <div className="text-[11px] font-bold text-book-text-sub">
                    背景图 URL
                  </div>
                  <input
                    type="text"
                    value={appearance.backgroundImageUrl || ''}
                    onChange={(event) =>
                      onAppearanceBackgroundImageUrlChange(event.target.value)
                    }
                    placeholder="https://..."
                    className="book-control mt-1 w-full rounded-2xl border px-4 py-2 text-xs text-book-text-main outline-none focus:border-book-primary/50"
                  />
                </div>

                <BookSlider
                  label="模糊（px）"
                  min={0}
                  max={48}
                  step={1}
                  value={Number(appearance.blurPx) || 0}
                  onChange={onAppearanceBlurChange}
                  formatValue={(value) => `${Math.round(value)}px`}
                  numberInputWidthClassName="w-20"
                />

                <BookSlider
                  label="遮罩不透明度（0~1）"
                  min={0}
                  max={1}
                  step={0.05}
                  value={Number(appearance.overlayOpacity) || 0}
                  onChange={onAppearanceOverlayChange}
                  formatValue={(value) => value.toFixed(2)}
                  numberInputWidthClassName="w-20"
                />
              </div>

              {appearance.enabled &&
              (appearance.backgroundImageUrl || '').trim() ? (
                <div className="mt-4">
                  <div className="mb-1 text-[11px] text-book-text-muted">
                    预览
                  </div>
                  <div className="relative h-28 overflow-hidden rounded-2xl border border-book-border/40 bg-book-bg">
                    <div
                      className="absolute inset-0 bg-center bg-cover"
                      style={{
                        backgroundImage: `url(${String(
                          appearance.backgroundImageUrl || '',
                        ).trim()})`,
                        filter:
                          (Number(appearance.blurPx) || 0) > 0
                            ? `blur(${Math.max(
                                0,
                                Math.min(48, Number(appearance.blurPx) || 0),
                              )}px)`
                            : undefined,
                        transform:
                          (Number(appearance.blurPx) || 0) > 0
                            ? 'scale(1.05)'
                            : undefined,
                      }}
                    />
                    <div
                      className="absolute inset-0 bg-book-bg"
                      style={{
                        opacity: Math.max(
                          0,
                          Math.min(1, Number(appearance.overlayOpacity) || 0),
                        ),
                      }}
                    />
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        ) : (
          <div className="py-10 text-center text-sm text-book-text-muted">
            无法加载该主题详情
          </div>
        )}
      </div>
    </section>
  );
};
