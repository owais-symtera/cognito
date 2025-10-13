'use client'

import { useEffect } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useToastStore, Toast } from '@/hooks/use-toast'
import { Button } from './button'

interface ToastProps {
  toast: Toast
}

function ToastComponent({ toast }: ToastProps) {
  const { removeToast } = useToastStore()

  useEffect(() => {
    const timer = setTimeout(() => {
      removeToast(toast.id)
    }, toast.duration || 5000)

    return () => clearTimeout(timer)
  }, [toast.id, toast.duration, removeToast])

  return (
    <div
      className={cn(
        "relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-6 pr-8 shadow-lg transition-all",
        {
          "border-destructive bg-destructive text-destructive-foreground": toast.variant === 'destructive',
          "border-green-200 bg-green-50 text-green-900": toast.variant === 'success',
          "bg-background text-foreground": toast.variant === 'default' || !toast.variant,
        }
      )}
    >
      <div className="grid gap-1">
        <div className="text-sm font-semibold">{toast.title}</div>
        {toast.description && (
          <div className="text-sm opacity-90">{toast.description}</div>
        )}
      </div>
      <Button
        variant="ghost"
        size="icon"
        className="absolute right-2 top-2 h-6 w-6 opacity-70 hover:opacity-100"
        onClick={() => removeToast(toast.id)}
      >
        <X className="h-3 w-3" />
      </Button>
    </div>
  )
}

export function Toaster() {
  const { toasts } = useToastStore()

  return (
    <div className="fixed bottom-0 right-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]">
      {toasts.map((toast) => (
        <ToastComponent key={toast.id} toast={toast} />
      ))}
    </div>
  )
}