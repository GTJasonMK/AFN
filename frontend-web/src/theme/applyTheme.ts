import { ThemeConfigUnifiedRead, ThemeMode } from '../api/themeConfigs';

type CssVarMap = Record<string, string>;

function clampByte(value: number): number {
  return Math.max(0, Math.min(255, Math.round(value)));
}

function hexToRgbTriplet(hex: string): string | null {
  const raw = hex.trim().replace(/^#/, '');
  if (!raw) return null;

  if (raw.length === 3) {
    const r = parseInt(raw[0] + raw[0], 16);
    const g = parseInt(raw[1] + raw[1], 16);
    const b = parseInt(raw[2] + raw[2], 16);
    if ([r, g, b].some((n) => Number.isNaN(n))) return null;
    return `${r} ${g} ${b}`;
  }

  if (raw.length === 6) {
    const r = parseInt(raw.slice(0, 2), 16);
    const g = parseInt(raw.slice(2, 4), 16);
    const b = parseInt(raw.slice(4, 6), 16);
    if ([r, g, b].some((n) => Number.isNaN(n))) return null;
    return `${r} ${g} ${b}`;
  }

  return null;
}

function parseRgbLikeToTriplet(value: string): string | null {
  const v = value.trim();
  if (!v) return null;

  // 已经是 “R G B” 形式
  if (/^\d+\s+\d+\s+\d+(\s+\/\s*[\d.]+)?$/.test(v)) {
    const parts = v.split(/\s+/).filter(Boolean);
    if (parts.length >= 3) return `${parts[0]} ${parts[1]} ${parts[2]}`;
  }

  const m = v.match(/rgba?\(([^)]+)\)/i);
  if (!m) return null;

  const body = m[1].replace(/\//g, ' ').replace(/,/g, ' ');
  const nums = body
    .split(/\s+/)
    .filter(Boolean)
    .map((x) => Number(x))
    .filter((n) => Number.isFinite(n));

  if (nums.length < 3) return null;
  const [r, g, b] = nums;
  return `${clampByte(r)} ${clampByte(g)} ${clampByte(b)}`;
}

function toRgbTriplet(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const v = value.trim();
  if (!v) return null;

  if (v.startsWith('#')) return hexToRgbTriplet(v);
  const rgb = parseRgbLikeToTriplet(v);
  if (rgb) return rgb;
  return null;
}

function getAnyKey(obj: Record<string, any> | null | undefined, keys: string[]): unknown {
  if (!obj) return null;
  for (const key of keys) {
    if (key in obj) return obj[key];
    const lower = key.toLowerCase();
    const foundKey = Object.keys(obj).find((k) => k.toLowerCase() === lower);
    if (foundKey) return obj[foundKey];
  }
  return null;
}

function buildCssVarsFromUnifiedConfig(config: ThemeConfigUnifiedRead): CssVarMap {
  const vars: CssVarMap = {};

  const primaryTriplet = toRgbTriplet(getAnyKey(config.primary_colors, ['PRIMARY'])) || toRgbTriplet(getAnyKey(config.accent_colors, ['ACCENT']));
  const primaryLightTriplet = toRgbTriplet(getAnyKey(config.primary_colors, ['PRIMARY_LIGHT'])) || primaryTriplet;

  const textPrimaryTriplet = toRgbTriplet(getAnyKey(config.text_colors, ['TEXT_PRIMARY']));
  const textSecondaryTriplet = toRgbTriplet(getAnyKey(config.text_colors, ['TEXT_SECONDARY']));
  const textTertiaryTriplet = toRgbTriplet(getAnyKey(config.text_colors, ['TEXT_TERTIARY']));

  const bgPrimaryTriplet = toRgbTriplet(getAnyKey(config.background_colors, ['BG_PRIMARY']));
  const bgSecondaryTriplet = toRgbTriplet(getAnyKey(config.background_colors, ['BG_SECONDARY']));
  const glassTriplet = toRgbTriplet(getAnyKey(config.background_colors, ['GLASS_BG'])) || bgPrimaryTriplet;

  const borderTriplet = toRgbTriplet(getAnyKey(config.border_effects, ['BORDER_DEFAULT']));

  if (primaryTriplet) vars['--color-primary'] = primaryTriplet;
  if (primaryLightTriplet) vars['--color-primary-light'] = primaryLightTriplet;
  if (textPrimaryTriplet) vars['--color-text-primary'] = textPrimaryTriplet;
  if (textSecondaryTriplet) vars['--color-text-secondary'] = textSecondaryTriplet;
  if (textTertiaryTriplet) vars['--color-text-tertiary'] = textTertiaryTriplet;
  if (bgPrimaryTriplet) vars['--color-bg-primary'] = bgPrimaryTriplet;
  if (bgSecondaryTriplet) vars['--color-bg-secondary'] = bgSecondaryTriplet;
  if (glassTriplet) vars['--color-bg-glass'] = glassTriplet;
  if (borderTriplet) vars['--color-border'] = borderTriplet;

  // 阴影可以直接使用后端给出的 CSS 字符串（若为空则保持默认）
  const shadowCard = getAnyKey(config.border_effects, ['SHADOW_CARD']);
  if (typeof shadowCard === 'string' && shadowCard.trim()) {
    vars['--shadow-card'] = shadowCard.trim();
  }

  return vars;
}

export function applyThemeVariables(mode: ThemeMode, vars: CssVarMap): void {
  const root = document.documentElement;

  // 注意：我们将变量写入 inline style，确保立刻生效；mode 仅用于未来扩展/调试
  // 当前实现：切换 light/dark 时会重新写一遍变量。
  void mode;

  Object.entries(vars).forEach(([key, value]) => {
    root.style.setProperty(key, value);
  });
}

export function clearThemeVariables(): void {
  const root = document.documentElement;
  const keys = [
    '--color-primary',
    '--color-primary-light',
    '--color-text-primary',
    '--color-text-secondary',
    '--color-text-tertiary',
    '--color-bg-primary',
    '--color-bg-secondary',
    '--color-bg-glass',
    '--color-border',
    '--shadow-card',
  ];
  keys.forEach((k) => root.style.removeProperty(k));
}

export function applyThemeFromUnifiedConfig(config: ThemeConfigUnifiedRead | null | undefined): void {
  if (!config) return;
  const vars = buildCssVarsFromUnifiedConfig(config);
  applyThemeVariables(config.parent_mode, vars);
}
