'use client'

import { useState } from 'react'
import { MainLayout } from '@/components/layout/main-layout'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { API_BASE_URL } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { formatJSON } from '@/lib/json-formatter'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  GitBranch,
  Database,
  CheckCircle2,
  Scale,
  Brain,
  AlertCircle,
  Info,
  TrendingUp,
  Settings2,
  Play,
  Pause,
  Activity
} from 'lucide-react'

interface PipelineStage {
  name: string
  order: number
  enabled: boolean
  description: string
  progress_weight: number
}

interface Phase2Category {
  id: string
  name: string
  order: number
  enabled: boolean
}

interface PipelineSummary {
  total_stages: number
  enabled_stages: number
  disabled_stages: number
  stages: PipelineStage[]
  progress_map: Record<string, number>
  phase2_categories?: Phase2Category[]
}

const stageIcons: Record<string, any> = {
  data_collection: Database,
  verification: CheckCircle2,
  merging: Scale,
  llm_summary: Brain
}

const stageColors: Record<string, string> = {
  data_collection: 'text-blue-500',
  verification: 'text-green-500',
  merging: 'text-purple-500',
  llm_summary: 'text-orange-500'
}

// Helper function for Phase 2 stage details
const getStageDetails = (name: string): string[] => {
  const details: Record<string, string[]> = {
    'Parameter-Based Scoring Matrix': [
      'Scores each parameter on 0-100 scale',
      'Market size, growth, competition, regulatory',
      'Manufacturing, patents, clinical differentiation'
    ],
    'Weighted Scoring Assessment': [
      'Applies weights: Commercial (35%), Technical (30%)',
      'Regulatory (20%), Competitive (15%)',
      'Calculates composite score with sensitivity analysis'
    ],
    'Risk Assessment Analysis': [
      'Categorizes risks: Regulatory, Commercial, Technical',
      'Financial and Strategic risks assessment',
      'Severity levels and mitigation strategies'
    ],
    'Go/No-Go Recommendation': [
      'Generates GO/NO-GO/CONDITIONAL verdict',
      'Confidence score (0-100%)',
      'Top 3 supporting reasons and top 3 risks'
    ],
    'Strategic Opportunities Analysis': [
      'Development strategy recommendations',
      'Partnership opportunities (licensing, co-dev)',
      'Market entry and portfolio fit analysis'
    ],
    'Competitive Positioning Strategy': [
      'Competitive landscape analysis',
      'Positioning and differentiation strategy',
      'Market access and pricing recommendations'
    ],
    'Executive Summary & Recommendations': [
      'C-suite presentation (max 500 words)',
      'Investment thesis, value drivers, risks',
      'Financial highlights and next steps with timeline'
    ]
  }
  return details[name] || ['Phase 2 decision intelligence stage']
}

export default function PipelinePage() {
  const queryClient = useQueryClient()

  // Fetch pipeline configuration
  const { data: pipelineData, isLoading, error } = useQuery<PipelineSummary>({
    queryKey: ['pipeline-stages'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/stages`)
      if (!response.ok) throw new Error('Failed to fetch pipeline stages')
      return response.json()
    },
    refetchInterval: 5000 // Auto-refresh every 5 seconds
  })

  // Toggle stage mutation
  const toggleStageMutation = useMutation({
    mutationFn: async ({ stageName, enabled }: { stageName: string, enabled: boolean }) => {
      const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/stages/${stageName}?enabled=${enabled}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
      })
      if (!response.ok) throw new Error('Failed to update stage')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline-stages'] })
    }
  })

  const handleToggleStage = (stageName: string, currentEnabled: boolean) => {
    if (stageName === 'data_collection') {
      alert('Data Collection stage cannot be disabled - it is always required')
      return
    }

    toggleStageMutation.mutate({
      stageName,
      enabled: !currentEnabled
    })
  }

  if (isLoading) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </MainLayout>
    )
  }

  if (error) {
    return (
      <MainLayout>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            Failed to load pipeline configuration. Please ensure the backend is running.
          </AlertDescription>
        </Alert>
      </MainLayout>
    )
  }

  const stages = pipelineData?.stages || []
  const enabledCount = pipelineData?.enabled_stages || 0
  const totalCount = pipelineData?.total_stages || 0

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <GitBranch className="h-8 w-8" />
            Processing Pipeline
          </h1>
          <p className="text-muted-foreground mt-2">
            Configure and monitor the 4-stage pharmaceutical intelligence processing pipeline
          </p>
        </div>

        {/* Tabs for Configuration and Monitoring */}
        <Tabs defaultValue="configuration" className="space-y-4">
          <TabsList className="grid w-full grid-cols-2 max-w-md">
            <TabsTrigger value="configuration" className="flex items-center gap-2">
              <Settings2 className="h-4 w-4" />
              Configuration
            </TabsTrigger>
            <TabsTrigger value="monitoring" className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Monitoring
            </TabsTrigger>
          </TabsList>

          {/* Configuration Tab */}
          <TabsContent value="configuration" className="space-y-6">
            {/* Status Overview */}
            <div className="grid gap-4 md:grid-cols-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Stages</CardTitle>
                  <Settings2 className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{totalCount}</div>
                  <p className="text-xs text-muted-foreground">
                    Processing stages
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Enabled</CardTitle>
                  <Play className="h-4 w-4 text-green-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-600">{enabledCount}</div>
                  <p className="text-xs text-muted-foreground">
                    Active stages
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Disabled</CardTitle>
                  <Pause className="h-4 w-4 text-gray-400" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-gray-600">
                    {totalCount - enabledCount}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Inactive stages
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Pipeline Status</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {enabledCount === totalCount ? 'Full' : 'Partial'}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {enabledCount === totalCount ? 'All stages active' : 'Some stages disabled'}
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Info Alert */}
            <Alert>
              <Info className="h-4 w-4" />
              <AlertTitle>How Pipeline Stages Work</AlertTitle>
              <AlertDescription>
                The processing pipeline transforms raw API responses into intelligent pharmaceutical intelligence.
                Disable stages to test different processing configurations. Data Collection cannot be disabled.
              </AlertDescription>
            </Alert>

            {/* Pipeline Stages Table */}
            <Card>
              <CardHeader>
                <CardTitle>Pipeline Stages</CardTitle>
                <CardDescription>
                  Configure which stages are active in the processing pipeline
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[50px]">Order</TableHead>
                      <TableHead>Stage</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead className="w-[120px]">Progress Weight</TableHead>
                      <TableHead className="w-[100px]">Status</TableHead>
                      <TableHead className="w-[100px]">Control</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {stages.map((stage) => {
                      const Icon = stageIcons[stage.name] || Settings2
                      const colorClass = stageColors[stage.name] || 'text-gray-500'
                      const isDataCollection = stage.name === 'data_collection'

                      return (
                        <TableRow key={stage.name}>
                          <TableCell className="font-medium">
                            <Badge variant="outline">{stage.order}</Badge>
                          </TableCell>

                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Icon className={`h-5 w-5 ${colorClass}`} />
                              <div>
                                <div className="font-semibold">
                                  {stage.name.split('_').map(word =>
                                    word.charAt(0).toUpperCase() + word.slice(1)
                                  ).join(' ')}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  {stage.name}
                                </div>
                              </div>
                            </div>
                          </TableCell>

                          <TableCell className="max-w-md">
                            <div className="text-sm">
                              {stage.description}
                            </div>
                          </TableCell>

                          <TableCell>
                            <div className="flex items-center gap-2">
                              <div className="w-full bg-muted rounded-full h-2">
                                <div
                                  className="bg-primary h-2 rounded-full transition-all"
                                  style={{ width: `${(stage.progress_weight / 100 * 100)}%` }}
                                />
                              </div>
                              <span className="text-sm font-medium">{stage.progress_weight}%</span>
                            </div>
                          </TableCell>

                          <TableCell>
                            {stage.enabled ? (
                              <Badge className="bg-green-500">
                                <Play className="h-3 w-3 mr-1" />
                                Enabled
                              </Badge>
                            ) : (
                              <Badge variant="secondary">
                                <Pause className="h-3 w-3 mr-1" />
                                Disabled
                              </Badge>
                            )}
                          </TableCell>

                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Switch
                                checked={stage.enabled}
                                onCheckedChange={() => handleToggleStage(stage.name, stage.enabled)}
                                disabled={isDataCollection || toggleStageMutation.isPending}
                              />
                              {isDataCollection && (
                                <span className="text-xs text-muted-foreground">Required</span>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            {/* Phase 2 Stages Table */}
            {pipelineData?.phase2_categories && pipelineData.phase2_categories.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Phase 2 Stages - Decision Intelligence</CardTitle>
                  <CardDescription>
                    LLM-powered decision stages that process Phase 1 results (runs after all Phase 1 stages complete)
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[50px]">Order</TableHead>
                        <TableHead>Stage</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead className="w-[100px]">Status</TableHead>
                        <TableHead className="w-[100px]">Control</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {pipelineData.phase2_categories.map((category: any) => {
                        const details = getStageDetails(category.name)

                        return (
                          <TableRow key={category.id}>
                            <TableCell className="font-medium">
                              <Badge variant="outline">{category.order}</Badge>
                            </TableCell>

                            <TableCell>
                              <div className="flex items-center gap-2">
                                <Brain className="h-5 w-5 text-orange-500" />
                                <div>
                                  <div className="font-semibold">
                                    {category.name}
                                  </div>
                                  <div className="text-xs text-muted-foreground">
                                    Phase 2 Stage
                                  </div>
                                </div>
                              </div>
                            </TableCell>

                            <TableCell className="max-w-md">
                              <ul className="text-sm space-y-1">
                                {details.map((detail, idx) => (
                                  <li key={idx} className="flex items-start">
                                    <span className="mr-2">•</span>
                                    <span>{detail}</span>
                                  </li>
                                ))}
                              </ul>
                            </TableCell>

                          <TableCell>
                            {category.enabled ? (
                              <Badge className="bg-green-500">
                                <Play className="h-3 w-3 mr-1" />
                                Enabled
                              </Badge>
                            ) : (
                              <Badge variant="secondary">
                                <Pause className="h-3 w-3 mr-1" />
                                Disabled
                              </Badge>
                            )}
                          </TableCell>

                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Switch
                                checked={category.enabled}
                                onCheckedChange={async (checked) => {
                                  const response = await fetch(
                                    `${API_BASE_URL}/api/v1/pipeline/phase2-categories/${category.id}?enabled=${checked}`,
                                    { method: 'PUT' }
                                  )
                                  if (response.ok) {
                                    queryClient.invalidateQueries({ queryKey: ['pipeline-stages'] })
                                  }
                                }}
                              />
                            </div>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            )}

            {/* Stage Details */}
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="h-5 w-5 text-blue-500" />
                    Stage 1: Data Collection
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• Calls all enabled API providers</li>
                    <li>• Uses temperature variations</li>
                    <li>• Stores raw responses to database</li>
                    <li>• <strong>Cannot be disabled</strong></li>
                  </ul>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                    Stage 2: Verification
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• Hierarchical source weighting</li>
                    <li>• Paid APIs: 10, Government: 8</li>
                    <li>• Authority & credibility scores</li>
                    <li>• Verification metadata</li>
                  </ul>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Scale className="h-5 w-5 text-purple-500" />
                    Stage 3: Merging
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• Conflict detection & resolution</li>
                    <li>• Weighted data consolidation</li>
                    <li>• Complementary data merging</li>
                    <li>• Confidence scoring</li>
                  </ul>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Brain className="h-5 w-5 text-orange-500" />
                    Stage 4: LLM Summary
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• Intelligent executive summary</li>
                    <li>• Key findings extraction</li>
                    <li>• Authority breakdown</li>
                    <li>• Strategic recommendations</li>
                  </ul>
                </CardContent>
              </Card>
            </div>

            {/* Progress Map */}
            {pipelineData?.progress_map && (
              <Card>
                <CardHeader>
                  <CardTitle>Progress Tracking</CardTitle>
                  <CardDescription>
                    How progress percentage is calculated based on enabled stages
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {Object.entries(pipelineData.progress_map).map(([stageName, percentage]) => {
                      const stage = stages.find(s => s.name === stageName)
                      if (!stage) return null

                      return (
                        <div key={stageName} className="space-y-1">
                          <div className="flex items-center justify-between text-sm">
                            <span className="font-medium">
                              {stageName.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                            </span>
                            <span className="text-muted-foreground">{percentage.toFixed(0)}%</span>
                          </div>
                          <div className="w-full bg-muted rounded-full h-2">
                            <div
                              className={`h-2 rounded-full transition-all ${
                                stage.enabled ? 'bg-primary' : 'bg-gray-300'
                              }`}
                              style={{ width: `${percentage}%` }}
                            />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Monitoring Tab */}
          <TabsContent value="monitoring" className="space-y-6">
            <PipelineMonitoring />
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  )
}

// Pipeline Monitoring Component
function PipelineMonitoring() {
  const [selectedRequest, setSelectedRequest] = useState<string>('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [requests, setRequests] = useState<any[]>([])

  // Fetch recent requests
  const { data: requestsData } = useQuery({
    queryKey: ['requests'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/requests`)
      if (!response.ok) throw new Error('Failed to fetch requests')
      return response.json()
    }
  })

  // Fetch categories for selected request
  const { data: categoriesData } = useQuery({
    queryKey: ['pipeline-categories', selectedRequest],
    queryFn: async () => {
      if (!selectedRequest) return null
      const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/request-categories/${selectedRequest}`)
      if (!response.ok) throw new Error('Failed to fetch categories')
      return response.json()
    },
    enabled: !!selectedRequest,
    refetchInterval: 5000
  })

  // Auto-select first category when categories load
  if (categoriesData?.categories?.length > 0 && !selectedCategory) {
    setSelectedCategory(categoriesData.categories[0].category_result_id)
  }

  // Fetch pipeline executions for selected category
  const { data: executionsData, isLoading: executionsLoading } = useQuery({
    queryKey: ['pipeline-executions', selectedCategory],
    queryFn: async () => {
      if (!selectedCategory) return null
      const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/category-stages/${selectedCategory}`)
      if (!response.ok) throw new Error('Failed to fetch executions')
      const data = await response.json()
      // Rename stages to logs for compatibility with existing UI
      return {
        ...data,
        logs: data.stages,
        executed_count: data.stages?.filter((s: any) => s.executed).length || 0,
        skipped_count: data.stages?.filter((s: any) => s.skipped).length || 0
      }
    },
    enabled: !!selectedCategory,
    refetchInterval: 5000
  })

  // Fetch API calls for selected request (Stage 1: Data Collection)
  const { data: apiCallsData, isLoading: apiCallsLoading } = useQuery({
    queryKey: ['api-calls', selectedRequest],
    queryFn: async () => {
      if (!selectedRequest) return null
      const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/api-calls/${selectedRequest}`)
      if (!response.ok) throw new Error('Failed to fetch API calls')
      return response.json()
    },
    enabled: !!selectedRequest,
    refetchInterval: 5000
  })

  // Filter API calls by selected category
  const currentCategoryName = categoriesData?.categories?.find(
    (cat: any) => cat.category_result_id === selectedCategory
  )?.category_name

  const filteredApiCalls = apiCallsData?.api_calls?.filter(
    (call: any) => call.category_name === currentCategoryName
  ) || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Pipeline Execution Logs</h2>
          <p className="text-muted-foreground">
            Track pipeline stage executions and intermediate data for each request
          </p>
        </div>
      </div>

      {/* Request Selector */}
      <Card>
        <CardHeader>
          <CardTitle>Select Request</CardTitle>
          <CardDescription>
            Choose a request to view its pipeline execution details
          </CardDescription>
        </CardHeader>
        <CardContent>
          <select
            className="w-full p-2 border rounded-md"
            value={selectedRequest}
            onChange={(e) => {
              setSelectedRequest(e.target.value)
              setSelectedCategory('') // Reset category when request changes
            }}
          >
            <option value="">-- Select a request --</option>
            {requestsData?.map((req: any) => (
              <option key={req.requestId} value={req.requestId}>
                {req.drugName} - {req.requestId} ({new Date(req.createdAt).toLocaleDateString()})
              </option>
            ))}
          </select>
        </CardContent>
      </Card>

      {/* Phase 1 Categories */}
      {selectedRequest && categoriesData && categoriesData.categories && categoriesData.categories.filter((c: any) => c.phase === 1).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5 text-blue-500" />
              Phase 1: Data Collection Categories
            </CardTitle>
            <CardDescription>
              Categories that collect data from external APIs
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs
              value={selectedCategory}
              onValueChange={setSelectedCategory}
              className="w-full"
            >
              <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${categoriesData.categories.filter((c: any) => c.phase === 1).length}, 1fr)` }}>
                {categoriesData.categories.filter((c: any) => c.phase === 1).map((category: any) => (
                  <TabsTrigger key={category.category_result_id} value={category.category_result_id}>
                    {category.category_name}
                  </TabsTrigger>
                ))}
              </TabsList>

              {categoriesData.categories.filter((c: any) => c.phase === 1).map((category: any) => (
                <TabsContent key={category.category_result_id} value={category.category_result_id} className="space-y-6 mt-6">
                  <CategoryPipelineData
                    categoryName={category.category_name}
                    categoryResultId={category.category_result_id}
                    apiCalls={filteredApiCalls}
                    executionsData={executionsData}
                    executionsLoading={executionsLoading}
                  />
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>
      )}

      {/* Phase 2 Categories */}
      {selectedRequest && categoriesData && categoriesData.categories && categoriesData.categories.filter((c: any) => c.phase === 2).length > 0 && (
        <Card className="border-purple-200 bg-purple-50/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-purple-500" />
              Phase 2: Decision Intelligence Categories
            </CardTitle>
            <CardDescription>
              Categories that analyze Phase 1 data to generate strategic insights
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs
              value={selectedCategory}
              onValueChange={setSelectedCategory}
              className="w-full"
            >
              <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${categoriesData.categories.filter((c: any) => c.phase === 2).length}, 1fr)` }}>
                {categoriesData.categories.filter((c: any) => c.phase === 2).map((category: any) => (
                  <TabsTrigger key={category.category_result_id} value={category.category_result_id}>
                    {category.category_name}
                  </TabsTrigger>
                ))}
              </TabsList>

              {categoriesData.categories.filter((c: any) => c.phase === 2).map((category: any) => (
                <TabsContent key={category.category_result_id} value={category.category_result_id} className="space-y-6 mt-6">
                  <CategoryPipelineData
                    categoryName={category.category_name}
                    categoryResultId={category.category_result_id}
                    apiCalls={filteredApiCalls}
                    executionsData={executionsData}
                    executionsLoading={executionsLoading}
                  />
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>
      )}

      {/* Show message if no categories */}
      {selectedRequest && categoriesData && (!categoriesData.categories || categoriesData.categories.length === 0) && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>No Categories Found</AlertTitle>
          <AlertDescription>
            No categories have been processed for this request yet.
          </AlertDescription>
        </Alert>
      )}

      {!selectedRequest && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            Select a request above to view its pipeline stage execution logs and intermediate data.
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}

// Category Pipeline Data Component
function CategoryPipelineData({
  categoryName,
  categoryResultId,
  apiCalls,
  executionsData,
  executionsLoading
}: {
  categoryName: string
  categoryResultId: string
  apiCalls: any[]
  executionsData: any
  executionsLoading: boolean
}) {
  // Calculate API call statistics for this category
  const totalCost = apiCalls.reduce((sum, call) => sum + call.total_cost, 0)
  const totalTokens = apiCalls.reduce((sum, call) => sum + call.token_count, 0)
  const providers = Array.from(new Set(apiCalls.map(call => call.provider)))

  return (
    <div className="space-y-6">
      {/* API Calls - Stage 1: Data Collection */}
      {apiCalls && apiCalls.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5 text-blue-500" />
                  Stage 1: Data Collection - API Calls for {categoryName}
                </CardTitle>
                <CardDescription>
                  All API calls made during the data collection phase for this category
                </CardDescription>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold">{apiCalls.length}</div>
                <p className="text-xs text-muted-foreground">Total calls</p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* Summary Stats */}
            <div className="grid gap-4 md:grid-cols-4 mb-6">
              <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                <div className="text-sm text-muted-foreground">Providers Used</div>
                <div className="text-lg font-semibold">{providers.length}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {providers.join(', ')}
                </div>
              </div>
              <div className="p-3 bg-green-50 rounded-lg border border-green-200">
                <div className="text-sm text-muted-foreground">Total Cost</div>
                <div className="text-lg font-semibold">${totalCost.toFixed(4)}</div>
                <div className="text-xs text-muted-foreground mt-1">USD</div>
              </div>
              <div className="p-3 bg-purple-50 rounded-lg border border-purple-200">
                <div className="text-sm text-muted-foreground">Total Tokens</div>
                <div className="text-lg font-semibold">{totalTokens.toLocaleString()}</div>
                <div className="text-xs text-muted-foreground mt-1">tokens used</div>
              </div>
              <div className="p-3 bg-orange-50 rounded-lg border border-orange-200">
                <div className="text-sm text-muted-foreground">Avg Response Time</div>
                <div className="text-lg font-semibold">
                  {(apiCalls.reduce((sum: number, call: any) => sum + call.response_time_ms, 0) / apiCalls.length / 1000).toFixed(2)}s
                </div>
                <div className="text-xs text-muted-foreground mt-1">per call</div>
              </div>
            </div>

            {/* Individual API Calls */}
            <div className="space-y-3">
              <h4 className="font-semibold text-sm">Individual API Calls</h4>
              {apiCalls.map((call: any, idx: number) => (
                <div key={call.id} className={`p-4 border rounded-lg ${call.response_status === 200 ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <Badge variant="outline">#{idx + 1}</Badge>
                      <span className="font-semibold">{call.provider}</span>
                      <Badge variant={call.response_status === 200 ? "default" : "destructive"}>
                        Status: {call.response_status}
                      </Badge>
                      {call.endpoint && <Badge variant="outline" className="text-xs">{call.endpoint}</Badge>}
                    </div>
                    <div className="flex items-center gap-3 text-sm text-muted-foreground">
                      <span>{(call.response_time_ms / 1000).toFixed(2)}s</span>
                      <span>${call.total_cost.toFixed(4)}</span>
                      {call.token_count > 0 && <span>{call.token_count.toLocaleString()} tokens</span>}
                    </div>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    {/* Request Payload */}
                    <div>
                      <h5 className="font-medium text-xs mb-2 flex items-center gap-2">
                        <Database className="h-3 w-3" />
                        Request Payload
                      </h5>
                      <pre className="bg-white p-2 rounded border text-xs overflow-auto max-h-32 whitespace-pre-wrap">
                        {formatJSON(call.request_payload)}
                      </pre>
                    </div>

                    {/* Response Data */}
                    <div>
                      <h5 className="font-medium text-xs mb-2 flex items-center gap-2">
                        <TrendingUp className="h-3 w-3" />
                        Response Data
                      </h5>
                      <pre className="bg-white p-2 rounded border text-xs overflow-auto max-h-32 whitespace-pre-wrap">
                        {formatJSON(call.response_data)}
                      </pre>
                    </div>
                  </div>

                  {/* Additional Details */}
                  <div className="mt-3 grid gap-2 md:grid-cols-3 text-xs">
                    <div className="bg-gray-50 p-2 rounded">
                      <strong>Cost per token:</strong> ${call.cost_per_token.toFixed(6)}
                    </div>
                    {call.rate_limit_remaining !== null && (
                      <div className="bg-gray-50 p-2 rounded">
                        <strong>Rate limit:</strong> {call.rate_limit_remaining}
                      </div>
                    )}
                    {call.error_message && (
                      <div className="bg-red-50 p-2 rounded text-red-600">
                        <strong>Error:</strong> {call.error_message}
                      </div>
                    )}
                  </div>

                  <div className="mt-2 text-xs text-muted-foreground">
                    {new Date(call.timestamp).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Execution Logs */}
      {executionsData && executionsData.logs && executionsData.logs.length > 0 && (
        <>
          {/* Stage Execution Details */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Stage Execution Timeline for {categoryName}</CardTitle>
                  <CardDescription>
                    Detailed view of each pipeline stage execution for this category
                  </CardDescription>
                </div>
                <div className="flex items-center gap-4">
                  {/* Summary Stats */}
                  <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 rounded-lg">
                    <Settings2 className="h-4 w-4 text-blue-600" />
                    <div className="text-xs">
                      <div className="font-semibold text-blue-900">Total Stages</div>
                      <div className="text-xl font-bold text-blue-600">{executionsData.total_stages}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-2 bg-green-50 rounded-lg">
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <div className="text-xs">
                      <div className="font-semibold text-green-900">Executed</div>
                      <div className="text-xl font-bold text-green-600">{executionsData.executed_count}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg">
                    <Pause className="h-4 w-4 text-gray-600" />
                    <div className="text-xs">
                      <div className="font-semibold text-gray-900">Skipped</div>
                      <div className="text-xl font-bold text-gray-600">{executionsData.skipped_count}</div>
                    </div>
                  </div>
                  {/* Progress Circle */}
                  <div className="relative w-20 h-20">
                    <svg className="w-20 h-20 transform -rotate-90">
                      <circle
                        cx="40"
                        cy="40"
                        r="32"
                        stroke="#e5e7eb"
                        strokeWidth="6"
                        fill="none"
                      />
                      <circle
                        cx="40"
                        cy="40"
                        r="32"
                        stroke="#3b82f6"
                        strokeWidth="6"
                        fill="none"
                        strokeDasharray={`${2 * Math.PI * 32}`}
                        strokeDashoffset={`${2 * Math.PI * 32 * (1 - (executionsData.executed_count / executionsData.total_stages))}`}
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-sm font-bold text-blue-600">
                        {Math.round((executionsData.executed_count / executionsData.total_stages) * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {executionsData.logs?.map((log: any) => (
                  <div
                    key={log.id}
                    className={`p-4 border rounded-lg ${
                      log.executed ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <Badge variant={log.executed ? 'default' : 'secondary'}>
                          Stage {log.stage_order}
                        </Badge>
                        <h3 className="font-semibold text-lg">
                          {log.stage_name.startsWith('phase2_')
                            ? log.stage_name.replace('phase2_', '')
                            : log.stage_name.split('_').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
                          }
                        </h3>
                      </div>
                      <div className="flex items-center gap-2">
                        {log.executed ? (
                          <Badge className="bg-green-500">
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            Executed
                          </Badge>
                        ) : (
                          <Badge variant="secondary">
                            <Pause className="h-3 w-3 mr-1" />
                            Skipped
                          </Badge>
                        )}
                        <span className="text-sm text-muted-foreground">
                          {(log.execution_time_ms / 1000).toFixed(2)}s
                        </span>
                      </div>
                    </div>

                    {log.executed && (
                      <>
                        {/* LLM Usage Stats for stages that use LLM (like merging and Phase 2) */}
                        {(log.stage_name === 'merging' || log.stage_name.startsWith('phase2_')) && log.stage_metadata && (() => {
                          try {
                            const metadata = typeof log.stage_metadata === 'string'
                              ? JSON.parse(log.stage_metadata)
                              : log.stage_metadata;
                            const hasTokens = metadata.tokens_used || metadata.total_tokens || metadata.token_count;
                            const hasCost = metadata.total_cost || metadata.cost;

                            if (hasTokens || hasCost) {
                              return (
                                <div className="grid gap-2 md:grid-cols-3 mb-4">
                                  {hasTokens && (
                                    <div className="p-3 bg-purple-50 rounded-lg border border-purple-200">
                                      <div className="text-sm text-muted-foreground">Tokens Used</div>
                                      <div className="text-lg font-semibold text-purple-600">
                                        {(metadata.tokens_used || metadata.total_tokens || metadata.token_count).toLocaleString()}
                                      </div>
                                      <div className="text-xs text-muted-foreground mt-1">LLM tokens</div>
                                    </div>
                                  )}
                                  {hasCost && (
                                    <div className="p-3 bg-green-50 rounded-lg border border-green-200">
                                      <div className="text-sm text-muted-foreground">LLM Cost</div>
                                      <div className="text-lg font-semibold text-green-600">
                                        ${(metadata.total_cost || metadata.cost).toFixed(4)}
                                      </div>
                                      <div className="text-xs text-muted-foreground mt-1">USD</div>
                                    </div>
                                  )}
                                  <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                                    <div className="text-sm text-muted-foreground">Processing Time</div>
                                    <div className="text-lg font-semibold text-blue-600">
                                      {(log.execution_time_ms / 1000).toFixed(2)}s
                                    </div>
                                    <div className="text-xs text-muted-foreground mt-1">execution time</div>
                                  </div>
                                </div>
                              );
                            }
                          } catch (e) {
                            return null;
                          }
                          return null;
                        })()}

                        {/* Phase 2 LLM Metadata */}
                        {log.stage_name.startsWith('phase2_') && log.stage_metadata && (() => {
                          try {
                            const metadata = typeof log.stage_metadata === 'string'
                              ? JSON.parse(log.stage_metadata)
                              : log.stage_metadata;

                            if (metadata.llm_provider || metadata.llm_model || metadata.confidence_score) {
                              return (
                                <div className="mb-4 p-4 bg-gradient-to-r from-orange-50 to-yellow-50 rounded-lg border border-orange-200">
                                  <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                                    <Brain className="h-4 w-4 text-orange-600" />
                                    Phase 2 Decision Intelligence
                                  </h4>
                                  <div className="grid gap-3 md:grid-cols-3 text-sm">
                                    {metadata.llm_provider && (
                                      <div>
                                        <span className="text-muted-foreground">LLM Provider:</span>
                                        <div className="font-semibold text-orange-700 mt-1">{metadata.llm_provider}</div>
                                      </div>
                                    )}
                                    {metadata.llm_model && (
                                      <div>
                                        <span className="text-muted-foreground">Model:</span>
                                        <div className="font-semibold text-orange-700 mt-1">{metadata.llm_model}</div>
                                      </div>
                                    )}
                                    {typeof metadata.confidence_score === 'number' && (
                                      <div>
                                        <span className="text-muted-foreground">Confidence:</span>
                                        <div className="font-semibold text-orange-700 mt-1">{(metadata.confidence_score * 100).toFixed(1)}%</div>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              );
                            }
                          } catch (e) {
                            return null;
                          }
                          return null;
                        })()}

                        <div className="grid gap-4 md:grid-cols-2 mt-4">
                          {/* Input Data */}
                          <div>
                            <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                              <Database className="h-4 w-4" />
                              Input Data
                            </h4>
                            <pre className="bg-white p-3 rounded border text-xs overflow-auto max-h-40 whitespace-pre-wrap">
                              {formatJSON(log.input_data)}
                            </pre>
                          </div>

                          {/* Output Data */}
                          <div>
                            <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                              <TrendingUp className="h-4 w-4" />
                              {log.stage_name === 'llm_summary' ? 'Generated Summary' : log.stage_name === 'merging' ? 'Output Metadata' : 'Output Data'}
                            </h4>
                            {log.stage_name === 'llm_summary' && log.output_data?.summary ? (
                              <div className="bg-white p-4 rounded border overflow-auto max-h-96">
                                <div className="prose prose-sm max-w-none">
                                  <div className="whitespace-pre-wrap text-sm leading-relaxed">
                                    {log.output_data.summary}
                                  </div>
                                </div>
                              </div>
                            ) : log.stage_name === 'merging' && log.output_metadata ? (
                              <pre className="bg-white p-3 rounded border text-xs overflow-auto max-h-40 whitespace-pre-wrap">
                                {formatJSON(log.output_metadata)}
                              </pre>
                            ) : (
                              <pre className="bg-white p-3 rounded border text-xs overflow-auto max-h-40 whitespace-pre-wrap">
                                {formatJSON(log.output_data)}
                              </pre>
                            )}
                          </div>

                          {/* Structured Data for Merging Stage / Stage Metadata for others */}
                          {log.stage_name === 'merging' && log.structured_data ? (
                            <div className="md:col-span-2">
                              <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                                <Scale className="h-4 w-4 text-purple-500" />
                                Structured Data (Merged Results)
                              </h4>
                              <pre className="bg-white p-3 rounded border text-xs overflow-auto max-h-60 whitespace-pre-wrap">
                                {formatJSON(log.structured_data)}
                              </pre>
                            </div>
                          ) : log.stage_metadata && (
                            <div className="md:col-span-2">
                              <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                                <Info className="h-4 w-4" />
                                Stage Metadata
                              </h4>
                              <pre className="bg-white p-3 rounded border text-xs overflow-auto max-h-40 whitespace-pre-wrap">
                                {formatJSON(log.stage_metadata)}
                              </pre>
                            </div>
                          )}
                        </div>
                      </>
                    )}

                    <div className="mt-3 text-xs text-muted-foreground">
                      Started: {new Date(log.started_at).toLocaleString()}
                      {log.completed_at && ` • Completed: ${new Date(log.completed_at).toLocaleString()}`}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Empty State */}
      {!executionsLoading && (!executionsData || !executionsData.logs || executionsData.logs.length === 0) && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>No Execution Logs Found</AlertTitle>
          <AlertDescription>
            This category has not been processed through the pipeline yet, or has not generated any execution logs.
          </AlertDescription>
        </Alert>
      )}

      {apiCalls.length === 0 && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertTitle>No API Calls Found</AlertTitle>
          <AlertDescription>
            No API calls have been made for this category yet.
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}
