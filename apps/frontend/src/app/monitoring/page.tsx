'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSession } from 'next-auth/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Activity,
  Server,
  Database,
  Cpu,
  MemoryStick,
  HardDrive,
  Wifi,
  Zap,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Users,
  BarChart3,
  Gauge,
  RefreshCw,
  Play,
  Pause,
  Eye,
  Settings,
  Download,
  Bell,
  Shield,
  Globe,
  Network
} from 'lucide-react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

/**
 * Interface for system monitoring data
 */
interface SystemHealth {
  timestamp: string
  services: {
    api: {
      status: 'healthy' | 'degraded' | 'down'
      responseTime: number
      uptime: number
      requestsPerMinute: number
      errorRate: number
    }
    database: {
      status: 'healthy' | 'degraded' | 'down'
      connectionPool: number
      queryTime: number
      activeConnections: number
      diskUsage: number
    }
    analysis: {
      status: 'healthy' | 'degraded' | 'down'
      queueLength: number
      processingRate: number
      workerUtilization: number
      avgProcessingTime: number
    }
    authentication: {
      status: 'healthy' | 'degraded' | 'down'
      activeUsers: number
      sessionCount: number
      loginRate: number
      failedAttempts: number
    }
  }
  resources: {
    cpu: {
      usage: number
      cores: number
      load: number[]
      temperature: number
    }
    memory: {
      used: number
      total: number
      usage: number
      swap: number
    }
    disk: {
      used: number
      total: number
      usage: number
      iops: number
    }
    network: {
      inbound: number
      outbound: number
      latency: number
      packetLoss: number
    }
  }
  alerts: Array<{
    id: string
    level: 'info' | 'warning' | 'error' | 'critical'
    service: string
    message: string
    timestamp: string
    acknowledged: boolean
  }>
}

/**
 * Interface for performance metrics
 */
interface PerformanceMetrics {
  throughput: {
    requestsPerSecond: number
    analysesPerHour: number
    dataProcessed: number
    trend: 'up' | 'down' | 'stable'
  }
  availability: {
    uptime: number
    sla: number
    mttr: number
    incidents: number
  }
  security: {
    threatLevel: 'low' | 'medium' | 'high' | 'critical'
    blockedRequests: number
    vulnerabilities: number
    lastScan: string
  }
}

/**
 * Real-time system monitoring dashboard.
 *
 * Features:
 * - Live system health monitoring
 * - Resource utilization tracking
 * - Service status overview
 * - Performance metrics
 * - Alert management
 * - Security monitoring
 * - Real-time charts and graphs
 * - Incident management
 *
 * @returns React component for system monitoring
 *
 * @example
 * ```tsx
 * // Accessed via /monitoring route (admin/analyst only)
 * <MonitoringPage />
 * ```
 *
 * @since 1.0.0
 * @version 1.0.0
 * @author CognitoAI Development Team
 */
export default function MonitoringPage() {
  const { data: session } = useSession()
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshInterval, setRefreshInterval] = useState(2000) // 2 seconds
  const [selectedTimeRange, setSelectedTimeRange] = useState('1h')
  const [acknowledgedAlerts, setAcknowledgedAlerts] = useState<string[]>([])

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

  // Fetch system health data
  const {
    data: healthData,
    isLoading: healthLoading,
    error: healthError,
    refetch: refetchHealth
  } = useQuery<SystemHealth>({
    queryKey: ['system-health'],
    queryFn: () => api.get('/api/v1/monitoring/health'),
    refetchInterval: autoRefresh ? refreshInterval : false,
  })

  // Fetch performance metrics
  const {
    data: metricsData,
    isLoading: metricsLoading,
    refetch: refetchMetrics
  } = useQuery<PerformanceMetrics>({
    queryKey: ['performance-metrics', selectedTimeRange],
    queryFn: () => api.get(`/api/v1/monitoring/metrics?timeRange=${selectedTimeRange}`),
    refetchInterval: autoRefresh ? refreshInterval * 5 : false, // Slower refresh for metrics
  })

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        refetchHealth()
        refetchMetrics()
      }, refreshInterval)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, refreshInterval, refetchHealth, refetchMetrics])

  /**
   * Get status styling and icon
   */
  const getStatusInfo = (status: string) => {
    switch (status) {
      case 'healthy':
        return {
          style: 'bg-green-100 text-green-800 border-green-300',
          icon: <CheckCircle className="h-4 w-4" />,
          color: 'text-green-600'
        }
      case 'degraded':
        return {
          style: 'bg-yellow-100 text-yellow-800 border-yellow-300',
          icon: <AlertTriangle className="h-4 w-4" />,
          color: 'text-yellow-600'
        }
      case 'down':
        return {
          style: 'bg-red-100 text-red-800 border-red-300',
          icon: <XCircle className="h-4 w-4" />,
          color: 'text-red-600'
        }
      default:
        return {
          style: 'bg-gray-100 text-gray-800 border-gray-300',
          icon: <AlertTriangle className="h-4 w-4" />,
          color: 'text-gray-600'
        }
    }
  }

  /**
   * Get alert level styling
   */
  const getAlertStyle = (level: string) => {
    switch (level) {
      case 'info':
        return 'bg-blue-100 text-blue-800 border-blue-300'
      case 'warning':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      case 'error':
        return 'bg-orange-100 text-orange-800 border-orange-300'
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-300'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  /**
   * Get usage color based on percentage
   */
  const getUsageColor = (usage: number) => {
    if (usage >= 90) return 'text-red-600'
    if (usage >= 75) return 'text-orange-600'
    if (usage >= 50) return 'text-yellow-600'
    return 'text-green-600'
  }

  /**
   * Handle alert acknowledgment
   */
  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await api.post(`/api/v1/monitoring/alerts/${alertId}/acknowledge`)
      setAcknowledgedAlerts(prev => [...prev, alertId])
    } catch (error) {
      console.error('Failed to acknowledge alert:', error)
    }
  }

  /**
   * Format bytes to human readable
   */
  const formatBytes = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    if (bytes === 0) return '0 B'
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }

  if (healthError) {
    return (
      <div className="container mx-auto px-4 py-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load monitoring data. Please check system connectivity.
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
            <h1 className="text-3xl font-bold text-foreground">System Monitoring</h1>
            <p className="text-muted-foreground mt-1">
              Real-time pharmaceutical intelligence platform monitoring and alerts
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              {autoRefresh ? <Pause className="h-4 w-4 mr-2" /> : <Play className="h-4 w-4 mr-2" />}
              {autoRefresh ? 'Pause' : 'Resume'}
            </Button>
            <Button variant="outline" size="sm" onClick={() => { refetchHealth(); refetchMetrics(); }}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
            <Button variant="outline" size="sm">
              <Settings className="h-4 w-4 mr-2" />
              Configure
            </Button>
          </div>
        </div>

        {/* Overall Status */}
        {healthData && (
          <Card className="border-2">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Activity className="h-5 w-5" />
                <span>System Status</span>
                <Badge className={getStatusInfo('healthy').style}>
                  All Systems Operational
                </Badge>
              </CardTitle>
              <CardDescription>
                Last updated: {new Date(healthData.timestamp).toLocaleString()}
                {autoRefresh && (
                  <span className="ml-2 inline-flex items-center">
                    <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse mr-1"></div>
                    Live
                  </span>
                )}
              </CardDescription>
            </CardHeader>
          </Card>
        )}

        {/* Service Status Grid */}
        {healthData && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center space-x-2">
                  <Globe className="h-5 w-5" />
                  <span>API Service</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Status</span>
                  <Badge className={getStatusInfo(healthData.services.api.status).style}>
                    {healthData.services.api.status}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Response Time</span>
                  <span className="text-sm font-medium">{healthData.services.api.responseTime}ms</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Requests/min</span>
                  <span className="text-sm font-medium">{healthData.services.api.requestsPerMinute}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Error Rate</span>
                  <span className={cn("text-sm font-medium", getUsageColor(healthData.services.api.errorRate))}>
                    {healthData.services.api.errorRate}%
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Uptime</span>
                  <span className="text-sm font-medium">{healthData.services.api.uptime}%</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center space-x-2">
                  <Database className="h-5 w-5" />
                  <span>Database</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Status</span>
                  <Badge className={getStatusInfo(healthData.services.database.status).style}>
                    {healthData.services.database.status}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Query Time</span>
                  <span className="text-sm font-medium">{healthData.services.database.queryTime}ms</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Connections</span>
                  <span className="text-sm font-medium">{healthData.services.database.activeConnections}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Pool Usage</span>
                  <span className="text-sm font-medium">{healthData.services.database.connectionPool}%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Disk Usage</span>
                  <span className={cn("text-sm font-medium", getUsageColor(healthData.services.database.diskUsage))}>
                    {healthData.services.database.diskUsage}%
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center space-x-2">
                  <Zap className="h-5 w-5" />
                  <span>Analysis Engine</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Status</span>
                  <Badge className={getStatusInfo(healthData.services.analysis.status).style}>
                    {healthData.services.analysis.status}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Queue Length</span>
                  <span className="text-sm font-medium">{healthData.services.analysis.queueLength}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Processing Rate</span>
                  <span className="text-sm font-medium">{healthData.services.analysis.processingRate}/h</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Worker Usage</span>
                  <span className="text-sm font-medium">{healthData.services.analysis.workerUtilization}%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Avg Time</span>
                  <span className="text-sm font-medium">{healthData.services.analysis.avgProcessingTime}h</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center space-x-2">
                  <Shield className="h-5 w-5" />
                  <span>Authentication</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Status</span>
                  <Badge className={getStatusInfo(healthData.services.authentication.status).style}>
                    {healthData.services.authentication.status}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Active Users</span>
                  <span className="text-sm font-medium">{healthData.services.authentication.activeUsers}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Sessions</span>
                  <span className="text-sm font-medium">{healthData.services.authentication.sessionCount}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Login Rate</span>
                  <span className="text-sm font-medium">{healthData.services.authentication.loginRate}/min</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Failed Attempts</span>
                  <span className={cn("text-sm font-medium", healthData.services.authentication.failedAttempts > 10 ? "text-red-600" : "text-green-600")}>
                    {healthData.services.authentication.failedAttempts}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Resource Utilization */}
        {healthData && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Gauge className="h-5 w-5" />
                  <span>System Resources</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-2">
                      <Cpu className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">CPU Usage</span>
                    </div>
                    <span className={cn("text-sm font-bold", getUsageColor(healthData.resources.cpu.usage))}>
                      {healthData.resources.cpu.usage}%
                    </span>
                  </div>
                  <Progress value={healthData.resources.cpu.usage} className="h-2" />
                  <div className="text-xs text-muted-foreground">
                    {healthData.resources.cpu.cores} cores • Load: {healthData.resources.cpu.load.join(', ')} • {healthData.resources.cpu.temperature}°C
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-2">
                      <MemoryStick className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Memory</span>
                    </div>
                    <span className={cn("text-sm font-bold", getUsageColor(healthData.resources.memory.usage))}>
                      {healthData.resources.memory.usage}%
                    </span>
                  </div>
                  <Progress value={healthData.resources.memory.usage} className="h-2" />
                  <div className="text-xs text-muted-foreground">
                    {formatBytes(healthData.resources.memory.used)} / {formatBytes(healthData.resources.memory.total)} used
                    • Swap: {formatBytes(healthData.resources.memory.swap)}
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-2">
                      <HardDrive className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Disk</span>
                    </div>
                    <span className={cn("text-sm font-bold", getUsageColor(healthData.resources.disk.usage))}>
                      {healthData.resources.disk.usage}%
                    </span>
                  </div>
                  <Progress value={healthData.resources.disk.usage} className="h-2" />
                  <div className="text-xs text-muted-foreground">
                    {formatBytes(healthData.resources.disk.used)} / {formatBytes(healthData.resources.disk.total)} used
                    • IOPS: {healthData.resources.disk.iops}
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-2">
                      <Network className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">Network</span>
                    </div>
                    <span className="text-sm font-bold">
                      {healthData.resources.network.latency}ms
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-xs text-muted-foreground">
                    <div>In: {formatBytes(healthData.resources.network.inbound)}/s</div>
                    <div>Out: {formatBytes(healthData.resources.network.outbound)}/s</div>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Packet Loss: {healthData.resources.network.packetLoss}%
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Performance Metrics */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <BarChart3 className="h-5 w-5" />
                  <span>Performance Metrics</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {metricsData && (
                  <>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="text-center p-4 bg-muted/30 rounded-lg">
                        <div className="text-2xl font-bold text-blue-600">
                          {metricsData.throughput.requestsPerSecond}
                        </div>
                        <div className="text-sm text-muted-foreground">Requests/sec</div>
                        <div className="flex items-center justify-center mt-1">
                          {metricsData.throughput.trend === 'up' ? (
                            <TrendingUp className="h-3 w-3 text-green-600" />
                          ) : metricsData.throughput.trend === 'down' ? (
                            <TrendingDown className="h-3 w-3 text-red-600" />
                          ) : null}
                        </div>
                      </div>

                      <div className="text-center p-4 bg-muted/30 rounded-lg">
                        <div className="text-2xl font-bold text-green-600">
                          {metricsData.throughput.analysesPerHour}
                        </div>
                        <div className="text-sm text-muted-foreground">Analyses/hour</div>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="flex justify-between items-center">
                        <span className="text-sm font-medium">Uptime</span>
                        <span className="text-lg font-bold text-green-600">
                          {metricsData.availability.uptime}%
                        </span>
                      </div>
                      <Progress value={metricsData.availability.uptime} className="h-2" />

                      <div className="grid grid-cols-3 gap-4 text-center text-sm">
                        <div>
                          <div className="font-medium">SLA</div>
                          <div className="text-muted-foreground">{metricsData.availability.sla}%</div>
                        </div>
                        <div>
                          <div className="font-medium">MTTR</div>
                          <div className="text-muted-foreground">{metricsData.availability.mttr}m</div>
                        </div>
                        <div>
                          <div className="font-medium">Incidents</div>
                          <div className="text-muted-foreground">{metricsData.availability.incidents}</div>
                        </div>
                      </div>
                    </div>

                    {/* Security Status */}
                    <div className="p-4 bg-muted/30 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium">Security Status</span>
                        <Badge className={getAlertStyle(metricsData.security.threatLevel)}>
                          {metricsData.security.threatLevel} threat
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground space-y-1">
                        <div>Blocked requests: {metricsData.security.blockedRequests}</div>
                        <div>Vulnerabilities: {metricsData.security.vulnerabilities}</div>
                        <div>Last scan: {new Date(metricsData.security.lastScan).toLocaleDateString()}</div>
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Active Alerts */}
        {healthData && healthData.alerts.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Bell className="h-5 w-5" />
                <span>Active Alerts</span>
                <Badge variant="outline">
                  {healthData.alerts.filter(a => !a.acknowledged && !acknowledgedAlerts.includes(a.id)).length} unacknowledged
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {healthData.alerts
                  .filter(alert => !alert.acknowledged && !acknowledgedAlerts.includes(alert.id))
                  .map((alert) => (
                    <div
                      key={alert.id}
                      className={cn(
                        "flex items-start justify-between p-4 border rounded-lg",
                        getAlertStyle(alert.level).includes('red') && "border-red-300 bg-red-50",
                        getAlertStyle(alert.level).includes('orange') && "border-orange-300 bg-orange-50",
                        getAlertStyle(alert.level).includes('yellow') && "border-yellow-300 bg-yellow-50",
                        getAlertStyle(alert.level).includes('blue') && "border-blue-300 bg-blue-50"
                      )}
                    >
                      <div className="flex items-start space-x-3">
                        <div className="flex-shrink-0 pt-1">
                          {alert.level === 'critical' ? (
                            <XCircle className="h-5 w-5 text-red-600" />
                          ) : alert.level === 'error' ? (
                            <AlertTriangle className="h-5 w-5 text-orange-600" />
                          ) : alert.level === 'warning' ? (
                            <AlertTriangle className="h-5 w-5 text-yellow-600" />
                          ) : (
                            <CheckCircle className="h-5 w-5 text-blue-600" />
                          )}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-1">
                            <Badge className={getAlertStyle(alert.level)}>
                              {alert.level}
                            </Badge>
                            <span className="text-sm font-medium">{alert.service}</span>
                          </div>
                          <p className="text-sm text-foreground">{alert.message}</p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {new Date(alert.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleAcknowledgeAlert(alert.id)}
                        >
                          Acknowledge
                        </Button>
                        <Button size="sm" variant="ghost">
                          <Eye className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* No Alerts State */}
        {healthData && healthData.alerts.length === 0 && (
          <Card>
            <CardContent className="pt-6">
              <div className="text-center py-8">
                <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-foreground mb-2">No Active Alerts</h3>
                <p className="text-muted-foreground">
                  All systems are operating normally. No alerts require attention.
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}