"use client";

import { useEffect, useState } from "react";
import { create } from "./create";

export interface ToastItem {
  id: string;
  title?: string;
  description?: string;
  variant?: "default" | "success" | "destructive" | "warning";
  duration?: number;
}

export interface ToastState {
  toasts: ToastItem[];
}

const listeners = new Set<(s: ToastState) => void>();
let state: ToastState = { toasts: [] };

function setState(next: ToastState) {
  state = next;
  listeners.forEach((l) => l(state));
}

function genId(): string {
  return `toast-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export const toastStore = {
  getState: () => state,
  subscribe: (l: (s: ToastState) => void) => {
    listeners.add(l);
    return () => listeners.delete(l);
  },
  push(t: Omit<ToastItem, "id">) {
    const id = genId();
    const item: ToastItem = { id, duration: 4000, variant: "default", ...t };
    setState({ toasts: [...state.toasts, item] });
    setTimeout(() => toastStore.dismiss(id), item.duration ?? 4000);
    return id;
  },
  dismiss(id: string) {
    setState({ toasts: state.toasts.filter((t) => t.id !== id) });
  },
  success(description: string, title?: string) {
    return this.push({ title, description, variant: "success" });
  },
  error(description: string, title?: string) {
    return this.push({ title, description, variant: "destructive" });
  },
  warning(description: string, title?: string) {
    return this.push({ title, description, variant: "warning" });
  },
  info(description: string, title?: string) {
    return this.push({ title, description, variant: "default" });
  },
};

export function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>(state.toasts);
  useEffect(() => {
    const unsub = toastStore.subscribe((s) => setToasts(s.toasts));
    return () => { unsub(); };
  }, []);
  return {
    toasts,
    push: toastStore.push.bind(toastStore),
    dismiss: toastStore.dismiss.bind(toastStore),
    success: toastStore.success.bind(toastStore),
    error: toastStore.error.bind(toastStore),
    warning: toastStore.warning.bind(toastStore),
    info: toastStore.info.bind(toastStore),
  };
}

export const toast = toastStore;
