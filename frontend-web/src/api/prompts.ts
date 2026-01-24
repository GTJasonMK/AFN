import { apiClient } from './client';

export interface PromptRead {
  id: number;
  name: string;
  title?: string | null;
  content: string;
  description?: string | null;
  tags?: string[] | null;
  is_modified: boolean;
  category?: string | null;
  status?: string | null;
  project_type?: string | null;
}

export interface PromptUpdate {
  content: string;
}

export const promptsApi = {
  list: async () => {
    const response = await apiClient.get<PromptRead[]>('/prompts');
    return response.data;
  },

  get: async (name: string) => {
    const response = await apiClient.get<PromptRead>(`/prompts/${name}`);
    return response.data;
  },

  update: async (name: string, payload: PromptUpdate) => {
    const response = await apiClient.put<PromptRead>(`/prompts/${name}`, payload);
    return response.data;
  },

  reset: async (name: string) => {
    const response = await apiClient.post<PromptRead>(`/prompts/${name}/reset`);
    return response.data;
  },

  resetAll: async () => {
    const response = await apiClient.post<{ reset_count: number; message: string }>('/prompts/reset-all');
    return response.data;
  },
};

