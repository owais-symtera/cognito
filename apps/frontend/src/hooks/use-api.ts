/**
 * Custom hooks for API integration with React Query
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '@/lib/api'
import { useAuthStore } from '@/stores/auth-store'
import { toast } from '@/hooks/use-toast'

// Query keys
export const queryKeys = {
  dashboard: {
    stats: ['dashboard', 'stats'] as const,
    recentActivity: ['dashboard', 'recent-activity'] as const,
  },
  requests: {
    all: ['requests'] as const,
    list: (params?: any) => ['requests', 'list', params] as const,
    detail: (id: string) => ['requests', 'detail', id] as const,
  },
  analysis: {
    all: ['analysis'] as const,
    list: (params?: any) => ['analysis', 'list', params] as const,
    detail: (id: string) => ['analysis', 'detail', id] as const,
  },
  reports: {
    all: ['reports'] as const,
    list: (params?: any) => ['reports', 'list', params] as const,
    detail: (id: string) => ['reports', 'detail', id] as const,
  },
  users: {
    all: ['users'] as const,
    list: (params?: any) => ['users', 'list', params] as const,
    detail: (id: string) => ['users', 'detail', id] as const,
  },
  settings: ['settings'] as const,
  profile: ['profile'] as const,
}

// Error handler
function handleApiError(error: unknown) {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 401:
        toast({
          title: 'Authentication Required',
          description: 'Please sign in to continue',
          variant: 'destructive',
        })
        break
      case 403:
        toast({
          title: 'Access Denied',
          description: 'You don\'t have permission to perform this action',
          variant: 'destructive',
        })
        break
      case 500:
        toast({
          title: 'Server Error',
          description: 'An internal server error occurred. Please try again later.',
          variant: 'destructive',
        })
        break
      default:
        toast({
          title: 'Error',
          description: error.message || 'An unexpected error occurred',
          variant: 'destructive',
        })
    }
  } else {
    toast({
      title: 'Error',
      description: 'An unexpected error occurred',
      variant: 'destructive',
    })
  }
}

// Dashboard hooks
export function useDashboardStats() {
  const query = useQuery({
    queryKey: queryKeys.dashboard.stats,
    queryFn: api.getDashboardStats,
  })

  // Handle errors in effect
  if (query.error) {
    handleApiError(query.error)
  }

  return query
}

export function useRecentActivity() {
  const query = useQuery({
    queryKey: queryKeys.dashboard.recentActivity,
    queryFn: api.getRecentActivity,
  })

  // Handle errors in effect
  if (query.error) {
    handleApiError(query.error)
  }

  return query
}

// Profile hooks
export function useProfile() {
  const query = useQuery({
    queryKey: queryKeys.profile,
    queryFn: api.getProfile,
  })

  // Handle errors in effect
  if (query.error) {
    handleApiError(query.error)
  }

  return query
}

// Request hooks
export function useRequests(params?: any) {
  const query = useQuery({
    queryKey: queryKeys.requests.list(params),
    queryFn: () => api.getRequests(params),
  })

  // Handle errors in effect
  if (query.error) {
    handleApiError(query.error)
  }

  return query
}

export function useRequest(id: string) {
  const query = useQuery({
    queryKey: queryKeys.requests.detail(id),
    queryFn: () => api.getRequest(id),
    enabled: !!id,
  })

  // Handle errors in effect
  if (query.error) {
    handleApiError(query.error)
  }

  return query
}

export function useCreateRequest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.createRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.requests.all })
      toast({
        title: 'Success',
        description: 'Request created successfully',
      })
    },
    onError: handleApiError,
  })
}

export function useUpdateRequest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => api.updateRequest(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.requests.detail(variables.id) })
      queryClient.invalidateQueries({ queryKey: queryKeys.requests.all })
      toast({
        title: 'Success',
        description: 'Request updated successfully',
      })
    },
    onError: handleApiError,
  })
}

export function useDeleteRequest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.deleteRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.requests.all })
      toast({
        title: 'Success',
        description: 'Request deleted successfully',
      })
    },
    onError: handleApiError,
  })
}

// Analysis hooks
export function useAnalyses(params?: any) {
  const query = useQuery({
    queryKey: queryKeys.analysis.list(params),
    queryFn: () => api.getAnalyses(params),
  })

  // Handle errors in effect
  if (query.error) {
    handleApiError(query.error)
  }

  return query
}

export function useAnalysis(id: string) {
  const query = useQuery({
    queryKey: queryKeys.analysis.detail(id),
    queryFn: () => api.getAnalysis(id),
    enabled: !!id,
  })

  // Handle errors in effect
  if (query.error) {
    handleApiError(query.error)
  }

  return query
}

export function useCreateAnalysis() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.createAnalysis,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.analysis.all })
      toast({
        title: 'Success',
        description: 'Analysis started successfully',
      })
    },
    onError: handleApiError,
  })
}

// Reports hooks
export function useReports(params?: any) {
  const query = useQuery({
    queryKey: queryKeys.reports.list(params),
    queryFn: () => api.getReports(params),
  })

  // Handle errors in effect
  if (query.error) {
    handleApiError(query.error)
  }

  return query
}

export function useReport(id: string) {
  const query = useQuery({
    queryKey: queryKeys.reports.detail(id),
    queryFn: () => api.getReport(id),
    enabled: !!id,
  })

  // Handle errors in effect
  if (query.error) {
    handleApiError(query.error)
  }

  return query
}

export function useGenerateReport() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.generateReport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all })
      toast({
        title: 'Success',
        description: 'Report generation started',
      })
    },
    onError: handleApiError,
  })
}

// Settings hooks
export function useSettings() {
  const query = useQuery({
    queryKey: queryKeys.settings,
    queryFn: api.getSettings,
  })

  // Handle errors in effect
  if (query.error) {
    handleApiError(query.error)
  }

  return query
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.updateSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings })
      toast({
        title: 'Success',
        description: 'Settings updated successfully',
      })
    },
    onError: handleApiError,
  })
}

// File upload hook
export function useFileUpload() {
  return useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => api.uploadFile(id, file),
    onSuccess: () => {
      toast({
        title: 'Success',
        description: 'File uploaded successfully',
      })
    },
    onError: handleApiError,
  })
}