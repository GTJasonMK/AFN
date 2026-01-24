import { apiClient } from './client';

export type ImageProviderType = 'openai_compatible' | 'stability' | 'midjourney' | 'comfyui';
export type ImageQualityPreset = 'draft' | 'standard' | 'high';

export interface ImageConfigBase {
  config_name: string;
  provider_type: ImageProviderType;
  api_base_url?: string | null;
  api_key?: string | null;
  model_name?: string | null;
  default_style?: string | null;
  default_ratio?: string | null;
  default_resolution?: string | null;
  default_quality?: ImageQualityPreset | string | null;
  extra_params?: Record<string, any> | null;
}

export interface ImageConfigResponse extends ImageConfigBase {
  id: number;
  is_active: boolean;
  is_verified: boolean;
  last_test_at?: string | null;
  test_status?: string | null;
  test_message?: string | null;
  created_at: string;
  updated_at: string;
}

export type ImageConfigCreate = ImageConfigBase;

export type ImageConfigUpdate = Partial<ImageConfigBase>;

export interface ImageConfigTestResponse {
  success: boolean;
  message: string;
  response_time_ms?: number | null;
  provider_info?: string | null;
}

export const imageConfigsApi = {
  list: async () => {
    const response = await apiClient.get<ImageConfigResponse[]>('/image-generation/configs');
    return response.data;
  },

  create: async (payload: ImageConfigCreate) => {
    const response = await apiClient.post<ImageConfigResponse>('/image-generation/configs', payload);
    return response.data;
  },

  update: async (id: number, payload: ImageConfigUpdate) => {
    const response = await apiClient.put<ImageConfigResponse>(`/image-generation/configs/${id}`, payload);
    return response.data;
  },

  activate: async (id: number) => {
    const response = await apiClient.post<{ success: boolean }>(`/image-generation/configs/${id}/activate`);
    return response.data;
  },

  delete: async (id: number) => {
    await apiClient.delete(`/image-generation/configs/${id}`);
  },

  test: async (id: number) => {
    const response = await apiClient.post<ImageConfigTestResponse>(`/image-generation/configs/${id}/test`);
    return response.data;
  },
};

