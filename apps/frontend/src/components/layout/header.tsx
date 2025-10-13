'use client'

import { useState } from 'react'
import { Bell, Menu, Search, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ThemeToggle } from '@/components/theme-toggle'
import { useCurrentUser } from '@/stores/auth-store'
import { signOut } from 'next-auth/react'
import Link from 'next/link'

interface HeaderProps {
  onMenuClick?: () => void
  showMenuButton?: boolean
}

export function Header({ onMenuClick, showMenuButton = false }: HeaderProps) {
  const currentUser = useCurrentUser()
  const [searchQuery, setSearchQuery] = useState('')

  return (
    <header className="flex items-center justify-between px-6 py-4 bg-background border-b">
      <div className="flex items-center space-x-4">
        {showMenuButton && (
          <Button variant="ghost" size="icon" onClick={onMenuClick}>
            <Menu className="h-5 w-5" />
          </Button>
        )}

        {/* Global Search */}
        <div className="hidden md:flex items-center space-x-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search requests, analysis, reports..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 w-96"
            />
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* Mobile Search */}
        <Button variant="ghost" size="icon" className="md:hidden">
          <Search className="h-5 w-5" />
        </Button>

        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5" />
              <span className="absolute top-0 right-0 h-2 w-2 bg-red-500 rounded-full"></span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel>Notifications</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <div className="p-2">
              <div className="space-y-2">
                <div className="flex items-start space-x-3 p-2 rounded-md hover:bg-accent">
                  <div className="h-2 w-2 bg-blue-500 rounded-full mt-2"></div>
                  <div className="flex-1 space-y-1">
                    <p className="text-sm font-medium">Analysis Complete</p>
                    <p className="text-xs text-muted-foreground">
                      Your pharmaceutical analysis for Request #1234 is ready for review.
                    </p>
                    <p className="text-xs text-muted-foreground">5 minutes ago</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3 p-2 rounded-md hover:bg-accent">
                  <div className="h-2 w-2 bg-green-500 rounded-full mt-2"></div>
                  <div className="flex-1 space-y-1">
                    <p className="text-sm font-medium">Report Generated</p>
                    <p className="text-xs text-muted-foreground">
                      Monthly compliance report has been generated successfully.
                    </p>
                    <p className="text-xs text-muted-foreground">1 hour ago</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3 p-2 rounded-md hover:bg-accent">
                  <div className="h-2 w-2 bg-yellow-500 rounded-full mt-2"></div>
                  <div className="flex-1 space-y-1">
                    <p className="text-sm font-medium">System Maintenance</p>
                    <p className="text-xs text-muted-foreground">
                      Scheduled maintenance will occur tonight from 2-4 AM.
                    </p>
                    <p className="text-xs text-muted-foreground">3 hours ago</p>
                  </div>
                </div>
              </div>
              <DropdownMenuSeparator className="my-2" />
              <Link href="/notifications">
                <Button variant="ghost" size="sm" className="w-full">
                  View All Notifications
                </Button>
              </Link>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Theme Toggle */}
        <ThemeToggle />

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-9 w-9 rounded-full">
              {currentUser ? (
                <div className="h-8 w-8 bg-primary rounded-full flex items-center justify-center">
                  <span className="text-sm font-medium text-primary-foreground">
                    {currentUser.name.charAt(0).toUpperCase()}
                  </span>
                </div>
              ) : (
                <User className="h-5 w-5" />
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {currentUser && (
              <>
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium">{currentUser.name}</p>
                    <p className="text-xs text-muted-foreground">{currentUser.email}</p>
                    <p className="text-xs text-muted-foreground capitalize">
                      {currentUser.role.replace('_', ' ')}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
              </>
            )}
            <DropdownMenuItem asChild>
              <Link href="/profile">Profile</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/settings">Settings</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/help">Help & Support</Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => signOut()}
              className="text-red-600 focus:text-red-600"
            >
              Sign Out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}