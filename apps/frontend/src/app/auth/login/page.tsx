'use client'

import { signIn } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

export default function LoginPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    const formData = new FormData(e.currentTarget)
    const email = formData.get('email') as string
    const password = formData.get('password') as string

    try {
      const result = await signIn('credentials', {
        email,
        password,
        redirect: false,
        callbackUrl: '/'
      })

      console.log('SignIn result:', result)

      if (result?.error) {
        setError(result.error)
        setIsLoading(false)
      } else if (result?.ok) {
        // Successful sign in
        router.push('/')
        router.refresh()
      }
    } catch (error) {
      console.error('SignIn error:', error)
      setError('An unexpected error occurred')
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-gray-50 to-white p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-blue-600">CognitoAI Engine</h1>
          <p className="text-gray-600 mt-2">Pharmaceutical Intelligence Platform</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Sign In</h2>
            <p className="text-gray-600">Enter your credentials to access CognitoAI Engine</p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              defaultValue="admin@cognitoai.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter your email"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              defaultValue="admin123"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-8 text-center">
          <p className="text-sm text-gray-600">
            Need help accessing your account?{' '}
            <a href="#" className="text-blue-600 hover:underline">
              Contact IT Support
            </a>
          </p>
        </div>

        <div className="mt-8 pt-4 border-t border-gray-200">
          <p className="text-xs text-gray-500 text-center">
            By signing in, you agree to our{' '}
            <a href="#" className="text-blue-600 hover:underline">Terms of Service</a>
            {' '}and{' '}
            <a href="#" className="text-blue-600 hover:underline">Privacy Policy</a>
          </p>
        </div>

        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-800">
            <strong>Test Credentials:</strong><br/>
            Email: admin@cognitoai.com<br/>
            Password: admin123
          </p>
        </div>
      </div>
    </div>
  )
}