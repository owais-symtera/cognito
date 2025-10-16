'use client'

import { formatDistanceToNow } from '@/lib/date-utils'
import { FileText, BarChart3, CheckCircle, AlertCircle, User } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface ActivityItem {
  id: string
  type: 'request' | 'analysis' | 'report' | 'user' | 'system'
  title: string
  description: string
  timestamp: Date
  status?: 'completed' | 'pending' | 'failed' | 'in_progress'
  user?: {
    name: string
    email: string
  }
}

const activityIcons = {
  request: FileText,
  analysis: BarChart3,
  report: CheckCircle,
  user: User,
  system: AlertCircle,
}

const statusColors = {
  completed: 'bg-green-100 text-green-800 border-green-200',
  pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  failed: 'bg-red-100 text-red-800 border-red-200',
  in_progress: 'bg-blue-100 text-blue-800 border-blue-200',
}

interface RecentActivityProps {
  activities?: ActivityItem[]
  isLoading?: boolean
}

export function RecentActivity({ activities, isLoading }: RecentActivityProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center space-x-4 animate-pulse">
                <div className="h-8 w-8 bg-muted rounded-full"></div>
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-muted rounded w-3/4"></div>
                  <div className="h-3 bg-muted rounded w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  const defaultActivities: ActivityItem[] = [
    {
      id: '1',
      type: 'request',
      title: 'New pharmaceutical analysis request',
      description: 'Drug interaction study for compound ABC-123',
      timestamp: new Date(Date.now() - 5 * 60 * 1000), // 5 minutes ago
      status: 'pending',
      user: { name: 'Dr. Sarah Chen', email: 'sarah.chen@pharma.com' }
    },
    {
      id: '2',
      type: 'analysis',
      title: 'Analysis completed',
      description: 'Molecular structure analysis for request #1234',
      timestamp: new Date(Date.now() - 15 * 60 * 1000), // 15 minutes ago
      status: 'completed',
      user: { name: 'System', email: '' }
    },
    {
      id: '3',
      type: 'report',
      title: 'Compliance report generated',
      description: 'Monthly safety assessment report',
      timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000), // 1 hour ago
      status: 'completed',
      user: { name: 'Dr. Michael Rodriguez', email: 'michael.r@pharma.com' }
    },
    {
      id: '4',
      type: 'user',
      title: 'User access granted',
      description: 'New researcher joined the team',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
      status: 'completed',
      user: { name: 'Admin', email: 'admin@pharma.com' }
    },
    {
      id: '5',
      type: 'system',
      title: 'System maintenance',
      description: 'Scheduled backup completed successfully',
      timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000), // 3 hours ago
      status: 'completed',
      user: { name: 'System', email: '' }
    }
  ]

  const data = activities || defaultActivities

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {data.map((activity) => {
            const Icon = activityIcons[activity.type]
            return (
              <div key={activity.id} className="flex items-start space-x-4">
                <div className={cn(
                  "h-8 w-8 rounded-full flex items-center justify-center",
                  activity.type === 'request' && "bg-blue-100 text-blue-600",
                  activity.type === 'analysis' && "bg-purple-100 text-purple-600",
                  activity.type === 'report' && "bg-green-100 text-green-600",
                  activity.type === 'user' && "bg-orange-100 text-orange-600",
                  activity.type === 'system' && "bg-gray-100 text-gray-600"
                )}>
                  <Icon className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-foreground truncate">
                      {activity.title}
                    </p>
                    {activity.status && (
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-xs",
                          statusColors[activity.status]
                        )}
                      >
                        {activity.status.replace('_', ' ')}
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {activity.description}
                  </p>
                  <div className="flex items-center mt-1 text-xs text-muted-foreground">
                    <span>
                      {formatDistanceToNow(activity.timestamp)}
                    </span>
                    {activity.user && activity.user.name !== 'System' && (
                      <>
                        <span className="mx-1">•</span>
                        <span>{activity.user.name}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}