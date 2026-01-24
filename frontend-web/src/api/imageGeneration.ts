import { apiClient, API_BASE_URL } from './client';

export interface GeneratedImageInfo {
  id: number;
  file_name: string;
  file_path: string;
  url: string;
  scene_id: number;
  panel_id?: string | null;
  image_type?: 'panel' | 'page' | string;
  width?: number | null;
  height?: number | null;
  prompt?: string | null;
  created_at: string;
}

export interface ImageGenerationResult {
  success: boolean;
  images: GeneratedImageInfo[];
  error_message?: string | null;
  generation_time?: number | null;
}

export interface ImageGenerationRequest {
  prompt: string;
  negative_prompt?: string | null;
  style?: string | null;
  ratio?: string | null;
  resolution?: string | null;
  quality?: string | null;
  count?: number;
  seed?: number | null;
  chapter_version_id?: number | null;
  panel_id?: string | null;
  reference_image_paths?: string[] | null;
  reference_strength?: number;

  // 漫画元数据（可选）
  dialogue?: string | null;
  dialogue_speaker?: string | null;
  dialogue_bubble_type?: string | null;
  dialogue_emotion?: string | null;
  dialogue_position?: string | null;
  narration?: string | null;
  narration_position?: string | null;
  sound_effects?: string[] | null;
  sound_effect_details?: Record<string, any>[] | null;
  composition?: string | null;
  camera_angle?: string | null;
  is_key_panel?: boolean;
  characters?: string[] | null;
  lighting?: string | null;
  atmosphere?: string | null;
  key_visual_elements?: string[] | null;
  dialogue_language?: string | null;
}

export interface PageImageGenerationRequest {
  full_page_prompt: string;
  negative_prompt?: string | null;
  layout_template?: string;
  layout_description?: string;
  ratio?: string;
  resolution?: string;
  style?: string | null;
  chapter_version_id?: number | null;
  reference_image_paths?: string[] | null;
  reference_strength?: number;
  panel_summaries?: Record<string, any>[] | null;
  dialogue_language?: string | null;
}

export interface ChapterMangaPDFRequest {
  title?: string | null;
  include_prompts?: boolean;
  page_size?: string;
  layout?: 'full' | 'manga' | string;
  chapter_version_id?: number | null;
}

export interface ChapterMangaPDFResponse {
  success: boolean;
  file_path?: string | null;
  file_name?: string | null;
  download_url?: string | null;
  page_count?: number;
  error_message?: string | null;
}

export function resolveAssetUrl(url: string): string {
  if (!url) return url;
  if (url.startsWith('http')) return url;
  const baseUrl = API_BASE_URL.replace(/\/api$/, '');
  return `${baseUrl}${url}`;
}

export const imageGenerationApi = {
  generatePanelImage: async (
    projectId: string,
    chapterNumber: number,
    sceneId: number,
    payload: ImageGenerationRequest
  ) => {
    const response = await apiClient.post<ImageGenerationResult>(
      `/image-generation/novels/${projectId}/chapters/${chapterNumber}/scenes/${sceneId}/generate`,
      payload,
      { timeout: 10 * 60 * 1000 }
    );
    return response.data;
  },

  generatePageImage: async (
    projectId: string,
    chapterNumber: number,
    pageNumber: number,
    payload: PageImageGenerationRequest
  ) => {
    const response = await apiClient.post<ImageGenerationResult>(
      `/image-generation/novels/${projectId}/chapters/${chapterNumber}/pages/${pageNumber}/generate`,
      payload,
      { timeout: 10 * 60 * 1000 }
    );
    return response.data;
  },

  listChapterImages: async (
    projectId: string,
    chapterNumber: number,
    params?: { chapter_version_id?: number; include_legacy?: boolean }
  ) => {
    const response = await apiClient.get<GeneratedImageInfo[]>(
      `/image-generation/novels/${projectId}/chapters/${chapterNumber}/images`,
      { params }
    );
    return response.data;
  },

  generateChapterMangaPDF: async (
    projectId: string,
    chapterNumber: number,
    payload?: ChapterMangaPDFRequest
  ) => {
    const response = await apiClient.post<ChapterMangaPDFResponse>(
      `/image-generation/novels/${projectId}/chapters/${chapterNumber}/manga-pdf`,
      payload || {},
      { timeout: 10 * 60 * 1000 }
    );
    return response.data;
  },

  getLatestChapterMangaPDF: async (projectId: string, chapterNumber: number) => {
    const response = await apiClient.get<ChapterMangaPDFResponse>(
      `/image-generation/novels/${projectId}/chapters/${chapterNumber}/manga-pdf/latest`
    );
    return response.data;
  },
};

