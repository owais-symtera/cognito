'use client'

import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { useAuthStore } from '@/stores/auth-store'
import { AuthUser } from '@/lib/auth'
import { Loader2 } from 'lucide-react'

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRole?: AuthUser['role'] | AuthUser['role'][]
  requiredPermission?: string
  fallback?: React.ReactNode
}

export function ProtectedRoute({
  children,
  requiredRole,
  requiredPermission,
  fallback = <div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin" /></div>
}: ProtectedRouteProps) {
  const { data: session, status } = useSession()
  const router = useRouter()
  const { setUser, hasRole, hasPermission, checkSession } = useAuthStore()

  useEffect(() => {
    if (status === 'authenticated' && session?.user) {
      setUser(session.user as AuthUser)

      // Check if session is still valid
      if (!checkSession()) {
        router.push('/auth/login')
        return
      }
    }
  }, [session, status, setUser, checkSession, router])

  // Loading state
  if (status === 'loading') {
    return fallback
  }

  // Not authenticated
  if (status === 'unauthenticated') {
    router.push('/auth/login')
    return fallback
  }

  // Authenticated but no session user data
  if (!session?.user) {
    router.push('/auth/login')
    return fallback
  }

  // Check role requirements
  if (requiredRole && !hasRole(requiredRole)) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4">
          <h2 className="text-2xl font-bold text-destructive">Access Denied</h2>
          <p className="text-muted-foreground">
            You don't have the required permissions to access this page.
          </p>
          <button
            onClick={() => router.back()}
            className="text-primary hover:underline"
          >
            Go Back
          </button>
        </div>
      </div>
    )
  }

  // Check permission requirements
  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4">
          <h2 className="text-2xl font-bold text-destructive">Access Denied</h2>
          <p className="text-muted-foreground">
            You don't have the required permissions to access this feature.
          </p>
          <button
            onClick={() => router.back()}
            className="text-primary hover:underline"
          >
            Go Back
          </button>
        </div>
      </div>
    )
  }

  return <>{children}</>
}

/**
 * HOC for protecting pages with role/permission requirements
 */
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  options?: {
    requiredRole?: AuthUser['role'] | AuthUser['role'][]
    requiredPermission?: string
  }
) {
  return function AuthenticatedComponent(props: P) {
    return (
      <ProtectedRoute
        requiredRole={options?.requiredRole}
        requiredPermission={options?.requiredPermission}
      >
        <Component {...props} />
      </ProtectedRoute>
    )
  }
}