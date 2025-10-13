/**
 * Date utility functions for consistent date formatting across the application
 */

export function formatDistanceToNow(date: Date): string {
  const now = new Date()
  const diffInMs = now.getTime() - date.getTime()
  const diffInMinutes = Math.floor(diffInMs / (1000 * 60))
  const diffInHours = Math.floor(diffInMinutes / 60)
  const diffInDays = Math.floor(diffInHours / 24)

  if (diffInMinutes < 1) {
    return 'just now'
  } else if (diffInMinutes < 60) {
    return `${diffInMinutes} minute${diffInMinutes > 1 ? 's' : ''} ago`
  } else if (diffInHours < 24) {
    return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`
  } else if (diffInDays < 7) {
    return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`
  } else {
    return date.toLocaleDateString()
  }
}

export function formatDate(date: Date, format: 'short' | 'long' | 'time' = 'short'): string {
  switch (format) {
    case 'short':
      return date.toLocaleDateString()
    case 'long':
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    case 'time':
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
      })
    default:
      return date.toLocaleDateString()
  }
}