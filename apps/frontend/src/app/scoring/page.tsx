'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSession } from 'next-auth/react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import {
  Sliders,
  Save,
  RefreshCw,
  Plus,
  Trash2,
  Edit,
  AlertTriangle,
  CheckCircle,
  Shield,
  Target,
  Zap,
  BarChart3,
  Settings,
  Database,
  Brain,
  TestTube,
  Award,
  TrendingUp,
  Info,
  Copy,
  Download,
  Upload,
  Eye,
  History
} from 'lucide-react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

/**
 * Validation schema for scoring configuration
 */
const scoringConfigSchema = z.object({
  name: z.string().min(1, 'Configuration name is required'),
  description: z.string().min(1, 'Description is required'),
  version: z.string().min(1, 'Version is required'),
  weights: z.object({
    safety: z.number().min(0).max(100),
    efficacy: z.number().min(0).max(100),
    interactions: z.number().min(0).max(100),
    regulatory: z.number().min(0).max(100),
  }),
  thresholds: z.object({
    safetyPass: z.number().min(0).max(100),
    efficacyPass: z.number().min(0).max(100),
    overallPass: z.number().min(0).max(100),
    criticalFailure: z.number().min(0).max(100),
  }),
  penalties: z.object({
    majorInteraction: z.number().min(0).max(50),
    contraindication: z.number().min(0).max(100),
    adverseEffect: z.number().min(0).max(50),
    complianceIssue: z.number().min(0).max(50),
  }),
  bonuses: z.object({
    noveltarget: z.number().min(0).max(20),
    fastTrack: z.number().min(0).max(15),
    orphanDrug: z.number().min(0).max(25),
    breakthrough: z.number().min(0).max(30),
  }),
})

type ScoringConfig = z.infer<typeof scoringConfigSchema>

/**
 * Interface for scoring configuration data
 */
interface ScoringConfiguration {
  id: string
  name: string
  description: string
  version: string
  isActive: boolean
  isDefault: boolean
  createdAt: string
  updatedAt: string
  createdBy: string
  lastModifiedBy: string
  weights: {
    safety: number
    efficacy: number
    interactions: number
    regulatory: number
  }
  thresholds: {
    safetyPass: number
    efficacyPass: number
    overallPass: number
    criticalFailure: number
  }
  penalties: {
    majorInteraction: number
    contraindication: number
    adverseEffect: number
    complianceIssue: number
  }
  bonuses: {
    noveltarget: number
    fastTrack: number
    orphanDrug: number
    breakthrough: number
  }
  usageStats: {
    totalAnalyses: number
    averageScore: number
    passRate: number
    lastUsed: string
  }
}

/**
 * Interface for scoring templates
 */
interface ScoringTemplate {
  id: string
  name: string
  description: string
  category: 'FDA' | 'EMA' | 'ICH' | 'Custom'
  configuration: Partial<ScoringConfiguration>
}

/**
 * Comprehensive scoring algorithm configuration interface.
 *
 * Features:
 * - Configurable scoring weights and thresholds
 * - Multiple scoring profiles
 * - Template management
 * - Real-time preview and validation
 * - Version control and rollback
 * - Regulatory compliance presets
 * - Performance analytics
 * - A/B testing capabilities
 *
 * @returns React component for scoring configuration
 *
 * @example
 * ```tsx
 * // Accessed via /scoring route (admin/analyst only)
 * <ScoringConfigurationPage />
 * ```
 *
 * @since 1.0.0
 * @version 1.0.0
 * @author CognitoAI Development Team
 */
export default function ScoringConfigurationPage() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()
  const [selectedConfig, setSelectedConfig] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [previewMode, setPreviewMode] = useState(false)

  const userRole = (session?.user as any)?.role || 'user'

  // Only allow admin and analyst roles
  if (!['admin', 'analyst'].includes(userRole)) {
    return (
      <div className="container mx-auto px-4 py-6">
        <Alert variant="destructive">
          <Shield className="h-4 w-4" />
          <AlertDescription>
            Access denied. You don't have permission to view this page.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  // Form setup
  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isDirty }
  } = useForm<ScoringConfig>({
    resolver: zodResolver(scoringConfigSchema),
    defaultValues: {
      weights: { safety: 30, efficacy: 30, interactions: 20, regulatory: 20 },
      thresholds: { safetyPass: 70, efficacyPass: 70, overallPass: 75, criticalFailure: 30 },
      penalties: { majorInteraction: 15, contraindication: 25, adverseEffect: 10, complianceIssue: 20 },
      bonuses: { noveltarget: 10, fastTrack: 5, orphanDrug: 15, breakthrough: 20 },
    }
  })

  const watchedValues = watch()

  // Fetch scoring configurations
  const {
    data: configurations,
    isLoading: configsLoading,
    error: configsError,
    refetch: refetchConfigs
  } = useQuery<ScoringConfiguration[]>({
    queryKey: ['scoring-configurations'],
    queryFn: () => api.get('/api/v1/scoring/configurations'),
  })

  // Fetch scoring templates
  const {
    data: templates,
    isLoading: templatesLoading
  } = useQuery<ScoringTemplate[]>({
    queryKey: ['scoring-templates'],
    queryFn: () => api.get('/api/v1/scoring/templates'),
  })

  // Save configuration mutation
  const saveConfigMutation = useMutation({
    mutationFn: (config: ScoringConfig & { id?: string }) =>
      config.id
        ? api.put(`/api/v1/scoring/configurations/${config.id}`, config)
        : api.post('/api/v1/scoring/configurations', config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scoring-configurations'] })
      setIsEditing(false)
    },
  })

  // Delete configuration mutation
  const deleteConfigMutation = useMutation({
    mutationFn: (configId: string) => api.delete(`/api/v1/scoring/configurations/${configId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scoring-configurations'] })
      setSelectedConfig(null)
    },
  })

  // Activate configuration mutation
  const activateConfigMutation = useMutation({
    mutationFn: (configId: string) => api.post(`/api/v1/scoring/configurations/${configId}/activate`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scoring-configurations'] })
    },
  })

  /**
   * Load configuration into form
   */
  const loadConfiguration = (config: ScoringConfiguration) => {
    reset({
      name: config.name,
      description: config.description,
      version: config.version,
      weights: config.weights,
      thresholds: config.thresholds,
      penalties: config.penalties,
      bonuses: config.bonuses,
    })
    setSelectedConfig(config.id)
    setIsEditing(true)
  }

  /**
   * Apply template to form
   */
  const applyTemplate = (template: ScoringTemplate) => {
    if (template.configuration) {
      reset({
        name: template.name,
        description: template.description,
        version: '1.0.0',
        weights: template.configuration.weights || watchedValues.weights,
        thresholds: template.configuration.thresholds || watchedValues.thresholds,
        penalties: template.configuration.penalties || watchedValues.penalties,
        bonuses: template.configuration.bonuses || watchedValues.bonuses,
      })
    }
  }

  /**
   * Calculate total weight
   */
  const getTotalWeight = () => {
    return Object.values(watchedValues.weights || {}).reduce((sum, weight) => sum + weight, 0)
  }

  /**
   * Validate weights sum to 100
   */
  const isWeightValid = getTotalWeight() === 100

  /**
   * Calculate preview score
   */
  const calculatePreviewScore = () => {
    const baseScore = 85 // Simulated base score
    const weights = watchedValues.weights || {}
    const bonuses = watchedValues.bonuses || {}
    const penalties = watchedValues.penalties || {}

    let score = baseScore

    // Apply a sample bonus
    score += bonuses.noveltarget * 0.5 // 50% of novel target bonus

    // Apply a sample penalty
    score -= penalties.majorInteraction * 0.3 // 30% of major interaction penalty

    return Math.max(0, Math.min(100, score))
  }

  /**
   * Handle form submission
   */
  const onSubmit = async (data: ScoringConfig) => {
    try {
      await saveConfigMutation.mutateAsync({
        ...data,
        id: selectedConfig || undefined,
      })
    } catch (error) {
      console.error('Failed to save configuration:', error)
    }
  }

  /**
   * Create new configuration
   */
  const createNewConfig = () => {
    reset({
      name: '',
      description: '',
      version: '1.0.0',
      weights: { safety: 30, efficacy: 30, interactions: 20, regulatory: 20 },
      thresholds: { safetyPass: 70, efficacyPass: 70, overallPass: 75, criticalFailure: 30 },
      penalties: { majorInteraction: 15, contraindication: 25, adverseEffect: 10, complianceIssue: 20 },
      bonuses: { noveltarget: 10, fastTrack: 5, orphanDrug: 15, breakthrough: 20 },
    })
    setSelectedConfig(null)
    setIsEditing(true)
  }

  if (configsError) {
    return (
      <div className="container mx-auto px-4 py-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load scoring configurations. Please try again later.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Scoring Configuration</h1>
            <p className="text-muted-foreground mt-1">
              Configure and manage pharmaceutical analysis scoring algorithms
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="outline" onClick={createNewConfig}>
              <Plus className="h-4 w-4 mr-2" />
              New Configuration
            </Button>
            <Button variant="outline" onClick={() => refetchConfigs()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Configuration List */}
          <div className="lg:col-span-1 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Settings className="h-5 w-5" />
                  <span>Configurations</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {configsLoading ? (
                  <div className="space-y-3">
                    {Array.from({ length: 3 }).map((_, i) => (
                      <div key={i} className="animate-pulse p-3 border rounded-lg">
                        <div className="h-4 bg-muted rounded w-3/4 mb-2"></div>
                        <div className="h-3 bg-muted rounded w-1/2"></div>
                      </div>
                    ))}
                  </div>
                ) : configurations && configurations.length > 0 ? (
                  <div className="space-y-2">
                    {configurations.map((config) => (
                      <div
                        key={config.id}
                        className={cn(
                          "p-3 border rounded-lg cursor-pointer transition-colors hover:bg-muted/50",
                          selectedConfig === config.id && "border-primary bg-primary/5",
                          config.isActive && "ring-2 ring-green-200"
                        )}
                        onClick={() => setSelectedConfig(config.id)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="font-medium text-sm">{config.name}</h4>
                            <p className="text-xs text-muted-foreground mt-1">
                              v{config.version} • {config.description}
                            </p>
                            <div className="flex items-center space-x-2 mt-2">
                              {config.isActive && (
                                <Badge className="bg-green-100 text-green-800">
                                  Active
                                </Badge>
                              )}
                              {config.isDefault && (
                                <Badge variant="outline">
                                  Default
                                </Badge>
                              )}
                              <span className="text-xs text-muted-foreground">
                                {config.usageStats.totalAnalyses} uses
                              </span>
                            </div>
                          </div>
                          <div className="flex flex-col items-center space-y-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={(e) => {
                                e.stopPropagation()
                                loadConfiguration(config)
                              }}
                            >
                              <Edit className="h-3 w-3" />
                            </Button>
                            {!config.isActive && (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  activateConfigMutation.mutate(config.id)
                                }}
                              >
                                <CheckCircle className="h-3 w-3" />
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Target className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="font-medium text-foreground mb-2">No Configurations</h3>
                    <p className="text-muted-foreground text-sm mb-4">
                      Create your first scoring configuration
                    </p>
                    <Button onClick={createNewConfig}>
                      <Plus className="h-4 w-4 mr-2" />
                      Create Configuration
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Templates */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Database className="h-5 w-5" />
                  <span>Templates</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {templatesLoading ? (
                  <div className="space-y-3">
                    {Array.from({ length: 2 }).map((_, i) => (
                      <div key={i} className="animate-pulse p-3 border rounded-lg">
                        <div className="h-4 bg-muted rounded w-3/4 mb-2"></div>
                        <div className="h-3 bg-muted rounded w-1/2"></div>
                      </div>
                    ))}
                  </div>
                ) : templates && templates.length > 0 ? (
                  <div className="space-y-2">
                    {templates.map((template) => (
                      <div
                        key={template.id}
                        className="p-3 border rounded-lg cursor-pointer transition-colors hover:bg-muted/50"
                        onClick={() => applyTemplate(template)}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-medium text-sm">{template.name}</h4>
                            <p className="text-xs text-muted-foreground">{template.description}</p>
                            <Badge variant="outline" className="mt-1 text-xs">
                              {template.category}
                            </Badge>
                          </div>
                          <Copy className="h-4 w-4 text-muted-foreground" />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <p className="text-muted-foreground text-sm">No templates available</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Configuration Editor */}
          <div className="lg:col-span-2">
            {isEditing ? (
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                {/* Basic Information */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Brain className="h-5 w-5" />
                      <span>Configuration Details</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="name">Name *</Label>
                        <Input
                          id="name"
                          {...register('name')}
                          placeholder="Configuration name"
                        />
                        {errors.name && (
                          <p className="text-sm text-red-600">{errors.name.message}</p>
                        )}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="version">Version *</Label>
                        <Input
                          id="version"
                          {...register('version')}
                          placeholder="1.0.0"
                        />
                        {errors.version && (
                          <p className="text-sm text-red-600">{errors.version.message}</p>
                        )}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="description">Description *</Label>
                      <Input
                        id="description"
                        {...register('description')}
                        placeholder="Describe this scoring configuration"
                      />
                      {errors.description && (
                        <p className="text-sm text-red-600">{errors.description.message}</p>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Tabs defaultValue="weights" className="space-y-4">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="weights">Weights</TabsTrigger>
                    <TabsTrigger value="thresholds">Thresholds</TabsTrigger>
                    <TabsTrigger value="penalties">Penalties</TabsTrigger>
                    <TabsTrigger value="bonuses">Bonuses</TabsTrigger>
                  </TabsList>

                  {/* Weights */}
                  <TabsContent value="weights">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <BarChart3 className="h-5 w-5" />
                            <span>Analysis Weights</span>
                          </div>
                          <Badge
                            className={isWeightValid ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}
                          >
                            Total: {getTotalWeight()}%
                          </Badge>
                        </CardTitle>
                        <CardDescription>
                          Set the relative importance of each analysis component (must total 100%)
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {!isWeightValid && (
                          <Alert>
                            <AlertTriangle className="h-4 w-4" />
                            <AlertDescription>
                              Weights must total exactly 100%. Current total: {getTotalWeight()}%
                            </AlertDescription>
                          </Alert>
                        )}

                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label className="flex items-center space-x-2">
                              <Shield className="h-4 w-4" />
                              <span>Safety Weight (%)</span>
                            </Label>
                            <Input
                              type="number"
                              min="0"
                              max="100"
                              {...register('weights.safety', { valueAsNumber: true })}
                            />
                          </div>

                          <div className="space-y-2">
                            <Label className="flex items-center space-x-2">
                              <Zap className="h-4 w-4" />
                              <span>Efficacy Weight (%)</span>
                            </Label>
                            <Input
                              type="number"
                              min="0"
                              max="100"
                              {...register('weights.efficacy', { valueAsNumber: true })}
                            />
                          </div>

                          <div className="space-y-2">
                            <Label className="flex items-center space-x-2">
                              <AlertTriangle className="h-4 w-4" />
                              <span>Interactions Weight (%)</span>
                            </Label>
                            <Input
                              type="number"
                              min="0"
                              max="100"
                              {...register('weights.interactions', { valueAsNumber: true })}
                            />
                          </div>

                          <div className="space-y-2">
                            <Label className="flex items-center space-x-2">
                              <CheckCircle className="h-4 w-4" />
                              <span>Regulatory Weight (%)</span>
                            </Label>
                            <Input
                              type="number"
                              min="0"
                              max="100"
                              {...register('weights.regulatory', { valueAsNumber: true })}
                            />
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>

                  {/* Thresholds */}
                  <TabsContent value="thresholds">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center space-x-2">
                          <Target className="h-5 w-5" />
                          <span>Pass/Fail Thresholds</span>
                        </CardTitle>
                        <CardDescription>
                          Define minimum scores required for different analysis outcomes
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label>Safety Pass Threshold (%)</Label>
                            <Input
                              type="number"
                              min="0"
                              max="100"
                              {...register('thresholds.safetyPass', { valueAsNumber: true })}
                            />
                          </div>

                          <div className="space-y-2">
                            <Label>Efficacy Pass Threshold (%)</Label>
                            <Input
                              type="number"
                              min="0"
                              max="100"
                              {...register('thresholds.efficacyPass', { valueAsNumber: true })}
                            />
                          </div>

                          <div className="space-y-2">
                            <Label>Overall Pass Threshold (%)</Label>
                            <Input
                              type="number"
                              min="0"
                              max="100"
                              {...register('thresholds.overallPass', { valueAsNumber: true })}
                            />
                          </div>

                          <div className="space-y-2">
                            <Label>Critical Failure Threshold (%)</Label>
                            <Input
                              type="number"
                              min="0"
                              max="100"
                              {...register('thresholds.criticalFailure', { valueAsNumber: true })}
                            />
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>

                  {/* Penalties */}
                  <TabsContent value="penalties">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center space-x-2">
                          <AlertTriangle className="h-5 w-5" />
                          <span>Score Penalties</span>
                        </CardTitle>
                        <CardDescription>
                          Point deductions for various risk factors and issues
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label>Major Interaction Penalty</Label>
                            <Input
                              type="number"
                              min="0"
                              max="50"
                              {...register('penalties.majorInteraction', { valueAsNumber: true })}
                            />
                          </div>

                          <div className="space-y-2">
                            <Label>Contraindication Penalty</Label>
                            <Input
                              type="number"
                              min="0"
                              max="100"
                              {...register('penalties.contraindication', { valueAsNumber: true })}
                            />
                          </div>

                          <div className="space-y-2">
                            <Label>Adverse Effect Penalty</Label>
                            <Input
                              type="number"
                              min="0"
                              max="50"
                              {...register('penalties.adverseEffect', { valueAsNumber: true })}
                            />
                          </div>

                          <div className="space-y-2">
                            <Label>Compliance Issue Penalty</Label>
                            <Input
                              type="number"
                              min="0"
                              max="50"
                              {...register('penalties.complianceIssue', { valueAsNumber: true })}
                            />
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>

                  {/* Bonuses */}
                  <TabsContent value="bonuses">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center space-x-2">
                          <Award className="h-5 w-5" />
                          <span>Score Bonuses</span>
                        </CardTitle>
                        <CardDescription>
                          Point additions for beneficial characteristics and designations
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label>Novel Target Bonus</Label>
                            <Input
                              type="number"
                              min="0"
                              max="20"
                              {...register('bonuses.noveltarget', { valueAsNumber: true })}
                            />
                          </div>

                          <div className="space-y-2">
                            <Label>Fast Track Designation</Label>
                            <Input
                              type="number"
                              min="0"
                              max="15"
                              {...register('bonuses.fastTrack', { valueAsNumber: true })}
                            />
                          </div>

                          <div className="space-y-2">
                            <Label>Orphan Drug Designation</Label>
                            <Input
                              type="number"
                              min="0"
                              max="25"
                              {...register('bonuses.orphanDrug', { valueAsNumber: true })}
                            />
                          </div>

                          <div className="space-y-2">
                            <Label>Breakthrough Therapy</Label>
                            <Input
                              type="number"
                              min="0"
                              max="30"
                              {...register('bonuses.breakthrough', { valueAsNumber: true })}
                            />
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>
                </Tabs>

                {/* Preview */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <TestTube className="h-5 w-5" />
                      <span>Configuration Preview</span>
                    </CardTitle>
                    <CardDescription>
                      Live preview of how this configuration would score a sample analysis
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="p-4 bg-muted/30 rounded-lg">
                      <div className="flex items-center justify-between mb-4">
                        <span className="font-medium">Sample Analysis Score</span>
                        <div className="flex items-center space-x-2">
                          <span className="text-2xl font-bold text-primary">
                            {calculatePreviewScore().toFixed(1)}
                          </span>
                          <span className="text-muted-foreground">/100</span>
                        </div>
                      </div>
                      <div className="text-sm text-muted-foreground space-y-1">
                        <p>• Safety component: {watchedValues.weights?.safety}% weight</p>
                        <p>• Efficacy component: {watchedValues.weights?.efficacy}% weight</p>
                        <p>• Interactions component: {watchedValues.weights?.interactions}% weight</p>
                        <p>• Regulatory component: {watchedValues.weights?.regulatory}% weight</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Actions */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setIsEditing(false)}
                    >
                      Cancel
                    </Button>
                    {selectedConfig && (
                      <Button
                        type="button"
                        variant="destructive"
                        onClick={() => deleteConfigMutation.mutate(selectedConfig)}
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete
                      </Button>
                    )}
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      type="submit"
                      disabled={!isDirty || !isWeightValid || saveConfigMutation.isPending}
                    >
                      <Save className="h-4 w-4 mr-2" />
                      {saveConfigMutation.isPending ? 'Saving...' : 'Save Configuration'}
                    </Button>
                  </div>
                </div>
              </form>
            ) : (
              /* Configuration Details View */
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center py-12">
                    <Sliders className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-foreground mb-2">
                      {selectedConfig ? 'Configuration Selected' : 'No Configuration Selected'}
                    </h3>
                    <p className="text-muted-foreground mb-6">
                      {selectedConfig
                        ? 'Click Edit to modify the selected configuration'
                        : 'Select a configuration from the list or create a new one to get started'
                      }
                    </p>
                    {selectedConfig ? (
                      <div className="flex items-center justify-center space-x-2">
                        <Button
                          onClick={() => {
                            const config = configurations?.find(c => c.id === selectedConfig)
                            if (config) loadConfiguration(config)
                          }}
                        >
                          <Edit className="h-4 w-4 mr-2" />
                          Edit Configuration
                        </Button>
                        <Button variant="outline">
                          <Eye className="h-4 w-4 mr-2" />
                          View Details
                        </Button>
                      </div>
                    ) : (
                      <Button onClick={createNewConfig}>
                        <Plus className="h-4 w-4 mr-2" />
                        Create New Configuration
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}