import './globals.css'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Providers } from '@/components/providers'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'CognitoAI Engine',
  description: 'Pharmaceutical Intelligence Processing Platform with Source Tracking',
  keywords: 'pharmaceutical, intelligence, drug analysis, regulatory compliance',
}

/**
 * Root layout component for the CognitoAI Engine application.
 *
 * Provides the base HTML structure and global styling for all pages
 * in the pharmaceutical intelligence platform.
 *
 * @param children - Child components to render within the layout
 * @returns JSX element containing the root application structure
 *
 * @example
 * ```tsx
 * // Automatically applied to all pages in the app directory
 * export default function Page() {
 *   return <div>Page content</div>
 * }
 * ```
 *
 * @since 1.0.0
 * @version 1.0.0
 * @author CognitoAI Development Team
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}