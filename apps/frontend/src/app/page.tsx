'use client'

import { useSession } from 'next-auth/react'
import { redirect } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle,
  Clock,
  FileText,
  Plus,
  TrendingUp,
  TrendingDown,
  Shield,
  Zap,
  Database,
  AlertCircle,
  Users,
  Target
} from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { MainLayout } from '@/components/layout/main-layout'

/**
 * Interface for dashboard statistics data
 */
interface DashboardStats {
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

/**
 * Interface for recent activity items
 */
interface ActivityItem {
  id: string
  type: 'request' | 'analysis' | 'alert' | 'compliance'
  title: string
  description: string
  timestamp: string
  severity?: 'low' | 'medium' | 'high' | 'critical'
  userId?: string
  userName?: string
}

/**
 * Comprehensive pharmaceutical intelligence dashboard component.
 *
 * Features:
 * - Real-time metrics and KPIs
 * - Drug request processing statistics
 * - Compliance monitoring
 * - System health indicators
 * - Recent activity feed
 * - Quick action shortcuts
 * - Role-based access controls
 *
 * @returns React component for the main dashboard
 *
 * @example
 * ```tsx
 * // Rendered automatically at the root route
 * <Dashboard />
 * ```
 *
 * @since 1.0.0
 * @version 1.0.0
 * @author CognitoAI Development Team
 */
export default function Dashboard() {
  const { data: session, status } = useSession()

  // Fetch dashboard data - hooks must be called unconditionally
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.getDashboardStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: status === 'authenticated', // Only fetch when authenticated
  })

  const { data: activities, isLoading: activitiesLoading } = useQuery<ActivityItem[]>({
    queryKey: ['recent-activity'],
    queryFn: () => api.getRecentActivity(),
    refetchInterval: 60000, // Refresh every minute
    enabled: status === 'authenticated', // Only fetch when authenticated
  })

  // Redirect unauthenticated users
  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (status === 'unauthenticated') {
    redirect('/auth/login')
  }

  const userRole = (session?.user as any)?.role || 'user'
  const userName = session?.user?.name || session?.user?.email || 'User'

  /**
   * Renders a metric card with trend indicator
   */
  const MetricCard = ({
    title,
    value,
    description,
    icon: Icon,
    trend,
    trendValue,
    className
  }: {
    title: string
    value: string | number
    description: string
    icon: any
    trend?: 'up' | 'down' | 'neutral'
    trendValue?: string
    className?: string
  }) => (
    <Card className={cn("transition-all hover:shadow-md", className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <div className="flex items-center space-x-2 text-xs text-muted-foreground">
          <span>{description}</span>
          {trend && trendValue && (
            <div className={cn(
              "flex items-center",
              trend === 'up' ? "text-green-600" : trend === 'down' ? "text-red-600" : ""
            )}>
              {trend === 'up' ? (
                <TrendingUp className="h-3 w-3 mr-1" />
              ) : trend === 'down' ? (
                <TrendingDown className="h-3 w-3 mr-1" />
              ) : null}
              <span>{trendValue}</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )

  /**
   * Renders activity item with appropriate styling based on type and severity
   */
  const ActivityItem = ({ activity }: { activity: ActivityItem }) => {
    const getActivityIcon = (type: string) => {
      switch (type) {
        case 'request': return FileText
        case 'analysis': return BarChart3
        case 'alert': return AlertTriangle
        case 'compliance': return Shield
        default: return Activity
      }
    }

    const getSeverityColor = (severity?: string) => {
      switch (severity) {
        case 'critical': return 'bg-red-100 text-red-800 border-red-200'
        case 'high': return 'bg-orange-100 text-orange-800 border-orange-200'
        case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
        case 'low': return 'bg-blue-100 text-blue-800 border-blue-200'
        default: return 'bg-gray-100 text-gray-800 border-gray-200'
      }
    }

    const Icon = getActivityIcon(activity.type)

    return (
      <div className="flex items-start space-x-3 p-3 rounded-lg border hover:bg-muted/50 transition-colors">
        <div className="flex-shrink-0">
          <Icon className="h-5 w-5 text-muted-foreground mt-0.5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-foreground truncate">
              {activity.title}
            </h4>
            {activity.severity && (
              <Badge variant="outline" className={getSeverityColor(activity.severity)}>
                {activity.severity}
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {activity.description}
          </p>
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-muted-foreground">
              {new Date(activity.timestamp).toLocaleString()}
            </span>
            {activity.userName && (
              <span className="text-xs text-muted-foreground">
                by {activity.userName}
              </span>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
          <div>
            <h1 className="text-3xl font-bold text-foreground">
              Pharmaceutical Intelligence Dashboard
            </h1>
            <p className="text-muted-foreground mt-1">
              Welcome back, {userName}. Monitor your drug analysis pipeline and compliance status.
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">
              {userRole.replace('_', ' ').toUpperCase()}
            </Badge>
            <Link href="/requests/new">
              <Button className="flex items-center space-x-2">
                <Plus className="h-4 w-4" />
                <span>New Request</span>
              </Button>
            </Link>
          </div>
        </div>

        {/* Error State */}
        {statsError && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Failed to load dashboard data. Please refresh the page or contact support.
            </AlertDescription>
          </Alert>
        )}

        {/* Loading State */}
        {statsLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <Card key={i} className="animate-pulse">
                <CardHeader>
                  <div className="h-4 bg-muted rounded w-3/4"></div>
                </CardHeader>
                <CardContent>
                  <div className="h-8 bg-muted rounded w-1/2 mb-2"></div>
                  <div className="h-4 bg-muted rounded w-full"></div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Main Metrics */}
        {stats && !statsLoading && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <MetricCard
                title="Total Requests"
                value={stats.requests.total.toLocaleString()}
                description="All time drug requests"
                icon={FileText}
                trend={stats.requests.growth > 0 ? 'up' : stats.requests.growth < 0 ? 'down' : 'neutral'}
                trendValue={`${Math.abs(stats.requests.growth)}% this month`}
              />

              <MetricCard
                title="Processing"
                value={stats.requests.processing.toLocaleString()}
                description="Currently in analysis"
                icon={Clock}
                className="border-orange-200 bg-orange-50"
              />

              <MetricCard
                title="Success Rate"
                value={`${stats.analysis.successRate}%`}
                description="Analysis completion rate"
                icon={CheckCircle}
                trend={stats.analysis.successRate > 95 ? 'up' : 'down'}
                trendValue="Last 30 days"
                className="border-green-200 bg-green-50"
              />

              <MetricCard
                title="Compliance Score"
                value={`${stats.compliance.score}%`}
                description="Regulatory compliance"
                icon={Shield}
                trend={stats.compliance.score > 90 ? 'up' : 'down'}
                trendValue="FDA standards"
                className="border-blue-200 bg-blue-50"
              />
            </div>

            {/* Secondary Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <MetricCard
                title="Avg Processing Time"
                value={`${stats.analysis.avgProcessingTime}h`}
                description="Per analysis request"
                icon={Zap}
              />

              <MetricCard
                title="Critical Findings"
                value={stats.analysis.criticalFindings.toLocaleString()}
                description="Requiring attention"
                icon={AlertCircle}
                className={stats.analysis.criticalFindings > 0 ? "border-red-200 bg-red-50" : ""}
              />

              <MetricCard
                title="Active Users"
                value={stats.system.activeUsers.toLocaleString()}
                description="Current session"
                icon={Users}
              />

              <MetricCard
                title="System Uptime"
                value={`${stats.system.uptime}%`}
                description="Last 30 days"
                icon={Activity}
                trend={stats.system.uptime > 99 ? 'up' : 'down'}
                trendValue="99.9% SLA"
              />
            </div>

            {/* Status Overview */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Target className="h-5 w-5" />
                    <span>Request Pipeline Status</span>
                  </CardTitle>
                  <CardDescription>
                    Current distribution of drug analysis requests
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Pending Review</span>
                      <span className="text-sm font-medium">{stats.requests.pending}</span>
                    </div>
                    <Progress value={(stats.requests.pending / stats.requests.total) * 100} className="h-2" />
                  </div>

                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">In Processing</span>
                      <span className="text-sm font-medium">{stats.requests.processing}</span>
                    </div>
                    <Progress
                      value={(stats.requests.processing / stats.requests.total) * 100}
                      className="h-2"
                    />
                  </div>

                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Completed</span>
                      <span className="text-sm font-medium">{stats.requests.completed}</span>
                    </div>
                    <Progress
                      value={(stats.requests.completed / stats.requests.total) * 100}
                      className="h-2"
                    />
                  </div>

                  {stats.requests.failed > 0 && (
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground text-red-600">Failed</span>
                        <span className="text-sm font-medium text-red-600">{stats.requests.failed}</span>
                      </div>
                      <Progress
                        value={(stats.requests.failed / stats.requests.total) * 100}
                        className="h-2"
                      />
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Database className="h-5 w-5" />
                    <span>System Health</span>
                  </CardTitle>
                  <CardDescription>
                    Platform performance and resource utilization
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">API Calls Today</span>
                      <span className="text-sm font-medium">{stats.system.apiCalls.toLocaleString()}</span>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Storage Usage</span>
                      <span className="text-sm font-medium">{stats.system.storage}%</span>
                    </div>
                    <Progress value={stats.system.storage} className="h-2" />
                  </div>

                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Audit Trails</span>
                      <span className="text-sm font-medium">{stats.compliance.auditTrails.toLocaleString()}</span>
                    </div>
                  </div>

                  {stats.compliance.warnings > 0 && (
                    <Alert>
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        {stats.compliance.warnings} compliance warnings require attention
                      </AlertDescription>
                    </Alert>
                  )}
                </CardContent>
              </Card>
            </div>
          </>
        )}

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Activity className="h-5 w-5" />
              <span>Recent Activity</span>
            </CardTitle>
            <CardDescription>
              Latest system events and user actions
            </CardDescription>
          </CardHeader>
          <CardContent>
            {activitiesLoading ? (
              <div className="space-y-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="animate-pulse flex space-x-3 p-3">
                    <div className="h-5 w-5 bg-muted rounded"></div>
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-muted rounded w-3/4"></div>
                      <div className="h-3 bg-muted rounded w-1/2"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : activities && activities.length > 0 ? (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {activities.slice(0, 10).map((activity) => (
                  <ActivityItem key={activity.id} activity={activity} />
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-muted-foreground">
                No recent activity to display
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common pharmaceutical intelligence tasks
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Link href="/requests/new">
                <Button variant="outline" className="w-full justify-start h-auto p-4">
                  <div className="flex flex-col items-start space-y-1">
                    <Plus className="h-5 w-5" />
                    <span className="font-medium">New Drug Request</span>
                    <span className="text-xs text-muted-foreground">Submit new analysis</span>
                  </div>
                </Button>
              </Link>

              <Link href="/processing">
                <Button variant="outline" className="w-full justify-start h-auto p-4">
                  <div className="flex flex-col items-start space-y-1">
                    <Clock className="h-5 w-5" />
                    <span className="font-medium">Track Processing</span>
                    <span className="text-xs text-muted-foreground">Monitor progress</span>
                  </div>
                </Button>
              </Link>

              <Link href="/results">
                <Button variant="outline" className="w-full justify-start h-auto p-4">
                  <div className="flex flex-col items-start space-y-1">
                    <BarChart3 className="h-5 w-5" />
                    <span className="font-medium">View Results</span>
                    <span className="text-xs text-muted-foreground">Analysis reports</span>
                  </div>
                </Button>
              </Link>

              {['admin', 'analyst'].includes(userRole) && (
                <Link href="/monitoring">
                  <Button variant="outline" className="w-full justify-start h-auto p-4">
                    <div className="flex flex-col items-start space-y-1">
                      <Activity className="h-5 w-5" />
                      <span className="font-medium">System Monitor</span>
                      <span className="text-xs text-muted-foreground">Real-time metrics</span>
                    </div>
                  </Button>
                </Link>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  )
}