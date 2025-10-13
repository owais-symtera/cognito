/**
 * System Configuration Page
 * @module app/configuration/page
 * @since 1.0.0
 */

'use client'

import React from 'react'
import { useSession } from 'next-auth/react'
import { redirect } from 'next/navigation'
import { SystemConfigDashboard } from '@/components/configuration/SystemConfigDashboard'
import { Settings } from 'lucide-react'

/**
 * System Configuration Page - Admin dashboard for managing system settings
 */
export default function ConfigurationPage() {
  const { data: session, status } = useSession()

  // Redirect if not authenticated
  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!session) {
    redirect('/auth/login')
  }

  // Check if user has admin role
  const userRole = (session.user as any)?.role
  const hasAccess = userRole === 'admin'

  if (!hasAccess) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-8 text-center">
          <Settings className="h-12 w-12 text-red-600 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-red-800 mb-2">Access Denied</h2>
          <p className="text-red-600">
            You do not have permission to access system configuration.
            Please contact your system administrator.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center">
          <Settings className="h-8 w-8 mr-3 text-blue-600" />
          System Configuration
        </h1>
        <p className="text-gray-600 mt-2">
          Manage system settings, integrations, performance tuning, and security configurations
        </p>
      </div>

      <SystemConfigDashboard userRole={userRole} />
    </div>
  )
}