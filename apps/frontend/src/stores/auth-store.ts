/**
 * Authentication state management using Zustand
 * Manages user session, authentication status, and role-based permissions
 *
 * @module stores/auth
 * @since 1.0.0
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { AuthUser } from '@/lib/auth'

interface AuthState {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  lastActivity: Date | null
  sessionTimeout: number // minutes

  // Actions
  setUser: (user: AuthUser | null) => void
  setLoading: (loading: boolean) => void
  updateLastActivity: () => void
  checkSession: () => boolean
  clearSession: () => void
  hasRole: (role: AuthUser['role'] | AuthUser['role'][]) => boolean
  hasPermission: (permission: string) => boolean
}

// Role-based permissions mapping
const rolePermissions: Record<AuthUser['role'], string[]> = {
  admin: ['*'], // All permissions
  analyst: [
    'requests.create',
    'requests.read',
    'requests.update',
    'analysis.read',
    'analysis.create',
    'reports.generate',
    'reports.export',
    'monitoring.read',
    'failures.manage',
    'scoring.manage'
  ],
  researcher: [
    'requests.create',
    'requests.read',
    'requests.update',
    'analysis.read',
    'reports.generate',
    'reports.export'
  ],
  viewer: [
    'requests.read',
    'analysis.read',
    'reports.read'
  ],
  compliance_officer: [
    'requests.read',
    'analysis.read',
    'reports.read',
    'audit.read',
    'compliance.manage'
  ]
}

/**
 * Authentication store with session management and role-based access control
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      lastActivity: null,
      sessionTimeout: 30, // 30 minutes default

      setUser: (user) => {
        set({
          user,
          isAuthenticated: !!user,
          lastActivity: user ? new Date() : null
        })
      },

      setLoading: (loading) => {
        set({ isLoading: loading })
      },

      updateLastActivity: () => {
        const state = get()
        if (state.isAuthenticated) {
          set({ lastActivity: new Date() })
        }
      },

      checkSession: () => {
        const state = get()

        if (!state.isAuthenticated || !state.lastActivity) {
          return false
        }

        const now = new Date()
        const lastActivity = new Date(state.lastActivity)
        const diffMinutes = (now.getTime() - lastActivity.getTime()) / (1000 * 60)

        // Session expired
        if (diffMinutes > state.sessionTimeout) {
          get().clearSession()
          return false
        }

        return true
      },

      clearSession: () => {
        set({
          user: null,
          isAuthenticated: false,
          lastActivity: null
        })
      },

      hasRole: (role) => {
        const user = get().user
        if (!user) return false

        if (Array.isArray(role)) {
          return role.includes(user.role)
        }
        return user.role === role
      },

      hasPermission: (permission) => {
        const user = get().user
        if (!user) return false

        const userPermissions = rolePermissions[user.role] || []

        // Admin has all permissions
        if (userPermissions.includes('*')) {
          return true
        }

        // Check specific permission
        return userPermissions.includes(permission)
      }
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        lastActivity: state.lastActivity
      })
    }
  )
)

/**
 * Hook to check if user has required role
 */
export const useHasRole = (role: AuthUser['role'] | AuthUser['role'][]) => {
  return useAuthStore((state) => state.hasRole(role))
}

/**
 * Hook to check if user has required permission
 */
export const useHasPermission = (permission: string) => {
  return useAuthStore((state) => state.hasPermission(permission))
}

/**
 * Hook to get current user
 */
export const useCurrentUser = () => {
  return useAuthStore((state) => state.user)
}