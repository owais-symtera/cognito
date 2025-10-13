/**
 * Simple toast hook for notifications
 */

import { create } from 'zustand'

export interface Toast {
  id: string
  title: string
  description?: string
  variant?: 'default' | 'destructive' | 'success'
  duration?: number
}

interface ToastState {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
  clearToasts: () => void
}

export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],
  addToast: (toast) => {
    const id = Date.now().toString()
    const newToast = { ...toast, id }

    set((state) => ({
      toasts: [...state.toasts, newToast]
    }))

    // Auto remove after duration
    const duration = toast.duration ?? 5000
    setTimeout(() => {
      get().removeToast(id)
    }, duration)
  },
  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id)
    }))
  },
  clearToasts: () => {
    set({ toasts: [] })
  }
}))

export function toast(toast: Omit<Toast, 'id'>) {
  useToastStore.getState().addToast(toast)
}

export function useToast() {
  return { toast }
}