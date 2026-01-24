import { apiClient } from './client';

const WRITER_PREFIX = '/writer';

export interface Chapter {
  id: string;
  project_id: string;
  chapter_number: number;
  title: string;
  content?: string;
  summary?: string;
  word_count?: number;
  status: string;
  selected_version_id?: string;
  versions?: ChapterVersion[];
}

export interface ChapterVersion {
  id: string;
  chapter_id: string;
  version_label: string;
  content: string;
  created_at: string;
  provider: string;
}

export interface MangaPanel {
  panel_id: string;
  page_number: number;
  panel_number: number;
  scene_id: number;
  shape: string;
  shot_type: string;
  row_id: number;
  row_span: number;
  width_ratio: string;
  aspect_ratio: string;
  prompt: string;
  negative_prompt: string;
  dialogues: any[];
  characters: string[];
  reference_image_paths: string[];
  dialogue_language: string;
}

export interface MangaPage {
  page_number: number;
  panel_count: number;
  layout_description?: string;
  gutter_horizontal?: number;
  gutter_vertical?: number;
}

export interface MangaPagePrompt {
  page_number: number;
  layout_template: string;
  layout_description: string;
  full_page_prompt: string;
  negative_prompt: string;
  aspect_ratio: string;
  panel_summaries: any[];
  reference_image_paths: string[];
}

export interface MangaPromptResult {
  chapter_number: number;
  style: string;
  character_profiles: Record<string, string>;
  total_pages: number;
  total_panels: number;
  pages: MangaPage[];
  scenes: any[];
  panels: MangaPanel[];
  dialogue_language: string;
  analysis_data?: any;
  is_complete: boolean;
  completed_pages_count?: number | null;
  page_prompts: MangaPagePrompt[];
}

export const writerApi = {
  // === 章节基础操作 ===
  getChapter: async (projectId: string, chapterNumber: number) => {
    const response = await apiClient.get<Chapter>(`/novels/${projectId}/chapters/${chapterNumber}`);
    return response.data;
  },

  updateChapter: async (projectId: string, chapterNumber: number, content: string) => {
    const response = await apiClient.put(`${WRITER_PREFIX}/novels/${projectId}/chapters/${chapterNumber}`, {
      content,
      trigger_rag: false 
    });
    return response.data;
  },

  createChapter: async (projectId: string, chapterNumber: number) => {
    return writerApi.updateChapter(projectId, chapterNumber, "");
  },
  
  deleteChapters: async (projectId: string, chapterNumbers: number[]) => {
    const response = await apiClient.post(`${WRITER_PREFIX}/novels/${projectId}/chapters/delete`, {
      chapter_numbers: chapterNumbers
    });
    return response.data;
  },

  resetChapter: async (projectId: string, chapterNumber: number) => {
    const response = await apiClient.post(`${WRITER_PREFIX}/novels/${projectId}/chapters/${chapterNumber}/reset`);
    return response.data;
  },

  updateOutline: async (projectId: string, chapterNumber: number, title: string, summary: string) => {
    const response = await apiClient.post(`${WRITER_PREFIX}/novels/${projectId}/chapters/update-outline`, {
      chapter_number: chapterNumber,
      title,
      summary
    });
    return response.data;
  },

  // === 版本管理 ===
  selectVersion: async (projectId: string, chapterNumber: number, versionIndex: number) => {
    const response = await apiClient.post(`${WRITER_PREFIX}/novels/${projectId}/chapters/select`, {
      chapter_number: chapterNumber,
      version_index: versionIndex
    });
    return response.data;
  },

  retryVersion: async (projectId: string, chapterNumber: number, versionIndex: number, customPrompt?: string) => {
    const response = await apiClient.post(`${WRITER_PREFIX}/novels/${projectId}/chapters/retry-version`, {
      chapter_number: chapterNumber,
      version_index: versionIndex,
      custom_prompt: customPrompt
    });
    return response.data;
  },

  evaluateChapter: async (projectId: string, chapterNumber: number) => {
    const response = await apiClient.post(`${WRITER_PREFIX}/novels/${projectId}/chapters/evaluate`, {
      chapter_number: chapterNumber
    });
    return response.data;
  },

  // === 批量大纲生成 ===
  generateOutlinesByCount: async (projectId: string) => {
    // 这是一个流式接口，通常通过 useSSE 调用，但也可以作为触发器
    // 这里仅提供类型定义参考，实际调用在组件中通过 useSSE
    return `${WRITER_PREFIX}/novels/${projectId}/chapter-outlines/generate-by-count`;
  },

  // === 长篇部分大纲 (Part Outlines) ===
  getPartOutlines: async (projectId: string) => {
    // 获取部分大纲进度/列表
    const response = await apiClient.get(`${WRITER_PREFIX}/novels/${projectId}/parts/progress`);
    return response.data;
  },

  generatePartOutlines: async (projectId: string, totalChapters: number, chaptersPerPart: number = 20) => {
    const response = await apiClient.post(`${WRITER_PREFIX}/novels/${projectId}/parts/generate`, {
        total_chapters: totalChapters,
        chapters_per_part: chaptersPerPart
    });
    return response.data;
  },

  // === 漫画 ===
  getMangaPrompts: async (projectId: string, chapterNumber: number) => {
    const response = await apiClient.get<MangaPromptResult>(`${WRITER_PREFIX}/novels/${projectId}/chapters/${chapterNumber}/manga-prompts`);
    return response.data;
  },

  generateMangaPrompts: async (projectId: string, chapterNumber: number) => {
    const response = await apiClient.post<MangaPromptResult>(`${WRITER_PREFIX}/novels/${projectId}/chapters/${chapterNumber}/manga-prompts`, {
      style: "manga",
      min_pages: 8,
      max_pages: 15
    });
    return response.data;
  },

  // === 项目获取 ===
  getProject: async (projectId: string) => {
    const response = await apiClient.get(`/novels/${projectId}`);
    return response.data;
  }
};
