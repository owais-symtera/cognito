/**
 * Configuration Types for System Settings
 * @module types/configuration
 * @since 1.0.0
 */

export interface SystemConfiguration {
  id: string
  category: ConfigurationCategory
  key: string
  value: any
  description: string
  data_type: ConfigDataType
  is_sensitive: boolean
  is_required: boolean
  default_value?: any
  validation_rules?: ValidationRule[]
  environment: Environment
  last_modified: string
  modified_by: string
  version: number
}

export enum ConfigurationCategory {
  SYSTEM = 'SYSTEM',
  PROCESSING = 'PROCESSING',
  SECURITY = 'SECURITY',
  INTEGRATION = 'INTEGRATION',
  PERFORMANCE = 'PERFORMANCE',
  COMPLIANCE = 'COMPLIANCE',
  NOTIFICATION = 'NOTIFICATION',
  BACKUP = 'BACKUP',
  AI_MODELS = 'AI_MODELS',
  PHARMACEUTICAL = 'PHARMACEUTICAL'
}

export enum ConfigDataType {
  STRING = 'STRING',
  NUMBER = 'NUMBER',
  BOOLEAN = 'BOOLEAN',
  JSON = 'JSON',
  ENCRYPTED = 'ENCRYPTED',
  URL = 'URL',
  EMAIL = 'EMAIL',
  DATETIME = 'DATETIME'
}

export enum Environment {
  DEVELOPMENT = 'DEVELOPMENT',
  STAGING = 'STAGING',
  PRODUCTION = 'PRODUCTION',
  ALL = 'ALL'
}

export interface ValidationRule {
  type: 'min' | 'max' | 'pattern' | 'required' | 'custom'
  value?: any
  message: string
}

export interface ConfigurationGroup {
  category: ConfigurationCategory
  name: string
  description: string
  icon: string
  configurations: SystemConfiguration[]
  permissions_required: string[]
}

export interface IntegrationConfig {
  id: string
  name: string
  type: 'API' | 'DATABASE' | 'MESSAGING' | 'STORAGE'
  enabled: boolean
  endpoint?: string
  credentials?: Record<string, any>
  test_status?: 'SUCCESS' | 'FAILED' | 'PENDING'
  last_tested?: string
  configuration: Record<string, any>
}

export interface PerformanceConfig {
  id: string
  metric_name: string
  current_value: number
  optimal_value: number
  threshold_warning: number
  threshold_critical: number
  unit: string
  auto_optimize: boolean
}

export interface BackupConfig {
  id: string
  name: string
  type: 'FULL' | 'INCREMENTAL' | 'DIFFERENTIAL'
  schedule: string // Cron expression
  retention_days: number
  destination: string
  enabled: boolean
  last_backup?: string
  next_backup?: string
  status: 'ACTIVE' | 'PAUSED' | 'FAILED'
}

export interface SecurityConfig {
  password_policy: {
    min_length: number
    require_uppercase: boolean
    require_lowercase: boolean
    require_numbers: boolean
    require_special_chars: boolean
    expiry_days: number
  }
  session_config: {
    timeout_minutes: number
    max_concurrent_sessions: number
    require_mfa: boolean
  }
  api_security: {
    rate_limit_per_minute: number
    require_api_key: boolean
    allowed_origins: string[]
  }
}

export interface ConfigurationChange {
  id: string
  configuration_id: string
  old_value: any
  new_value: any
  changed_by: string
  changed_at: string
  reason?: string
  approved_by?: string
  rollback_available: boolean
}

export interface ConfigurationTemplate {
  id: string
  name: string
  description: string
  category: ConfigurationCategory
  configurations: Partial<SystemConfiguration>[]
  is_default: boolean
  created_at: string
}