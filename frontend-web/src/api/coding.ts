import { apiClient } from './client';

export interface CodingProject {
  id: string;
  title: string;
  status: string; // 'draft', 'blueprint_ready', 'system_design_ready', etc.
  created_at: string;
  updated_at: string;
}

export interface CodingProjectSummary {
  id: string;
  title: string;
  project_type_desc: string;
  last_edited: string;
  status: string;
}

export interface CreateCodingProjectRequest {
  title: string;
  initial_prompt?: string;
  skip_conversation?: boolean;
}

export interface CodingChatMessage {
  id: number;
  role: string;
  content: string;
  created_at?: string | null;
}

export interface CodingFileDetail {
  id: number;
  project_id: string;
  directory_id: number;
  filename: string;
  file_path: string;
  file_type: string;
  language?: string | null;
  description?: string | null;
  purpose?: string | null;
  imports: string[];
  exports: string[];
  dependencies: string[];
  module_number?: number | null;
  system_number?: number | null;
  priority: string;
  sort_order: number;
  status: string;
  is_manual: boolean;
  has_content: boolean;
  selected_version_id?: number | null;
  version_count: number;
  content?: string | null;
  review_prompt?: string | null;
}

export interface CodingFileVersion {
  id: number;
  file_id: number;
  version_label?: string | null;
  provider?: string | null;
  content: string;
  created_at: string;
  metadata?: any;
}

export interface DirectoryAgentStateResponse {
  has_paused_state: boolean;
  current_phase?: string | null;
  total_directories: number;
  total_files: number;
  progress_percent: number;
  progress_message?: string | null;
  paused_at?: string | null;
}

export interface CodingSystem {
  system_number: number;
  name: string;
  description: string;
  responsibilities: string[];
  tech_requirements: string;
  module_count: number;
  generation_status: string;
  progress: number;
}

export interface CodingModule {
  module_number: number;
  system_number: number;
  name: string;
  type: string;
  description: string;
  interface: string;
  dependencies: string[];
  generation_status: string;
}

export interface CodingDependency {
  id: number;
  from_module: string;
  to_module: string;
  description: string;
  position: number;
}

export interface CodingRagTypeDetail {
  db_count: number;
  vector_count: number;
  complete: boolean;
  missing: number;
  display_name?: string;
}

export interface CodingRagCompletenessResponse {
  project_id: string;
  complete: boolean;
  total_db_count: number;
  total_vector_count: number;
  types: Record<string, CodingRagTypeDetail>;
}

export interface CodingRagIngestAllResponse {
  success: boolean;
  is_complete: boolean;
  total_items: number;
  added: number;
  skipped: number;
  failed: number;
  details: Record<string, any>;
}

export interface CodingRagChunk {
  content: string;
  chapter_number: number;
  source: string;
  score: number;
  data_type?: string | null;
}

export interface CodingRagSummary {
  chapter_number: number;
  title: string;
  summary: string;
  score: number;
}

export interface CodingRagQueryResponse {
  chunks: CodingRagChunk[];
  summaries: CodingRagSummary[];
}

export const codingApi = {
  list: async () => {
    const response = await apiClient.get<CodingProjectSummary[]>('/coding', {
      params: { page: 1, page_size: 100 }
    });
    return response.data;
  },

  create: async (data: CreateCodingProjectRequest) => {
    const response = await apiClient.post<CodingProject>('/coding', data);
    return response.data;
  },

  get: async (id: string) => {
    const response = await apiClient.get<CodingProject>(`/coding/${id}`);
    return response.data;
  },

  deleteProject: async (id: string) => {
    const response = await apiClient.delete(`/coding/${id}`);
    return response.data;
  },

  deleteProjects: async (ids: string[]) => {
    const response = await apiClient.post('/coding/batch-delete', ids);
    return response.data;
  },
  
  // Inspiration / Chat
  getChatHistory: async (projectId: string) => {
    const response = await apiClient.get<CodingChatMessage[]>(`/coding/${projectId}/inspiration/history`);
    return response.data;
  },

  converseStream: (projectId: string) => {
    return `/coding/${projectId}/inspiration/converse-stream`;
  },

  // Directory & Files
  getDirectoryTree: async (projectId: string) => {
    const response = await apiClient.get(`/coding/${projectId}/directories/tree`);
    return response.data;
  },

  getFile: async (projectId: string, fileId: number) => {
    const response = await apiClient.get<CodingFileDetail>(`/coding/${projectId}/files/${fileId}`);
    return response.data;
  },

  generateFilePrompt: async (projectId: string, fileId: number) => {
    const response = await apiClient.post(`/coding/${projectId}/files/${fileId}/generate`);
    return response.data;
  },

  generateFilePromptStream: (projectId: string, fileId: number) => {
    return `/coding/${projectId}/files/${fileId}/generate-stream`;
  },

  generateReviewPrompt: async (projectId: string, fileId: number, opts?: { writingNotes?: string }) => {
    const payload: any = {};
    const notes = (opts?.writingNotes || '').trim();
    if (notes) payload.writing_notes = notes;
    const response = await apiClient.post(`/coding/${projectId}/files/${fileId}/generate-review`, payload);
    return response.data;
  },

  generateReviewPromptStream: (projectId: string, fileId: number) => {
    return `/coding/${projectId}/files/${fileId}/generate-review-stream`;
  },

  saveReviewPrompt: async (projectId: string, fileId: number, content: string) => {
    const response = await apiClient.post(`/coding/${projectId}/files/${fileId}/save-review`, { content });
    return response.data;
  },

  saveFileContent: async (projectId: string, fileId: number, content: string, versionLabel?: string) => {
    const response = await apiClient.post(`/coding/${projectId}/files/${fileId}/save`, {
      content,
      version_label: versionLabel,
    });
    return response.data;
  },

  getFileVersions: async (projectId: string, fileId: number) => {
    const response = await apiClient.get<{ versions: CodingFileVersion[]; selected_version_id?: number | null }>(
      `/coding/${projectId}/files/${fileId}/versions`
    );
    return response.data;
  },

  selectFileVersion: async (projectId: string, fileId: number, versionId: number) => {
    const response = await apiClient.post(`/coding/${projectId}/files/${fileId}/select-version`, {
      version_id: versionId,
    });
    return response.data;
  },

  // Directory Planning (Agent/V2)
  planDirectoryV2Stream: (projectId: string) => {
    return `/coding/${projectId}/directories/plan-v2`;
  },

  planDirectoryAgentStream: (projectId: string) => {
    return `/coding/${projectId}/directories/plan-agent`;
  },

  getDirectoryAgentState: async (projectId: string) => {
    const response = await apiClient.get<DirectoryAgentStateResponse>(`/coding/${projectId}/directories/agent-state`);
    return response.data;
  },

  pauseDirectoryAgent: async (projectId: string, reason: string) => {
    const response = await apiClient.post(`/coding/${projectId}/directories/pause-agent`, {
      reason: reason || '用户手动停止',
    });
    return response.data;
  },

  clearDirectoryAgentState: async (projectId: string) => {
    const response = await apiClient.delete(`/coding/${projectId}/directories/agent-state`);
    return response.data;
  },
  
  // Blueprint generation
  generateBlueprint: async (projectId: string) => {
    const response = await apiClient.post(`/coding/${projectId}/blueprint/generate`, {
        allow_incomplete: true // Allow for demo purposes
    });
    return response.data;
  },

  // Systems
  listSystems: async (projectId: string) => {
    const response = await apiClient.get<CodingSystem[]>(`/coding/${projectId}/systems`);
    return response.data;
  },

  createSystem: async (
    projectId: string,
    payload: { name: string; description?: string; responsibilities?: string[]; tech_requirements?: string }
  ) => {
    const response = await apiClient.post<CodingSystem>(`/coding/${projectId}/systems`, payload);
    return response.data;
  },

  updateSystem: async (
    projectId: string,
    systemNumber: number,
    payload: { name?: string; description?: string; responsibilities?: string[]; tech_requirements?: string }
  ) => {
    const response = await apiClient.put<CodingSystem>(`/coding/${projectId}/systems/${systemNumber}`, payload);
    return response.data;
  },

  deleteSystem: async (projectId: string, systemNumber: number) => {
    const response = await apiClient.delete(`/coding/${projectId}/systems/${systemNumber}`);
    return response.data;
  },

  generateSystems: async (
    projectId: string,
    opts?: { minSystems?: number; maxSystems?: number; preference?: string }
  ) => {
    const response = await apiClient.post<CodingSystem[]>(`/coding/${projectId}/systems/generate`, {
      min_systems: opts?.minSystems ?? 3,
      max_systems: opts?.maxSystems ?? 8,
      preference: opts?.preference || undefined,
    });
    return response.data;
  },

  // Modules
  listModules: async (projectId: string) => {
    const response = await apiClient.get<CodingModule[]>(`/coding/${projectId}/modules`);
    return response.data;
  },

  createModule: async (
    projectId: string,
    payload: {
      system_number: number;
      name: string;
      type?: string;
      description?: string;
      interface?: string;
      dependencies?: string[];
    }
  ) => {
    const response = await apiClient.post<CodingModule>(`/coding/${projectId}/modules`, payload);
    return response.data;
  },

  updateModule: async (
    projectId: string,
    moduleNumber: number,
    payload: { name?: string; type?: string; description?: string; interface?: string; dependencies?: string[] }
  ) => {
    const response = await apiClient.put<CodingModule>(`/coding/${projectId}/modules/${moduleNumber}`, payload);
    return response.data;
  },

  deleteModule: async (projectId: string, moduleNumber: number) => {
    const response = await apiClient.delete(`/coding/${projectId}/modules/${moduleNumber}`);
    return response.data;
  },

  generateModules: async (
    projectId: string,
    opts: { systemNumber: number; minModules?: number; maxModules?: number; preference?: string }
  ) => {
    const response = await apiClient.post<CodingModule[]>(`/coding/${projectId}/modules/generate`, {
      system_number: opts.systemNumber,
      min_modules: opts.minModules ?? 3,
      max_modules: opts.maxModules ?? 8,
      preference: opts.preference || undefined,
    });
    return response.data;
  },

  generateAllModulesStream: (
    projectId: string,
    opts?: { minModules?: number; maxModules?: number; preference?: string }
  ) => {
    return {
      endpoint: `/coding/${projectId}/modules/generate-all`,
      body: {
        min_modules: opts?.minModules ?? 3,
        max_modules: opts?.maxModules ?? 8,
        preference: opts?.preference || undefined,
      },
    };
  },

  // Dependencies
  listDependencies: async (projectId: string) => {
    const response = await apiClient.get<CodingDependency[]>(`/coding/${projectId}/dependencies`);
    return response.data;
  },

  createDependency: async (
    projectId: string,
    payload: { from_module: string; to_module: string; description?: string }
  ) => {
    const response = await apiClient.post<CodingDependency>(`/coding/${projectId}/dependencies`, payload);
    return response.data;
  },

  deleteDependency: async (projectId: string, dep: { id: number; from: string; to: string }) => {
    const response = await apiClient.delete(`/coding/${projectId}/dependencies/${dep.id}`, {
      params: { from_module: dep.from, to_module: dep.to },
    });
    return response.data;
  },

  syncDependencies: async (projectId: string) => {
    const response = await apiClient.post(`/coding/${projectId}/dependencies/sync`);
    return response.data;
  },

  // RAG
  getRagCompleteness: async (projectId: string) => {
    const response = await apiClient.get<CodingRagCompletenessResponse>(`/coding/${projectId}/rag/completeness`);
    return response.data;
  },

  ingestAllRagData: async (projectId: string, force = false) => {
    const response = await apiClient.post<CodingRagIngestAllResponse>(
      `/coding/${projectId}/rag/ingest-all`,
      { force },
      { timeout: 10 * 60 * 1000 }
    );
    return response.data;
  },

  queryRag: async (projectId: string, query: string, opts?: { topK?: number; dataTypes?: string[] }) => {
    const response = await apiClient.post<CodingRagQueryResponse>(`/coding/${projectId}/rag/query`, {
      query,
      top_k: opts?.topK ?? 5,
      data_types: opts?.dataTypes || undefined,
      use_type_weights: true,
    });
    return response.data;
  },
};
