import React, { useCallback, useEffect, useRef, useState } from "react";

export type ToastType = "success" | "error" | "info";

export interface Toast {
  id: number;
  message: string;
  type: ToastType;
  exiting?: boolean;
}

const ICONS: Record<ToastType, string> = {
  success: "\u2713",
  error: "\u2717",
  info: "\u2139",
};

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(0);
  const timersRef = useRef<Set<ReturnType<typeof setTimeout>>>(new Set());

  // Clean up all pending timers on unmount
  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      timers.forEach((t) => clearTimeout(t));
      timers.clear();
    };
  }, []);

  const addToast = useCallback((message: string, type: ToastType = "info") => {
    const id = nextId.current++;
    setToasts((prev) => [...prev.slice(-4), { id, message, type }]);
    const exitTimer = setTimeout(() => {
      timersRef.current.delete(exitTimer);
      setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, exiting: true } : t)));
      const removeTimer = setTimeout(() => {
        timersRef.current.delete(removeTimer);
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 250);
      timersRef.current.add(removeTimer);
    }, 3500);
    timersRef.current.add(exitTimer);
  }, []);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return { toasts, addToast, removeToast };
}

export function Toaster({ toasts, onRemove }: { toasts: Toast[]; onRemove: (id: number) => void }) {
  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type} ${t.exiting ? "toast-exit" : ""}`} onClick={() => onRemove(t.id)}>
          <span className="toast-icon">{ICONS[t.type]}</span>
          <span>{t.message}</span>
        </div>
      ))}
    </div>
  );
}
