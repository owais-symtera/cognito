/**
 * Audit Trail Service
 * @module services/audit
 * @since 1.0.0
 */

import { AuditEvent, AuditFilter, AuditStats, AuditExportOptions, AuditRetentionPolicy } from '@/types/audit'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Service for managing audit trail operations
 */
export class AuditService {
  private static instance: AuditService
  private baseUrl: string

  private constructor() {
    this.baseUrl = `${API_BASE_URL}/api/audit`
  }

  /**
   * Get singleton instance
   */
  public static getInstance(): AuditService {
    if (!AuditService.instance) {
      AuditService.instance = new AuditService()
    }
    return AuditService.instance
  }

  /**
   * Fetch audit events with filters
   */
  async getAuditEvents(filters: AuditFilter): Promise<{
    events: AuditEvent[]
    total: number
    page: number
    page_size: number
  }> {
    const queryParams = new URLSearchParams()

    if (filters.event_types?.length) {
      queryParams.append('event_types', filters.event_types.join(','))
    }
    if (filters.severities?.length) {
      queryParams.append('severities', filters.severities.join(','))
    }
    if (filters.user_ids?.length) {
      queryParams.append('user_ids', filters.user_ids.join(','))
    }
    if (filters.start_date) {
      queryParams.append('start_date', filters.start_date.toISOString())
    }
    if (filters.end_date) {
      queryParams.append('end_date', filters.end_date.toISOString())
    }
    if (filters.search_query) {
      queryParams.append('search', filters.search_query)
    }
    if (filters.page) {
      queryParams.append('page', filters.page.toString())
    }
    if (filters.page_size) {
      queryParams.append('page_size', filters.page_size.toString())
    }
    if (filters.sort_by) {
      queryParams.append('sort_by', filters.sort_by)
    }
    if (filters.sort_order) {
      queryParams.append('sort_order', filters.sort_order)
    }

    const response = await fetch(`${this.baseUrl}/events?${queryParams}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch audit events: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get a specific audit event by ID
   */
  async getAuditEvent(eventId: string): Promise<AuditEvent> {
    const response = await fetch(`${this.baseUrl}/events/${eventId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch audit event: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get audit statistics
   */
  async getAuditStats(filters?: AuditFilter): Promise<AuditStats> {
    const queryParams = new URLSearchParams()

    if (filters?.start_date) {
      queryParams.append('start_date', filters.start_date.toISOString())
    }
    if (filters?.end_date) {
      queryParams.append('end_date', filters.end_date.toISOString())
    }

    const response = await fetch(`${this.baseUrl}/stats?${queryParams}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch audit stats: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Export audit events
   */
  async exportAuditEvents(options: AuditExportOptions): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/export`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      },
      body: JSON.stringify(options)
    })

    if (!response.ok) {
      throw new Error(`Failed to export audit events: ${response.statusText}`)
    }

    return response.blob()
  }

  /**
   * Get related audit events
   */
  async getRelatedEvents(eventId: string): Promise<AuditEvent[]> {
    const response = await fetch(`${this.baseUrl}/events/${eventId}/related`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch related events: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get retention policies
   */
  async getRetentionPolicies(): Promise<AuditRetentionPolicy[]> {
    const response = await fetch(`${this.baseUrl}/retention-policies`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch retention policies: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Create retention policy
   */
  async createRetentionPolicy(policy: Omit<AuditRetentionPolicy, 'id' | 'created_at' | 'updated_at'>): Promise<AuditRetentionPolicy> {
    const response = await fetch(`${this.baseUrl}/retention-policies`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      },
      body: JSON.stringify(policy)
    })

    if (!response.ok) {
      throw new Error(`Failed to create retention policy: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Archive audit events
   */
  async archiveEvents(filters: AuditFilter): Promise<{
    archived_count: number
    archive_location: string
  }> {
    const response = await fetch(`${this.baseUrl}/archive`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      },
      body: JSON.stringify(filters)
    })

    if (!response.ok) {
      throw new Error(`Failed to archive audit events: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Search audit events with advanced query
   */
  async searchEvents(query: string, options?: {
    fields?: string[]
    highlight?: boolean
    fuzzy?: boolean
  }): Promise<AuditEvent[]> {
    const response = await fetch(`${this.baseUrl}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      },
      body: JSON.stringify({
        query,
        ...options
      })
    })

    if (!response.ok) {
      throw new Error(`Failed to search audit events: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get compliance report
   */
  async getComplianceReport(framework: string, dateRange?: {
    start: Date
    end: Date
  }): Promise<any> {
    const queryParams = new URLSearchParams({
      framework
    })

    if (dateRange) {
      queryParams.append('start_date', dateRange.start.toISOString())
      queryParams.append('end_date', dateRange.end.toISOString())
    }

    const response = await fetch(`${this.baseUrl}/compliance-report?${queryParams}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch compliance report: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get access token from session
   */
  private getAccessToken(): string {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('access_token') || ''
    }
    return ''
  }
}