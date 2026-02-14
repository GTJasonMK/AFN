import { apiClient } from './client';

export interface AdminStatusCount {
  status: string;
  count: number;
}

export interface AdminOverviewSummary {
  total_users: number;
  active_users: number;
  recently_active_users: number;
  total_novel_projects: number;
  total_coding_projects: number;
  total_projects: number;
  total_llm_configs: number;
  total_embedding_configs: number;
  total_image_configs: number;
  total_theme_configs: number;
}

export interface AdminOverviewResponse {
  summary: AdminOverviewSummary;
  novel_status_distribution: AdminStatusCount[];
  coding_status_distribution: AdminStatusCount[];
  generated_at: string;
}

export interface AdminProjectSummary {
  total_novel_projects: number;
  total_coding_projects: number;
  total_projects: number;
}

export interface AdminRecentProjectItem {
  kind: 'novel' | 'coding' | string;
  project_id: string;
  title: string;
  status: string;
  user_id: number;
  username: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AdminTopProjectUser {
  user_id: number;
  username: string;
  novel_projects: number;
  coding_projects: number;
  total_projects: number;
  last_project_updated_at?: string | null;
}

export interface AdminProjectsResponse {
  summary: AdminProjectSummary;
  recent_projects: AdminRecentProjectItem[];
  top_users: AdminTopProjectUser[];
  novel_status_distribution: AdminStatusCount[];
  coding_status_distribution: AdminStatusCount[];
  generated_at: string;
}

export interface AdminConfigTypeSummary {
  config_type: string;
  total: number;
  active: number;
}

export interface AdminConfigsSummary {
  total_configs: number;
  total_active_configs: number;
  by_type: AdminConfigTypeSummary[];
}

export interface AdminTopConfigUser {
  user_id: number;
  username: string;
  llm_configs: number;
  embedding_configs: number;
  image_configs: number;
  theme_configs: number;
  total_configs: number;
}

export interface AdminActiveConfigItem {
  config_type: string;
  config_id: number;
  config_name: string;
  user_id: number;
  username: string;
  updated_at?: string | null;
  test_status?: string | null;
}

export interface AdminConfigTestStatusCount {
  status: string;
  count: number;
}

export interface AdminConfigsResponse {
  summary: AdminConfigsSummary;
  top_users: AdminTopConfigUser[];
  active_configs: AdminActiveConfigItem[];
  test_status_distribution: AdminConfigTestStatusCount[];
  generated_at: string;
}

export interface AdminTrendPoint {
  date: string;
  value: number;
}

export interface AdminTrendSeries {
  key: string;
  label: string;
  points: AdminTrendPoint[];
}

export interface AdminDashboardTrendsResponse {
  days: number;
  series: AdminTrendSeries[];
  generated_at: string;
}

const TRENDS_CACHE_TTL_MS = 30_000;
const trendsCache = new Map<number, { expiresAt: number; data: AdminDashboardTrendsResponse }>();
const trendsInFlight = new Map<number, Promise<AdminDashboardTrendsResponse>>();

const normalizeDays = (days: number): number => {
  const safeDays = Number(days);
  if (!Number.isFinite(safeDays) || safeDays <= 0) return 21;
  return Math.max(1, Math.min(90, Math.round(safeDays)));
};

const fetchTrends = async (days: number, force = false): Promise<AdminDashboardTrendsResponse> => {
  const normalizedDays = normalizeDays(days);

  if (!force) {
    const cached = trendsCache.get(normalizedDays);
    if (cached && cached.expiresAt > Date.now()) {
      return cached.data;
    }

    const inFlight = trendsInFlight.get(normalizedDays);
    if (inFlight) {
      return inFlight;
    }
  }

  const request = apiClient
    .get<AdminDashboardTrendsResponse>('/admin/dashboard/trends', {
      params: { days: normalizedDays },
    })
    .then((res) => {
      trendsCache.set(normalizedDays, {
        data: res.data,
        expiresAt: Date.now() + TRENDS_CACHE_TTL_MS,
      });
      return res.data;
    })
    .finally(() => {
      trendsInFlight.delete(normalizedDays);
    });

  trendsInFlight.set(normalizedDays, request);
  return request;
};

export const adminDashboardApi = {
  overview: async () => {
    const res = await apiClient.get<AdminOverviewResponse>('/admin/dashboard/overview');
    return res.data;
  },

  projects: async (limit = 40) => {
    const res = await apiClient.get<AdminProjectsResponse>('/admin/dashboard/projects', {
      params: { limit },
    });
    return res.data;
  },

  configs: async (limit = 100) => {
    const res = await apiClient.get<AdminConfigsResponse>('/admin/dashboard/configs', {
      params: { limit },
    });
    return res.data;
  },

  trends: async (days = 21, force = false) => {
    return fetchTrends(days, force);
  },

  prefetchTrends: (days = 21) => {
    void fetchTrends(days).catch(() => undefined);
  },

  clearTrendsCache: () => {
    trendsCache.clear();
    trendsInFlight.clear();
  },
};
