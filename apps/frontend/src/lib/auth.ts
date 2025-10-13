/**
 * NextAuth.js authentication configuration for CognitoAI-Engine
 * Provides JWT-based authentication with role-based access control
 *
 * @module auth
 * @since 1.0.0
 */

import { NextAuthOptions } from 'next-auth'
import CredentialsProvider from 'next-auth/providers/credentials'
import { JWT } from 'next-auth/jwt'
import { Session, User } from 'next-auth'

export interface AuthUser extends User {
  id: string
  email: string
  name: string
  role: 'admin' | 'analyst' | 'researcher' | 'viewer' | 'compliance_officer'
  requiresMFA?: boolean
  lastLogin?: Date
}

/**
 * NextAuth configuration with credentials provider and JWT strategy
 */
export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'credentials',
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
        mfaCode: { label: "MFA Code", type: "text", optional: true }
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null
        }

        try {
          // Call backend auth endpoint with JSON data
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
          const response = await fetch(`${apiUrl}/api/v1/auth/signin`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password
            }),
          })

          if (!response.ok) {
            console.error('Auth failed:', response.status)
            return null
          }

          const data = await response.json()

          // Ensure we have the required user data
          if (!data.user || !data.user.id) {
            console.error('Invalid response format')
            return null
          }

          // Return user object for JWT - NextAuth expects this exact format
          const user = {
            id: data.user.id,
            email: data.user.email,
            name: data.user.name || data.user.email,
            role: data.user.role || 'user',
            accessToken: data.access_token,
            refreshToken: data.refresh_token || null,
            requiresMFA: data.user.requires_mfa || false
          }

          console.log('Auth successful for:', user.email)
          return user
        } catch (error) {
          console.error('Auth error:', error)
          return null
        }
      }
    })
  ],

  session: {
    strategy: 'jwt',
    maxAge: 30 * 60, // 30 minutes
    updateAge: 5 * 60, // Update session every 5 minutes
  },

  jwt: {
    secret: process.env.NEXTAUTH_SECRET,
    maxAge: 30 * 60, // 30 minutes
  },

  pages: {
    signIn: '/auth/login',
    signOut: '/auth/logout',
    error: '/auth/error',
    verifyRequest: '/auth/verify',
    newUser: '/auth/register'
  },

  callbacks: {
    async jwt({ token, user, account, trigger }) {
      // Initial sign in
      if (user && account) {
        return {
          ...token,
          id: user.id,
          email: user.email,
          name: user.name,
          role: (user as AuthUser).role,
          accessToken: (user as any).accessToken,
          refreshToken: (user as any).refreshToken,
          accessTokenExpires: Date.now() + 30 * 60 * 1000, // 30 minutes
        }
      }

      // Return previous token if access token not expired
      if (Date.now() < (token.accessTokenExpires as number)) {
        return token
      }

      // Access token expired, refresh it
      return await refreshAccessToken(token)
    },

    async session({ session, token }) {
      // Send properties to the client
      if (session.user) {
        session.user = {
          ...session.user,
          id: token.id as string,
          email: token.email as string,
          name: token.name as string,
          role: token.role as AuthUser['role'],
        } as AuthUser

        // Add access token for API calls
        (session as any).accessToken = token.accessToken
      }
      return session
    },

    async redirect({ url, baseUrl }) {
      // Redirect to dashboard after login
      if (url === '/auth/login') {
        return '/'
      }
      // Allow relative callbacks
      if (url.startsWith('/')) {
        return `${baseUrl}${url}`
      }
      // Allow callbacks on the same origin
      if (new URL(url).origin === baseUrl) {
        return url
      }
      return baseUrl
    }
  },

  events: {
    async signIn({ user, account }) {
      // Log successful sign in for audit
      console.log(`User ${user.email} signed in at ${new Date().toISOString()}`)
    },
    async signOut({ token }) {
      // Clear server-side session
      if (token?.refreshToken) {
        try {
          await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/logout`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token.accessToken}`,
            },
          })
        } catch (error) {
          console.error('Logout error:', error)
        }
      }
    }
  },

  debug: process.env.NODE_ENV === 'development',
}

/**
 * Refreshes expired access token using refresh token
 */
async function refreshAccessToken(token: JWT) {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: token.refreshToken,
      }),
    })

    if (!response.ok) {
      throw new Error('Failed to refresh token')
    }

    const refreshed = await response.json()

    return {
      ...token,
      accessToken: refreshed.access_token,
      accessTokenExpires: Date.now() + 30 * 60 * 1000,
      refreshToken: refreshed.refresh_token ?? token.refreshToken,
    }
  } catch (error) {
    console.error('Token refresh error:', error)
    return {
      ...token,
      error: 'RefreshAccessTokenError',
    }
  }
}