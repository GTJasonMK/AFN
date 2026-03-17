import { ThemeConfigUnifiedRead, ThemeMode } from '../api/themeConfigs';

type CssVarMap = Record<string, string>;

const THEME_APPLIED_EVENT = 'afn:theme-applied';

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

function readV2TokenTriplet(config: ThemeConfigUnifiedRead, keys: string[]): string | null {
  return toRgbTriplet(getAnyKey(config.token_colors ?? null, keys));
}

function readV1TokenTriplet(obj: Record<string, any> | null | undefined, keys: string[]): string | null {
  return toRgbTriplet(getAnyKey(obj ?? null, keys));
}

function buildCssVarsFromUnifiedConfig(config: ThemeConfigUnifiedRead): CssVarMap {
  const vars: CssVarMap = {};

  const configVersion = Number(config.config_version || 1);

  // V2：token_colors / comp_*（WebUI 优先使用 V2 的设计令牌）
  const v2PrimaryTriplet = readV2TokenTriplet(config, ['brand', 'primary']);
  const v2PrimaryLightTriplet = readV2TokenTriplet(config, ['brand_light', 'primary_light']);

  const v2TextPrimaryTriplet = readV2TokenTriplet(config, ['text', 'text_primary']);
  const v2TextSecondaryTriplet = readV2TokenTriplet(config, ['text_muted', 'text_secondary']);
  const v2TextTertiaryTriplet = readV2TokenTriplet(config, ['text_subtle', 'text_tertiary']);

  const v2BgPrimaryTriplet = readV2TokenTriplet(config, ['background', 'bg', 'bg_primary']);
  const v2BgSecondaryTriplet = readV2TokenTriplet(config, ['surface', 'bg_secondary', 'surface_primary']);
  const v2GlassTriplet = readV2TokenTriplet(config, ['surface', 'background']) || v2BgPrimaryTriplet;

  const v2BorderTriplet = readV2TokenTriplet(config, ['border', 'border_default']);

  // V1：primary_colors/text_colors/background_colors...
  const v1PrimaryTriplet = readV1TokenTriplet(config.primary_colors, ['PRIMARY'])
    || readV1TokenTriplet(config.accent_colors, ['ACCENT']);
  const v1PrimaryLightTriplet = readV1TokenTriplet(config.primary_colors, ['PRIMARY_LIGHT']) || v1PrimaryTriplet;

  const v1TextPrimaryTriplet = readV1TokenTriplet(config.text_colors, ['TEXT_PRIMARY']);
  const v1TextSecondaryTriplet = readV1TokenTriplet(config.text_colors, ['TEXT_SECONDARY']);
  const v1TextTertiaryTriplet = readV1TokenTriplet(config.text_colors, ['TEXT_TERTIARY']);

  const v1BgPrimaryTriplet = readV1TokenTriplet(config.background_colors, ['BG_PRIMARY']);
  const v1BgSecondaryTriplet = readV1TokenTriplet(config.background_colors, ['BG_SECONDARY']);
  const v1GlassTriplet = readV1TokenTriplet(config.background_colors, ['GLASS_BG']) || v1BgPrimaryTriplet;

  const v1BorderTriplet = readV1TokenTriplet(config.border_effects, ['BORDER_DEFAULT']);

  // 选择策略：V2 优先，其次 V1（避免 V2 配置下 WebUI 不生效）
  const primaryTriplet = v2PrimaryTriplet || v1PrimaryTriplet;
  const primaryLightTriplet = v2PrimaryLightTriplet || v1PrimaryLightTriplet || primaryTriplet;
  const textPrimaryTriplet = v2TextPrimaryTriplet || v1TextPrimaryTriplet;
  const textSecondaryTriplet = v2TextSecondaryTriplet || v1TextSecondaryTriplet;
  const textTertiaryTriplet = v2TextTertiaryTriplet || v1TextTertiaryTriplet;
  const bgPrimaryTriplet = v2BgPrimaryTriplet || v1BgPrimaryTriplet;
  const bgSecondaryTriplet = v2BgSecondaryTriplet || v1BgSecondaryTriplet;
  const glassTriplet = v2GlassTriplet || v1GlassTriplet || bgPrimaryTriplet;
  const borderTriplet = v2BorderTriplet || v1BorderTriplet;

  if (primaryTriplet) vars['--color-primary'] = primaryTriplet;
  if (primaryLightTriplet) vars['--color-primary-light'] = primaryLightTriplet;
  if (textPrimaryTriplet) vars['--color-text-primary'] = textPrimaryTriplet;
  if (textSecondaryTriplet) vars['--color-text-secondary'] = textSecondaryTriplet;
  if (textTertiaryTriplet) vars['--color-text-tertiary'] = textTertiaryTriplet;
  if (bgPrimaryTriplet) vars['--color-bg-primary'] = bgPrimaryTriplet;
  if (bgSecondaryTriplet) vars['--color-bg-secondary'] = bgSecondaryTriplet;
  if (glassTriplet) vars['--color-bg-glass'] = glassTriplet;
  if (borderTriplet) vars['--color-border'] = borderTriplet;

  // 阴影：优先 V2 comp_card，其次 V1 border_effects
  const shadowCardV2 = getAnyKey(config.comp_card ?? null, ['shadow']);
  if (typeof shadowCardV2 === 'string' && shadowCardV2.trim()) {
    vars['--shadow-card'] = shadowCardV2.trim();
  } else {
    const shadowCardV1 = getAnyKey(config.border_effects, ['SHADOW_CARD']);
    if (typeof shadowCardV1 === 'string' && shadowCardV1.trim()) {
      vars['--shadow-card'] = shadowCardV1.trim();
    }
  }

  // V2 effects（可选）：允许通过后端配置统一过渡速度
  if (configVersion === 2 && config.effects && typeof config.effects === 'object') {
    const transitionBase = getAnyKey(config.effects, ['transition_base', 'transitionBase']);
    if (typeof transitionBase === 'string' && transitionBase.trim()) {
      vars['--transition-base'] = transitionBase.trim();
    }
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
    '--transition-base',
  ];
  keys.forEach((k) => root.style.removeProperty(k));
}

export function applyThemeFromUnifiedConfig(config: ThemeConfigUnifiedRead | null | undefined): void {
  if (!config) return;
  const vars = buildCssVarsFromUnifiedConfig(config);
  applyThemeVariables(config.parent_mode, vars);

  // 通知依赖主题变量的 UI（如粒子背景）刷新调色板
  try {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(THEME_APPLIED_EVENT, { detail: { mode: config.parent_mode } }));
    }
  } catch {
    // ignore
  }
}
