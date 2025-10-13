'use client'

import Link from 'next/link'
import { Plus, Upload, BarChart3, FileText, Users, Settings } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useHasPermission } from '@/stores/auth-store'

interface QuickActionProps {
  title: string
  description: string
  href: string
  icon: React.ReactNode
  permission?: string
}

function QuickAction({ title, description, href, icon, permission }: QuickActionProps) {
  const hasPermission = useHasPermission(permission || '')

  if (permission && !hasPermission) {
    return null
  }

  return (
    <Link href={href}>
      <Card className="h-full hover:shadow-md transition-shadow cursor-pointer group">
        <CardContent className="p-6">
          <div className="flex items-center space-x-4">
            <div className="p-2 bg-primary/10 rounded-lg group-hover:bg-primary/20 transition-colors">
              {icon}
            </div>
            <div className="flex-1">
              <h3 className="font-medium text-sm">{title}</h3>
              <p className="text-xs text-muted-foreground">{description}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}

export function QuickActions() {
  const actions = [
    {
      title: 'New Request',
      description: 'Submit pharmaceutical analysis request',
      href: '/requests/new',
      icon: <Plus className="h-5 w-5 text-primary" />,
      permission: 'requests.create',
    },
    {
      title: 'Upload Documents',
      description: 'Upload files for analysis',
      href: '/upload',
      icon: <Upload className="h-5 w-5 text-primary" />,
      permission: 'requests.create',
    },
    {
      title: 'View Analytics',
      description: 'Review analysis results',
      href: '/analysis',
      icon: <BarChart3 className="h-5 w-5 text-primary" />,
      permission: 'analysis.read',
    },
    {
      title: 'Generate Report',
      description: 'Create compliance reports',
      href: '/reports/new',
      icon: <FileText className="h-5 w-5 text-primary" />,
      permission: 'reports.generate',
    },
    {
      title: 'Manage Users',
      description: 'User administration',
      href: '/users',
      icon: <Users className="h-5 w-5 text-primary" />,
      permission: 'users.manage',
    },
    {
      title: 'System Settings',
      description: 'Configure application',
      href: '/settings',
      icon: <Settings className="h-5 w-5 text-primary" />,
    },
  ]

  // Filter actions based on permissions
  const availableActions = actions.filter(action => {
    if (!action.permission) return true
    return useHasPermission(action.permission)
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 md:grid-cols-2">
          {availableActions.map((action) => (
            <QuickAction
              key={action.href}
              title={action.title}
              description={action.description}
              href={action.href}
              icon={action.icon}
              permission={action.permission}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}