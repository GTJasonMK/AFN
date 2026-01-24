import { apiClient } from './client';

export interface QueueStatus {
  active: number;
  waiting: number;
  max_concurrent: number;
  total_processed: number;
}

export interface QueueStatusResponse {
  llm: QueueStatus;
  image: QueueStatus;
}

export interface QueueConfigResponse {
  llm_max_concurrent: number;
  image_max_concurrent: number;
}

export interface QueueConfigUpdate {
  llm_max_concurrent?: number;
  image_max_concurrent?: number;
}

export const queueApi = {
  getStatus: async () => {
    const response = await apiClient.get<QueueStatusResponse>('/queue/status');
    return response.data;
  },

  getConfig: async () => {
    const response = await apiClient.get<QueueConfigResponse>('/queue/config');
    return response.data;
  },

  updateConfig: async (config: QueueConfigUpdate) => {
    const response = await apiClient.put<QueueConfigResponse>('/queue/config', config);
    return response.data;
  },
};

