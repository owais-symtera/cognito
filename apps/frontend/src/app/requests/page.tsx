'use client'

import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSession } from 'next-auth/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  FileText,
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  Eye,
  Edit,
  Trash2,
  Download,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Calendar,
  User,
  Building,
  ArrowUpDown,
  RefreshCw
} from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { MainLayout } from '@/components/layout/main-layout'

/**
 * Interface for drug request data
 */
interface DrugRequest {
  id: string
  drugName: string
  description: string
  status: 'pending' | 'in_review' | 'processing' | 'completed' | 'failed' | 'cancelled'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  analysisType?: 'full_analysis' | 'interaction_check' | 'regulatory_compliance' | 'safety_profile'
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
  files?: Array<{
    id: string
    name: string
    size: number
    url: string
  }>
}

/**
 * Filter and sorting options
 */
interface FilterOptions {
  status: string[]
  priority: string[]
  analysisType: string[]
  department: string[]
  dateRange: {
    start?: string
    end?: string
  }
}

/**
 * Comprehensive drug request management interface.
 *
 * Features:
 * - Filterable and sortable request list
 * - Real-time status updates
 * - Bulk operations support
 * - Advanced search capabilities
 * - Export functionality
 * - Role-based actions
 * - Progress tracking
 * - File management
 *
 * @returns React component for managing drug analysis requests
 *
 * @example
 * ```tsx
 * // Accessed via /requests route
 * <DrugRequestsPage />
 * ```
 *
 * @since 1.0.0
 * @version 1.0.0
 * @author CognitoAI Development Team
 */
export default function DrugRequestsPage() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedRequests, setSelectedRequests] = useState<string[]>([])
  const [sortField, setSortField] = useState<keyof DrugRequest>('createdAt')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [filters, setFilters] = useState<FilterOptions>({
    status: [],
    priority: [],
    analysisType: [],
    department: [],
    dateRange: {}
  })

  // Fetch requests data
  const {
    data: requests,
    isLoading,
    error,
    refetch
  } = useQuery<DrugRequest[]>({
    queryKey: ['drug-requests', filters, sortField, sortDirection],
    queryFn: () => api.getRequests({
      ...filters,
      sortBy: sortField,
      sortOrder: sortDirection,
      search: searchQuery
    }),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Delete request mutation
  const deleteRequestMutation = useMutation({
    mutationFn: (requestId: string) => api.deleteRequest(requestId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['drug-requests'] })
      setSelectedRequests(prev => prev.filter(id => !selectedRequests.includes(id)))
    },
  })

  const userRole = (session?.user as any)?.role || 'user'

  /**
   * Handle sorting
   */
  const handleSort = (field: keyof DrugRequest) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  /**
   * Filter requests based on search and filters
   */
  const filteredRequests = useMemo(() => {
    if (!requests) return []

    return requests.filter(request => {
      // Search filter
      if (searchQuery) {
        const searchLower = searchQuery.toLowerCase()
        const searchFields = [
          request.drugName,
          request.description,
          request.requestedBy,
          request.department,
          request.assignedAnalyst
        ].filter(Boolean)

        if (!searchFields.some(field => field?.toLowerCase().includes(searchLower))) {
          return false
        }
      }

      // Status filter
      if (filters.status.length > 0 && !filters.status.includes(request.status)) {
        return false
      }

      // Priority filter
      if (filters.priority.length > 0 && !filters.priority.includes(request.priority)) {
        return false
      }

      // Analysis type filter
      if (filters.analysisType.length > 0 && !filters.analysisType.includes(request.analysisType)) {
        return false
      }

      // Department filter
      if (filters.department.length > 0 && !filters.department.includes(request.department)) {
        return false
      }

      return true
    })
  }, [requests, searchQuery, filters])

  /**
   * Get status styling
   */
  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      case 'in_review':
        return 'bg-blue-100 text-blue-800 border-blue-300'
      case 'processing':
        return 'bg-purple-100 text-purple-800 border-purple-300'
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-300'
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'cancelled':
        return 'bg-gray-100 text-gray-800 border-gray-300'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  /**
   * Get priority styling
   */
  const getPriorityStyle = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'bg-red-100 text-red-800'
      case 'high':
        return 'bg-orange-100 text-orange-800'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800'
      case 'low':
        return 'bg-blue-100 text-blue-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  /**
   * Get status icon
   */
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-4 w-4" />
      case 'in_review':
        return <Eye className="h-4 w-4" />
      case 'processing':
        return <RefreshCw className="h-4 w-4 animate-spin" />
      case 'completed':
        return <CheckCircle className="h-4 w-4" />
      case 'failed':
        return <XCircle className="h-4 w-4" />
      case 'cancelled':
        return <XCircle className="h-4 w-4" />
      default:
        return <AlertTriangle className="h-4 w-4" />
    }
  }

  /**
   * Format analysis type for display
   */
  const formatAnalysisType = (type?: string) => {
    if (!type) return 'Standard Analysis'
    return type.split('_').map(word =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ')
  }

  /**
   * Handle bulk selection
   */
  const handleSelectAll = () => {
    if (selectedRequests.length === filteredRequests.length) {
      setSelectedRequests([])
    } else {
      setSelectedRequests(filteredRequests.map(r => r.id))
    }
  }

  /**
   * Handle individual selection
   */
  const handleSelectRequest = (requestId: string) => {
    setSelectedRequests(prev =>
      prev.includes(requestId)
        ? prev.filter(id => id !== requestId)
        : [...prev, requestId]
    )
  }

  /**
   * Export selected requests
   */
  const handleExport = () => {
    // Implementation for exporting requests
    console.log('Exporting requests:', selectedRequests)
  }

  if (error) {
    return (
      <MainLayout>
        <div className="container mx-auto px-4 py-6">
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Failed to load requests. Please try again later.
            </AlertDescription>
          </Alert>
        </div>
      </MainLayout>
    )
  }

  return (
    <MainLayout>
      <div className="container mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Drug Analysis Requests</h1>
            <p className="text-muted-foreground mt-1">
              Manage and track pharmaceutical compound analysis requests
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
            <Link href="/requests/new">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                New Request
              </Button>
            </Link>
          </div>
        </div>

        {/* Search and Filter Bar */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col lg:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search requests by drug name, requester, or description..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <Button variant="outline" size="sm">
                  <Filter className="h-4 w-4 mr-2" />
                  Filters
                </Button>
                {selectedRequests.length > 0 && (
                  <>
                    <Button variant="outline" size="sm" onClick={handleExport}>
                      <Download className="h-4 w-4 mr-2" />
                      Export ({selectedRequests.length})
                    </Button>
                    {['admin', 'analyst'].includes(userRole) && (
                      <Button variant="destructive" size="sm">
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete ({selectedRequests.length})
                      </Button>
                    )}
                  </>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Statistics */}
        {requests && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Requests</p>
                    <p className="text-2xl font-bold">{requests.length}</p>
                  </div>
                  <FileText className="h-8 w-8 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">In Progress</p>
                    <p className="text-2xl font-bold">
                      {requests.filter(r => ['in_review', 'processing'].includes(r.status)).length}
                    </p>
                  </div>
                  <RefreshCw className="h-8 w-8 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Completed</p>
                    <p className="text-2xl font-bold">
                      {requests.filter(r => r.status === 'completed').length}
                    </p>
                  </div>
                  <CheckCircle className="h-8 w-8 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Urgent</p>
                    <p className="text-2xl font-bold">
                      {requests.filter(r => r.priority === 'urgent').length}
                    </p>
                  </div>
                  <AlertTriangle className="h-8 w-8 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Requests Table */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Requests</CardTitle>
              {filteredRequests.length > 0 && (
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={selectedRequests.length === filteredRequests.length}
                    onChange={handleSelectAll}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm text-muted-foreground">
                    Select all ({filteredRequests.length})
                  </span>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="flex items-center space-x-4 p-4 border rounded-lg">
                      <div className="h-4 w-4 bg-muted rounded"></div>
                      <div className="flex-1 space-y-2">
                        <div className="h-4 bg-muted rounded w-1/4"></div>
                        <div className="h-3 bg-muted rounded w-1/2"></div>
                      </div>
                      <div className="h-6 w-16 bg-muted rounded"></div>
                      <div className="h-6 w-20 bg-muted rounded"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : filteredRequests.length === 0 ? (
              <div className="text-center py-12">
                <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium text-foreground mb-2">No requests found</h3>
                <p className="text-muted-foreground mb-4">
                  {searchQuery || Object.values(filters).some(f => Array.isArray(f) ? f.length > 0 : f)
                    ? 'Try adjusting your search or filter criteria'
                    : 'Get started by creating your first drug analysis request'
                  }
                </p>
                <Link href="/requests/new">
                  <Button>
                    <Plus className="h-4 w-4 mr-2" />
                    Create Request
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-2">
                {filteredRequests.map((request) => (
                  <div
                    key={request.id}
                    className={cn(
                      "flex items-center space-x-4 p-4 border rounded-lg transition-colors hover:bg-muted/50",
                      selectedRequests.includes(request.id) && "bg-muted/50 border-primary"
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={selectedRequests.includes(request.id)}
                      onChange={() => handleSelectRequest(request.id)}
                      className="rounded border-gray-300"
                    />

                    <div className="flex-1 grid grid-cols-1 lg:grid-cols-5 gap-4">
                      {/* Drug Info */}
                      <div className="lg:col-span-2">
                        <div className="flex items-start space-x-3">
                          <div className="flex-shrink-0">
                            {getStatusIcon(request.status)}
                          </div>
                          <div className="min-w-0 flex-1">
                            <Link href={`/requests/${request.id}`}>
                              <h4 className="font-medium text-foreground hover:text-primary transition-colors truncate">
                                {request.drugName}
                              </h4>
                            </Link>
                            <p className="text-sm text-muted-foreground truncate">
                              {request.description}
                            </p>
                            <div className="flex items-center space-x-2 mt-1">
                              <Badge variant="outline" className="text-xs">
                                {formatAnalysisType(request.analysisType)}
                              </Badge>
                              {request.files && request.files.length > 0 && (
                                <Badge variant="outline" className="text-xs">
                                  {request.files.length} files
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Status & Priority */}
                      <div className="space-y-1">
                        <Badge className={getStatusStyle(request.status)}>
                          {request.status.replace('_', ' ')}
                        </Badge>
                        <Badge className={getPriorityStyle(request.priority)}>
                          {request.priority}
                        </Badge>
                      </div>

                      {/* Requester Info */}
                      <div>
                        <div className="flex items-center space-x-1 text-sm">
                          <User className="h-3 w-3 text-muted-foreground" />
                          <span className="font-medium">{request.requestedBy}</span>
                        </div>
                        <div className="flex items-center space-x-1 text-xs text-muted-foreground">
                          <Building className="h-3 w-3" />
                          <span>{request.department}</span>
                        </div>
                        {request.assignedAnalyst && (
                          <div className="text-xs text-muted-foreground mt-1">
                            Analyst: {request.assignedAnalyst}
                          </div>
                        )}
                      </div>

                      {/* Timeline */}
                      <div>
                        <div className="flex items-center space-x-1 text-xs text-muted-foreground">
                          <Calendar className="h-3 w-3" />
                          <span>Created {new Date(request.createdAt).toLocaleDateString()}</span>
                        </div>
                        {request.expectedDelivery && (
                          <div className="text-xs text-muted-foreground mt-1">
                            Due: {new Date(request.expectedDelivery).toLocaleDateString()}
                          </div>
                        )}
                        {request.estimatedTimeRemaining && request.status === 'processing' && (
                          <div className="text-xs text-blue-600 mt-1">
                            ETA: {request.estimatedTimeRemaining}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Progress Bar */}
                    {['in_review', 'processing'].includes(request.status) && (
                      <div className="w-20">
                        <div className="text-xs text-muted-foreground mb-1 text-center">
                          {request.progressPercentage}%
                        </div>
                        <div className="w-full bg-muted rounded-full h-2">
                          <div
                            className="bg-primary h-2 rounded-full transition-all"
                            style={{ width: `${request.progressPercentage}%` }}
                          />
                        </div>
                      </div>
                    )}

                    {/* Actions */}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuLabel>Actions</DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem asChild>
                          <Link href={`/pipeline`}>
                            <Eye className="h-4 w-4 mr-2" />
                            View Pipeline
                          </Link>
                        </DropdownMenuItem>
                        {(['admin', 'analyst'].includes(userRole) || request.requesterEmail === session?.user?.email) && (
                          <DropdownMenuItem asChild>
                            <Link href={`/requests/${request.id}/edit`}>
                              <Edit className="h-4 w-4 mr-2" />
                              Edit Request
                            </Link>
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuItem>
                          <Download className="h-4 w-4 mr-2" />
                          Export Report
                        </DropdownMenuItem>
                        {['admin'].includes(userRole) && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-red-600"
                              onClick={() => deleteRequestMutation.mutate(request.id)}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete Request
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  )
}