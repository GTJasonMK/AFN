import { apiClient } from './client';

export interface AuthStatusResponse {
  auth_enabled: boolean;
  auth_allow_registration: boolean;
}

export interface UserPublic {
  id: number;
  username: string;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AuthOkResponse {
  success: boolean;
  user: UserPublic;
}

export const authApi = {
  status: async () => {
    const res = await apiClient.get<AuthStatusResponse>('/auth/status', { silent: true } as any);
    return res.data;
  },

  me: async () => {
    const res = await apiClient.get<UserPublic>('/auth/me', { silent: true } as any);
    return res.data;
  },

  register: async (payload: { username: string; password: string }) => {
    const res = await apiClient.post<AuthOkResponse>('/auth/register', payload);
    return res.data;
  },

  login: async (payload: { username: string; password: string }) => {
    const res = await apiClient.post<AuthOkResponse>('/auth/login', payload, { silent: true } as any);
    return res.data;
  },

  logout: async () => {
    const res = await apiClient.post<{ success: boolean }>('/auth/logout', undefined, { silent: true } as any);
    return res.data;
  },

  changePassword: async (payload: { old_password: string; new_password: string }) => {
    const res = await apiClient.post<{ success: boolean }>('/auth/change-password', payload);
    return res.data;
  },
};

