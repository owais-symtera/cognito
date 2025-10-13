/**
 * Audit Trail Viewer Component
 * @module components/audit/AuditTrailViewer
 * @since 1.0.0
 */

'use client'

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { format } from 'date-fns'
import {
  Search,
  Download,
  Filter,
  Calendar,
  AlertTriangle,
  Shield,
  FileText,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Archive,
  Eye,
  Clock,
  User,
  Database,
  Lock
} from 'lucide-react'
import { AuditService } from '@/services/audit.service'
import { formatJSON } from '@/lib/json-formatter'
import {
  AuditEvent,
  AuditFilter,
  AuditEventType,
  AuditSeverity,
  ComplianceFramework,
  AuditExportOptions
} from '@/types/audit'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface AuditTrailViewerProps {
  userId?: string
  entityType?: string
  entityId?: string
  showExport?: boolean
  showArchive?: boolean
  complianceMode?: boolean
}

/**
 * Comprehensive audit trail viewer with filtering, search, and export
 */
export const AuditTrailViewer: React.FC<AuditTrailViewerProps> = ({
  userId,
  entityType,
  entityId,
  showExport = true,
  showArchive = true,
  complianceMode = false
}) => {
  const auditService = useMemo(() => AuditService.getInstance(), [])

  const [filters, setFilters] = useState<AuditFilter>({
    user_ids: userId ? [userId] : undefined,
    entity_types: entityType ? [entityType] : undefined,
    entity_ids: entityId ? [entityId] : undefined,
    page: 1,
    page_size: 50,
    sort_by: 'timestamp',
    sort_order: 'desc'
  })

  const [searchQuery, setSearchQuery] = useState('')
  const [selectedEvents, setSelectedEvents] = useState<Set<string>>(new Set())
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set())
  const [showFilters, setShowFilters] = useState(false)
  const [selectedFramework, setSelectedFramework] = useState<ComplianceFramework | null>(null)

  // Fetch audit events
  const {
    data: auditData,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['audit-events', filters],
    queryFn: () => auditService.getAuditEvents(filters),
    refetchInterval: 30000 // Refresh every 30 seconds
  })

  // Fetch audit statistics
  const { data: auditStats } = useQuery({
    queryKey: ['audit-stats', filters.start_date, filters.end_date],
    queryFn: () => auditService.getAuditStats({
      start_date: filters.start_date,
      end_date: filters.end_date
    }),
    refetchInterval: 60000
  })

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: (options: AuditExportOptions) => auditService.exportAuditEvents(options),
    onSuccess: (blob, variables) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit-export-${format(new Date(), 'yyyy-MM-dd-HHmmss')}.${variables.format.toLowerCase()}`
      a.click()
      URL.revokeObjectURL(url)
    }
  })

  // Archive mutation
  const archiveMutation = useMutation({
    mutationFn: () => auditService.archiveEvents(filters),
    onSuccess: () => {
      refetch()
    }
  })

  /**
   * Handle search
   */
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query)
    setFilters(prev => ({
      ...prev,
      search_query: query,
      page: 1
    }))
  }, [])

  /**
   * Handle filter change
   */
  const handleFilterChange = useCallback((key: keyof AuditFilter, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
      page: 1
    }))
  }, [])

  /**
   * Toggle event expansion
   */
  const toggleEventExpansion = useCallback((eventId: string) => {
    setExpandedEvents(prev => {
      const next = new Set(prev)
      if (next.has(eventId)) {
        next.delete(eventId)
      } else {
        next.add(eventId)
      }
      return next
    })
  }, [])

  /**
   * Get severity badge color
   */
  const getSeverityColor = (severity: AuditSeverity) => {
    switch (severity) {
      case AuditSeverity.CRITICAL:
        return 'bg-red-500'
      case AuditSeverity.HIGH:
        return 'bg-orange-500'
      case AuditSeverity.MEDIUM:
        return 'bg-yellow-500'
      case AuditSeverity.LOW:
        return 'bg-green-500'
      default:
        return 'bg-gray-500'
    }
  }

  /**
   * Get event type icon
   */
  const getEventIcon = (eventType: AuditEventType) => {
    if (eventType.startsWith('USER_')) return <User className="h-4 w-4" />
    if (eventType.startsWith('REQUEST_')) return <FileText className="h-4 w-4" />
    if (eventType.startsWith('DATA_')) return <Database className="h-4 w-4" />
    if (eventType.startsWith('SECURITY_') || eventType === 'COMPLIANCE_CHECK') return <Shield className="h-4 w-4" />
    if (eventType.startsWith('SYSTEM_')) return <Lock className="h-4 w-4" />
    return <Clock className="h-4 w-4" />
  }

  /**
   * Render audit event row
   */
  const renderEventRow = (event: AuditEvent) => {
    const isExpanded = expandedEvents.has(event.id)
    const isSelected = selectedEvents.has(event.id)

    return (
      <div
        key={event.id}
        className={`border rounded-lg p-4 mb-2 transition-colors ${
          isSelected ? 'bg-blue-50 border-blue-300' : 'hover:bg-gray-50'
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => toggleEventExpansion(event.id)}
              className="p-1 hover:bg-gray-200 rounded"
              aria-label={isExpanded ? 'Collapse' : 'Expand'}
            >
              {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>

            <input
              type="checkbox"
              checked={isSelected}
              onChange={(e) => {
                const next = new Set(selectedEvents)
                if (e.target.checked) {
                  next.add(event.id)
                } else {
                  next.delete(event.id)
                }
                setSelectedEvents(next)
              }}
              className="h-4 w-4"
              aria-label="Select event"
            />

            <div className="flex items-center space-x-2">
              {getEventIcon(event.event_type)}
              <Badge className={getSeverityColor(event.severity)}>
                {event.severity}
              </Badge>
            </div>

            <div className="flex-1">
              <div className="font-medium">{event.action}</div>
              <div className="text-sm text-gray-600">
                {event.description}
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-4 text-sm text-gray-500">
            {event.user_email && (
              <span className="flex items-center">
                <User className="h-3 w-3 mr-1" />
                {event.user_email}
              </span>
            )}
            <span className="flex items-center">
              <Clock className="h-3 w-3 mr-1" />
              {format(new Date(event.timestamp), 'yyyy-MM-dd HH:mm:ss')}
            </span>
            {event.ip_address && (
              <span className="text-xs">{event.ip_address}</span>
            )}
          </div>
        </div>

        {isExpanded && (
          <div className="mt-4 pl-8 space-y-3">
            {event.entity_type && (
              <div className="text-sm">
                <span className="font-medium">Entity:</span> {event.entity_type} ({event.entity_id})
              </div>
            )}

            {event.old_values && (
              <div className="text-sm">
                <span className="font-medium">Previous Values:</span>
                <pre className="mt-1 p-2 bg-gray-100 rounded text-xs overflow-x-auto whitespace-pre-wrap">
                  {formatJSON(event.old_values)}
                </pre>
              </div>
            )}

            {event.new_values && (
              <div className="text-sm">
                <span className="font-medium">New Values:</span>
                <pre className="mt-1 p-2 bg-gray-100 rounded text-xs overflow-x-auto whitespace-pre-wrap">
                  {formatJSON(event.new_values)}
                </pre>
              </div>
            )}

            {event.metadata && (
              <div className="text-sm">
                <span className="font-medium">Metadata:</span>
                <pre className="mt-1 p-2 bg-gray-100 rounded text-xs overflow-x-auto whitespace-pre-wrap">
                  {formatJSON(event.metadata)}
                </pre>
              </div>
            )}

            {event.compliance_frameworks && event.compliance_frameworks.length > 0 && (
              <div className="text-sm">
                <span className="font-medium">Compliance Frameworks:</span>
                <div className="mt-1 flex flex-wrap gap-1">
                  {event.compliance_frameworks.map(framework => (
                    <Badge key={framework} variant="outline">
                      {framework}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="text-sm text-gray-500">
              <span className="font-medium">Session ID:</span> {event.session_id}
              {event.correlation_id && (
                <>
                  {' | '}
                  <span className="font-medium">Correlation ID:</span> {event.correlation_id}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      {auditStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold">{auditStats.total_events}</div>
              <div className="text-sm text-gray-600">Total Events</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-orange-600">
                {auditStats.suspicious_activities}
              </div>
              <div className="text-sm text-gray-600">Suspicious Activities</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-red-600">
                {auditStats.compliance_violations}
              </div>
              <div className="text-sm text-gray-600">Compliance Violations</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold">
                {Object.keys(auditStats.events_by_user || {}).length}
              </div>
              <div className="text-sm text-gray-600">Active Users</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Controls */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center">
              <Shield className="h-5 w-5 mr-2" />
              Audit Trail
            </span>
            <div className="flex space-x-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => refetch()}
                disabled={isLoading}
              >
                <RefreshCw className={`h-4 w-4 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>

              {showExport && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    exportMutation.mutate({
                      format: 'CSV',
                      filters,
                      include_metadata: true,
                      compliance_report: complianceMode
                    })
                  }}
                  disabled={exportMutation.isPending}
                >
                  <Download className="h-4 w-4 mr-1" />
                  Export
                </Button>
              )}

              {showArchive && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => archiveMutation.mutate()}
                  disabled={archiveMutation.isPending}
                >
                  <Archive className="h-4 w-4 mr-1" />
                  Archive
                </Button>
              )}
            </div>
          </CardTitle>
        </CardHeader>

        <CardContent>
          {/* Search and Filters */}
          <div className="space-y-4 mb-6">
            <div className="flex space-x-2">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  type="text"
                  placeholder="Search audit events..."
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>

              <Button
                variant="outline"
                onClick={() => setShowFilters(!showFilters)}
              >
                <Filter className="h-4 w-4 mr-1" />
                Filters
              </Button>
            </div>

            {showFilters && (
              <div className="border rounded-lg p-4 space-y-3 bg-gray-50">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div>
                    <label className="text-sm font-medium">Event Type</label>
                    <select
                      className="w-full mt-1 p-2 border rounded"
                      onChange={(e) => handleFilterChange('event_types', e.target.value ? [e.target.value] : undefined)}
                    >
                      <option value="">All Types</option>
                      {Object.values(AuditEventType).map(type => (
                        <option key={type} value={type}>{type}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-sm font-medium">Severity</label>
                    <select
                      className="w-full mt-1 p-2 border rounded"
                      onChange={(e) => handleFilterChange('severities', e.target.value ? [e.target.value] : undefined)}
                    >
                      <option value="">All Severities</option>
                      {Object.values(AuditSeverity).map(severity => (
                        <option key={severity} value={severity}>{severity}</option>
                      ))}
                    </select>
                  </div>

                  {complianceMode && (
                    <div>
                      <label className="text-sm font-medium">Compliance Framework</label>
                      <select
                        className="w-full mt-1 p-2 border rounded"
                        value={selectedFramework || ''}
                        onChange={(e) => {
                          const framework = e.target.value as ComplianceFramework
                          setSelectedFramework(framework || null)
                          handleFilterChange('compliance_frameworks', framework ? [framework] : undefined)
                        }}
                      >
                        <option value="">All Frameworks</option>
                        {Object.values(ComplianceFramework).map(framework => (
                          <option key={framework} value={framework}>{framework}</option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm font-medium">Start Date</label>
                    <Input
                      type="datetime-local"
                      onChange={(e) => handleFilterChange('start_date', e.target.value ? new Date(e.target.value) : undefined)}
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium">End Date</label>
                    <Input
                      type="datetime-local"
                      onChange={(e) => handleFilterChange('end_date', e.target.value ? new Date(e.target.value) : undefined)}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Events List */}
          <div className="space-y-2">
            {isLoading && (
              <div className="text-center py-8">
                <RefreshCw className="h-8 w-8 animate-spin mx-auto text-gray-400" />
                <p className="mt-2 text-gray-600">Loading audit events...</p>
              </div>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-center">
                  <AlertTriangle className="h-5 w-5 text-red-600 mr-2" />
                  <span className="text-red-800">Failed to load audit events</span>
                </div>
              </div>
            )}

            {auditData?.events && auditData.events.length > 0 ? (
              <>
                {auditData.events.map(renderEventRow)}

                {/* Pagination */}
                <div className="flex items-center justify-between pt-4">
                  <div className="text-sm text-gray-600">
                    Showing {((filters.page || 1) - 1) * (filters.page_size || 50) + 1} to{' '}
                    {Math.min((filters.page || 1) * (filters.page_size || 50), auditData.total)} of{' '}
                    {auditData.total} events
                  </div>

                  <div className="flex space-x-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleFilterChange('page', (filters.page || 1) - 1)}
                      disabled={(filters.page || 1) <= 1}
                    >
                      Previous
                    </Button>

                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleFilterChange('page', (filters.page || 1) + 1)}
                      disabled={(filters.page || 1) * (filters.page_size || 50) >= auditData.total}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              </>
            ) : !isLoading && (
              <div className="text-center py-8 text-gray-600">
                No audit events found
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}