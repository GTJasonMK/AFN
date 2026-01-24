import { apiClient } from './client';

export type EmbeddingProvider = 'openai' | 'ollama' | 'local';

export interface EmbeddingProviderInfo {
  provider: EmbeddingProvider;
  name: string;
  description: string;
  default_model: string;
  requires_api_key: boolean;
  default_base_url?: string | null;
}

export interface EmbeddingConfigRead {
  id: number;
  user_id: number;
  config_name: string;
  provider: EmbeddingProvider;
  api_base_url?: string | null;
  api_key_masked?: string | null;
  model_name?: string | null;
  vector_size?: number | null;
  is_active: boolean;
  is_verified: boolean;
  last_test_at?: string | null;
  test_status?: 'success' | 'failed' | 'pending' | null;
  test_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmbeddingConfigCreate {
  config_name: string;
  provider: EmbeddingProvider;
  api_base_url?: string | null;
  api_key?: string | null;
  model_name?: string | null;
  vector_size?: number | null;
}

export interface EmbeddingConfigUpdate {
  config_name?: string | null;
  provider?: EmbeddingProvider | null;
  api_base_url?: string | null;
  api_key?: string | null;
  model_name?: string | null;
  vector_size?: number | null;
}

export interface EmbeddingConfigTestResponse {
  success: boolean;
  message: string;
  response_time_ms?: number | null;
  vector_dimension?: number | null;
  model_info?: string | null;
}

export const embeddingConfigsApi = {
  listProviders: async () => {
    const response = await apiClient.get<EmbeddingProviderInfo[]>('/embedding-configs/providers');
    return response.data;
  },

  list: async () => {
    const response = await apiClient.get<EmbeddingConfigRead[]>('/embedding-configs');
    return response.data;
  },

  getActive: async () => {
    const response = await apiClient.get<EmbeddingConfigRead>('/embedding-configs/active');
    return response.data;
  },

  create: async (payload: EmbeddingConfigCreate) => {
    const response = await apiClient.post<EmbeddingConfigRead>('/embedding-configs', payload);
    return response.data;
  },

  update: async (id: number, payload: EmbeddingConfigUpdate) => {
    const response = await apiClient.put<EmbeddingConfigRead>(`/embedding-configs/${id}`, payload);
    return response.data;
  },

  activate: async (id: number) => {
    const response = await apiClient.post<EmbeddingConfigRead>(`/embedding-configs/${id}/activate`);
    return response.data;
  },

  delete: async (id: number) => {
    await apiClient.delete(`/embedding-configs/${id}`);
  },

  test: async (id: number) => {
    const response = await apiClient.post<EmbeddingConfigTestResponse>(`/embedding-configs/${id}/test`);
    return response.data;
  },
};

