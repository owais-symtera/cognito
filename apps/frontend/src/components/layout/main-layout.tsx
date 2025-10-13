'use client'

import { useState } from 'react'
import { Sidebar, SidebarMobile } from './sidebar'
import { Header } from './header'
import { cn } from '@/lib/utils'

interface MainLayoutProps {
  children: React.ReactNode
}

export function MainLayout({ children }: MainLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="h-screen flex overflow-hidden">
      {/* Desktop Sidebar */}
      <div className="hidden lg:flex">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
      </div>

      {/* Mobile Sidebar */}
      <SidebarMobile
        open={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header
          onMenuClick={() => setMobileMenuOpen(true)}
          showMenuButton={true}
        />

        <main className="flex-1 overflow-y-auto bg-background p-6">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}