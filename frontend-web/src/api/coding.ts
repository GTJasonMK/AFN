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
  
  // Blueprint generation
  generateBlueprint: async (projectId: string) => {
    const response = await apiClient.post(`/coding/${projectId}/blueprint/generate`, {
        allow_incomplete: true // Allow for demo purposes
    });
    return response.data;
  }
};
