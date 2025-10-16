/**
 * System Configuration Dashboard Component
 * @module components/configuration/SystemConfigDashboard
 * @since 1.0.0
 */

'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import {
  Settings,
  Database,
  Shield,
  Cloud,
  Zap,
  Archive,
  Key,
  RefreshCw,
  Save,
  Upload,
  Download,
  AlertTriangle,
  CheckCircle,
  Info,
  History,
  FileText
} from 'lucide-react'
import { ConfigurationService } from '@/services/configuration.service'
import {
  SystemConfiguration,
  ConfigurationGroup,
  ConfigurationCategory,
  Environment,
  IntegrationConfig,
  PerformanceConfig,
  BackupConfig,
  SecurityConfig,
  ConfigDataType
} from '@/types/configuration'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'

interface SystemConfigDashboardProps {
  userRole: string
}

/**
 * Comprehensive system configuration management dashboard
 */
export const SystemConfigDashboard: React.FC<SystemConfigDashboardProps> = ({ userRole }) => {
  const { toast } = useToast()
  const configService = React.useMemo(() => ConfigurationService.getInstance(), [])

  const [activeTab, setActiveTab] = useState<ConfigurationCategory>(ConfigurationCategory.SYSTEM)
  const [selectedEnvironment, setSelectedEnvironment] = useState<Environment>(Environment.ALL)
  const [unsavedChanges, setUnsavedChanges] = useState<Map<string, any>>(new Map())
  const [showHistory, setShowHistory] = useState(false)
  const [selectedConfig, setSelectedConfig] = useState<SystemConfiguration | null>(null)

  // Fetch configurations by category
  const { data: configGroups, isLoading, refetch } = useQuery({
    queryKey: ['configurations', activeTab],
    queryFn: () => configService.getConfigurationsByCategory(activeTab)
  })

  // Fetch integrations
  const { data: integrations } = useQuery({
    queryKey: ['integrations'],
    queryFn: () => configService.getIntegrations(),
    enabled: activeTab === ConfigurationCategory.INTEGRATION
  })

  // Fetch performance configs
  const { data: performanceConfigs } = useQuery({
    queryKey: ['performance'],
    queryFn: () => configService.getPerformanceConfigs(),
    enabled: activeTab === ConfigurationCategory.PERFORMANCE
  })

  // Fetch backup configs
  const { data: backupConfigs } = useQuery({
    queryKey: ['backups'],
    queryFn: () => configService.getBackupConfigs(),
    enabled: activeTab === ConfigurationCategory.BACKUP
  })

  // Fetch security config
  const { data: securityConfig } = useQuery({
    queryKey: ['security'],
    queryFn: () => configService.getSecurityConfig(),
    enabled: activeTab === ConfigurationCategory.SECURITY
  })

  // Update configuration mutation
  const updateMutation = useMutation({
    mutationFn: ({ key, value, reason }: { key: string; value: any; reason?: string }) =>
      configService.updateConfiguration(key, value, reason),
    onSuccess: () => {
      toast({
        title: 'Configuration Updated',
        description: 'The configuration has been successfully updated.',
        variant: 'default'
      })
      refetch()
      setUnsavedChanges(new Map())
    },
    onError: (error: any) => {
      toast({
        title: 'Update Failed',
        description: error.message || 'Failed to update configuration',
        variant: 'destructive'
      })
    }
  })

  // Test integration mutation
  const testIntegrationMutation = useMutation({
    mutationFn: (integrationId: string) => configService.testIntegration(integrationId),
    onSuccess: (data) => {
      toast({
        title: data.success ? 'Connection Successful' : 'Connection Failed',
        description: data.message,
        variant: data.success ? 'default' : 'destructive'
      })
    }
  })

  // Trigger backup mutation
  const triggerBackupMutation = useMutation({
    mutationFn: (backupId: string) => configService.triggerBackup(backupId),
    onSuccess: (data) => {
      toast({
        title: 'Backup Triggered',
        description: `Backup job ${data.job_id} has been started`,
        variant: 'default'
      })
    }
  })

  /**
   * Handle configuration value change
   */
  const handleConfigChange = useCallback((key: string, value: any) => {
    setUnsavedChanges(prev => {
      const next = new Map(prev)
      next.set(key, value)
      return next
    })
  }, [])

  /**
   * Save all pending changes
   */
  const saveAllChanges = useCallback(async () => {
    const updates = Array.from(unsavedChanges.entries()).map(([key, value]) => ({
      key,
      value
    }))

    try {
      await configService.batchUpdateConfigurations(updates)
      toast({
        title: 'All Changes Saved',
        description: `Successfully updated ${updates.length} configuration(s)`,
        variant: 'default'
      })
      setUnsavedChanges(new Map())
      refetch()
    } catch (error: any) {
      toast({
        title: 'Save Failed',
        description: error.message,
        variant: 'destructive'
      })
    }
  }, [unsavedChanges, configService, toast, refetch])

  /**
   * Export configurations
   */
  const handleExport = useCallback(async () => {
    try {
      const blob = await configService.exportConfigurations(activeTab)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `config-${activeTab.toLowerCase()}-${new Date().toISOString().split('T')[0]}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (error: any) {
      toast({
        title: 'Export Failed',
        description: error.message,
        variant: 'destructive'
      })
    }
  }, [activeTab, configService, toast])

  /**
   * Import configurations
   */
  const handleImport = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      const result = await configService.importConfigurations(file)
      toast({
        title: 'Import Complete',
        description: `Imported: ${result.imported}, Skipped: ${result.skipped}`,
        variant: 'default'
      })
      refetch()
    } catch (error: any) {
      toast({
        title: 'Import Failed',
        description: error.message,
        variant: 'destructive'
      })
    }
  }, [configService, toast, refetch])

  /**
   * Get tab icon
   */
  const getTabIcon = (category: ConfigurationCategory) => {
    switch (category) {
      case ConfigurationCategory.SYSTEM:
        return <Settings className="h-4 w-4" />
      case ConfigurationCategory.PROCESSING:
        return <Zap className="h-4 w-4" />
      case ConfigurationCategory.SECURITY:
        return <Shield className="h-4 w-4" />
      case ConfigurationCategory.INTEGRATION:
        return <Cloud className="h-4 w-4" />
      case ConfigurationCategory.PERFORMANCE:
        return <Zap className="h-4 w-4" />
      case ConfigurationCategory.COMPLIANCE:
        return <FileText className="h-4 w-4" />
      case ConfigurationCategory.BACKUP:
        return <Archive className="h-4 w-4" />
      case ConfigurationCategory.PHARMACEUTICAL:
        return <Database className="h-4 w-4" />
      default:
        return <Settings className="h-4 w-4" />
    }
  }

  /**
   * Render configuration input based on data type
   */
  const renderConfigInput = (config: SystemConfiguration) => {
    const currentValue = unsavedChanges.get(config.key) ?? config.value
    const hasChange = unsavedChanges.has(config.key)

    switch (config.data_type) {
      case ConfigDataType.BOOLEAN:
        return (
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={currentValue}
              onChange={(e) => handleConfigChange(config.key, e.target.checked)}
              className="h-4 w-4"
              disabled={userRole !== 'admin'}
            />
            {hasChange && <Badge variant="outline" className="text-xs">Modified</Badge>}
          </div>
        )

      case ConfigDataType.NUMBER:
        return (
          <div className="flex items-center space-x-2">
            <Input
              type="number"
              value={currentValue}
              onChange={(e) => handleConfigChange(config.key, parseFloat(e.target.value))}
              className={`w-32 ${hasChange ? 'border-yellow-400' : ''}`}
              disabled={userRole !== 'admin'}
            />
            {hasChange && <Badge variant="outline" className="text-xs">Modified</Badge>}
          </div>
        )

      case ConfigDataType.JSON:
        return (
          <div className="space-y-2">
            <textarea
              value={JSON.stringify(currentValue, null, 2)}
              onChange={(e) => {
                try {
                  handleConfigChange(config.key, JSON.parse(e.target.value))
                } catch {}
              }}
              className={`w-full p-2 border rounded font-mono text-xs ${hasChange ? 'border-yellow-400' : ''}`}
              rows={4}
              disabled={userRole !== 'admin'}
            />
            {hasChange && <Badge variant="outline" className="text-xs">Modified</Badge>}
          </div>
        )

      case ConfigDataType.ENCRYPTED:
        return (
          <div className="flex items-center space-x-2">
            <Input
              type="password"
              value={currentValue}
              onChange={(e) => handleConfigChange(config.key, e.target.value)}
              className={`flex-1 ${hasChange ? 'border-yellow-400' : ''}`}
              disabled={userRole !== 'admin'}
            />
            {hasChange && <Badge variant="outline" className="text-xs">Modified</Badge>}
          </div>
        )

      default:
        return (
          <div className="flex items-center space-x-2">
            <Input
              type="text"
              value={currentValue}
              onChange={(e) => handleConfigChange(config.key, e.target.value)}
              className={`flex-1 ${hasChange ? 'border-yellow-400' : ''}`}
              disabled={userRole !== 'admin'}
            />
            {hasChange && <Badge variant="outline" className="text-xs">Modified</Badge>}
          </div>
        )
    }
  }

  /**
   * Render configuration group
   */
  const renderConfigGroup = (group: ConfigurationGroup) => {
    return (
      <Card key={group.category} className="mb-4">
        <CardHeader>
          <CardTitle className="text-lg flex items-center">
            {getTabIcon(group.category)}
            <span className="ml-2">{group.name}</span>
          </CardTitle>
          <p className="text-sm text-gray-600">{group.description}</p>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {group.configurations
              .filter(config => config.environment === selectedEnvironment || config.environment === Environment.ALL)
              .map(config => (
                <div key={config.key} className="border-b pb-4 last:border-0">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <Label className="font-medium">{config.key}</Label>
                        {config.is_required && (
                          <Badge variant="destructive" className="text-xs">Required</Badge>
                        )}
                        {config.is_sensitive && (
                          <Badge variant="secondary" className="text-xs">
                            <Key className="h-3 w-3 mr-1" />
                            Sensitive
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{config.description}</p>
                      {renderConfigInput(config)}
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setSelectedConfig(config)
                        setShowHistory(true)
                      }}
                    >
                      <History className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <select
            value={selectedEnvironment}
            onChange={(e) => setSelectedEnvironment(e.target.value as Environment)}
            className="p-2 border rounded"
          >
            {Object.values(Environment).map(env => (
              <option key={env} value={env}>{env}</option>
            ))}
          </select>

          {unsavedChanges.size > 0 && (
            <Badge variant="outline" className="px-3 py-1">
              <AlertTriangle className="h-3 w-3 mr-1" />
              {unsavedChanges.size} Unsaved Changes
            </Badge>
          )}
        </div>

        <div className="flex space-x-2">
          {userRole === 'admin' && unsavedChanges.size > 0 && (
            <Button onClick={saveAllChanges} variant="default">
              <Save className="h-4 w-4 mr-2" />
              Save All Changes
            </Button>
          )}

          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>

          <Button variant="outline" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>

          {userRole === 'admin' && (
            <label>
              <span className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2 cursor-pointer">
                <Upload className="h-4 w-4 mr-2" />
                Import
              </span>
              <input
                type="file"
                accept=".json"
                onChange={handleImport}
                className="hidden"
              />
            </label>
          )}
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex space-x-2 border-b">
        {Object.values(ConfigurationCategory).map(category => (
          <button
            key={category}
            onClick={() => setActiveTab(category)}
            className={`flex items-center space-x-2 px-4 py-2 border-b-2 transition-colors ${
              activeTab === category
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent hover:text-gray-700'
            }`}
          >
            {getTabIcon(category)}
            <span>{category.replace(/_/g, ' ')}</span>
          </button>
        ))}
      </div>

      {/* Configuration Content */}
      <div>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        ) : (
          <>
            {configGroups?.map(renderConfigGroup)}

            {/* Special handling for integrations */}
            {activeTab === ConfigurationCategory.INTEGRATION && integrations && (
              <Card>
                <CardHeader>
                  <CardTitle>External Integrations</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {integrations.map(integration => (
                      <div key={integration.id} className="flex items-center justify-between p-4 border rounded">
                        <div>
                          <h4 className="font-medium">{integration.name}</h4>
                          <p className="text-sm text-gray-600">{integration.type}</p>
                          {integration.endpoint && (
                            <p className="text-xs text-gray-500 mt-1">{integration.endpoint}</p>
                          )}
                        </div>
                        <div className="flex items-center space-x-2">
                          {integration.test_status === 'SUCCESS' ? (
                            <CheckCircle className="h-5 w-5 text-green-500" />
                          ) : integration.test_status === 'FAILED' ? (
                            <AlertTriangle className="h-5 w-5 text-red-500" />
                          ) : (
                            <Info className="h-5 w-5 text-gray-400" />
                          )}
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => testIntegrationMutation.mutate(integration.id)}
                            disabled={testIntegrationMutation.isPending}
                          >
                            Test Connection
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  )
}