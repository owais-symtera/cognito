/**
 * Configuration Service
 * @module services/configuration
 * @since 1.0.0
 */

import {
  SystemConfiguration,
  ConfigurationGroup,
  IntegrationConfig,
  PerformanceConfig,
  BackupConfig,
  SecurityConfig,
  ConfigurationChange,
  ConfigurationTemplate,
  ConfigurationCategory,
  Environment
} from '@/types/configuration'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Service for managing system configurations
 */
export class ConfigurationService {
  private static instance: ConfigurationService
  private baseUrl: string

  private constructor() {
    this.baseUrl = `${API_BASE_URL}/api/configuration`
  }

  /**
   * Get singleton instance
   */
  public static getInstance(): ConfigurationService {
    if (!ConfigurationService.instance) {
      ConfigurationService.instance = new ConfigurationService()
    }
    return ConfigurationService.instance
  }

  /**
   * Get all configurations by category
   */
  async getConfigurationsByCategory(category?: ConfigurationCategory): Promise<ConfigurationGroup[]> {
    const queryParams = category ? `?category=${category}` : ''

    const response = await fetch(`${this.baseUrl}/groups${queryParams}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch configurations: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get a specific configuration by key
   */
  async getConfiguration(key: string): Promise<SystemConfiguration> {
    const response = await fetch(`${this.baseUrl}/${key}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch configuration: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Update a configuration
   */
  async updateConfiguration(
    key: string,
    value: any,
    reason?: string
  ): Promise<SystemConfiguration> {
    const response = await fetch(`${this.baseUrl}/${key}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      },
      body: JSON.stringify({ value, reason })
    })

    if (!response.ok) {
      throw new Error(`Failed to update configuration: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Batch update configurations
   */
  async batchUpdateConfigurations(
    updates: Array<{ key: string; value: any }>
  ): Promise<SystemConfiguration[]> {
    const response = await fetch(`${this.baseUrl}/batch`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      },
      body: JSON.stringify({ updates })
    })

    if (!response.ok) {
      throw new Error(`Failed to batch update configurations: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get integration configurations
   */
  async getIntegrations(): Promise<IntegrationConfig[]> {
    const response = await fetch(`${this.baseUrl}/integrations`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch integrations: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Test integration connectivity
   */
  async testIntegration(integrationId: string): Promise<{
    success: boolean
    message: string
    latency?: number
  }> {
    const response = await fetch(`${this.baseUrl}/integrations/${integrationId}/test`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to test integration: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get performance configurations
   */
  async getPerformanceConfigs(): Promise<PerformanceConfig[]> {
    const response = await fetch(`${this.baseUrl}/performance`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch performance configs: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Optimize performance settings
   */
  async optimizePerformance(metricId: string): Promise<PerformanceConfig> {
    const response = await fetch(`${this.baseUrl}/performance/${metricId}/optimize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to optimize performance: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get backup configurations
   */
  async getBackupConfigs(): Promise<BackupConfig[]> {
    const response = await fetch(`${this.baseUrl}/backups`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch backup configs: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Trigger manual backup
   */
  async triggerBackup(backupId: string): Promise<{
    success: boolean
    job_id: string
  }> {
    const response = await fetch(`${this.baseUrl}/backups/${backupId}/trigger`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to trigger backup: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get security configuration
   */
  async getSecurityConfig(): Promise<SecurityConfig> {
    const response = await fetch(`${this.baseUrl}/security`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch security config: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Update security configuration
   */
  async updateSecurityConfig(config: Partial<SecurityConfig>): Promise<SecurityConfig> {
    const response = await fetch(`${this.baseUrl}/security`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      },
      body: JSON.stringify(config)
    })

    if (!response.ok) {
      throw new Error(`Failed to update security config: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get configuration change history
   */
  async getConfigurationHistory(key?: string): Promise<ConfigurationChange[]> {
    const queryParams = key ? `?key=${key}` : ''

    const response = await fetch(`${this.baseUrl}/history${queryParams}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch configuration history: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Rollback configuration change
   */
  async rollbackConfiguration(changeId: string): Promise<SystemConfiguration> {
    const response = await fetch(`${this.baseUrl}/history/${changeId}/rollback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to rollback configuration: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get configuration templates
   */
  async getTemplates(category?: ConfigurationCategory): Promise<ConfigurationTemplate[]> {
    const queryParams = category ? `?category=${category}` : ''

    const response = await fetch(`${this.baseUrl}/templates${queryParams}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch templates: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Apply configuration template
   */
  async applyTemplate(templateId: string, environment: Environment): Promise<SystemConfiguration[]> {
    const response = await fetch(`${this.baseUrl}/templates/${templateId}/apply`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAccessToken()}`
      },
      body: JSON.stringify({ environment })
    })

    if (!response.ok) {
      throw new Error(`Failed to apply template: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Export configurations
   */
  async exportConfigurations(category?: ConfigurationCategory): Promise<Blob> {
    const queryParams = category ? `?category=${category}` : ''

    const response = await fetch(`${this.baseUrl}/export${queryParams}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${this.getAccessToken()}`
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to export configurations: ${response.statusText}`)
    }

    return response.blob()
  }

  /**
   * Import configurations
   */
  async importConfigurations(file: File): Promise<{
    imported: number
    skipped: number
    errors: string[]
  }> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${this.baseUrl}/import`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.getAccessToken()}`
      },
      body: formData
    })

    if (!response.ok) {
      throw new Error(`Failed to import configurations: ${response.statusText}`)
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