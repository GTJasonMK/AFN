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

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`
            pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border border-book-border/50
            bg-book-bg-paper/90 backdrop-blur-md text-book-text-main min-w-[300px]
            animate-fade-in
          `}
        >
          {toast.type === 'success' && <CheckCircle size={20} className="text-green-500" />}
          {toast.type === 'error' && <AlertCircle size={20} className="text-red-500" />}
          {toast.type === 'info' && <Info size={20} className="text-blue-500" />}
          
          <p className="flex-1 text-sm font-medium">{toast.message}</p>
          
          <button 
            onClick={() => removeToast(toast.id)}
            className="text-book-text-muted hover:text-book-text-main"
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}
