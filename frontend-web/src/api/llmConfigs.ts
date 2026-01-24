import { apiClient } from './client';

export interface LLMConfigRead {
  id: number;
  user_id: number;
  config_name: string;
  llm_provider_url?: string | null;
  llm_provider_api_key_masked?: string | null;
  llm_provider_model?: string | null;
  is_active: boolean;
  is_verified: boolean;
  last_test_at?: string | null;
  test_status?: 'success' | 'failed' | 'pending' | null;
  test_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LLMConfigCreate {
  config_name: string;
  llm_provider_url?: string | null;
  llm_provider_api_key?: string | null;
  llm_provider_model?: string | null;
}

export interface LLMConfigUpdate {
  config_name?: string | null;
  llm_provider_url?: string | null;
  llm_provider_api_key?: string | null;
  llm_provider_model?: string | null;
}

export interface LLMConfigTestResponse {
  success: boolean;
  message: string;
  response_time_ms?: number | null;
  model_info?: string | null;
}

export const llmConfigsApi = {
  list: async () => {
    const response = await apiClient.get<LLMConfigRead[]>('/llm-configs');
    return response.data;
  },

  getActive: async () => {
    const response = await apiClient.get<LLMConfigRead>('/llm-configs/active');
    return response.data;
  },

  create: async (payload: LLMConfigCreate) => {
    const response = await apiClient.post<LLMConfigRead>('/llm-configs', payload);
    return response.data;
  },

  update: async (id: number, payload: LLMConfigUpdate) => {
    const response = await apiClient.put<LLMConfigRead>(`/llm-configs/${id}`, payload);
    return response.data;
  },

  activate: async (id: number) => {
    const response = await apiClient.post<LLMConfigRead>(`/llm-configs/${id}/activate`);
    return response.data;
  },

  delete: async (id: number) => {
    await apiClient.delete(`/llm-configs/${id}`);
  },

  test: async (id: number) => {
    const response = await apiClient.post<LLMConfigTestResponse>(`/llm-configs/${id}/test`);
    return response.data;
  },
};

