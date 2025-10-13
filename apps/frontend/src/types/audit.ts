/**
 * Audit Trail Types for CognitoAI-Engine
 * @module types/audit
 * @since 1.0.0
 */

export enum AuditEventType {
  // User Activity
  USER_LOGIN = 'USER_LOGIN',
  USER_LOGOUT = 'USER_LOGOUT',
  USER_CREATED = 'USER_CREATED',
  USER_UPDATED = 'USER_UPDATED',
  USER_DELETED = 'USER_DELETED',

  // Drug Request Activity
  REQUEST_CREATED = 'REQUEST_CREATED',
  REQUEST_UPDATED = 'REQUEST_UPDATED',
  REQUEST_DELETED = 'REQUEST_DELETED',
  REQUEST_PROCESSED = 'REQUEST_PROCESSED',
  REQUEST_FAILED = 'REQUEST_FAILED',

  // Data Access
  DATA_VIEWED = 'DATA_VIEWED',
  DATA_EXPORTED = 'DATA_EXPORTED',
  DATA_MODIFIED = 'DATA_MODIFIED',

  // System Events
  SYSTEM_CONFIG_CHANGED = 'SYSTEM_CONFIG_CHANGED',
  SECURITY_EVENT = 'SECURITY_EVENT',
  COMPLIANCE_CHECK = 'COMPLIANCE_CHECK',

  // Category Processing
  CATEGORY_PROCESSING_STARTED = 'CATEGORY_PROCESSING_STARTED',
  CATEGORY_PROCESSING_COMPLETED = 'CATEGORY_PROCESSING_COMPLETED',
  CATEGORY_PROCESSING_FAILED = 'CATEGORY_PROCESSING_FAILED',

  // Source Management
  SOURCE_VERIFIED = 'SOURCE_VERIFIED',
  SOURCE_CONFLICT_DETECTED = 'SOURCE_CONFLICT_DETECTED',
  SOURCE_CONFLICT_RESOLVED = 'SOURCE_CONFLICT_RESOLVED'
}

export enum AuditSeverity {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL'
}

export enum ComplianceFramework {
  FDA_21_CFR_11 = 'FDA_21_CFR_11',
  GDPR = 'GDPR',
  HIPAA = 'HIPAA',
  SOX = 'SOX',
  ISO_27001 = 'ISO_27001',
  GxP = 'GxP'
}

export interface AuditEvent {
  id: string
  event_type: AuditEventType
  severity: AuditSeverity
  user_id?: string
  user_email?: string
  user_role?: string
  entity_type?: string
  entity_id?: string
  action: string
  description: string
  old_values?: Record<string, any>
  new_values?: Record<string, any>
  ip_address?: string
  user_agent?: string
  session_id?: string
  correlation_id?: string
  compliance_frameworks?: ComplianceFramework[]
  metadata?: Record<string, any>
  timestamp: string
  created_at: string
}

export interface AuditFilter {
  event_types?: AuditEventType[]
  severities?: AuditSeverity[]
  user_ids?: string[]
  entity_types?: string[]
  entity_ids?: string[]
  start_date?: Date
  end_date?: Date
  search_query?: string
  compliance_frameworks?: ComplianceFramework[]
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface AuditStats {
  total_events: number
  events_by_type: Record<AuditEventType, number>
  events_by_severity: Record<AuditSeverity, number>
  events_by_user: Record<string, number>
  events_by_hour: Array<{
    hour: string
    count: number
  }>
  suspicious_activities: number
  compliance_violations: number
}

export interface AuditExportOptions {
  format: 'CSV' | 'JSON' | 'PDF'
  filters: AuditFilter
  include_metadata?: boolean
  compliance_report?: boolean
  date_range?: {
    start: Date
    end: Date
  }
}

export interface AuditRetentionPolicy {
  id: string
  name: string
  description: string
  retention_days: number
  event_types?: AuditEventType[]
  compliance_frameworks?: ComplianceFramework[]
  archive_location?: string
  auto_archive: boolean
  auto_delete: boolean
  created_at: string
  updated_at: string
}