import { apiClient } from './client';

export interface ProtagonistProfileSummary {
  id: number;
  character_name: string;
  last_synced_chapter: number;
  attribute_counts: {
    explicit: number;
    implicit: number;
    social: number;
  };
  created_at: string;
}

export interface ProtagonistProfileResponse {
  id: number;
  project_id: string;
  character_name: string;
  explicit_attributes: Record<string, any>;
  implicit_attributes: Record<string, any>;
  social_attributes: Record<string, any>;
  last_synced_chapter: number;
  created_at: string;
  updated_at: string;
}

export interface ProtagonistSyncResult {
  changes_applied: number;
  behaviors_recorded: number;
  deletions_marked: number;
  synced_chapter: number;
}

export type AttributeCategory = 'explicit' | 'implicit' | 'social';

export interface AttributeChangeResponse {
  id: number;
  profile_id: number;
  chapter_number: number;
  attribute_category: string;
  attribute_key: string;
  operation: string;
  old_value?: string | null;
  new_value?: string | null;
  change_description: string;
  event_cause: string;
  evidence: string;
  created_at: string;
}

export interface BehaviorRecordResponse {
  id: number;
  profile_id: number;
  chapter_number: number;
  behavior_description: string;
  original_text: string;
  behavior_tags: string[];
  classification_results: Record<string, string>;
  created_at: string;
}

export interface DeletionMarkResponse {
  id: number;
  profile_id: number;
  attribute_category: string;
  attribute_key: string;
  chapter_number: number;
  mark_reason: string;
  evidence: string;
  consecutive_count: number;
  last_marked_chapter: number;
  is_executed: boolean;
  created_at: string;
  updated_at: string;
}

export interface ImplicitStatsResponse {
  attribute_key: string;
  total: number;
  conform_count: number;
  non_conform_count: number;
  conform_rate: number;
  threshold_reached: boolean;
}

export interface ImplicitCheckResponse {
  attribute_key: string;
  current_value: any;
  decision: string;
  reasoning: string;
  suggested_new_value?: any;
  evidence_summary: string;
}

export interface SnapshotSummary {
  chapter_number: number;
  changes_in_chapter: number;
  behaviors_in_chapter: number;
  attribute_counts: {
    explicit: number;
    implicit: number;
    social: number;
  };
  created_at: string;
}

export interface SnapshotListResponse {
  profile_id: number;
  character_name: string;
  total_snapshots: number;
  snapshots: SnapshotSummary[];
}

export interface SnapshotResponse {
  id: number;
  profile_id: number;
  chapter_number: number;
  explicit_attributes: Record<string, any>;
  implicit_attributes: Record<string, any>;
  social_attributes: Record<string, any>;
  changes_in_chapter: number;
  behaviors_in_chapter: number;
  created_at: string;
}

export interface AttributeDiff {
  added: Record<string, any>;
  modified: Record<string, { from: any; to: any }>;
  deleted: Record<string, any>;
}

export interface DiffResponse {
  profile_id: number;
  character_name: string;
  from_chapter: number;
  to_chapter: number;
  categories: Record<string, AttributeDiff>;
  has_changes: boolean;
}

export interface RollbackResponse {
  success: boolean;
  target_chapter: number;
  message: string;
}

export interface ProfileConflictCheck {
  has_conflict: boolean;
  last_synced_chapter: number;
  max_available_chapter: number;
  available_snapshot_chapters: number[];
}

export const protagonistApi = {
  listProfiles: async (projectId: string) => {
    const res = await apiClient.get<ProtagonistProfileSummary[]>(`/novels/${projectId}/protagonist-profiles`);
    return res.data;
  },

  createProfile: async (projectId: string, characterName: string) => {
    const res = await apiClient.post<ProtagonistProfileResponse>(`/novels/${projectId}/protagonist-profiles`, {
      character_name: characterName,
      explicit_attributes: {},
      implicit_attributes: {},
      social_attributes: {},
    });
    return res.data;
  },

  getProfile: async (projectId: string, characterName: string) => {
    const res = await apiClient.get<ProtagonistProfileResponse>(
      `/novels/${projectId}/protagonist-profiles/${encodeURIComponent(characterName)}`
    );
    return res.data;
  },

  deleteProfile: async (projectId: string, characterName: string) => {
    const res = await apiClient.delete(`/novels/${projectId}/protagonist-profiles/${encodeURIComponent(characterName)}`);
    return res.data;
  },

  syncProfile: async (projectId: string, characterName: string, chapterNumber: number) => {
    const res = await apiClient.post<ProtagonistSyncResult>(
      `/novels/${projectId}/protagonist-profiles/${encodeURIComponent(characterName)}/sync`,
      { chapter_number: chapterNumber }
    );
    return res.data;
  },

  conflictCheck: async (projectId: string, characterName: string) => {
    const res = await apiClient.get<ProfileConflictCheck>(
      `/novels/${projectId}/protagonist-profiles/${encodeURIComponent(characterName)}/conflict-check`
    );
    return res.data;
  },

  getHistory: async (
    projectId: string,
    characterName: string,
    opts?: { startChapter?: number; endChapter?: number; category?: AttributeCategory }
  ) => {
    const res = await apiClient.get<AttributeChangeResponse[]>(
      `/novels/${projectId}/protagonist-profiles/${encodeURIComponent(characterName)}/history`,
      {
        params: {
          start_chapter: opts?.startChapter,
          end_chapter: opts?.endChapter,
          category: opts?.category,
        },
      }
    );
    return res.data;
  },

  getBehaviors: async (projectId: string, characterName: string, opts?: { chapter?: number; limit?: number }) => {
    const res = await apiClient.get<BehaviorRecordResponse[]>(
      `/novels/${projectId}/protagonist-profiles/${encodeURIComponent(characterName)}/behaviors`,
      { params: { chapter: opts?.chapter, limit: opts?.limit ?? 20 } }
    );
    return res.data;
  },

  getDeletionMarks: async (projectId: string, characterName: string, category?: AttributeCategory) => {
    const res = await apiClient.get<DeletionMarkResponse[]>(
      `/novels/${projectId}/protagonist-profiles/${encodeURIComponent(characterName)}/deletion-marks`,
      { params: category ? { category } : undefined }
    );
    return res.data;
  },

  executeDeletion: async (projectId: string, characterName: string, category: AttributeCategory, key: string) => {
    const res = await apiClient.post(
      `/novels/${projectId}/protagonist-profiles/${encodeURIComponent(characterName)}/deletion-marks/${category}/${encodeURIComponent(key)}/execute`
    );
    return res.data;
  },

  resetDeletionMarks: async (projectId: string, characterName: string, category: AttributeCategory, key: string) => {
    const res = await apiClient.post(
      `/novels/${projectId}/protagonist-profiles/${encodeURIComponent(characterName)}/deletion-marks/${category}/${encodeURIComponent(key)}/reset`
    );
    return res.data;
  },

  getSnapshots: async (projectId: string, characterName: string, opts?: { startChapter?: number; endChapter?: number }) => {
    const res = await apiClient.get<SnapshotListResponse>(
      `/novels/${projectId}/protagonist-profiles/${encodeURIComponent(characterName)}/snapshots`,
      { params: { start_chapter: opts?.startChapter, end_chapter: opts?.endChapter } }
    );
    return res.data;
  },

  getSnapshotAtChapter: async (projectId: string, characterName: string, chapter: number) => {
    const res = await apiClient.get<SnapshotResponse>(
      `/novels/${projectId}/protagonist-profiles/${encodeURIComponent(characterName)}/snapshots/${chapter}`
    );
    return res.data;
  },

  diffBetweenChapters: async (projectId: string, characterName: string, fromChapter: number, toChapter: number) => {
    const res = await apiClient.get<DiffResponse>(
      `/novels/${projectId}/protagonist-profiles/${encodeURIComponent(characterName)}/diff`,
      { params: { from_chapter: fromChapter, to_chapter: toChapter } }
    );
    return res.data;
  },

  rollbackToChapter: async (projectId: string, characterName: string, targetChapter: number) => {
    const res = await apiClient.post<RollbackResponse>(
      `/novels/${projectId}/protagonist-profiles/${encodeURIComponent(characterName)}/rollback`,
      { target_chapter: targetChapter }
    );
    return res.data;
  },

  getImplicitStats: async (projectId: string, characterName: string, attributeKey: string, window = 10) => {
    const res = await apiClient.get<ImplicitStatsResponse>(
      `/novels/${projectId}/protagonist-profiles/${encodeURIComponent(characterName)}/implicit-stats`,
      { params: { attribute_key: attributeKey, window } }
    );
    return res.data;
  },

  checkImplicitUpdate: async (projectId: string, characterName: string, attributeKey: string) => {
    const res = await apiClient.post<ImplicitCheckResponse>(
      `/novels/${projectId}/protagonist-profiles/${encodeURIComponent(characterName)}/implicit-check`,
      { attribute_key: attributeKey }
    );
    return res.data;
  },
};
