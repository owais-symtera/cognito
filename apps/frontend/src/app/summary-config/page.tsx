'use client'

import { useState } from 'react'
import { MainLayout } from '@/components/layout/main-layout'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { API_BASE_URL } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import {
  FileText,
  Edit,
  Plus,
  Settings,
  History,
  Link,
  CheckCircle,
  XCircle,
  AlertCircle,
  Sparkles,
} from 'lucide-react'

// ==================== Type Definitions ====================

interface SummaryStyle {
  id: string
  style_name: string
  display_name: string
  description: string
  system_prompt: string
  user_prompt_template: string
  length_type: string
  target_word_count: number
  enabled: boolean
  created_at: string
  updated_at: string
}

interface CategoryMapping {
  id: string
  category_name: string
  summary_style_id: string
  style_name: string
  display_name: string
  enabled: boolean
  custom_instructions: string | null
}

interface Provider {
  key: string
  name: string
  model: string
  temperature: number
  max_tokens: number
  enabled: boolean
}

interface SummaryHistoryItem {
  id: string
  request_id: string
  category_name: string
  drug_name: string
  style_name: string
  display_name: string
  provider_name: string
  model_name: string
  generated_summary: string
  tokens_used: number
  cost_estimate: number
  generation_time_ms: number
  success: boolean
  error_message: string | null
  created_at: string
}

// ==================== Main Component ====================

export default function SummaryConfigPage() {
  const [activeTab, setActiveTab] = useState('styles')
  const [isStyleDialogOpen, setIsStyleDialogOpen] = useState(false)
  const [isMappingDialogOpen, setIsMappingDialogOpen] = useState(false)
  const [selectedStyle, setSelectedStyle] = useState<SummaryStyle | null>(null)
  const [selectedMapping, setSelectedMapping] = useState<CategoryMapping | null>(null)
  const queryClient = useQueryClient()

  // ==================== API Queries ====================

  // Fetch summary styles
  const { data: stylesData, isLoading: stylesLoading } = useQuery({
    queryKey: ['summary-styles'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/summary/styles`)
      if (!response.ok) throw new Error('Failed to fetch styles')
      const data = await response.json()
      return data.styles as SummaryStyle[]
    }
  })

  // Fetch category mappings
  const { data: mappingsData, isLoading: mappingsLoading } = useQuery({
    queryKey: ['category-mappings'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/summary/categories`)
      if (!response.ok) throw new Error('Failed to fetch mappings')
      const data = await response.json()
      return data.category_configs as CategoryMapping[]
    }
  })

  // Fetch providers
  const { data: providersData, isLoading: providersLoading } = useQuery({
    queryKey: ['summary-providers'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/summary/providers`)
      if (!response.ok) throw new Error('Failed to fetch providers')
      const data = await response.json()
      return data.providers as Provider[]
    }
  })

  // Fetch active provider
  const { data: activeProviderData } = useQuery({
    queryKey: ['active-summary-provider'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/summary/providers/active`)
      if (!response.ok) throw new Error('Failed to fetch active provider')
      const data = await response.json()
      return data.provider as Provider
    }
  })

  // Fetch summary history
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['summary-history'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/summary/history?limit=50`)
      if (!response.ok) throw new Error('Failed to fetch history')
      const data = await response.json()
      return data.history as SummaryHistoryItem[]
    }
  })

  // ==================== Mutations ====================

  // Update style mutation
  const updateStyleMutation = useMutation({
    mutationFn: async ({ id, ...data }: Partial<SummaryStyle> & { id: string }) => {
      const response = await fetch(`${API_BASE_URL}/api/v1/summary/styles/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      if (!response.ok) throw new Error('Failed to update style')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['summary-styles'] })
      setIsStyleDialogOpen(false)
    }
  })

  // Update category mapping mutation
  const updateMappingMutation = useMutation({
    mutationFn: async ({ category_name, ...data }: { category_name: string; summary_style_id: string; enabled: boolean; custom_instructions?: string }) => {
      const response = await fetch(`${API_BASE_URL}/api/v1/summary/categories/${category_name}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...data, category_name })
      })
      if (!response.ok) throw new Error('Failed to update mapping')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['category-mappings'] })
      setIsMappingDialogOpen(false)
    }
  })

  // Update active provider mutation
  const updateProviderMutation = useMutation({
    mutationFn: async (providerKey: string) => {
      const provider = providersData?.find(p => p.key === providerKey)
      if (!provider) throw new Error('Provider not found')

      const response = await fetch(`${API_BASE_URL}/api/v1/summary/providers/active`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_key: providerKey,
          model: provider.model,
          temperature: provider.temperature,
          max_tokens: provider.max_tokens
        })
      })
      if (!response.ok) throw new Error('Failed to update provider')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['active-summary-provider'] })
    }
  })

  // ==================== Handlers ====================

  const handleEditStyle = (style: SummaryStyle) => {
    setSelectedStyle(style)
    setIsStyleDialogOpen(true)
  }

  const handleEditMapping = (mapping: CategoryMapping) => {
    setSelectedMapping(mapping)
    setIsMappingDialogOpen(true)
  }

  const handleSaveStyle = () => {
    if (!selectedStyle) return
    updateStyleMutation.mutate(selectedStyle)
  }

  const handleSaveMapping = () => {
    if (!selectedMapping) return
    updateMappingMutation.mutate({
      category_name: selectedMapping.category_name,
      summary_style_id: selectedMapping.summary_style_id,
      enabled: selectedMapping.enabled,
      custom_instructions: selectedMapping.custom_instructions || undefined
    })
  }

  // ==================== Render ====================

  return (
    <MainLayout>
      <div className="container mx-auto p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <Sparkles className="h-8 w-8 text-purple-500" />
              Summary Configuration
            </h1>
            <p className="text-muted-foreground mt-1">
              Manage summary styles, category mappings, and generation settings
            </p>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="styles" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Styles
            </TabsTrigger>
            <TabsTrigger value="mappings" className="flex items-center gap-2">
              <Link className="h-4 w-4" />
              Mappings
            </TabsTrigger>
            <TabsTrigger value="providers" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Providers
            </TabsTrigger>
            <TabsTrigger value="history" className="flex items-center gap-2">
              <History className="h-4 w-4" />
              History
            </TabsTrigger>
          </TabsList>

          {/* ==================== Styles Tab ==================== */}
          <TabsContent value="styles" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Summary Styles</CardTitle>
                <CardDescription>
                  Manage pre-configured summary styles with custom prompts and settings
                </CardDescription>
              </CardHeader>
              <CardContent>
                {stylesLoading ? (
                  <div className="text-center py-8 text-muted-foreground">Loading styles...</div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Style</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Target Length</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {stylesData?.map((style) => (
                        <TableRow key={style.id}>
                          <TableCell>
                            <div>
                              <div className="font-medium">{style.display_name}</div>
                              <div className="text-sm text-muted-foreground">{style.description}</div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">{style.length_type}</Badge>
                          </TableCell>
                          <TableCell>{style.target_word_count} words</TableCell>
                          <TableCell>
                            {style.enabled ? (
                              <Badge variant="default" className="gap-1">
                                <CheckCircle className="h-3 w-3" />
                                Enabled
                              </Badge>
                            ) : (
                              <Badge variant="secondary" className="gap-1">
                                <XCircle className="h-3 w-3" />
                                Disabled
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleEditStyle(style)}
                            >
                              <Edit className="h-4 w-4 mr-1" />
                              Edit
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* ==================== Mappings Tab ==================== */}
          <TabsContent value="mappings" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Category to Style Mappings</CardTitle>
                <CardDescription>
                  Configure which summary style is used for each pharmaceutical category
                </CardDescription>
              </CardHeader>
              <CardContent>
                {mappingsLoading ? (
                  <div className="text-center py-8 text-muted-foreground">Loading mappings...</div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Category</TableHead>
                        <TableHead>Summary Style</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {mappingsData?.map((mapping) => (
                        <TableRow key={mapping.id}>
                          <TableCell className="font-medium">{mapping.category_name}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{mapping.display_name}</Badge>
                          </TableCell>
                          <TableCell>
                            {mapping.enabled ? (
                              <Badge variant="default" className="gap-1">
                                <CheckCircle className="h-3 w-3" />
                                Active
                              </Badge>
                            ) : (
                              <Badge variant="secondary" className="gap-1">
                                <XCircle className="h-3 w-3" />
                                Inactive
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleEditMapping(mapping)}
                            >
                              <Edit className="h-4 w-4 mr-1" />
                              Edit
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* ==================== Providers Tab ==================== */}
          <TabsContent value="providers" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>LLM Provider Configuration</CardTitle>
                <CardDescription>
                  Select and configure the AI provider used for summary generation
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label>Active Provider</Label>
                  <Select
                    value={activeProviderData?.key}
                    onValueChange={(value) => updateProviderMutation.mutate(value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select provider" />
                    </SelectTrigger>
                    <SelectContent>
                      {providersData?.filter(p => p.enabled).map((provider) => (
                        <SelectItem key={provider.key} value={provider.key}>
                          {provider.name} - {provider.model}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {activeProviderData && (
                    <div className="text-sm text-muted-foreground space-y-1 mt-4">
                      <div>Model: <span className="font-medium">{activeProviderData.model}</span></div>
                      <div>Temperature: <span className="font-medium">{activeProviderData.temperature}</span></div>
                      <div>Max Tokens: <span className="font-medium">{activeProviderData.max_tokens}</span></div>
                    </div>
                  )}
                </div>

                <div className="border-t pt-6">
                  <h3 className="font-semibold mb-4">Available Providers</h3>
                  <div className="space-y-2">
                    {providersData?.map((provider) => (
                      <div
                        key={provider.key}
                        className={`flex items-center justify-between p-4 rounded-lg border ${
                          activeProviderData?.key === provider.key ? 'border-primary bg-primary/5' : ''
                        }`}
                      >
                        <div>
                          <div className="font-medium">{provider.name}</div>
                          <div className="text-sm text-muted-foreground">{provider.model}</div>
                        </div>
                        <Badge variant={provider.enabled ? 'default' : 'secondary'}>
                          {provider.enabled ? 'Available' : 'Disabled'}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ==================== History Tab ==================== */}
          <TabsContent value="history" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Summary Generation History</CardTitle>
                <CardDescription>
                  View recent summary generations with performance metrics
                </CardDescription>
              </CardHeader>
              <CardContent>
                {historyLoading ? (
                  <div className="text-center py-8 text-muted-foreground">Loading history...</div>
                ) : (
                  <div className="space-y-4">
                    {historyData?.map((item) => (
                      <div key={item.id} className="border rounded-lg p-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">{item.category_name}</Badge>
                            <span className="text-sm font-medium">{item.drug_name}</span>
                          </div>
                          {item.success ? (
                            <Badge variant="default" className="gap-1">
                              <CheckCircle className="h-3 w-3" />
                              Success
                            </Badge>
                          ) : (
                            <Badge variant="destructive" className="gap-1">
                              <AlertCircle className="h-3 w-3" />
                              Failed
                            </Badge>
                          )}
                        </div>
                        <div className="text-sm text-muted-foreground grid grid-cols-4 gap-4">
                          <div>
                            <div className="font-medium text-foreground">Style</div>
                            <div>{item.display_name}</div>
                          </div>
                          <div>
                            <div className="font-medium text-foreground">Provider</div>
                            <div>{item.provider_name}</div>
                          </div>
                          <div>
                            <div className="font-medium text-foreground">Tokens</div>
                            <div>{item.tokens_used}</div>
                          </div>
                          <div>
                            <div className="font-medium text-foreground">Time</div>
                            <div>{item.generation_time_ms}ms</div>
                          </div>
                        </div>
                        {item.error_message && (
                          <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription>{item.error_message}</AlertDescription>
                          </Alert>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* ==================== Edit Style Dialog ==================== */}
        <Dialog open={isStyleDialogOpen} onOpenChange={setIsStyleDialogOpen}>
          <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Edit Summary Style</DialogTitle>
              <DialogDescription>
                Modify the configuration for {selectedStyle?.display_name}
              </DialogDescription>
            </DialogHeader>
            {selectedStyle && (
              <div className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    checked={selectedStyle.enabled}
                    onCheckedChange={(checked) =>
                      setSelectedStyle({ ...selectedStyle, enabled: checked })
                    }
                  />
                  <Label>Enabled</Label>
                </div>

                <div className="space-y-2">
                  <Label>Display Name</Label>
                  <Input
                    value={selectedStyle.display_name}
                    onChange={(e) =>
                      setSelectedStyle({ ...selectedStyle, display_name: e.target.value })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea
                    value={selectedStyle.description}
                    onChange={(e) =>
                      setSelectedStyle({ ...selectedStyle, description: e.target.value })
                    }
                    rows={2}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Length Type</Label>
                    <Select
                      value={selectedStyle.length_type}
                      onValueChange={(value) =>
                        setSelectedStyle({ ...selectedStyle, length_type: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="BRIEF">Brief</SelectItem>
                        <SelectItem value="STANDARD">Standard</SelectItem>
                        <SelectItem value="DETAILED">Detailed</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Target Word Count</Label>
                    <Input
                      type="number"
                      value={selectedStyle.target_word_count}
                      onChange={(e) =>
                        setSelectedStyle({
                          ...selectedStyle,
                          target_word_count: parseInt(e.target.value)
                        })
                      }
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>System Prompt</Label>
                  <Textarea
                    value={selectedStyle.system_prompt}
                    onChange={(e) =>
                      setSelectedStyle({ ...selectedStyle, system_prompt: e.target.value })
                    }
                    rows={4}
                    className="font-mono text-sm"
                  />
                </div>

                <div className="space-y-2">
                  <Label>User Prompt Template</Label>
                  <Textarea
                    value={selectedStyle.user_prompt_template}
                    onChange={(e) =>
                      setSelectedStyle({ ...selectedStyle, user_prompt_template: e.target.value })
                    }
                    rows={6}
                    className="font-mono text-sm"
                  />
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsStyleDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSaveStyle} disabled={updateStyleMutation.isPending}>
                {updateStyleMutation.isPending ? 'Saving...' : 'Save Changes'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ==================== Edit Mapping Dialog ==================== */}
        <Dialog open={isMappingDialogOpen} onOpenChange={setIsMappingDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Category Mapping</DialogTitle>
              <DialogDescription>
                Configure summary style for {selectedMapping?.category_name}
              </DialogDescription>
            </DialogHeader>
            {selectedMapping && (
              <div className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    checked={selectedMapping.enabled}
                    onCheckedChange={(checked) =>
                      setSelectedMapping({ ...selectedMapping, enabled: checked })
                    }
                  />
                  <Label>Enabled</Label>
                </div>

                <div className="space-y-2">
                  <Label>Summary Style</Label>
                  <Select
                    value={selectedMapping.summary_style_id}
                    onValueChange={(value) =>
                      setSelectedMapping({ ...selectedMapping, summary_style_id: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {stylesData?.map((style) => (
                        <SelectItem key={style.id} value={style.id}>
                          {style.display_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Custom Instructions (Optional)</Label>
                  <Textarea
                    value={selectedMapping.custom_instructions || ''}
                    onChange={(e) =>
                      setSelectedMapping({
                        ...selectedMapping,
                        custom_instructions: e.target.value
                      })
                    }
                    rows={3}
                    placeholder="Add category-specific instructions..."
                  />
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsMappingDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSaveMapping} disabled={updateMappingMutation.isPending}>
                {updateMappingMutation.isPending ? 'Saving...' : 'Save Changes'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </MainLayout>
  )
}
