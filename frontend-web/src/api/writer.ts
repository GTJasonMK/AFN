import { apiClient } from './client';
import type { AxiosRequestConfig } from 'axios';

const WRITER_PREFIX = '/writer';

export interface Chapter {
  chapter_number: number;
  title: string;
  summary: string;
  real_summary?: string | null;
  content?: string | null;
  versions?: string[] | null;
  evaluation?: string | null;
  generation_status: string;
  selected_version?: number | null;
  selected_version_id?: number | null;
  word_count?: number;
  analysis_data?: any | null;
}

export interface ChapterVersion {
  id: string;
  chapter_id: string;
  version_label: string;
  content: string;
  created_at: string;
  provider: string;
}

export interface RAGStatistics {
  chunk_count: number;
  summary_count: number;
  context_length: number;
  query_main?: string | null;
  query_characters: string[];
  query_foreshadowing: string[];
}

export interface PromptPreviewResponse {
  system_prompt: string;
  user_prompt: string;
  rag_statistics: RAGStatistics;
  prompt_sections: Record<string, string>;
  total_length: number;
  estimated_tokens: number;
}

export interface TrackedCharactersResponse {
  project_id: string;
  characters: string[];
  count: number;
}

export interface ChapterCharacterStatesResponse {
  project_id: string;
  chapter_number: number;
  character_states: Record<string, any>;
}

export interface CharacterTimelineItem {
  chapter_number: number;
  location?: string | null;
  status?: string | null;
  changes?: string[];
}

export interface CharacterTimelineResponse {
  project_id: string;
  character_name: string;
  timeline: CharacterTimelineItem[];
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

export interface MangaPromptProgress {
  status: string;
  stage: string;
  stage_label: string;
  current: number;
  total: number;
  message: string;
  can_resume: boolean;
  analysis_data?: any;
}

export const writerApi = {
  // === 章节基础操作 ===
  getChapter: async (projectId: string, chapterNumber: number) => {
    const response = await apiClient.get<Chapter>(`/novels/${projectId}/chapters/${chapterNumber}`);
    return response.data;
  },

  updateChapter: async (projectId: string, chapterNumber: number, content: string, opts?: { triggerRag?: boolean }) => {
    const response = await apiClient.put(`${WRITER_PREFIX}/novels/${projectId}/chapters/${chapterNumber}`, {
      content,
      trigger_rag: Boolean(opts?.triggerRag),
    });
    return response.data;
  },

  importChapter: async (
    projectId: string,
    chapterNumber: number,
    title: string,
    content: string,
    reqConfig?: AxiosRequestConfig
  ) => {
    const response = await apiClient.post(
      `${WRITER_PREFIX}/novels/${projectId}/chapters/import`,
      {
        chapter_number: chapterNumber,
        title,
        content,
      },
      reqConfig
    );
    return response.data;
  },

  createChapter: async (projectId: string, chapterNumber: number) => {
    // 与桌面端一致：创建章节时同步 upsert 大纲（title）与章节记录
    return writerApi.importChapter(projectId, chapterNumber, `第${chapterNumber}章`, "");
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
  selectVersion: async (
    projectId: string,
    chapterNumber: number,
    versionIndex: number,
    opts?: { triggerRagProcessing?: boolean }
  ) => {
    const response = await apiClient.post(`${WRITER_PREFIX}/novels/${projectId}/chapters/select`, {
      chapter_number: chapterNumber,
      version_index: versionIndex,
      trigger_rag_processing: Boolean(opts?.triggerRagProcessing),
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

  // === 提示词预览 ===
  previewChapterPrompt: async (
    projectId: string,
    chapterNumber: number,
    opts?: { writingNotes?: string; isRetry?: boolean; useRag?: boolean }
  ) => {
    const response = await apiClient.post<PromptPreviewResponse>(
      `${WRITER_PREFIX}/novels/${projectId}/chapters/preview-prompt`,
      {
        chapter_number: chapterNumber,
        writing_notes: opts?.writingNotes || undefined,
        is_retry: Boolean(opts?.isRetry),
        use_rag: opts?.useRag !== false,
      }
    );
    return response.data;
  },

  // === 批量大纲生成 ===
  generateOutlinesByCount: async (projectId: string) => {
    // 这是一个流式接口，通常通过 useSSE 调用，但也可以作为触发器
    // 这里仅提供类型定义参考，实际调用在组件中通过 useSSE
    return `${WRITER_PREFIX}/novels/${projectId}/chapter-outlines/generate-by-count`;
  },

  deleteLatestChapterOutlines: async (projectId: string, count: number) => {
    const response = await apiClient.delete(
      `${WRITER_PREFIX}/novels/${projectId}/chapter-outlines/delete-latest`,
      { data: { count } }
    );
    return response.data;
  },

  regenerateChapterOutline: async (
    projectId: string,
    chapterNumber: number,
    opts?: { prompt?: string; cascadeDelete?: boolean },
    reqConfig?: AxiosRequestConfig
  ) => {
    const response = await apiClient.post(
      `${WRITER_PREFIX}/novels/${projectId}/chapter-outlines/${chapterNumber}/regenerate`,
      {
        prompt: opts?.prompt || undefined,
        cascade_delete: Boolean(opts?.cascadeDelete),
      },
      reqConfig
    );
    return response.data;
  },

  // === 长篇部分大纲 (Part Outlines) ===
  getPartOutlines: async (projectId: string) => {
    // 获取部分大纲进度/列表
    const response = await apiClient.get(`${WRITER_PREFIX}/novels/${projectId}/parts/progress`);
    return response.data;
  },

  deleteLatestPartOutlines: async (projectId: string, count: number, reqConfig?: AxiosRequestConfig) => {
    const response = await apiClient.delete(
      `${WRITER_PREFIX}/novels/${projectId}/parts/delete-latest`,
      {
        params: { count: Math.max(1, Number(count) || 1) },
        ...(reqConfig || {}),
      }
    );
    return response.data;
  },

  generatePartOutlines: async (
    projectId: string,
    totalChapters: number,
    chaptersPerPart: number = 20,
    reqConfig?: AxiosRequestConfig
  ) => {
    const response = await apiClient.post(
      `${WRITER_PREFIX}/novels/${projectId}/parts/generate`,
      {
        total_chapters: totalChapters,
        chapters_per_part: chaptersPerPart,
      },
      reqConfig
    );
    return response.data;
  },

  regenerateAllPartOutlines: async (projectId: string, prompt?: string, reqConfig?: AxiosRequestConfig) => {
    const response = await apiClient.post(
      `${WRITER_PREFIX}/novels/${projectId}/part-outlines/regenerate`,
      { prompt: prompt || undefined, cascade_delete: true },
      reqConfig
    );
    return response.data;
  },

  regenerateLastPartOutline: async (projectId: string, prompt?: string, reqConfig?: AxiosRequestConfig) => {
    const response = await apiClient.post(
      `${WRITER_PREFIX}/novels/${projectId}/part-outlines/regenerate-last`,
      { prompt: prompt || undefined, cascade_delete: false },
      reqConfig
    );
    return response.data;
  },

  regeneratePartOutline: async (
    projectId: string,
    partNumber: number,
    opts?: { prompt?: string; cascadeDelete?: boolean },
    reqConfig?: AxiosRequestConfig
  ) => {
    const response = await apiClient.post(
      `${WRITER_PREFIX}/novels/${projectId}/part-outlines/${partNumber}/regenerate`,
      { prompt: opts?.prompt || undefined, cascade_delete: Boolean(opts?.cascadeDelete) },
      reqConfig
    );
    return response.data;
  },

  generatePartChapters: async (
    projectId: string,
    partNumber: number,
    regenerate = false,
    reqConfig?: AxiosRequestConfig
  ) => {
    const response = await apiClient.post(
      `${WRITER_PREFIX}/novels/${projectId}/parts/${partNumber}/chapters`,
      { regenerate: Boolean(regenerate) },
      reqConfig
    );
    return response.data;
  },

  // === 角色状态追踪 ===
  listTrackedCharacters: async (projectId: string) => {
    const response = await apiClient.get<TrackedCharactersResponse>(
      `${WRITER_PREFIX}/novels/${projectId}/character-states/characters`
    );
    return response.data;
  },

  getChapterCharacterStates: async (projectId: string, chapterNumber: number, characterName?: string) => {
    const response = await apiClient.get<ChapterCharacterStatesResponse>(
      `${WRITER_PREFIX}/novels/${projectId}/character-states/chapter/${chapterNumber}`,
      { params: characterName ? { character_name: characterName } : undefined }
    );
    return response.data;
  },

  getCharacterTimeline: async (
    projectId: string,
    characterName: string,
    opts?: { fromChapter?: number; toChapter?: number }
  ) => {
    const response = await apiClient.get<CharacterTimelineResponse>(
      `${WRITER_PREFIX}/novels/${projectId}/character-states/timeline/${encodeURIComponent(characterName)}`,
      {
        params: {
          from_chapter: opts?.fromChapter ?? 1,
          to_chapter: opts?.toChapter,
        },
      }
    );
    return response.data;
  },

  // === 漫画 ===
  getMangaPrompts: async (projectId: string, chapterNumber: number, reqConfig?: AxiosRequestConfig) => {
    const response = await apiClient.get<MangaPromptResult>(
      `${WRITER_PREFIX}/novels/${projectId}/chapters/${chapterNumber}/manga-prompts`,
      reqConfig
    );
    return response.data;
  },

  getMangaPromptProgress: async (projectId: string, chapterNumber: number, reqConfig?: AxiosRequestConfig) => {
    const response = await apiClient.get<MangaPromptProgress>(
      `${WRITER_PREFIX}/novels/${projectId}/chapters/${chapterNumber}/manga-prompts/progress`,
      reqConfig
    );
    return response.data;
  },

  cancelMangaPromptGeneration: async (projectId: string, chapterNumber: number, reqConfig?: AxiosRequestConfig) => {
    const response = await apiClient.post(
      `${WRITER_PREFIX}/novels/${projectId}/chapters/${chapterNumber}/manga-prompts/cancel`,
      undefined,
      reqConfig
    );
    return response.data;
  },

  deleteMangaPrompts: async (projectId: string, chapterNumber: number, reqConfig?: AxiosRequestConfig) => {
    const response = await apiClient.delete(
      `${WRITER_PREFIX}/novels/${projectId}/chapters/${chapterNumber}/manga-prompts`,
      reqConfig
    );
    return response.data;
  },

  generateMangaPrompts: async (projectId: string, chapterNumber: number) => {
    const response = await apiClient.post<MangaPromptResult>(
      `${WRITER_PREFIX}/novels/${projectId}/chapters/${chapterNumber}/manga-prompts`,
      {
        style: "manga",
        min_pages: 8,
        max_pages: 15
      }
    );
    return response.data;
  },

  generateMangaPromptsWithOptions: async (
    projectId: string,
    chapterNumber: number,
    opts?: {
      style?: string;
      minPages?: number;
      maxPages?: number;
      language?: 'chinese' | 'japanese' | 'english' | 'korean';
      usePortraits?: boolean;
      autoGeneratePortraits?: boolean;
      forceRestart?: boolean;
      startFromStage?: 'extraction' | 'planning' | 'storyboard' | 'prompt_building' | 'page_prompt_building' | null;
      autoGeneratePageImages?: boolean;
      pagePromptConcurrency?: number;
    },
    reqConfig?: AxiosRequestConfig
  ) => {
    const response = await apiClient.post<MangaPromptResult>(
      `${WRITER_PREFIX}/novels/${projectId}/chapters/${chapterNumber}/manga-prompts`,
      {
        style: opts?.style ?? "manga",
        min_pages: typeof opts?.minPages === 'number' ? opts.minPages : 8,
        max_pages: typeof opts?.maxPages === 'number' ? opts.maxPages : 15,
        language: opts?.language ?? undefined,
        use_portraits: typeof opts?.usePortraits === 'boolean' ? opts.usePortraits : undefined,
        auto_generate_portraits: typeof opts?.autoGeneratePortraits === 'boolean' ? opts.autoGeneratePortraits : undefined,
        force_restart: Boolean(opts?.forceRestart),
        start_from_stage: opts?.startFromStage ?? undefined,
        auto_generate_page_images: typeof opts?.autoGeneratePageImages === 'boolean' ? opts.autoGeneratePageImages : undefined,
        page_prompt_concurrency: typeof opts?.pagePromptConcurrency === 'number' ? opts.pagePromptConcurrency : undefined,
      },
      reqConfig
    );
    return response.data;
  },

  // === 项目获取 ===
  getProject: async (projectId: string) => {
    const response = await apiClient.get(`/novels/${projectId}`);
    return response.data;
  }
};
