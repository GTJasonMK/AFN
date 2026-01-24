import { apiClient } from './client';

export interface Novel {
  id: string;
  title: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
  cover_image?: string;
  word_count?: number;
}

export interface NovelProjectDetail extends Novel {
  blueprint?: any;
  chapters?: any[];
}

export interface CharacterPortrait {
  id: string;
  character_name: string;
  image_url: string; // The backend returns a relative path or full URL
  prompt: string;
  style: string;
  is_active: boolean;
}

export interface CreateNovelRequest {
  title: string;
  initial_prompt?: string;
  skip_inspiration?: boolean;
}

export interface UpdateNovelRequest {
  title?: string;
  description?: string;
}

export interface RagTypeInfo {
  value: string;
  display_name: string;
  weight: string;
  source_table: string;
}

export interface RagTypeDetail {
  data_type: string;
  display_name: string;
  db_count: number;
  vector_count: number;
  new_count: number;
  modified_count: number;
  deleted_count: number;
  complete: boolean;
}

export interface RagCompleteness {
  project_id: string;
  complete: boolean;
  total_db_count: number;
  total_vector_count: number;
  total_new: number;
  total_modified: number;
  total_deleted: number;
  types: RagTypeDetail[];
}

export interface RagDiagnoseResponse {
  project_id: string;
  vector_store_enabled: boolean;
  embedding_service_enabled: boolean;
  completeness?: RagCompleteness | null;
  data_type_list: RagTypeInfo[];
}

export interface RagIngestionItem {
  data_type: string;
  display_name: string;
  success: boolean;
  added_count?: number;
  updated_count?: number;
  error_message?: string | null;
}

export interface RagIngestAllResponse {
  project_id: string;
  success: boolean;
  is_complete_before: boolean;
  total_added: number;
  total_updated: number;
  total_skipped: number;
  results: Record<string, RagIngestionItem>;
}

export interface BlueprintGenerationResponse {
  blueprint: any;
  ai_message: string;
}

export const novelsApi = {
  // ... existing methods ...
  list: async (page = 1, pageSize = 100) => {
    const response = await apiClient.get<Novel[]>('/novels', {
      params: { page, page_size: pageSize }
    });
    return response.data;
  },

  get: async (id: string) => {
    const response = await apiClient.get<NovelProjectDetail>(`/novels/${id}`);
    return response.data;
  },

  create: async (data: CreateNovelRequest) => {
    const response = await apiClient.post<Novel>('/novels', data);
    return response.data;
  },

  update: async (id: string, data: UpdateNovelRequest) => {
    const response = await apiClient.patch<Novel>(`/novels/${id}`, data);
    return response.data;
  },

  delete: async (ids: string[]) => {
    const response = await apiClient.delete('/novels', { data: ids });
    return response.data;
  },
  
  getChatHistory: async (id: string) => {
    const response = await apiClient.get<{id: number, role: string, content: string}[]>(`/novels/${id}/inspiration/history`);
    return response.data;
  },
  
  // 生成蓝图
  generateBlueprint: async (id: string) => {
    const response = await apiClient.post(`/novels/${id}/blueprint/generate`);
    return response.data;
  },

  // 优化蓝图（会重置后续数据；后端可能返回 409 提示需确认 force）
  refineBlueprint: async (id: string, refinementInstruction: string, force = false) => {
    const response = await apiClient.post<BlueprintGenerationResponse>(
      `/novels/${id}/blueprint/refine`,
      { refinement_instruction: refinementInstruction },
      { params: { force } }
    );
    return response.data;
  },

  // 获取蓝图详情
  getBlueprint: async (id: string) => {
    // 蓝图通常包含在项目详情中，或者有专门的 section
    const response = await apiClient.get(`/novels/${id}/sections/blueprint`);
    return response.data;
  },

  // 批量更新蓝图（用于保存角色、世界观等）
  updateBlueprint: async (id: string, updates: any) => {
    const response = await apiClient.post(`/novels/${id}/blueprint/batch-update`, {
      blueprint_updates: updates
    });
    return response.data;
  },

  // 角色立绘
  getPortraits: async (projectId: string) => {
    const response = await apiClient.get<{portraits: CharacterPortrait[]}>(`/novels/${projectId}/character-portraits`);
    return response.data.portraits;
  },

  generatePortrait: async (projectId: string, characterName: string, description: string) => {
    const response = await apiClient.post(`/novels/${projectId}/character-portraits/generate`, {
        character_name: characterName,
        character_description: description
    });
    return response.data;
  },

  // RAG 查询
  queryRAG: async (projectId: string, query: string) => {
    const response = await apiClient.post(`/writer/novels/${projectId}/rag/query`, {
      query,
      top_k: 5
    });
    return response.data;
  },

  getRagDiagnose: async (projectId: string) => {
    const response = await apiClient.get<RagDiagnoseResponse>(`/novels/${projectId}/rag/diagnose`);
    return response.data;
  },

  ingestAllRagData: async (projectId: string, force = false) => {
    const response = await apiClient.post<RagIngestAllResponse>(
      `/novels/${projectId}/rag/ingest-all`,
      undefined,
      { params: { force }, timeout: 10 * 60 * 1000 }
    );
    return response.data;
  },

  // 导出小说
  exportNovel: async (projectId: string, format: 'txt' | 'markdown' = 'txt') => {
    const response = await apiClient.get(`/novels/${projectId}/export`, {
      params: { format },
      responseType: 'blob' // Important for file download
    });
    return response;
  },

  // 部分大纲（writer 路由）
  generatePartOutlines: async (projectId: string, totalChapters: number, chaptersPerPart: number) => {
    const response = await apiClient.post(`/writer/novels/${projectId}/parts/generate`, {
      total_chapters: totalChapters,
      chapters_per_part: chaptersPerPart
    });
    return response.data;
  }
};
