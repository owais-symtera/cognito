'use client'

import { FileText, BarChart3, CheckCircle, Clock, TrendingUp, TrendingDown } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface StatsCardProps {
  title: string
  value: string | number
  description?: string
  icon: React.ReactNode
  trend?: {
    value: number
    isPositive: boolean
  }
  className?: string
}

function StatsCard({ title, value, description, icon, trend, className }: StatsCardProps) {
  return (
    <Card className={cn("", className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <div className="text-muted-foreground">
          {icon}
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground mt-1">
            {description}
          </p>
        )}
        {trend && (
          <div className="flex items-center mt-2">
            {trend.isPositive ? (
              <TrendingUp className="h-4 w-4 text-green-600" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-600" />
            )}
            <span
              className={cn(
                "text-xs ml-1",
                trend.isPositive ? "text-green-600" : "text-red-600"
              )}
            >
              {trend.isPositive ? '+' : ''}{trend.value}% from last month
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface DashboardStatsProps {
  stats?: {
    totalRequests: number
    activeAnalyses: number
    completedReports: number
    pendingReviews: number
    trends: {
      requests: number
      analyses: number
      reports: number
      reviews: number
    }
  }
  isLoading?: boolean
}

export function DashboardStats({ stats, isLoading }: DashboardStatsProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="h-4 bg-muted rounded w-20"></div>
              <div className="h-4 w-4 bg-muted rounded"></div>
            </CardHeader>
            <CardContent>
              <div className="h-7 bg-muted rounded w-16 mb-2"></div>
              <div className="h-3 bg-muted rounded w-24"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const defaultStats = {
    totalRequests: 0,
    activeAnalyses: 0,
    completedReports: 0,
    pendingReviews: 0,
    trends: {
      requests: 0,
      analyses: 0,
      reports: 0,
      reviews: 0,
    }
  }

  const data = stats || defaultStats

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatsCard
        title="Total Requests"
        value={data.totalRequests.toLocaleString()}
        description="Pharmaceutical analysis requests"
        icon={<FileText className="h-4 w-4" />}
        trend={{
          value: data.trends.requests,
          isPositive: data.trends.requests >= 0,
        }}
      />

      <StatsCard
        title="Active Analyses"
        value={data.activeAnalyses.toLocaleString()}
        description="Currently being processed"
        icon={<BarChart3 className="h-4 w-4" />}
        trend={{
          value: data.trends.analyses,
          isPositive: data.trends.analyses >= 0,
        }}
      />

      <StatsCard
        title="Completed Reports"
        value={data.completedReports.toLocaleString()}
        description="Ready for review"
        icon={<CheckCircle className="h-4 w-4" />}
        trend={{
          value: data.trends.reports,
          isPositive: data.trends.reports >= 0,
        }}
      />

      <StatsCard
        title="Pending Reviews"
        value={data.pendingReviews.toLocaleString()}
        description="Awaiting compliance check"
        icon={<Clock className="h-4 w-4" />}
        trend={{
          value: data.trends.reviews,
          isPositive: data.trends.reviews <= 0, // Fewer pending is better
        }}
      />
    </div>
  )
}