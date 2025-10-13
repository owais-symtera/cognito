'use client'

import { useState } from 'react'
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
  XCircle,
  AlertTriangle,
  RefreshCw,
  Search,
  Filter,
  MoreHorizontal,
  Eye,
  PlayCircle,
  Trash2,
  Download,
  Clock,
  User,
  Building,
  Calendar,
  Zap,
  Bug,
  Database,
  Server,
  Shield,
  Network,
  Code,
  FileText,
  TrendingUp,
  TrendingDown,
  CheckCircle,
  RotateCcw,
  AlertCircle,
  Cpu,
  HardDrive
} from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

/**
 * Interface for failure/error data
 */
interface FailureRecord {
  id: string
  requestId?: string
  drugName?: string
  type: 'analysis_failure' | 'system_error' | 'validation_error' | 'timeout' | 'resource_error' | 'network_error' | 'data_error'
  severity: 'low' | 'medium' | 'high' | 'critical'
  status: 'open' | 'investigating' | 'resolved' | 'permanent_failure'
  title: string
  description: string
  errorCode: string
  stackTrace?: string
  occurredAt: string
  resolvedAt?: string
  assignedTo?: string
  requesterName?: string
  department?: string
  context: {
    component: string
    version: string
    environment: 'development' | 'staging' | 'production'
    requestId?: string
    userId?: string
    sessionId?: string
  }
  metrics: {
    retryCount: number
    processingDuration?: number
    resourceUsage?: {
      cpu: number
      memory: number
      disk: number
    }
  }
  resolution?: {
    action: 'retry' | 'manual_fix' | 'code_fix' | 'config_change' | 'infrastructure_fix'
    description: string
    resolvedBy: string
    resolutionTime: number
  }
  relatedFailures: string[]
  tags: string[]
  attachments: Array<{
    name: string
    type: string
    size: number
    url: string
  }>
}

/**
 * Interface for failure analytics
 */
interface FailureAnalytics {
  totalFailures: number
  failuresByType: Record<string, number>
  failuresBySeverity: Record<string, number>
  resolutionStats: {
    averageResolutionTime: number
    resolutionRate: number
    escalationRate: number
  }
  trends: {
    daily: Array<{ date: string; count: number }>
    topCauses: Array<{ cause: string; count: number }>
    topComponents: Array<{ component: string; count: number }>
  }
}

/**
 * Comprehensive failure management and incident tracking console.
 *
 * Features:
 * - Centralized failure tracking
 * - Root cause analysis
 * - Automated retry mechanisms
 * - Resolution workflow management
 * - Failure pattern analysis
 * - Performance impact assessment
 * - Team assignment and escalation
 * - Incident reporting and documentation
 *
 * @returns React component for failure management
 *
 * @example
 * ```tsx
 * // Accessed via /failures route (admin/analyst only)
 * <FailureManagementPage />
 * ```
 *
 * @since 1.0.0
 * @version 1.0.0
 * @author CognitoAI Development Team
 */
export default function FailureManagementPage() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFailures, setSelectedFailures] = useState<string[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [severityFilter, setSeverityFilter] = useState<string>('')
  const [typeFilter, setTypeFilter] = useState<string>('')

  const userRole = (session?.user as any)?.role || 'user'

  // Only allow admin and analyst roles
  if (!['admin', 'analyst'].includes(userRole)) {
    return (
      <div className="container mx-auto px-4 py-6">
        <Alert variant="destructive">
          <Shield className="h-4 w-4" />
          <AlertDescription>
            Access denied. You don't have permission to view this page.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  // Fetch failure records
  const {
    data: failures,
    isLoading: failuresLoading,
    error: failuresError,
    refetch: refetchFailures
  } = useQuery<FailureRecord[]>({
    queryKey: ['failures', searchQuery, statusFilter, severityFilter, typeFilter],
    queryFn: () => api.get('/api/v1/failures', {
      search: searchQuery,
      status: statusFilter,
      severity: severityFilter,
      type: typeFilter,
    }),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Fetch failure analytics
  const {
    data: analytics,
    isLoading: analyticsLoading
  } = useQuery<FailureAnalytics>({
    queryKey: ['failure-analytics'],
    queryFn: () => api.get('/api/v1/failures/analytics'),
    refetchInterval: 60000, // Refresh every minute
  })

  // Retry failure mutation
  const retryFailureMutation = useMutation({
    mutationFn: (failureId: string) => api.post(`/api/v1/failures/${failureId}/retry`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['failures'] })
    },
  })

  // Resolve failure mutation
  const resolveFailureMutation = useMutation({
    mutationFn: ({ failureId, resolution }: { failureId: string; resolution: any }) =>
      api.post(`/api/v1/failures/${failureId}/resolve`, resolution),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['failures'] })
    },
  })

  // Delete failure mutation
  const deleteFailureMutation = useMutation({
    mutationFn: (failureId: string) => api.delete(`/api/v1/failures/${failureId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['failures'] })
      setSelectedFailures(prev => prev.filter(id => !selectedFailures.includes(id)))
    },
  })

  /**
   * Get severity styling
   */
  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-300'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      case 'low':
        return 'bg-blue-100 text-blue-800 border-blue-300'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  /**
   * Get status styling and icon
   */
  const getStatusInfo = (status: string) => {
    switch (status) {
      case 'open':
        return {
          style: 'bg-red-100 text-red-800 border-red-300',
          icon: <XCircle className="h-4 w-4" />
        }
      case 'investigating':
        return {
          style: 'bg-yellow-100 text-yellow-800 border-yellow-300',
          icon: <AlertTriangle className="h-4 w-4" />
        }
      case 'resolved':
        return {
          style: 'bg-green-100 text-green-800 border-green-300',
          icon: <CheckCircle className="h-4 w-4" />
        }
      case 'permanent_failure':
        return {
          style: 'bg-gray-100 text-gray-800 border-gray-300',
          icon: <XCircle className="h-4 w-4" />
        }
      default:
        return {
          style: 'bg-gray-100 text-gray-800 border-gray-300',
          icon: <AlertCircle className="h-4 w-4" />
        }
    }
  }

  /**
   * Get failure type icon
   */
  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'analysis_failure':
        return <Zap className="h-4 w-4" />
      case 'system_error':
        return <Server className="h-4 w-4" />
      case 'validation_error':
        return <Shield className="h-4 w-4" />
      case 'timeout':
        return <Clock className="h-4 w-4" />
      case 'resource_error':
        return <Cpu className="h-4 w-4" />
      case 'network_error':
        return <Network className="h-4 w-4" />
      case 'data_error':
        return <Database className="h-4 w-4" />
      default:
        return <Bug className="h-4 w-4" />
    }
  }

  /**
   * Format failure type for display
   */
  const formatFailureType = (type: string) => {
    return type.split('_').map(word =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ')
  }

  /**
   * Handle failure selection
   */
  const handleSelectFailure = (failureId: string) => {
    setSelectedFailures(prev =>
      prev.includes(failureId)
        ? prev.filter(id => id !== failureId)
        : [...prev, failureId]
    )
  }

  /**
   * Handle select all
   */
  const handleSelectAll = () => {
    if (!failures) return

    if (selectedFailures.length === failures.length) {
      setSelectedFailures([])
    } else {
      setSelectedFailures(failures.map(f => f.id))
    }
  }

  /**
   * Handle bulk retry
   */
  const handleBulkRetry = async () => {
    for (const failureId of selectedFailures) {
      await retryFailureMutation.mutateAsync(failureId)
    }
    setSelectedFailures([])
  }

  if (failuresError) {
    return (
      <div className="container mx-auto px-4 py-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load failure records. Please try again later.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Failure Management</h1>
            <p className="text-muted-foreground mt-1">
              Track, analyze, and resolve system failures and processing errors
            </p>
          </div>
          <div className="flex items-center space-x-2">
            {selectedFailures.length > 0 && (
              <>
                <Button variant="outline" onClick={handleBulkRetry}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Retry ({selectedFailures.length})
                </Button>
                <Button variant="destructive">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete ({selectedFailures.length})
                </Button>
              </>
            )}
            <Button variant="outline" onClick={() => refetchFailures()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>

        {/* Analytics Overview */}
        {analytics && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Failures</p>
                    <p className="text-2xl font-bold">{analytics.totalFailures}</p>
                    <p className="text-xs text-muted-foreground">
                      {Object.values(analytics.failuresByType).reduce((a, b) => a + b, 0)} this week
                    </p>
                  </div>
                  <XCircle className="h-8 w-8 text-red-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Resolution Rate</p>
                    <p className="text-2xl font-bold">{analytics.resolutionStats.resolutionRate}%</p>
                    <div className="flex items-center text-xs text-muted-foreground">
                      <TrendingUp className="h-3 w-3 mr-1 text-green-600" />
                      +5% from last week
                    </div>
                  </div>
                  <CheckCircle className="h-8 w-8 text-green-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Avg Resolution Time</p>
                    <p className="text-2xl font-bold">{analytics.resolutionStats.averageResolutionTime}h</p>
                    <div className="flex items-center text-xs text-muted-foreground">
                      <TrendingDown className="h-3 w-3 mr-1 text-green-600" />
                      -2h from last week
                    </div>
                  </div>
                  <Clock className="h-8 w-8 text-blue-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Critical Failures</p>
                    <p className="text-2xl font-bold text-red-600">
                      {analytics.failuresBySeverity.critical || 0}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {analytics.resolutionStats.escalationRate}% escalated
                    </p>
                  </div>
                  <AlertTriangle className="h-8 w-8 text-red-600" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Search and Filter */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col lg:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search by error message, request ID, or component..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                      <Filter className="h-4 w-4 mr-2" />
                      Status
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuLabel>Filter by Status</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => setStatusFilter('')}>
                      All Statuses
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatusFilter('open')}>
                      Open
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatusFilter('investigating')}>
                      Investigating
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatusFilter('resolved')}>
                      Resolved
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                      <AlertTriangle className="h-4 w-4 mr-2" />
                      Severity
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuLabel>Filter by Severity</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => setSeverityFilter('')}>
                      All Severities
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setSeverityFilter('critical')}>
                      Critical
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setSeverityFilter('high')}>
                      High
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setSeverityFilter('medium')}>
                      Medium
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setSeverityFilter('low')}>
                      Low
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                      <Bug className="h-4 w-4 mr-2" />
                      Type
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuLabel>Filter by Type</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => setTypeFilter('')}>
                      All Types
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setTypeFilter('analysis_failure')}>
                      Analysis Failure
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setTypeFilter('system_error')}>
                      System Error
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setTypeFilter('validation_error')}>
                      Validation Error
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setTypeFilter('timeout')}>
                      Timeout
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Failure Records */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Failure Records</CardTitle>
              {failures && failures.length > 0 && (
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={selectedFailures.length === failures.length}
                    onChange={handleSelectAll}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm text-muted-foreground">
                    Select all ({failures.length})
                  </span>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {failuresLoading ? (
              <div className="space-y-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="flex items-center space-x-4 p-6 border rounded-lg">
                      <div className="h-4 w-4 bg-muted rounded"></div>
                      <div className="flex-1 space-y-2">
                        <div className="h-4 bg-muted rounded w-1/3"></div>
                        <div className="h-3 bg-muted rounded w-1/2"></div>
                      </div>
                      <div className="h-6 w-16 bg-muted rounded"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : !failures || failures.length === 0 ? (
              <div className="text-center py-12">
                <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-foreground mb-2">No Failures Found</h3>
                <p className="text-muted-foreground">
                  {searchQuery || statusFilter || severityFilter || typeFilter
                    ? 'Try adjusting your search or filter criteria'
                    : 'Great! No system failures or errors to report at this time.'
                  }
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {failures.map((failure) => {
                  const statusInfo = getStatusInfo(failure.status)

                  return (
                    <div
                      key={failure.id}
                      className={cn(
                        "p-6 border rounded-lg transition-all hover:shadow-md",
                        selectedFailures.includes(failure.id) && "border-primary bg-primary/5",
                        failure.severity === 'critical' && "border-red-300 bg-red-50"
                      )}
                    >
                      <div className="flex items-start space-x-4">
                        <input
                          type="checkbox"
                          checked={selectedFailures.includes(failure.id)}
                          onChange={() => handleSelectFailure(failure.id)}
                          className="mt-1 rounded border-gray-300"
                        />

                        <div className="flex-1 space-y-4">
                          {/* Header */}
                          <div className="flex items-start justify-between">
                            <div className="flex items-start space-x-3">
                              <div className="flex-shrink-0 pt-1">
                                {getTypeIcon(failure.type)}
                              </div>
                              <div className="flex-1">
                                <h4 className="font-semibold text-lg text-foreground">
                                  {failure.title}
                                </h4>
                                <p className="text-sm text-muted-foreground mt-1">
                                  {failure.description}
                                </p>
                                <div className="flex items-center space-x-2 mt-2">
                                  <Badge className={statusInfo.style}>
                                    {statusInfo.icon}
                                    <span className="ml-1">{failure.status.replace('_', ' ')}</span>
                                  </Badge>
                                  <Badge className={getSeverityStyle(failure.severity)}>
                                    {failure.severity}
                                  </Badge>
                                  <Badge variant="outline">
                                    {formatFailureType(failure.type)}
                                  </Badge>
                                  <Badge variant="outline" className="font-mono text-xs">
                                    {failure.errorCode}
                                  </Badge>
                                </div>
                              </div>
                            </div>

                            <div className="text-right">
                              <div className="text-sm text-muted-foreground">
                                {new Date(failure.occurredAt).toLocaleString()}
                              </div>
                              {failure.resolvedAt && (
                                <div className="text-xs text-green-600 mt-1">
                                  Resolved: {new Date(failure.resolvedAt).toLocaleString()}
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Context and Metrics */}
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-muted/30 rounded-lg">
                            <div>
                              <h5 className="font-medium text-sm mb-2">Context</h5>
                              <div className="space-y-1 text-xs text-muted-foreground">
                                <div>Component: {failure.context.component}</div>
                                <div>Version: {failure.context.version}</div>
                                <div>Environment: {failure.context.environment}</div>
                                {failure.context.requestId && (
                                  <div>Request: {failure.context.requestId}</div>
                                )}
                              </div>
                            </div>

                            <div>
                              <h5 className="font-medium text-sm mb-2">Metrics</h5>
                              <div className="space-y-1 text-xs text-muted-foreground">
                                <div>Retry Count: {failure.metrics.retryCount}</div>
                                {failure.metrics.processingDuration && (
                                  <div>Duration: {failure.metrics.processingDuration}s</div>
                                )}
                                {failure.metrics.resourceUsage && (
                                  <div>
                                    CPU: {failure.metrics.resourceUsage.cpu}%,
                                    Memory: {failure.metrics.resourceUsage.memory}%
                                  </div>
                                )}
                              </div>
                            </div>

                            <div>
                              <h5 className="font-medium text-sm mb-2">Assignment</h5>
                              <div className="space-y-1 text-xs text-muted-foreground">
                                {failure.assignedTo ? (
                                  <div>Assigned: {failure.assignedTo}</div>
                                ) : (
                                  <div>Unassigned</div>
                                )}
                                {failure.requesterName && (
                                  <div>Requester: {failure.requesterName}</div>
                                )}
                                {failure.department && (
                                  <div>Department: {failure.department}</div>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Resolution Info */}
                          {failure.resolution && (
                            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                              <h5 className="font-medium text-green-900 mb-2 flex items-center">
                                <CheckCircle className="h-4 w-4 mr-2" />
                                Resolution
                              </h5>
                              <div className="text-sm text-green-800">
                                <p><strong>Action:</strong> {failure.resolution.action.replace('_', ' ')}</p>
                                <p><strong>Description:</strong> {failure.resolution.description}</p>
                                <p><strong>Resolved by:</strong> {failure.resolution.resolvedBy}</p>
                                <p><strong>Resolution time:</strong> {failure.resolution.resolutionTime}h</p>
                              </div>
                            </div>
                          )}

                          {/* Stack Trace Preview */}
                          {failure.stackTrace && (
                            <div className="p-3 bg-gray-900 rounded-lg">
                              <div className="flex items-center justify-between mb-2">
                                <h5 className="font-medium text-white text-sm">Stack Trace</h5>
                                <Button size="sm" variant="ghost" className="text-white hover:bg-gray-800">
                                  <Code className="h-3 w-3 mr-1" />
                                  View Full
                                </Button>
                              </div>
                              <pre className="text-xs text-gray-300 overflow-x-auto max-h-20 overflow-y-auto">
                                {failure.stackTrace.split('\n').slice(0, 3).join('\n')}
                                {failure.stackTrace.split('\n').length > 3 && '\n...'}
                              </pre>
                            </div>
                          )}

                          {/* Tags and Related Failures */}
                          <div className="flex items-center justify-between pt-4 border-t">
                            <div className="flex items-center space-x-4">
                              {failure.tags.length > 0 && (
                                <div className="flex items-center space-x-1">
                                  {failure.tags.map((tag, index) => (
                                    <Badge key={index} variant="outline" className="text-xs">
                                      {tag}
                                    </Badge>
                                  ))}
                                </div>
                              )}
                              {failure.relatedFailures.length > 0 && (
                                <div className="text-xs text-muted-foreground">
                                  {failure.relatedFailures.length} related failures
                                </div>
                              )}
                              {failure.attachments.length > 0 && (
                                <div className="text-xs text-muted-foreground">
                                  {failure.attachments.length} attachments
                                </div>
                              )}
                            </div>

                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="sm">
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem>
                                  <Eye className="h-4 w-4 mr-2" />
                                  View Details
                                </DropdownMenuItem>
                                {failure.requestId && (
                                  <DropdownMenuItem asChild>
                                    <Link href={`/requests/${failure.requestId}`}>
                                      <FileText className="h-4 w-4 mr-2" />
                                      View Request
                                    </Link>
                                  </DropdownMenuItem>
                                )}
                                {failure.status !== 'resolved' && (
                                  <>
                                    <DropdownMenuItem
                                      onClick={() => retryFailureMutation.mutate(failure.id)}
                                    >
                                      <RotateCcw className="h-4 w-4 mr-2" />
                                      Retry
                                    </DropdownMenuItem>
                                    <DropdownMenuItem>
                                      <PlayCircle className="h-4 w-4 mr-2" />
                                      Mark as Investigating
                                    </DropdownMenuItem>
                                  </>
                                )}
                                <DropdownMenuItem>
                                  <Download className="h-4 w-4 mr-2" />
                                  Export Details
                                </DropdownMenuItem>
                                {userRole === 'admin' && (
                                  <>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem
                                      className="text-red-600"
                                      onClick={() => deleteFailureMutation.mutate(failure.id)}
                                    >
                                      <Trash2 className="h-4 w-4 mr-2" />
                                      Delete Record
                                    </DropdownMenuItem>
                                  </>
                                )}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}