'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  Home,
  FileText,
  BarChart3,
  Users,
  Settings,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
  Search,
  Bell,
  LogOut,
  Shield,
  Activity,
  AlertCircle,
  Sliders,
  Clock,
  Database,
  FileSearch,
  Plus,
  Tags,
  GitBranch,
  Zap,
  Sparkles
} from 'lucide-react'
import { useCurrentUser, useHasRole } from '@/stores/auth-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { signOut } from 'next-auth/react'

const navigation = [
  {
    name: 'Dashboard',
    href: '/',
    icon: Home,
    permission: null,
  },
  {
    name: 'Categories',
    href: '/categories',
    icon: Tags,
    permission: null,
  },
  {
    name: 'API Providers',
    href: '/providers',
    icon: Zap,
    permission: null,
  },
  {
    name: 'Pipeline',
    href: '/pipeline',
    icon: GitBranch,
    permission: null,
  },
  {
    name: 'New Request',
    href: '/requests/new',
    icon: Plus,
    permission: 'requests.create',
  },
  {
    name: 'Drug Requests',
    href: '/requests',
    icon: FileText,
    permission: 'requests.read',
  },
  {
    name: 'Processing Status',
    href: '/processing',
    icon: Clock,
    permission: 'requests.read',
  },
  {
    name: 'Analysis Results',
    href: '/results',
    icon: FileSearch,
    permission: 'analysis.read',
  },
  {
    name: 'Reports',
    href: '/reports',
    icon: BarChart3,
    permission: 'reports.read',
  },
  {
    name: 'Monitoring',
    href: '/monitoring',
    icon: Activity,
    permission: 'monitoring.read',
    roles: ['admin', 'analyst'] as const,
  },
  {
    name: 'Audit Trail',
    href: '/audit',
    icon: Shield,
    permission: 'audit.read',
    roles: ['admin', 'compliance_officer'] as const,
  },
  {
    name: 'Configuration',
    href: '/configuration',
    icon: Settings,
    permission: 'config.manage',
    roles: ['admin'] as const,
  },
  {
    name: 'Summary Config',
    href: '/summary-config',
    icon: Sparkles,
    permission: 'config.manage',
    roles: ['admin', 'analyst'] as const,
  },
  {
    name: 'Technology Scoring',
    href: '/technology-scoring',
    icon: BarChart3,
    permission: null,
  },
  {
    name: 'Scoring Config',
    href: '/scoring',
    icon: Sliders,
    permission: 'scoring.manage',
    roles: ['admin', 'analyst'] as const,
  },
  {
    name: 'Failures',
    href: '/failures',
    icon: AlertCircle,
    permission: 'failures.manage',
    roles: ['admin', 'analyst'] as const,
  },
  {
    name: 'Users',
    href: '/users',
    icon: Users,
    permission: 'users.read',
    roles: ['admin'] as const,
  },
  {
    name: 'Data Sources',
    href: '/sources',
    icon: Database,
    permission: 'sources.read',
  },
  {
    name: 'Help',
    href: '/help',
    icon: HelpCircle,
    permission: null,
  },
]

interface SidebarProps {
  collapsed?: boolean
  onToggle?: () => void
}

export function Sidebar({ collapsed = false, onToggle }: SidebarProps) {
  const pathname = usePathname()
  const currentUser = useCurrentUser()
  const [searchQuery, setSearchQuery] = useState('')

  // Filter navigation items based on user permissions
  const filteredNavigation = navigation.filter((item) => {
    // Check role-based access
    if (item.roles && currentUser) {
      return item.roles.includes(currentUser.role as any)
    }
    return true
  })

  return (
    <div className={cn(
      "flex flex-col h-full bg-card border-r transition-all duration-300",
      collapsed ? "w-16" : "w-64"
    )}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        {!collapsed && (
          <div className="flex items-center space-x-2">
            <div className="h-8 w-8 bg-primary rounded-lg flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-sm">C</span>
            </div>
            <div>
              <h2 className="font-semibold text-sm">CognitoAI</h2>
              <p className="text-xs text-muted-foreground">Engine</p>
            </div>
          </div>
        )}

        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className="h-8 w-8"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>

      {/* Search */}
      {!collapsed && (
        <div className="p-4 border-b">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 h-8"
            />
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
        {filteredNavigation.map((item) => {
          const isActive = pathname === item.href ||
            (item.href !== '/' && pathname.startsWith(item.href))

          return (
            <Link key={item.name} href={item.href}>
              <div className={cn(
                "flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent",
                collapsed && "justify-center"
              )}>
                <item.icon className="h-4 w-4 flex-shrink-0" />
                {!collapsed && <span>{item.name}</span>}
              </div>
            </Link>
          )
        })}
      </nav>

      {/* User section */}
      <div className="border-t p-2">
        {currentUser && (
          <div className={cn(
            "flex items-center space-x-3 px-3 py-2 rounded-md",
            collapsed ? "justify-center" : ""
          )}>
            <div className="h-8 w-8 bg-primary/10 rounded-full flex items-center justify-center">
              <span className="text-sm font-medium">
                {currentUser.name.charAt(0).toUpperCase()}
              </span>
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{currentUser.name}</p>
                <p className="text-xs text-muted-foreground truncate capitalize">
                  {currentUser.role.replace('_', ' ')}
                </p>
              </div>
            )}
          </div>
        )}

        {!collapsed && (
          <div className="mt-2 space-y-1">
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start text-muted-foreground hover:text-foreground"
              onClick={() => signOut()}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Sign Out
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

export function SidebarMobile({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="fixed left-0 top-0 h-full w-64 bg-background">
        <Sidebar />
      </div>
    </div>
  )
}