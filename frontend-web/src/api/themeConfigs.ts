import { apiClient } from './client';

export type ThemeMode = 'light' | 'dark';

export interface ThemeConfigListItem {
  id: number;
  config_name: string;
  parent_mode: ThemeMode;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ThemeConfigUnifiedRead {
  id: number;
  user_id: number;
  config_name: string;
  parent_mode: ThemeMode;
  is_active: boolean;
  config_version: number;
  primary_colors?: Record<string, any> | null;
  accent_colors?: Record<string, any> | null;
  semantic_colors?: Record<string, any> | null;
  text_colors?: Record<string, any> | null;
  background_colors?: Record<string, any> | null;
  border_effects?: Record<string, any> | null;
  button_colors?: Record<string, any> | null;
  typography?: Record<string, any> | null;
  border_radius?: Record<string, any> | null;
  spacing?: Record<string, any> | null;
  animation?: Record<string, any> | null;
  button_sizes?: Record<string, any> | null;

  token_colors?: Record<string, any> | null;
  token_typography?: Record<string, any> | null;
  token_spacing?: Record<string, any> | null;
  token_radius?: Record<string, any> | null;
  comp_button?: Record<string, any> | null;
  comp_card?: Record<string, any> | null;
  comp_input?: Record<string, any> | null;
  comp_sidebar?: Record<string, any> | null;
  comp_header?: Record<string, any> | null;
  comp_dialog?: Record<string, any> | null;
  comp_scrollbar?: Record<string, any> | null;
  comp_tooltip?: Record<string, any> | null;
  comp_tabs?: Record<string, any> | null;
  comp_text?: Record<string, any> | null;
  comp_semantic?: Record<string, any> | null;
  effects?: Record<string, any> | null;

  created_at: string;
  updated_at: string;
}

export const themeConfigsApi = {
  list: async () => {
    const response = await apiClient.get<ThemeConfigListItem[]>('/theme-configs');
    return response.data;
  },

  getActive: async (mode: ThemeMode) => {
    const response = await apiClient.get<ThemeConfigUnifiedRead | null>(`/theme-configs/unified/active/${mode}`);
    return response.data;
  },

  activate: async (id: number) => {
    const response = await apiClient.post<ThemeConfigUnifiedRead>(`/theme-configs/${id}/activate`);
    return response.data;
  },
};

