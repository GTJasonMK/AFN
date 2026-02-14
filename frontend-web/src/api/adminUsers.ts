import { apiClient } from './client';

export interface AdminUserMetrics {
  novel_projects: number;
  coding_projects: number;
  total_projects: number;
  llm_configs: number;
  embedding_configs: number;
  image_configs: number;
  theme_configs: number;
  last_activity_at?: string | null;
  recently_active: boolean;
}

export interface AdminUserItem {
  id: number;
  username: string;
  is_active: boolean;
  is_admin: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AdminUserMonitorItem extends AdminUserItem {
  metrics: AdminUserMetrics;
}

export interface AdminUsersListResponse {
  users: AdminUserItem[];
}

export interface AdminUsersMonitorSummary {
  total_users: number;
  active_users: number;
  inactive_users: number;
  admin_users: number;
  recently_active_users: number;
  total_novel_projects: number;
  total_coding_projects: number;
  total_projects: number;
  total_llm_configs: number;
  total_embedding_configs: number;
  total_image_configs: number;
  total_theme_configs: number;
}

export interface AdminUsersMonitorResponse {
  summary: AdminUsersMonitorSummary;
  users: AdminUserMonitorItem[];
}

export interface AdminUserCreateRequest {
  username: string;
  password: string;
  is_active: boolean;
  is_admin: boolean;
}

export const adminUsersApi = {
  list: async () => {
    const res = await apiClient.get<AdminUsersListResponse>('/admin/users');
    return res.data.users || [];
  },

  monitor: async () => {
    const res = await apiClient.get<AdminUsersMonitorResponse>('/admin/users/monitor');
    return res.data;
  },

  create: async (payload: AdminUserCreateRequest) => {
    const res = await apiClient.post<{ success: boolean; user: AdminUserItem }>('/admin/users', payload);
    return res.data;
  },

  updateStatus: async (userId: number, isActive: boolean) => {
    const res = await apiClient.patch<{ success: boolean; user: AdminUserItem }>(`/admin/users/${userId}/status`, {
      is_active: isActive,
    });
    return res.data;
  },

  updateRole: async (userId: number, isAdmin: boolean) => {
    const res = await apiClient.patch<{ success: boolean; user: AdminUserItem }>(`/admin/users/${userId}/role`, {
      is_admin: isAdmin,
    });
    return res.data;
  },

  resetPassword: async (userId: number, newPassword: string) => {
    const res = await apiClient.post<{ success: boolean }>(`/admin/users/${userId}/reset-password`, {
      new_password: newPassword,
    });
    return res.data;
  },
};
