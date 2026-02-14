import React, { useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { useAuthStore } from '../../store/auth';
import { AuthPage } from '../../pages/AuthPage';

interface AuthGateProps {
  children: React.ReactNode;
}

export const AuthGate: React.FC<AuthGateProps> = ({ children }) => {
  const { initialized, authEnabled, user, init } = useAuthStore();

  useEffect(() => {
    init();
  }, [init]);

  if (!initialized) {
    return (
      <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/20 backdrop-blur-sm p-6">
        <div className="flex items-center gap-2 text-sm text-book-text-muted bg-book-bg-paper/90 border border-book-border/60 rounded-lg px-4 py-3 shadow-lg">
          <Loader2 size={18} className="animate-spin" />
          加载中…
        </div>
      </div>
    );
  }

  if (!authEnabled) return <>{children}</>;

  if (!user) return <AuthPage />;

  return <>{children}</>;
};
