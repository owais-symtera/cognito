/**
 * API client for CognitoAI Engine with authentication and error handling
 */

import { getSession } from 'next-auth/react'

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public details?: any
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export interface ApiResponse<T = any> {
  data: T
  message?: string
  status: number
}

export interface ApiErrorResponse {
  error: {
    message: string
    code?: string
    details?: any
  }
  status: number
}

// Common data types
export interface DashboardStats {
  requests: {
    total: number
    pending: number
    processing: number
    completed: number
    failed: number
    growth: number
  }
  analysis: {
    totalAnalyses: number
    avgProcessingTime: number
    successRate: number
    criticalFindings: number
  }
  compliance: {
    score: number
    auditTrails: number
    warnings: number
  }
  system: {
    uptime: number
    activeUsers: number
    apiCalls: number
    storage: number
  }
}

export interface ActivityItem {
  id: string
  type: 'request' | 'analysis' | 'alert' | 'compliance'
  title: string
  description: string
  timestamp: string
  severity?: 'low' | 'medium' | 'high' | 'critical'
  userId?: string
  userName?: string
}

export interface UserProfile {
  id: string
  email: string
  name: string
  role: string
  lastLogin?: string
  [key: string]: any
}

export interface DrugRequest {
  id: string
  drugName: string
  description: string
  status: 'pending' | 'in_review' | 'processing' | 'completed' | 'failed' | 'cancelled'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  analysisType: 'full_analysis' | 'interaction_check' | 'regulatory_compliance' | 'safety_profile'
  requestedBy: string
  department: string
  requesterEmail: string
  confidentialityLevel: 'public' | 'internal' | 'confidential' | 'highly_confidential'
  createdAt: string
  updatedAt: string
  expectedDelivery?: string
  completedAt?: string
  assignedAnalyst?: string
  progressPercentage: number
  estimatedTimeRemaining?: string
  files: Array<{
    id: string
    name: string
    size: number
    url: string
  }>
}

export interface Analysis {
  id: string
  requestId: string
  status: string
  results?: any
  createdAt: string
  completedAt?: string
  [key: string]: any
}

export interface AnalysisResult {
  id: string
  requestId: string
  drugName: string
  analysisType: string
  status: 'completed' | 'failed' | 'partial'
  overallScore: number
  confidenceLevel: number
  riskAssessment: 'low' | 'medium' | 'high' | 'critical'
  completedAt: string
  processingDuration: number
  analyst: string
  requesterName: string
  department: string
  findings: {
    safety: {
      score: number
      status: 'pass' | 'warning' | 'fail'
      details: string[]
      adverseEffects: string[]
    }
    efficacy: {
      score: number
      status: 'pass' | 'warning' | 'fail'
      details: string[]
      therapeuticIndex: number
    }
    interactions: {
      count: number
      severity: 'low' | 'medium' | 'high' | 'critical'
      majorInteractions: string[]
      contraindicatedWith: string[]
    }
    regulatory: {
      complianceScore: number
      status: 'compliant' | 'requires_review' | 'non_compliant'
      fdaStatus: string
      requiredStudies: string[]
    }
  }
  recommendations: {
    priority: 'low' | 'medium' | 'high' | 'urgent'
    actions: string[]
    followUpRequired: boolean
    nextSteps: string[]
  }
  reports: Array<{
    id: string
    name: string
    type: 'pdf' | 'excel' | 'xml' | 'json'
    size: number
    generatedAt: string
    url: string
  }>
  attachments: Array<{
    id: string
    name: string
    type: string
    size: number
    url: string
  }>
}

export interface Report {
  id: string
  title: string
  type: string
  status: string
  createdAt: string
  [key: string]: any
}

export interface User {
  id: string
  email: string
  name: string
  role: string
  isActive: boolean
  [key: string]: any
}

export interface Settings {
  [key: string]: any
}

class ApiClient {
  private baseURL: string

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL
  }

  private async getAuthHeaders(): Promise<HeadersInit> {
    const session = await getSession()
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    }

    if (session?.accessToken) {
      headers.Authorization = `Bearer ${session.accessToken}`
    }

    return headers
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    const contentType = response.headers.get('content-type')
    const isJson = contentType?.includes('application/json')

    let data: any
    try {
      data = isJson ? await response.json() : await response.text()
    } catch (error) {
      throw new ApiError(
        'Failed to parse response',
        response.status,
        'PARSE_ERROR'
      )
    }

    if (!response.ok) {
      const errorMessage = data?.error?.message || data?.message || `HTTP ${response.status}`
      const errorCode = data?.error?.code || 'HTTP_ERROR'
      const errorDetails = data?.error?.details || data?.details

      throw new ApiError(errorMessage, response.status, errorCode, errorDetails)
    }

    return data
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    const headers = await this.getAuthHeaders()

    const config: RequestInit = {
      ...options,
      headers: {
        ...headers,
        ...options.headers,
      },
      credentials: 'include', // Required for CORS with credentials
    }

    try {
      const response = await fetch(url, config)
      return await this.handleResponse<T>(response)
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }

      // Network or other fetch errors
      throw new ApiError(
        'Network error occurred',
        0,
        'NETWORK_ERROR',
        error
      )
    }
  }

  // HTTP methods
  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const searchParams = params ? `?${new URLSearchParams(params).toString()}` : ''
    return this.request<T>(`${endpoint}${searchParams}`, {
      method: 'GET',
    })
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async patch<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
    })
  }

  // File upload
  async upload<T>(endpoint: string, file: File, additionalData?: Record<string, any>): Promise<T> {
    const session = await getSession()
    const formData = new FormData()
    formData.append('file', file)

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, String(value))
      })
    }

    const headers: HeadersInit = {}
    if (session?.accessToken) {
      headers.Authorization = `Bearer ${session.accessToken}`
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers,
      body: formData,
      credentials: 'include', // Required for CORS with credentials
    })

    return await this.handleResponse<T>(response)
  }
}

// Create singleton instance
export const apiClient = new ApiClient()

// API endpoints
export const endpoints = {
  // Auth
  auth: {
    login: '/api/v1/auth/login',
    logout: '/api/v1/auth/logout',
    refresh: '/api/v1/auth/refresh',
    profile: '/api/v1/auth/profile',
  },

  // Dashboard
  dashboard: {
    stats: '/api/v1/dashboard/stats',
    recentActivity: '/api/v1/dashboard/recent-activity',
  },

  // Requests
  requests: {
    list: '/api/v1/requests',
    create: '/api/v1/requests',
    get: (id: string) => `/api/v1/requests/${id}`,
    update: (id: string) => `/api/v1/requests/${id}`,
    delete: (id: string) => `/api/v1/requests/${id}`,
    upload: (id: string) => `/api/v1/requests/${id}/upload`,
  },

  // Analysis
  analysis: {
    list: '/api/v1/analysis',
    get: (id: string) => `/api/v1/analysis/${id}`,
    create: '/api/v1/analysis',
  },

  // Reports
  reports: {
    list: '/api/v1/reports',
    get: (id: string) => `/api/v1/reports/${id}`,
    generate: '/api/v1/reports/generate',
    export: (id: string) => `/api/v1/reports/${id}/export`,
  },

  // Users
  users: {
    list: '/api/v1/users',
    get: (id: string) => `/api/v1/users/${id}`,
    create: '/api/v1/users',
    update: (id: string) => `/api/v1/users/${id}`,
    delete: (id: string) => `/api/v1/users/${id}`,
  },

  // Settings
  settings: {
    get: '/api/v1/settings',
    update: '/api/v1/settings',
  },
}

// Typed API functions
export const api = {
  // Direct HTTP methods (for custom endpoints)
  get: <T = any>(endpoint: string, params?: Record<string, any>): Promise<T> => apiClient.get<T>(endpoint, params),
  post: <T = any>(endpoint: string, data?: any): Promise<T> => apiClient.post<T>(endpoint, data),
  put: <T = any>(endpoint: string, data?: any): Promise<T> => apiClient.put<T>(endpoint, data),
  patch: <T = any>(endpoint: string, data?: any): Promise<T> => apiClient.patch<T>(endpoint, data),
  delete: <T = any>(endpoint: string): Promise<T> => apiClient.delete<T>(endpoint),

  // Dashboard
  getDashboardStats: (): Promise<DashboardStats> => apiClient.get<DashboardStats>(endpoints.dashboard.stats),
  getRecentActivity: (): Promise<ActivityItem[]> => apiClient.get<ActivityItem[]>(endpoints.dashboard.recentActivity),

  // Auth
  getProfile: (): Promise<UserProfile> => apiClient.get<UserProfile>(endpoints.auth.profile),

  // Requests
  getRequests: async (params?: any): Promise<DrugRequest[]> => {
    const data = await apiClient.get<any[]>(endpoints.requests.list, params)
    // Ensure id field exists (backend might use different field name)
    return data.map((request: any) => ({
      ...request,
      id: request.id || request._id || request.requestId || request.request_id
    }))
  },
  createRequest: (data: any): Promise<DrugRequest> => apiClient.post<DrugRequest>(endpoints.requests.create, data),
  getRequest: (id: string): Promise<DrugRequest> => apiClient.get<DrugRequest>(endpoints.requests.get(id)),
  updateRequest: (id: string, data: any): Promise<DrugRequest> => apiClient.put<DrugRequest>(endpoints.requests.update(id), data),
  deleteRequest: (id: string): Promise<void> => apiClient.delete<void>(endpoints.requests.delete(id)),
  uploadFile: (id: string, file: File): Promise<any> => apiClient.upload(endpoints.requests.upload(id), file),

  // Analysis
  getAnalyses: (params?: any): Promise<AnalysisResult[]> => apiClient.get<AnalysisResult[]>(endpoints.analysis.list, params),
  getAnalysis: (id: string): Promise<AnalysisResult> => apiClient.get<AnalysisResult>(endpoints.analysis.get(id)),
  createAnalysis: (data: any): Promise<Analysis> => apiClient.post<Analysis>(endpoints.analysis.create, data),

  // Reports
  getReports: (params?: any): Promise<Report[]> => apiClient.get<Report[]>(endpoints.reports.list, params),
  getReport: (id: string): Promise<Report> => apiClient.get<Report>(endpoints.reports.get(id)),
  generateReport: (data: any): Promise<Report> => apiClient.post<Report>(endpoints.reports.generate, data),
  exportReport: (id: string): Promise<Blob> => apiClient.get<Blob>(endpoints.reports.export(id)),

  // Users
  getUsers: (params?: any): Promise<User[]> => apiClient.get<User[]>(endpoints.users.list, params),
  getUser: (id: string): Promise<User> => apiClient.get<User>(endpoints.users.get(id)),
  createUser: (data: any): Promise<User> => apiClient.post<User>(endpoints.users.create, data),
  updateUser: (id: string, data: any): Promise<User> => apiClient.put<User>(endpoints.users.update(id), data),
  deleteUser: (id: string): Promise<void> => apiClient.delete<void>(endpoints.users.delete(id)),

  // Settings
  getSettings: (): Promise<Settings> => apiClient.get<Settings>(endpoints.settings.get),
  updateSettings: (data: any): Promise<Settings> => apiClient.put<Settings>(endpoints.settings.update, data),
}