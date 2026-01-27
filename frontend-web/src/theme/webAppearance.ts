export type WebAppearanceConfig = {
  enabled: boolean;
  backgroundImageUrl: string;
  blurPx: number;
  overlayOpacity: number; // 0~1
};

export const WEB_APPEARANCE_STORAGE_KEY = 'afn:web_appearance';
export const WEB_APPEARANCE_CHANGED_EVENT = 'afn-web-appearance-changed';

export function defaultWebAppearanceConfig(): WebAppearanceConfig {
  return {
    enabled: false,
    backgroundImageUrl: '',
    blurPx: 8,
    overlayOpacity: 0.75,
  };
}

function clampNumber(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.max(min, Math.min(max, value));
}

export function normalizeWebAppearanceConfig(input: Partial<WebAppearanceConfig> | null | undefined): WebAppearanceConfig {
  const base = defaultWebAppearanceConfig();
  const enabled = Boolean(input?.enabled);
  const url = String(input?.backgroundImageUrl || '').trim();
  const blurPx = clampNumber(Number(input?.blurPx ?? base.blurPx), 0, 48);
  const overlayOpacity = clampNumber(Number(input?.overlayOpacity ?? base.overlayOpacity), 0, 1);
  return {
    enabled,
    backgroundImageUrl: url,
    blurPx,
    overlayOpacity,
  };
}

export function readWebAppearanceConfig(): WebAppearanceConfig {
  try {
    const raw = localStorage.getItem(WEB_APPEARANCE_STORAGE_KEY);
    if (!raw) return defaultWebAppearanceConfig();
    const parsed = JSON.parse(raw) as Partial<WebAppearanceConfig>;
    return normalizeWebAppearanceConfig(parsed);
  } catch {
    return defaultWebAppearanceConfig();
  }
}

export function writeWebAppearanceConfig(cfg: WebAppearanceConfig): void {
  try {
    const normalized = normalizeWebAppearanceConfig(cfg);
    localStorage.setItem(WEB_APPEARANCE_STORAGE_KEY, JSON.stringify(normalized));
  } catch {
    // ignore
  }
}

export function notifyWebAppearanceChanged(): void {
  try {
    window.dispatchEvent(new Event(WEB_APPEARANCE_CHANGED_EVENT));
  } catch {
    // ignore
  }
}

