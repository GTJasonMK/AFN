import { create } from 'zustand';
import { authApi, UserPublic } from '../api/auth';
import { AUTH_UNAUTHORIZED_EVENT } from '../api/client';
import { clearBootstrapCache, readBootstrapCache, writeBootstrapCache } from '../utils/bootstrapCache';

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

type AuthBootstrapSnapshot = {
  authEnabled: boolean;
  allowRegistration: boolean;
  user: UserPublic | null;
};

const AUTH_BOOTSTRAP_CACHE_KEY = 'afn:auth:bootstrap:v1';
const AUTH_BOOTSTRAP_CACHE_TTL_MS = 10 * 60 * 1000;

const saveAuthSnapshot = (state: Pick<AuthStore, 'authEnabled' | 'allowRegistration' | 'user'>) => {
  writeBootstrapCache<AuthBootstrapSnapshot>(AUTH_BOOTSTRAP_CACHE_KEY, {
    authEnabled: Boolean(state.authEnabled),
    allowRegistration: Boolean(state.allowRegistration),
    user: state.user ?? null,
  });
};

let authInitPromise: Promise<void> | null = null;

export const useAuthStore = create<AuthStore>((set, get) => ({
  initialized: false,
  loading: false,
  authEnabled: false,
  allowRegistration: true,
  user: null,

  init: async () => {
    if (authInitPromise) return authInitPromise;

    authInitPromise = (async () => {
      const cached = readBootstrapCache<AuthBootstrapSnapshot>(AUTH_BOOTSTRAP_CACHE_KEY, AUTH_BOOTSTRAP_CACHE_TTL_MS);
      if (cached) {
        set({
          authEnabled: Boolean(cached.authEnabled),
          allowRegistration: Boolean(cached.allowRegistration),
          user: cached.user ?? null,
          initialized: true,
        });
      }

      const shouldBlock = !get().initialized;
      if (shouldBlock) {
        set({ loading: true });
      }

      try {
        const status = await authApi.status();
        const authEnabled = Boolean(status.auth_enabled);
        const allowRegistration = Boolean(status.auth_allow_registration);

        if (!authEnabled) {
          set({
            authEnabled: false,
            allowRegistration,
            user: null,
            initialized: true,
          });
          saveAuthSnapshot({ authEnabled: false, allowRegistration, user: null });
          return;
        }

        try {
          const me = await authApi.me();
          set({ authEnabled: true, allowRegistration, user: me, initialized: true });
          saveAuthSnapshot({ authEnabled: true, allowRegistration, user: me });
        } catch {
          set({ authEnabled: true, allowRegistration, user: null, initialized: true });
          saveAuthSnapshot({ authEnabled: true, allowRegistration, user: null });
        }
      } catch (error) {
        console.error('Auth init failed:', error);
        set({ authEnabled: false, allowRegistration: true, user: null, initialized: true });
        clearBootstrapCache(AUTH_BOOTSTRAP_CACHE_KEY);
      } finally {
        set({ loading: false });
      }
    })().finally(() => {
      authInitPromise = null;
    });

    return authInitPromise;
  },

  reloadStatus: async () => {
    set({ loading: !get().initialized });
    try {
      const status = await authApi.status();
      const authEnabled = Boolean(status.auth_enabled);
      const allowRegistration = Boolean(status.auth_allow_registration);
      set({ authEnabled, allowRegistration, initialized: true });

      if (!authEnabled) {
        set({ user: null });
        saveAuthSnapshot({ authEnabled: false, allowRegistration, user: null });
        return;
      }

      try {
        const me = await authApi.me();
        set({ user: me });
        saveAuthSnapshot({ authEnabled: true, allowRegistration, user: me });
      } catch {
        set({ user: null });
        saveAuthSnapshot({ authEnabled: true, allowRegistration, user: null });
      }
    } catch (error) {
      console.error('Auth reload failed:', error);
    } finally {
      set({ loading: false, initialized: true });
    }
  },

  refreshMe: async () => {
    if (!get().authEnabled) return;

    try {
      const me = await authApi.me();
      set({ user: me });
      saveAuthSnapshot({
        authEnabled: get().authEnabled,
        allowRegistration: get().allowRegistration,
        user: me,
      });
    } catch {
      set({ user: null });
      saveAuthSnapshot({
        authEnabled: get().authEnabled,
        allowRegistration: get().allowRegistration,
        user: null,
      });
    }
  },

  login: async (username: string, password: string) => {
    set({ loading: true });
    try {
      const res = await authApi.login({ username, password });
      set({ user: res.user, initialized: true });
      saveAuthSnapshot({
        authEnabled: get().authEnabled,
        allowRegistration: get().allowRegistration,
        user: res.user,
      });
    } finally {
      set({ loading: false });
    }
  },

  register: async (username: string, password: string) => {
    set({ loading: true });
    try {
      const res = await authApi.register({ username, password });
      set({ user: res.user, initialized: true });
      saveAuthSnapshot({
        authEnabled: get().authEnabled,
        allowRegistration: get().allowRegistration,
        user: res.user,
      });
    } finally {
      set({ loading: false });
    }
  },

  logout: async () => {
    set({ loading: true });
    try {
      await authApi.logout();
    } finally {
      set({ user: null, loading: false, initialized: true });
      saveAuthSnapshot({
        authEnabled: get().authEnabled,
        allowRegistration: get().allowRegistration,
        user: null,
      });
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
    saveAuthSnapshot({
      authEnabled: get().authEnabled,
      allowRegistration: get().allowRegistration,
      user: null,
    });
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
  if (!user) return false;

  // 兼容旧后端（尚未返回 is_admin）时的只读兜底，避免误判。
  if (typeof (user as any).is_admin !== 'boolean') {
    return (user.username || '').trim() === 'desktop_user';
  }

  return Boolean(user.is_admin);
};
