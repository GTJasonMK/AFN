import { apiClient } from './client';

export interface AdvancedConfig {
  writer_chapter_version_count: number;
  writer_parallel_generation: boolean;
  part_outline_threshold: number;
  agent_context_max_chars: number;
}

export interface MaxTokensConfig {
  // 小说系统
  llm_max_tokens_blueprint: number;
  llm_max_tokens_chapter: number;
  llm_max_tokens_outline: number;
  llm_max_tokens_manga: number;
  llm_max_tokens_analysis: number;
  llm_max_tokens_default: number;
  // 编程系统
  llm_max_tokens_coding_blueprint: number;
  llm_max_tokens_coding_system: number;
  llm_max_tokens_coding_module: number;
  llm_max_tokens_coding_feature: number;
  llm_max_tokens_coding_prompt: number;
  llm_max_tokens_coding_directory: number;
}

export interface TemperatureConfig {
  llm_temp_inspiration: number;
  llm_temp_blueprint: number;
  llm_temp_outline: number;
  llm_temp_writing: number;
  llm_temp_evaluation: number;
  llm_temp_summary: number;
}

export const settingsApi = {
  getAdvancedConfig: async () => {
    const response = await apiClient.get<AdvancedConfig>('/settings/advanced-config');
    return response.data;
  },

  updateAdvancedConfig: async (config: AdvancedConfig) => {
    const response = await apiClient.put('/settings/advanced-config', config);
    return response.data;
  },

  getMaxTokensConfig: async () => {
    const response = await apiClient.get<MaxTokensConfig>('/settings/max-tokens-config');
    return response.data;
  },

  updateMaxTokensConfig: async (config: MaxTokensConfig) => {
    const response = await apiClient.put('/settings/max-tokens-config', config);
    return response.data;
  },

  getTemperatureConfig: async () => {
    const response = await apiClient.get<TemperatureConfig>('/settings/temperature-config');
    return response.data;
  },

  updateTemperatureConfig: async (config: TemperatureConfig) => {
    const response = await apiClient.put('/settings/temperature-config', config);
    return response.data;
  },
};
