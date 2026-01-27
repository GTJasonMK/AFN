import { apiClient } from './client';

export interface Novel {
  id: string;
  title: string;
  description?: string;
  status: string;
  created_at?: string;
  updated_at?: string;

  // 项目摘要接口（GET /novels）字段（后端为 NovelProjectSummary）
  genre?: string;
  last_edited?: string;
  completed_chapters?: number;
  total_chapters?: number;

  // 导入分析相关字段（导入小说）
  is_imported?: boolean;
  import_analysis_status?: string | null;
  import_analysis_progress?: any;

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
  style: string;
  is_active: boolean;
  character_description?: string | null;
  prompt?: string | null;
  custom_prompt?: string | null;
  image_url?: string | null; // The backend returns a relative path or full URL
  image_path?: string | null;
  file_name?: string | null;
  file_size?: number | null;
  width?: number | null;
  height?: number | null;
  model_name?: string | null;
  is_secondary?: boolean;
  auto_generated?: boolean;
  created_at?: string;
  updated_at?: string;
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

export interface AvatarGenerateResponse {
  avatar_svg: string;
  animal: string;
  animal_cn?: string;
}

export interface ImportAnalysisStatusResponse {
  status: string;
  progress: any;
  is_imported: boolean;
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
  generateBlueprint: async (id: string, opts?: { forceRegenerate?: boolean; allowIncomplete?: boolean }) => {
    const response = await apiClient.post(
      `/novels/${id}/blueprint/generate`,
      {},
      {
        params: {
          force_regenerate: opts?.forceRegenerate ? true : undefined,
          allow_incomplete: opts?.allowIncomplete ? true : undefined,
        },
      }
    );
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

  // 小说头像（SVG动物）
  generateAvatar: async (projectId: string) => {
    const response = await apiClient.post<AvatarGenerateResponse>(`/novels/${projectId}/avatar/generate`);
    return response.data;
  },

  deleteAvatar: async (projectId: string) => {
    const response = await apiClient.delete(`/novels/${projectId}/avatar`);
    return response.data;
  },

  // 角色立绘
  getPortraits: async (projectId: string) => {
    const response = await apiClient.get<{portraits: CharacterPortrait[]}>(`/novels/${projectId}/character-portraits`);
    return response.data.portraits;
  },

  getActivePortraits: async (projectId: string) => {
    const response = await apiClient.get<{portraits: CharacterPortrait[]}>(`/novels/${projectId}/character-portraits/active`);
    return response.data.portraits;
  },

  getCharacterPortraits: async (projectId: string, characterName: string) => {
    const response = await apiClient.get<{portraits: CharacterPortrait[]}>(
      `/novels/${projectId}/character-portraits/${encodeURIComponent(characterName)}`
    );
    return response.data.portraits;
  },

  generatePortrait: async (
    projectId: string,
    characterName: string,
    description: string,
    opts?: { style?: 'anime' | 'manga' | 'realistic'; customPrompt?: string }
  ) => {
    const response = await apiClient.post(`/novels/${projectId}/character-portraits/generate`, {
        character_name: characterName,
        character_description: description || undefined,
        style: opts?.style || undefined,
        custom_prompt: opts?.customPrompt || undefined,
    });
    return response.data;
  },

  regeneratePortrait: async (
    projectId: string,
    portraitId: string,
    opts?: { style?: 'anime' | 'manga' | 'realistic'; customPrompt?: string }
  ) => {
    const response = await apiClient.post(`/novels/${projectId}/character-portraits/${portraitId}/regenerate`, {
      style: opts?.style || undefined,
      custom_prompt: opts?.customPrompt || undefined,
    });
    return response.data;
  },

  setActivePortrait: async (projectId: string, portraitId: string) => {
    const response = await apiClient.post(`/novels/${projectId}/character-portraits/${portraitId}/set-active`);
    return response.data;
  },

  deletePortrait: async (projectId: string, portraitId: string) => {
    const response = await apiClient.delete(`/novels/${projectId}/character-portraits/${portraitId}`);
    return response.data;
  },

  getPortraitStyles: async () => {
    const response = await apiClient.get<Array<{
      style: string;
      name: string;
      description: string;
      prompt_prefix: string;
    }>>(`/character-portrait-styles`);
    return response.data;
  },

  autoGeneratePortraits: async (
    projectId: string,
    characterProfiles: Record<string, string>,
    opts?: { style?: 'anime' | 'manga' | 'realistic'; excludeExisting?: boolean }
  ) => {
    const response = await apiClient.post(`/novels/${projectId}/character-portraits/auto-generate`, {
      character_profiles: characterProfiles,
      style: opts?.style || 'anime',
      exclude_existing: opts?.excludeExisting !== false,
    });
    return response.data;
  },

  // RAG 查询
  queryRAG: async (projectId: string, query: string, topK: number = 10) => {
    const safeTopK = Math.max(1, Math.min(50, Number(topK) || 10));
    const response = await apiClient.post(`/writer/novels/${projectId}/rag/query`, {
      query,
      top_k: safeTopK,
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
  },

  // 导入分析进度
  getImportAnalysisStatus: async (projectId: string) => {
    const response = await apiClient.get<ImportAnalysisStatusResponse>(`/novels/${projectId}/analyze/status`);
    return response.data;
  },

  cancelImportAnalysis: async (projectId: string) => {
    const response = await apiClient.post(`/novels/${projectId}/analyze/cancel`);
    return response.data;
  },
};
