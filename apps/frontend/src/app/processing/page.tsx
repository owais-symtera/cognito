'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSession } from 'next-auth/react'
import { MainLayout } from '@/components/layout/main-layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Clock,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Zap,
  Database,
  Cpu,
  Activity,
  TrendingUp,
  Eye,
  Pause,
  Play,
  Square,
  BarChart3,
  Timer,
  Users,
  Server
} from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

/**
 * Interface for processing job data
 */
interface ProcessingJob {
  id: string
  requestId: string
  drugName: string
  analysisType: string
  status: 'queued' | 'initializing' | 'processing' | 'analyzing' | 'validating' | 'completed' | 'failed' | 'paused'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  progress: number
  currentStep: string
  totalSteps: number
  completedSteps: number
  startedAt: string
  estimatedCompletion: string
  actualCompletion?: string
  assignedWorker: string
  cpuUsage: number
  memoryUsage: number
  requesterName: string
  department: string
  errorMessage?: string
  warnings: string[]
  artifacts: Array<{
    name: string
    type: string
    size: number
    generatedAt: string
  }>
}

/**
 * Interface for system metrics
 */
interface SystemMetrics {
  totalJobs: number
  activeJobs: number
  queuedJobs: number
  completedToday: number
  failedToday: number
  avgProcessingTime: number
  systemLoad: number
  availableWorkers: number
  busyWorkers: number
  throughputPerHour: number
}

/**
 * Real-time processing status monitoring interface.
 *
 * Features:
 * - Live job progress tracking
 * - System performance metrics
 * - Resource utilization monitoring
 * - Queue management
 * - Error handling and alerts
 * - Worker allocation status
 * - Processing analytics
 * - Role-based controls
 *
 * @returns React component for monitoring processing status
 *
 * @example
 * ```tsx
 * // Accessed via /processing route
 * <ProcessingStatusPage />
 * ```
 *
 * @since 1.0.0
 * @version 1.0.0
 * @author CognitoAI Development Team
 */
export default function ProcessingStatusPage() {
  const { data: session } = useSession()
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [selectedJobs, setSelectedJobs] = useState<string[]>([])
  const [refreshInterval, setRefreshInterval] = useState(5000) // 5 seconds

  // Fetch processing jobs
  const {
    data: jobs,
    isLoading: jobsLoading,
    error: jobsError,
    refetch: refetchJobs
  } = useQuery<ProcessingJob[]>({
    queryKey: ['processing-jobs'],
    queryFn: async () => {
      try {
        return await api.get('/api/v1/processing/jobs')
      } catch (error) {
        console.error('Failed to fetch processing jobs:', error)
        return []
      }
    },
    refetchInterval: autoRefresh ? refreshInterval : false,
  })

  // Fetch system metrics
  const {
    data: metrics,
    isLoading: metricsLoading,
    refetch: refetchMetrics
  } = useQuery<SystemMetrics>({
    queryKey: ['system-metrics'],
    queryFn: async () => {
      return await api.get('/api/v1/processing/metrics')
    },
    refetchInterval: autoRefresh ? refreshInterval : false,
  })

  const userRole = (session?.user as any)?.role || 'user'
  const canControlJobs = ['admin', 'analyst'].includes(userRole)

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        refetchJobs()
        refetchMetrics()
      }, refreshInterval)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, refreshInterval, refetchJobs, refetchMetrics])

  /**
   * Get status styling and icon
   */
  const getJobStatusInfo = (status: string) => {
    switch (status) {
      case 'queued':
        return {
          style: 'bg-gray-100 text-gray-800 border-gray-300',
          icon: <Clock className="h-4 w-4" />
        }
      case 'initializing':
        return {
          style: 'bg-blue-100 text-blue-800 border-blue-300',
          icon: <RefreshCw className="h-4 w-4 animate-spin" />
        }
      case 'processing':
      case 'analyzing':
      case 'validating':
        return {
          style: 'bg-purple-100 text-purple-800 border-purple-300',
          icon: <Cpu className="h-4 w-4" />
        }
      case 'completed':
        return {
          style: 'bg-green-100 text-green-800 border-green-300',
          icon: <CheckCircle className="h-4 w-4" />
        }
      case 'failed':
        return {
          style: 'bg-red-100 text-red-800 border-red-300',
          icon: <XCircle className="h-4 w-4" />
        }
      case 'paused':
        return {
          style: 'bg-yellow-100 text-yellow-800 border-yellow-300',
          icon: <Pause className="h-4 w-4" />
        }
      default:
        return {
          style: 'bg-gray-100 text-gray-800 border-gray-300',
          icon: <AlertTriangle className="h-4 w-4" />
        }
    }
  }

  /**
   * Get priority styling
   */
  const getPriorityStyle = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'bg-red-500 text-white'
      case 'high':
        return 'bg-orange-500 text-white'
      case 'medium':
        return 'bg-yellow-500 text-white'
      case 'low':
        return 'bg-blue-500 text-white'
      default:
        return 'bg-gray-500 text-white'
    }
  }

  /**
   * Format duration
   */
  const formatDuration = (startTime: string, endTime?: string) => {
    const start = new Date(startTime)
    const end = endTime ? new Date(endTime) : new Date()
    const diff = end.getTime() - start.getTime()

    const hours = Math.floor(diff / (1000 * 60 * 60))
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
    const seconds = Math.floor((diff % (1000 * 60)) / 1000)

    if (hours > 0) {
      return `${hours}h ${minutes}m`
    } else if (minutes > 0) {
      return `${minutes}m ${seconds}s`
    } else {
      return `${seconds}s`
    }
  }

  /**
   * Control job actions
   */
  const handleJobAction = async (jobId: string, action: 'pause' | 'resume' | 'cancel') => {
    try {
      await api.post(`/api/v1/processing/jobs/${jobId}/${action}`)
      refetchJobs()
    } catch (error) {
      console.error(`Failed to ${action} job:`, error)
    }
  }

  if (jobsError) {
    return (
      <div className="container mx-auto px-4 py-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load processing status. Please try again later.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Processing Status</h1>
            <p className="text-muted-foreground mt-1">
              Monitor real-time drug analysis processing and system performance
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              <Activity className={cn("h-4 w-4 mr-2", autoRefresh && "animate-pulse")} />
              {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
            </Button>
            <Button variant="outline" onClick={() => { refetchJobs(); refetchMetrics(); }}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>

        {/* System Metrics */}
        {metrics && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Active Jobs</p>
                    <p className="text-2xl font-bold">{metrics.activeJobs}</p>
                    <p className="text-xs text-muted-foreground">
                      {metrics.queuedJobs} queued
                    </p>
                  </div>
                  <Cpu className="h-8 w-8 text-blue-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">System Load</p>
                    <p className="text-2xl font-bold">{metrics.systemLoad}%</p>
                    <Progress value={metrics.systemLoad} className="h-2 mt-2" />
                  </div>
                  <Server className="h-8 w-8 text-orange-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Workers</p>
                    <p className="text-2xl font-bold">
                      {metrics.busyWorkers}/{metrics.availableWorkers}
                    </p>
                    <p className="text-xs text-muted-foreground">busy/available</p>
                  </div>
                  <Users className="h-8 w-8 text-purple-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Throughput</p>
                    <p className="text-2xl font-bold">{metrics.throughputPerHour}</p>
                    <p className="text-xs text-muted-foreground">jobs/hour</p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-green-600" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Performance Metrics */}
        {metrics && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <BarChart3 className="h-5 w-5" />
                  <span>Today's Summary</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Completed</span>
                  <div className="flex items-center space-x-2">
                    <span className="font-medium">{metrics.completedToday}</span>
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Failed</span>
                  <div className="flex items-center space-x-2">
                    <span className="font-medium">{metrics.failedToday}</span>
                    <XCircle className="h-4 w-4 text-red-600" />
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Avg Processing Time</span>
                  <div className="flex items-center space-x-2">
                    <span className="font-medium">{metrics.avgProcessingTime}h</span>
                    <Timer className="h-4 w-4 text-blue-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Database className="h-5 w-5" />
                  <span>Resource Usage</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>CPU Usage</span>
                    <span>{metrics.systemLoad}%</span>
                  </div>
                  <Progress value={metrics.systemLoad} className="h-2" />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Worker Utilization</span>
                    <span>{Math.round((metrics.busyWorkers / metrics.availableWorkers) * 100)}%</span>
                  </div>
                  <Progress value={(metrics.busyWorkers / metrics.availableWorkers) * 100} className="h-2" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Zap className="h-5 w-5" />
                  <span>Performance</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {((metrics.completedToday / (metrics.completedToday + metrics.failedToday)) * 100).toFixed(1)}%
                  </div>
                  <p className="text-sm text-muted-foreground">Success Rate</p>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {metrics.throughputPerHour}
                  </div>
                  <p className="text-sm text-muted-foreground">Jobs/Hour</p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Active Jobs */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center space-x-2">
                <Activity className="h-5 w-5" />
                <span>Processing Jobs</span>
              </CardTitle>
              <div className="flex items-center space-x-2">
                <Badge variant="outline">
                  {jobs?.length || 0} total jobs
                </Badge>
                {canControlJobs && selectedJobs.length > 0 && (
                  <div className="flex space-x-2">
                    <Button size="sm" variant="outline">
                      <Pause className="h-4 w-4 mr-1" />
                      Pause ({selectedJobs.length})
                    </Button>
                    <Button size="sm" variant="outline">
                      <Square className="h-4 w-4 mr-1" />
                      Cancel ({selectedJobs.length})
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {jobsLoading ? (
              <div className="space-y-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="flex items-center space-x-4 p-4 border rounded-lg">
                      <div className="h-10 w-10 bg-muted rounded-lg"></div>
                      <div className="flex-1 space-y-2">
                        <div className="h-4 bg-muted rounded w-1/3"></div>
                        <div className="h-3 bg-muted rounded w-1/2"></div>
                      </div>
                      <div className="h-4 w-20 bg-muted rounded"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : !jobs || jobs.length === 0 ? (
              <div className="text-center py-12">
                <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium text-foreground mb-2">No active processing jobs</h3>
                <p className="text-muted-foreground">
                  All jobs are currently completed or no new requests are being processed.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {jobs.map((job) => {
                  const statusInfo = getJobStatusInfo(job.status)
                  const isActive = ['processing', 'analyzing', 'validating'].includes(job.status)

                  return (
                    <div
                      key={job.id}
                      className={cn(
                        "p-4 border rounded-lg transition-all",
                        isActive && "border-primary/50 bg-primary/5",
                        selectedJobs.includes(job.id) && "ring-2 ring-primary/20"
                      )}
                    >
                      <div className="flex items-start space-x-4">
                        {canControlJobs && (
                          <input
                            type="checkbox"
                            checked={selectedJobs.includes(job.id)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedJobs(prev => [...prev, job.id])
                              } else {
                                setSelectedJobs(prev => prev.filter(id => id !== job.id))
                              }
                            }}
                            className="mt-1 rounded border-gray-300"
                          />
                        )}

                        <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4">
                          {/* Job Info */}
                          <div className="lg:col-span-2">
                            <div className="flex items-start space-x-3">
                              <div className="flex-shrink-0 pt-1">
                                {statusInfo.icon}
                              </div>
                              <div className="min-w-0 flex-1">
                                <Link href={`/requests/${job.requestId}`}>
                                  <h4 className="font-medium text-foreground hover:text-primary transition-colors">
                                    {job.drugName}
                                  </h4>
                                </Link>
                                <p className="text-sm text-muted-foreground">
                                  {job.analysisType.replace('_', ' ')} • {job.currentStep}
                                </p>
                                <div className="flex items-center space-x-2 mt-2">
                                  <Badge className={statusInfo.style}>
                                    {job.status.replace('_', ' ')}
                                  </Badge>
                                  <Badge className={getPriorityStyle(job.priority)}>
                                    {job.priority}
                                  </Badge>
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Progress */}
                          <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                              <span>Progress</span>
                              <span>{job.progress}%</span>
                            </div>
                            <Progress value={job.progress} className="h-2" />
                            <div className="text-xs text-muted-foreground">
                              Step {job.completedSteps + 1} of {job.totalSteps}
                            </div>
                          </div>

                          {/* Timing & Resources */}
                          <div className="space-y-1 text-sm">
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Runtime:</span>
                              <span>{formatDuration(job.startedAt, job.actualCompletion)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">ETA:</span>
                              <span>{new Date(job.estimatedCompletion).toLocaleTimeString()}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Worker:</span>
                              <span>{job.assignedWorker}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">CPU:</span>
                              <span>{job.cpuUsage}%</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Memory:</span>
                              <span>{job.memoryUsage}%</span>
                            </div>
                          </div>
                        </div>

                        {/* Actions */}
                        {canControlJobs && (
                          <div className="flex flex-col space-y-1">
                            <Link href={`/requests/${job.requestId}`}>
                              <Button variant="ghost" size="sm">
                                <Eye className="h-4 w-4" />
                              </Button>
                            </Link>
                            {job.status === 'processing' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleJobAction(job.id, 'pause')}
                              >
                                <Pause className="h-4 w-4" />
                              </Button>
                            )}
                            {job.status === 'paused' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleJobAction(job.id, 'resume')}
                              >
                                <Play className="h-4 w-4" />
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleJobAction(job.id, 'cancel')}
                            >
                              <Square className="h-4 w-4" />
                            </Button>
                          </div>
                        )}
                      </div>

                      {/* Error Message */}
                      {job.errorMessage && (
                        <Alert variant="destructive" className="mt-4">
                          <AlertTriangle className="h-4 w-4" />
                          <AlertDescription>
                            {job.errorMessage}
                          </AlertDescription>
                        </Alert>
                      )}

                      {/* Warnings */}
                      {job.warnings.length > 0 && (
                        <Alert className="mt-4">
                          <AlertTriangle className="h-4 w-4" />
                          <AlertDescription>
                            <div className="space-y-1">
                              <p className="font-medium">Warnings:</p>
                              <ul className="list-disc list-inside space-y-1">
                                {job.warnings.map((warning, index) => (
                                  <li key={index} className="text-sm">{warning}</li>
                                ))}
                              </ul>
                            </div>
                          </AlertDescription>
                        </Alert>
                      )}

                      {/* Artifacts */}
                      {job.artifacts.length > 0 && (
                        <div className="mt-4 p-3 bg-muted/50 rounded-lg">
                          <h5 className="text-sm font-medium mb-2">Generated Artifacts:</h5>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                            {job.artifacts.map((artifact, index) => (
                              <div key={index} className="text-xs p-2 bg-background rounded border">
                                <div className="font-medium truncate">{artifact.name}</div>
                                <div className="text-muted-foreground">{artifact.type}</div>
                                <div className="text-muted-foreground">
                                  {(artifact.size / 1024).toFixed(1)} KB
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  )
}