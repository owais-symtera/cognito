'use client'

import { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SessionProvider } from './session-provider'
import { ThemeProvider } from './theme-provider'
import { ErrorBoundary } from '@/components/error-boundary'
import { Toaster } from '@/components/ui/toast'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: (failureCount, error: any) => {
        // Don't retry on 401, 403, or 404
        if (error?.status === 401 || error?.status === 403 || error?.status === 404) {
          return false
        }
        return failureCount < 3
      },
    },
    mutations: {
      retry: false,
    },
  },
})

interface ProvidersProps {
  children: ReactNode
}

export function Providers({ children }: ProvidersProps) {
  return (
    <ErrorBoundary>
      <SessionProvider>
        <QueryClientProvider client={queryClient}>
          <ThemeProvider
            attribute="class"
            defaultTheme="system"
            enableSystem
            disableTransitionOnChange
          >
            {children}
            <Toaster />
          </ThemeProvider>
        </QueryClientProvider>
      </SessionProvider>
    </ErrorBoundary>
  )
}