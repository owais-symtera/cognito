'use client'

import { useState } from 'react'
import { MainLayout } from '@/components/layout/main-layout'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Settings,
  Power,
  Zap,
  AlertCircle,
  CheckCircle,
  TestTube,
  Save,
  RotateCcw,
  Key,
  Thermometer,
  Info,
  Plus,
  Trash2,
  Edit2,
  Activity
} from 'lucide-react'

interface TemperatureConfig {
  id: string
  value: number
  enabled: boolean
  label: string
}

interface ProviderConfig {
  id: string
  name: string
  enabled: boolean
  temperatures?: TemperatureConfig[]
  temperature?: number  // Old format support
  model?: string
  has_api_key?: boolean
  features?: string[]
  lastUpdated?: string
}

const PROVIDER_LOGOS = {
  openai: '🤖',
  claude: '🧠',
  gemini: '💎',
  grok: '🚀',
  perplexity: '🔍',
  tavily: '📊'
}

const PROVIDER_DESCRIPTIONS = {
  openai: 'Advanced language models for comprehensive drug analysis',
  claude: 'Sophisticated AI for clinical and regulatory insights',
  gemini: 'Google\'s multimodal AI for medical literature analysis',
  grok: 'Real-world evidence and usage pattern analysis',
  perplexity: 'Latest research and clinical trial aggregation',
  tavily: 'Regulatory updates and market analysis'
}

// Helper function to normalize provider data
function normalizeProvider(provider: any): ProviderConfig {
  // If provider already has temperatures array, return as is
  if (provider.temperatures && Array.isArray(provider.temperatures)) {
    return provider
  }

  // Convert old format to new format
  return {
    ...provider,
    temperatures: [{
      id: 'default',
      value: provider.temperature || 0.7,
      enabled: true,
      label: `Default (${(provider.temperature || 0.7).toFixed(1)})`
    }]
  }
}

export default function ProvidersPage() {
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null)
  const [addTempDialog, setAddTempDialog] = useState<{open: boolean, providerId?: string}>({open: false})
  const [newTemp, setNewTemp] = useState({ value: 0.5, label: '', enabled: true })
  const [editProvider, setEditProvider] = useState<ProviderConfig | null>(null)
  const [apiKeyDialog, setApiKeyDialog] = useState<{open: boolean, provider?: ProviderConfig}>({open: false})
  const [apiKey, setApiKey] = useState('')
  const queryClient = useQueryClient()

  // Fetch providers
  const { data: rawProviders = [], isLoading, error } = useQuery<ProviderConfig[]>({
    queryKey: ['providers'],
    queryFn: async () => {
      const response = await fetch('http://localhost:8001/api/v1/providers')
      if (!response.ok) throw new Error('Failed to fetch providers')
      const data = await response.json()
      // Normalize all providers to ensure they have temperatures array
      return data.map(normalizeProvider)
    }
  })

  // Ensure all providers have temperatures array
  const providers = rawProviders.map(normalizeProvider)

  // Update provider mutation
  const updateMutation = useMutation({
    mutationFn: async ({ id, ...data }: Partial<ProviderConfig> & {id: string}) => {
      const response = await fetch(`http://localhost:8001/api/v1/providers/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      if (!response.ok) throw new Error('Failed to update provider')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] })
    }
  })

  // Add temperature mutation
  const addTempMutation = useMutation({
    mutationFn: async ({ providerId, ...data }: { providerId: string, value: number, label: string, enabled: boolean }) => {
      const response = await fetch(`http://localhost:8001/api/v1/providers/${providerId}/temperatures`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      if (!response.ok) throw new Error('Failed to add temperature')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] })
      setAddTempDialog({open: false})
      setNewTemp({ value: 0.5, label: '', enabled: true })
    }
  })

  // Remove temperature mutation
  const removeTempMutation = useMutation({
    mutationFn: async ({ providerId, tempId }: { providerId: string, tempId: string }) => {
      const response = await fetch(`http://localhost:8001/api/v1/providers/${providerId}/temperatures/${tempId}`, {
        method: 'DELETE'
      })
      if (!response.ok) throw new Error('Failed to remove temperature')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] })
    }
  })

  // Test provider mutation
  const testMutation = useMutation({
    mutationFn: async (providerId: string) => {
      const response = await fetch(`http://localhost:8001/api/v1/providers/test/${providerId}`, {
        method: 'POST'
      })
      if (!response.ok) throw new Error('Failed to test provider')
      return response.json()
    }
  })

  // Fetch provider stats
  const { data: stats } = useQuery({
    queryKey: ['provider-stats'],
    queryFn: async () => {
      const response = await fetch('http://localhost:8001/api/v1/providers/stats/summary')
      if (!response.ok) throw new Error('Failed to fetch provider stats')
      return response.json()
    }
  })

  const handleToggleProvider = async (provider: ProviderConfig) => {
    await updateMutation.mutateAsync({
      id: provider.id,
      enabled: !provider.enabled
    })
  }

  const handleToggleTemperature = async (provider: ProviderConfig, tempId: string) => {
    const temps = provider.temperatures || []
    const updatedTemps = temps.map(t =>
      t.id === tempId ? { ...t, enabled: !t.enabled } : t
    )
    await updateMutation.mutateAsync({
      id: provider.id,
      temperatures: updatedTemps
    })
  }

  const handleAddTemperature = async () => {
    if (!addTempDialog.providerId || !newTemp.label) return

    await addTempMutation.mutateAsync({
      providerId: addTempDialog.providerId,
      ...newTemp
    })
  }

  const handleRemoveTemperature = async (providerId: string, tempId: string) => {
    if (confirm('Are you sure you want to remove this temperature setting?')) {
      await removeTempMutation.mutateAsync({ providerId, tempId })
    }
  }

  // Calculate total active configurations (enabled providers × enabled temperatures)
  const totalActiveConfigs = providers.reduce((acc, p) => {
    if (!p.enabled) return acc
    const temps = p.temperatures || []
    return acc + temps.filter(t => t.enabled).length
  }, 0)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">Multi-Temperature API Configuration</h1>
            <p className="text-muted-foreground">
              Configure multiple temperature settings per API for comprehensive data collection
            </p>
          </div>
        </div>

        {/* Statistics */}
        <div className="grid gap-4 md:grid-cols-5">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Providers</CardTitle>
              <Settings className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.total || 0}</div>
              <p className="text-xs text-muted-foreground">Available APIs</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Enabled APIs</CardTitle>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.enabled || 0}</div>
              <p className="text-xs text-muted-foreground">Active providers</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Temps</CardTitle>
              <Thermometer className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {providers.reduce((acc, p) => acc + (p.temperatures?.length || 0), 0)}
              </div>
              <p className="text-xs text-muted-foreground">Temperature configs</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Configs</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{totalActiveConfigs}</div>
              <p className="text-xs text-muted-foreground">API × Temperature combos</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">With API Keys</CardTitle>
              <Key className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.configured || 0}</div>
              <p className="text-xs text-muted-foreground">Ready to use</p>
            </CardContent>
          </Card>
        </div>

        {/* Info Alert */}
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <strong>Multi-Temperature Data Collection:</strong> Each enabled API will query with ALL its enabled temperature settings.
            For example, if OpenAI has 3 enabled temperatures and Claude has 2, the system will make 5 total API calls per drug query.
          </AlertDescription>
        </Alert>

        {/* Provider Cards with Multiple Temperatures */}
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {providers.map((provider) => {
            const temps = provider.temperatures || []
            return (
              <Card key={provider.id} className={!provider.enabled ? 'opacity-60' : ''}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-3">
                      <span className="text-3xl">
                        {PROVIDER_LOGOS[provider.id] || '🔌'}
                      </span>
                      <div className="flex-1">
                        <CardTitle className="text-lg">{provider.name}</CardTitle>
                        <CardDescription className="text-xs mt-1">
                          {PROVIDER_DESCRIPTIONS[provider.id]}
                        </CardDescription>
                      </div>
                    </div>
                    <Switch
                      checked={provider.enabled}
                      onCheckedChange={() => handleToggleProvider(provider)}
                    />
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Status Row */}
                  <div className="flex items-center justify-between">
                    <div className="flex gap-2">
                      <Badge variant={provider.enabled ? 'default' : 'secondary'}>
                        {provider.enabled ? 'Enabled' : 'Disabled'}
                      </Badge>
                      {provider.has_api_key && (
                        <Badge variant="outline" className="text-xs">
                          <Key className="mr-1 h-3 w-3" />
                          API Key
                        </Badge>
                      )}
                    </div>
                    <Badge variant="outline">
                      {temps.filter(t => t.enabled).length}/{temps.length} temps
                    </Badge>
                  </div>

                  {/* Model Info */}
                  {provider.model && (
                    <div className="text-sm">
                      <span className="text-muted-foreground">Model:</span>{' '}
                      <span className="font-medium">{provider.model}</span>
                    </div>
                  )}

                  {/* Temperature Configurations */}
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <Label className="text-sm font-semibold">Temperature Configurations</Label>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setAddTempDialog({ open: true, providerId: provider.id })}
                        disabled={!provider.enabled}
                      >
                        <Plus className="h-3 w-3" />
                      </Button>
                    </div>

                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {temps.map((temp) => (
                        <div
                          key={temp.id}
                          className="flex items-center justify-between p-2 rounded-lg bg-muted/50"
                        >
                          <div className="flex items-center gap-2 flex-1">
                            <Switch
                              checked={temp.enabled}
                              onCheckedChange={() => handleToggleTemperature(provider, temp.id)}
                              disabled={!provider.enabled}
                              className="scale-90"
                            />
                            <div className="flex-1">
                              <span className="text-sm font-medium">{temp.label}</span>
                              <Badge variant="outline" className="ml-2 text-xs">
                                {temp.value.toFixed(1)}
                              </Badge>
                            </div>
                          </div>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleRemoveTemperature(provider.id, temp.id)}
                            disabled={temps.length <= 1}
                            className="h-6 w-6 p-0"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Features */}
                  {provider.features && provider.features.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {provider.features.map((feature, idx) => (
                        <Badge key={idx} variant="outline" className="text-xs">
                          {feature}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => setApiKeyDialog({ open: true, provider })}
                      >
                        <Key className="mr-2 h-4 w-4" />
                        API Key
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => setEditProvider(provider)}
                      >
                        <Settings className="mr-2 h-4 w-4" />
                        Configure
                      </Button>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full"
                      onClick={() => testMutation.mutate(provider.id)}
                      disabled={!provider.enabled || testMutation.isPending}
                    >
                      <TestTube className="mr-2 h-4 w-4" />
                      Test Connection
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Summary Card */}
        <Card>
          <CardHeader>
            <CardTitle>Data Collection Matrix</CardTitle>
            <CardDescription>
              Active temperature configurations that will be used for data collection
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {providers
                .filter(p => p.enabled && p.temperatures && p.temperatures.some(t => t.enabled))
                .map(provider => {
                  const temps = provider.temperatures || []
                  return (
                    <div key={provider.id} className="flex items-start gap-3">
                      <span className="text-lg mt-1">{PROVIDER_LOGOS[provider.id]}</span>
                      <div className="flex-1">
                        <div className="font-medium text-sm">{provider.name}</div>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {temps
                            .filter(t => t.enabled)
                            .map(temp => (
                              <Badge key={temp.id} variant="secondary" className="text-xs">
                                {temp.label}
                              </Badge>
                            ))}
                        </div>
                      </div>
                    </div>
                  )
                })}

              {totalActiveConfigs === 0 && (
                <p className="text-muted-foreground text-sm text-center py-4">
                  No active configurations. Enable at least one provider with one temperature setting.
                </p>
              )}

              {totalActiveConfigs > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <p className="text-sm font-medium">
                    Total API calls per drug query: <span className="text-primary">{totalActiveConfigs}</span>
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Each query will be processed with all active temperature configurations across all enabled providers
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* API Key Dialog */}
        <Dialog open={apiKeyDialog.open} onOpenChange={(open) => setApiKeyDialog({ open })}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Configure API Key</DialogTitle>
              <DialogDescription>
                Enter the API key for {apiKeyDialog.provider?.name}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="api-key">API Key</Label>
                <Input
                  id="api-key"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-..."
                />
              </div>
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  API keys are stored securely and never exposed in the frontend.
                </AlertDescription>
              </Alert>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setApiKeyDialog({ open: false })}>
                Cancel
              </Button>
              <Button
                onClick={async () => {
                  if (apiKeyDialog.provider) {
                    await updateMutation.mutateAsync({
                      id: apiKeyDialog.provider.id,
                      api_key: apiKey
                    })
                    setApiKeyDialog({ open: false })
                    setApiKey('')
                  }
                }}
              >
                <Save className="mr-2 h-4 w-4" />
                Save API Key
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Provider Settings Dialog */}
        <Dialog open={!!editProvider} onOpenChange={(open) => !open && setEditProvider(null)}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Configure {editProvider?.name}</DialogTitle>
              <DialogDescription>
                Adjust provider settings and model configuration
              </DialogDescription>
            </DialogHeader>
            {editProvider && (
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="model">Model</Label>
                  <Input
                    id="model"
                    value={editProvider.model || ''}
                    onChange={(e) => setEditProvider({ ...editProvider, model: e.target.value })}
                    placeholder="e.g., gpt-4-turbo-preview"
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    checked={editProvider.enabled}
                    onCheckedChange={(enabled) => setEditProvider({ ...editProvider, enabled })}
                  />
                  <Label>Enable Provider</Label>
                </div>

                {editProvider.features && (
                  <div className="space-y-2">
                    <Label>Features</Label>
                    <div className="flex flex-wrap gap-2">
                      {editProvider.features.map((feature, idx) => (
                        <Badge key={idx} variant="outline">
                          {feature}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditProvider(null)}>
                Cancel
              </Button>
              <Button
                onClick={async () => {
                  if (editProvider) {
                    await updateMutation.mutateAsync(editProvider)
                    setEditProvider(null)
                  }
                }}
              >
                <Save className="mr-2 h-4 w-4" />
                Save Settings
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Add Temperature Dialog */}
        <Dialog open={addTempDialog.open} onOpenChange={(open) => setAddTempDialog({ open })}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Temperature Configuration</DialogTitle>
              <DialogDescription>
                Add a new temperature setting for this provider
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="temp-label">Label</Label>
                <Input
                  id="temp-label"
                  value={newTemp.label}
                  onChange={(e) => setNewTemp({ ...newTemp, label: e.target.value })}
                  placeholder="e.g., Creative High (0.9)"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label htmlFor="temp-value">Temperature Value</Label>
                  <span className="text-sm text-muted-foreground">{newTemp.value.toFixed(1)}</span>
                </div>
                <Slider
                  id="temp-value"
                  value={[newTemp.value]}
                  onValueChange={([value]) => setNewTemp({ ...newTemp, value })}
                  min={0}
                  max={1}
                  step={0.1}
                />
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  checked={newTemp.enabled}
                  onCheckedChange={(enabled) => setNewTemp({ ...newTemp, enabled })}
                />
                <Label>Enable immediately</Label>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setAddTempDialog({ open: false })}>
                Cancel
              </Button>
              <Button onClick={handleAddTemperature} disabled={!newTemp.label || addTempMutation.isPending}>
                <Plus className="mr-2 h-4 w-4" />
                Add Temperature
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </MainLayout>
  )
}