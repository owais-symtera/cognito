/**
 * NextAuth.js type extensions for CognitoAI-Engine
 * Extends the default NextAuth types to include custom properties
 */

import NextAuth from 'next-auth'

declare module 'next-auth' {
  /**
   * Extends the built-in session.user types
   */
  interface User {
    id: string
    email: string
    name: string
    role: 'admin' | 'analyst' | 'researcher' | 'viewer' | 'compliance_officer'
    requiresMFA?: boolean
    lastLogin?: Date
  }

  /**
   * Extends the built-in session type to include accessToken
   */
  interface Session {
    accessToken?: string
    user: User
  }
}

declare module 'next-auth/jwt' {
  /**
   * Extends the built-in JWT type
   */
  interface JWT {
    id: string
    email: string
    name: string
    role: 'admin' | 'analyst' | 'researcher' | 'viewer' | 'compliance_officer'
    accessToken?: string
    refreshToken?: string
    accessTokenExpires?: number
  }
}