import type { ReactNode } from 'react';
import type {
  ThemeConfigUnifiedRead,
  ThemeMode,
} from '../../../../api/themeConfigs';

export type ThemeActionMenuItem =
  | {
      label: string;
      onClick: () => void;
      danger?: boolean;
      icon?: ReactNode;
    }
  | {
      type: 'divider';
    };

export function formatTime(iso?: string | null): string {
  if (!iso) {
    return '—';
  }
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function formatDate(iso?: string | null): string {
  if (!iso) {
    return '—';
  }
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

export function formatThemeMode(mode: ThemeMode): string {
  return mode === 'dark' ? '深色' : '亮色';
}

export function sanitizeFilename(name: string): string {
  const raw = String(name || '').trim();
  if (!raw) {
    return 'theme';
  }
  return raw.replace(/[\\/:*?"<>|]/g, '_').slice(0, 80);
}

export function buildEditPayloadText(cfg: ThemeConfigUnifiedRead): string {
  const version = Number(cfg.config_version || 1);
  if (version === 2) {
    const payload = {
      token_colors: cfg.token_colors ?? null,
      token_typography: cfg.token_typography ?? null,
      token_spacing: cfg.token_spacing ?? null,
      token_radius: cfg.token_radius ?? null,
      comp_button: cfg.comp_button ?? null,
      comp_card: cfg.comp_card ?? null,
      comp_input: cfg.comp_input ?? null,
      comp_sidebar: cfg.comp_sidebar ?? null,
      comp_header: cfg.comp_header ?? null,
      comp_dialog: cfg.comp_dialog ?? null,
      comp_scrollbar: cfg.comp_scrollbar ?? null,
      comp_tooltip: cfg.comp_tooltip ?? null,
      comp_tabs: cfg.comp_tabs ?? null,
      comp_text: cfg.comp_text ?? null,
      comp_semantic: cfg.comp_semantic ?? null,
      effects: cfg.effects ?? null,
    };
    return JSON.stringify(payload, null, 2);
  }

  const payload = {
    primary_colors: cfg.primary_colors ?? null,
    accent_colors: cfg.accent_colors ?? null,
    semantic_colors: cfg.semantic_colors ?? null,
    text_colors: cfg.text_colors ?? null,
    background_colors: cfg.background_colors ?? null,
    border_effects: cfg.border_effects ?? null,
    button_colors: cfg.button_colors ?? null,
    typography: cfg.typography ?? null,
    border_radius: cfg.border_radius ?? null,
    spacing: cfg.spacing ?? null,
    animation: cfg.animation ?? null,
    button_sizes: cfg.button_sizes ?? null,
  };
  return JSON.stringify(payload, null, 2);
}
