import { create } from 'zustand';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'info';

interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastStore {
  toasts: Toast[];
  addToast: (message: unknown, type: ToastType) => void;
  removeToast: (id: string) => void;
}

const DEFAULT_TOAST_MESSAGE = '发生未知错误';

const formatValidationLoc = (loc: unknown): string => {
  if (!Array.isArray(loc)) return '';
  return loc
    .map((item) => String(item).trim())
    .filter(Boolean)
    .join('.');
};

const normalizeToastMessage = (message: unknown): string => {
  if (typeof message === 'string') {
    const text = message.trim();
    return text || DEFAULT_TOAST_MESSAGE;
  }

  if (message == null) {
    return DEFAULT_TOAST_MESSAGE;
  }

  if (Array.isArray(message)) {
    const parts = message
      .map((item) => normalizeToastMessage(item).trim())
      .filter((item) => Boolean(item) && item !== DEFAULT_TOAST_MESSAGE);

    if (parts.length === 0) return DEFAULT_TOAST_MESSAGE;
    return parts.slice(0, 3).join('；');
  }

  if (typeof message === 'object') {
    const value = message as {
      message?: unknown;
      msg?: unknown;
      detail?: unknown;
      loc?: unknown;
    };

    if (typeof value.message === 'string' && value.message.trim()) {
      return value.message.trim();
    }

    if (typeof value.msg === 'string' && value.msg.trim()) {
      const loc = formatValidationLoc(value.loc);
      return loc ? `${loc}: ${value.msg.trim()}` : value.msg.trim();
    }

    if (value.detail !== undefined) {
      return normalizeToastMessage(value.detail);
    }

    try {
      return JSON.stringify(message);
    } catch {
      return DEFAULT_TOAST_MESSAGE;
    }
  }

  return String(message);
};

export const useToast = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (message, type) => {
    const normalizedMessage = normalizeToastMessage(message);
    const id = Math.random().toString(36).substring(2, 9);
    set((state) => ({ toasts: [...state.toasts, { id, message: normalizedMessage, type }] }));
    setTimeout(() => {
      set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
    }, 3000);
  },
  removeToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));

export function ToastContainer() {
  const { toasts, removeToast } = useToast();

  const iconMap = {
    success: <CheckCircle size={18} className="text-emerald-500" />,
    error: <AlertCircle size={18} className="text-red-500" />,
    info: <Info size={18} className="text-sky-500" />,
  } satisfies Record<ToastType, React.ReactNode>;

  const toneClasses = {
    success: 'border-emerald-500/25 bg-emerald-500/8',
    error: 'border-red-500/25 bg-red-500/8',
    info: 'border-sky-500/25 bg-sky-500/8',
  } satisfies Record<ToastType, string>;

  return (
    <div className="pointer-events-none fixed right-3 top-3 z-[140] flex w-[min(92vw,24rem)] flex-col gap-3 sm:right-5 sm:top-5">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`
            toast-enter pointer-events-auto relative overflow-hidden rounded-[22px] border
            bg-book-bg-paper/94 px-4 py-3.5 shadow-[0_30px_70px_-40px_rgba(36,18,6,0.96)]
            backdrop-blur-xl
            ${toneClasses[toast.type]}
          `}
        >
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-book-primary/30 to-transparent" />
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-full border border-book-border/45 bg-book-bg/75">
              {iconMap[toast.type]}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[0.7rem] font-bold uppercase tracking-[0.18em] text-book-text-muted">
                {toast.type === 'success' ? 'Success' : toast.type === 'error' ? 'Error' : 'Info'}
              </div>
              <p className="mt-1 text-sm font-medium leading-relaxed text-book-text-main">
                {toast.message}
              </p>
            </div>
            <button
              type="button"
              aria-label="关闭提示"
              className="mt-0.5 inline-flex h-8 w-8 items-center justify-center rounded-full text-book-text-muted transition-colors hover:bg-book-bg hover:text-book-text-main"
            onClick={() => removeToast(toast.id)}
            >
              <X size={16} />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
