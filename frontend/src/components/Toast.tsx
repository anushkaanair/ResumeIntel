import { useEffect } from 'react';
import { create } from 'zustand';
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import './Toast.css';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

interface ToastStore {
  toasts: ToastItem[];
  add: (toast: Omit<ToastItem, 'id'>) => void;
  remove: (id: string) => void;
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  add: (toast) =>
    set((s) => ({
      toasts: [...s.toasts, { ...toast, id: `${Date.now()}-${Math.random()}` }],
    })),
  remove: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

/** Call these anywhere in the app instead of alert(). */
export const toast = {
  success: (message: string, duration = 4000) =>
    useToastStore.getState().add({ type: 'success', message, duration }),
  error: (message: string, duration = 6000) =>
    useToastStore.getState().add({ type: 'error', message, duration }),
  warning: (message: string, duration = 5000) =>
    useToastStore.getState().add({ type: 'warning', message, duration }),
  info: (message: string, duration = 4000) =>
    useToastStore.getState().add({ type: 'info', message, duration }),
};

const ICONS: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle2 size={16} />,
  error: <XCircle size={16} />,
  warning: <AlertTriangle size={16} />,
  info: <Info size={16} />,
};

function ToastItem({ item }: { item: ToastItem }) {
  const remove = useToastStore((s) => s.remove);

  useEffect(() => {
    const t = setTimeout(() => remove(item.id), item.duration ?? 5000);
    return () => clearTimeout(t);
  }, [item.id, item.duration, remove]);

  return (
    <div className={`toast toast-${item.type}`} role="alert" aria-live="polite">
      <span className="toast-icon">{ICONS[item.type]}</span>
      <span className="toast-message">{item.message}</span>
      <button className="toast-close" onClick={() => remove(item.id)} aria-label="Dismiss">
        <X size={13} />
      </button>
    </div>
  );
}

export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);
  if (!toasts.length) return null;
  return (
    <div className="toast-container" aria-label="Notifications">
      {toasts.map((t) => (
        <ToastItem key={t.id} item={t} />
      ))}
    </div>
  );
}
