import { create } from 'zustand';
import { authApi, UserPublic } from '../api/auth';
import { AUTH_UNAUTHORIZED_EVENT } from '../api/client';

interface AuthStore {
  initialized: boolean;
  loading: boolean;
  authEnabled: boolean;
  allowRegistration: boolean;
  user: UserPublic | null;
  init: () => Promise<void>;
  reloadStatus: () => Promise<void>;
  refreshMe: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>;
  onUnauthorized: (message?: string) => void;
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  initialized: false,
  loading: false,
  authEnabled: false,
  allowRegistration: true,
  user: null,

  init: async () => {
    if (get().initialized || get().loading) return;
    set({ loading: true });
    try {
      const status = await authApi.status();
      const authEnabled = Boolean(status.auth_enabled);
      const allowRegistration = Boolean(status.auth_allow_registration);
      set({ authEnabled, allowRegistration });

      if (authEnabled) {
        try {
          const me = await authApi.me();
          set({ user: me });
        } catch {
          set({ user: null });
        }
      } else {
        // 未启用登录时保持历史单用户行为：前端不需要 user 信息即可使用
        set({ user: null });
      }

      set({ initialized: true });
    } finally {
      set({ loading: false });
    }
  },

  reloadStatus: async () => {
    set({ loading: true });
    try {
      const status = await authApi.status();
      const authEnabled = Boolean(status.auth_enabled);
      const allowRegistration = Boolean(status.auth_allow_registration);
      set({ authEnabled, allowRegistration });

      if (!authEnabled) {
        set({ user: null });
        return;
      }

      try {
        const me = await authApi.me();
        set({ user: me });
      } catch {
        set({ user: null });
      }
    } finally {
      set({ loading: false, initialized: true });
    }
  },

  refreshMe: async () => {
    if (!get().authEnabled) return;
    try {
      const me = await authApi.me();
      set({ user: me });
    } catch {
      set({ user: null });
    }
  },

  login: async (username: string, password: string) => {
    set({ loading: true });
    try {
      const res = await authApi.login({ username, password });
      set({ user: res.user });
    } finally {
      set({ loading: false });
    }
  },

  register: async (username: string, password: string) => {
    set({ loading: true });
    try {
      const res = await authApi.register({ username, password });
      set({ user: res.user });
    } finally {
      set({ loading: false });
    }
  },

  logout: async () => {
    set({ loading: true });
    try {
      await authApi.logout();
    } finally {
      set({ user: null, loading: false });
    }
  },

  changePassword: async (oldPassword: string, newPassword: string) => {
    set({ loading: true });
    try {
      await authApi.changePassword({ old_password: oldPassword, new_password: newPassword });
    } finally {
      set({ loading: false });
    }
  },

  onUnauthorized: () => {
    // 401 时清空登录态，交由 AuthGate 展示登录页
    set({ user: null });
  },
}));

// 监听全局 401 事件（由 apiClient 拦截器派发）
if (typeof window !== 'undefined') {
  window.addEventListener(AUTH_UNAUTHORIZED_EVENT, () => {
    try {
      useAuthStore.getState().onUnauthorized();
    } catch {
      // ignore
    }
  });
}

export const isAdminUser = (authEnabled: boolean, user: UserPublic | null) => {
  if (!authEnabled) return true;
  return (user?.username || '').trim() === 'desktop_user';
};
