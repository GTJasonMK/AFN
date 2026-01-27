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

export interface ThemeConfigUpdateV1 {
  config_name?: string;
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
}

export interface ThemeConfigUpdateV2 {
  config_name?: string;
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
}

export interface ThemeConfigExport {
  config_name: string;
  parent_mode: ThemeMode;
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
}

export interface ThemeConfigExportData {
  version: string;
  export_time: string;
  configs: ThemeConfigExport[];
}

export interface ThemeConfigImportResult {
  success: boolean;
  message: string;
  imported_count: number;
  skipped_count: number;
  failed_count: number;
  details: string[];
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

  getUnified: async (id: number) => {
    const response = await apiClient.get<ThemeConfigUnifiedRead>(`/theme-configs/unified/${id}`);
    return response.data;
  },

  updateV1: async (id: number, payload: ThemeConfigUpdateV1) => {
    const response = await apiClient.put(`/theme-configs/${id}`, payload);
    return response.data;
  },

  updateV2: async (id: number, payload: ThemeConfigUpdateV2) => {
    const response = await apiClient.put(`/theme-configs/v2/${id}`, payload);
    return response.data;
  },

  resetV1: async (id: number) => {
    const response = await apiClient.post(`/theme-configs/${id}/reset`);
    return response.data;
  },

  resetV2: async (id: number) => {
    const response = await apiClient.post(`/theme-configs/v2/${id}/reset`);
    return response.data;
  },

  delete: async (id: number) => {
    const response = await apiClient.delete(`/theme-configs/${id}`);
    return response.data;
  },

  createV1: async (payload: { config_name: string; parent_mode: ThemeMode } & Omit<ThemeConfigUpdateV1, 'config_name'>) => {
    const response = await apiClient.post(`/theme-configs`, payload);
    return response.data;
  },

  createV2: async (payload: { config_name: string; parent_mode: ThemeMode } & Omit<ThemeConfigUpdateV2, 'config_name'>) => {
    const response = await apiClient.post(`/theme-configs/v2`, payload);
    return response.data;
  },

  migrateToV2: async (id: number) => {
    const response = await apiClient.post(`/theme-configs/${id}/migrate-to-v2`);
    return response.data;
  },

  exportAll: async () => {
    const response = await apiClient.get<ThemeConfigExportData>(`/theme-configs/export`);
    return response.data;
  },

  exportOne: async (id: number) => {
    const response = await apiClient.get<ThemeConfigExport>(`/theme-configs/${id}/export`);
    return response.data;
  },

  importAll: async (data: ThemeConfigExportData) => {
    const response = await apiClient.post<ThemeConfigImportResult>(`/theme-configs/import`, { data });
    return response.data;
  },
};
