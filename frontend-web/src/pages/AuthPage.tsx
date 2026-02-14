import React, { useMemo, useState } from 'react';
import { BookCard } from '../components/ui/BookCard';
import { BookInput } from '../components/ui/BookInput';
import { BookButton } from '../components/ui/BookButton';
import { useAuthStore } from '../store/auth';
import { useToast } from '../components/feedback/Toast';
import { Lock } from 'lucide-react';
import { extractApiErrorMessage } from '../api/client';

export const AuthPage: React.FC = () => {
  const { authEnabled, allowRegistration, loading, login, register } = useAuthStore();
  const { addToast } = useToast();

  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');

  const canRegister = Boolean(authEnabled && allowRegistration);
  const effectiveMode = useMemo(() => (canRegister ? mode : 'login'), [canRegister, mode]);

  const handleSubmit = async () => {
    const u = username.trim();
    if (!u) {
      addToast('请输入用户名', 'error');
      return;
    }
    if (!password) {
      addToast('请输入密码', 'error');
      return;
    }

    try {
      if (effectiveMode === 'register') {
        if (password !== password2) {
          addToast('两次输入的密码不一致', 'error');
          return;
        }
        await register(u, password);
        addToast('注册并登录成功', 'success');
      } else {
        await login(u, password);
        addToast('登录成功', 'success');
      }
    } catch (e: any) {
      console.error(e);
      const msg = extractApiErrorMessage(e, effectiveMode === 'register' ? '注册失败' : '登录失败');
      addToast(msg, 'error');
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <BookCard className="w-full max-w-md p-6">
        <div className="flex items-center gap-2 text-book-text-main">
          <Lock size={18} className="text-book-primary" />
          <div className="font-serif text-lg font-bold">需要登录</div>
        </div>

        <div className="mt-2 text-xs text-book-text-muted leading-relaxed">
          内置管理员账号：<span className="font-mono">desktop_user</span>
          <span className="ml-2">（初始密码由部署配置/首次启动生成，建议登录后立即修改）</span>
        </div>

        {canRegister ? (
          <div className="mt-4 grid grid-cols-2 gap-2">
            <button
              onClick={() => setMode('login')}
              className={`px-3 py-2 rounded-lg border text-sm font-bold transition-all ${
                effectiveMode === 'login'
                  ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
                  : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
              }`}
            >
              登录
            </button>
            <button
              onClick={() => setMode('register')}
              className={`px-3 py-2 rounded-lg border text-sm font-bold transition-all ${
                effectiveMode === 'register'
                  ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
                  : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
              }`}
            >
              注册
            </button>
          </div>
        ) : (
          <div className="mt-4 text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/40">
            当前已关闭自助注册，请使用管理员创建的账号登录。
          </div>
        )}

        <div className="mt-5 space-y-3">
          <BookInput
            label="用户名"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            placeholder="例如：desktop_user"
          />
          <BookInput
            label="密码"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={effectiveMode === 'register' ? 'new-password' : 'current-password'}
          />
          {effectiveMode === 'register' ? (
            <BookInput
              label="确认密码"
              type="password"
              value={password2}
              onChange={(e) => setPassword2(e.target.value)}
              autoComplete="new-password"
            />
          ) : null}
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <BookButton
            variant="primary"
            onClick={handleSubmit}
            disabled={loading}
            className="min-w-[120px]"
          >
            {loading ? '处理中…' : effectiveMode === 'register' ? '注册并登录' : '登录'}
          </BookButton>
        </div>
      </BookCard>
    </div>
  );
};
