/**
 * Audit Trail Page
 * @module app/audit/page
 * @since 1.0.0
 */

'use client'

import React from 'react'
import { useSession } from 'next-auth/react'
import { redirect } from 'next/navigation'
import { AuditTrailViewer } from '@/components/audit/AuditTrailViewer'
import { Shield } from 'lucide-react'

/**
 * Audit Trail Page - Comprehensive audit log viewer for compliance officers
 */
export default function AuditPage() {
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

  // Check if user has appropriate role (admin or compliance_officer)
  const userRole = (session.user as any)?.role
  const hasAccess = userRole === 'admin' || userRole === 'compliance_officer'

  if (!hasAccess) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-8 text-center">
          <Shield className="h-12 w-12 text-red-600 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-red-800 mb-2">Access Denied</h2>
          <p className="text-red-600">
            You do not have permission to view the audit trail.
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
          <Shield className="h-8 w-8 mr-3 text-blue-600" />
          Audit Trail & Compliance
        </h1>
        <p className="text-gray-600 mt-2">
          Monitor all system activities, track changes, and ensure regulatory compliance
        </p>
      </div>

      <AuditTrailViewer
        showExport={true}
        showArchive={userRole === 'admin'}
        complianceMode={true}
      />
    </div>
  )
}