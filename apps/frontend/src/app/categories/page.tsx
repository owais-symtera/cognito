'use client'

import { useState, useEffect } from 'react'
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
  Tags,
  Edit,
  AlertCircle,
  CheckCircle,
  Activity,
  Database,
  Brain,
  Search,
  Settings,
  Eye,
  EyeOff,
  Layers,
  Target
} from 'lucide-react'

interface Category {
  id: number
  key: string
  name: string
  phase: number
  enabled: boolean
  description: string
  prompt_template?: string
  weight?: number
  source_priorities?: string[]
  requires_phase1?: boolean
}

interface CategoriesResponse {
  categories: Category[]
  total: number
  phase1_count: number
  phase2_count: number
}

export default function CategoriesPage() {
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null)
  const [promptTemplate, setPromptTemplate] = useState('')
  const [weight, setWeight] = useState<number>(1.0)
  const queryClient = useQueryClient()

  // Fetch categories
  const { data: categoriesData, isLoading, error } = useQuery<CategoriesResponse>({
    queryKey: ['categories'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/categories`)
      if (!response.ok) throw new Error('Failed to fetch categories')
      return response.json()
    }
  })

  // Update category mutation
  const updateMutation = useMutation({
    mutationFn: async ({ key, ...data }: { key: string; enabled?: boolean; weight?: number; prompt_template?: string }) => {
      const response = await fetch(`${API_BASE_URL}/api/v1/categories/${key}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      if (!response.ok) throw new Error('Failed to update category')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      setIsEditDialogOpen(false)
      setSelectedCategory(null)
    }
  })

  // Toggle category enabled/disabled
  const toggleCategory = (category: Category) => {
    updateMutation.mutate({
      key: category.key,
      enabled: !category.enabled
    })
  }

  // Handle edit dialog
  const handleEdit = (category: Category) => {
    setSelectedCategory(category)
    setPromptTemplate(category.prompt_template || '')
    setWeight(category.weight || 1.0)
    setIsEditDialogOpen(true)
  }

  // Handle prompt update
  const handleUpdatePrompt = () => {
    if (selectedCategory) {
      updateMutation.mutate({
        key: selectedCategory.key,
        prompt_template: promptTemplate,
        weight: weight
      })
    }
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
          <AlertDescription>
            Failed to load categories. Please ensure the backend is running.
          </AlertDescription>
        </Alert>
      </MainLayout>
    )
  }

  const categories = categoriesData?.categories || []
  const phase1Categories = categories.filter(c => c.phase === 1)
  const phase2Categories = categories.filter(c => c.phase === 2)

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold">Pharmaceutical Intelligence Categories</h1>
          <p className="text-muted-foreground">
            Manage the 17 pharmaceutical categories used for drug intelligence analysis
          </p>
        </div>

        {/* Statistics Cards */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Categories</CardTitle>
              <Tags className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{categoriesData?.total || 0}</div>
              <p className="text-xs text-muted-foreground">
                Intelligence categories
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Phase 1 (Data)</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{categoriesData?.phase1_count || 0}</div>
              <p className="text-xs text-muted-foreground">
                Data collection categories
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Phase 2 (Intelligence)</CardTitle>
              <Brain className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{categoriesData?.phase2_count || 0}</div>
              <p className="text-xs text-muted-foreground">
                Decision intelligence
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Enabled</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {categories.filter(c => c.enabled).length}
              </div>
              <p className="text-xs text-muted-foreground">
                Active categories
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Categories Tabs */}
        <Card>
          <CardHeader>
            <CardTitle>Category Configuration</CardTitle>
            <CardDescription>
              Configure prompts and settings for each intelligence category
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="phase1" className="space-y-4">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="phase1" className="flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  Phase 1: Data Collection
                </TabsTrigger>
                <TabsTrigger value="phase2" className="flex items-center gap-2">
                  <Brain className="h-4 w-4" />
                  Phase 2: Decision Intelligence
                </TabsTrigger>
              </TabsList>

              {/* Phase 1 Categories */}
              <TabsContent value="phase1" className="space-y-4">
                <div className="text-sm text-muted-foreground mb-4">
                  Data collection categories gather pharmaceutical intelligence from multiple sources
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[50px]">ID</TableHead>
                      <TableHead>Category Name</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead className="w-[100px]">Weight</TableHead>
                      <TableHead className="w-[100px]">Status</TableHead>
                      <TableHead className="w-[100px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {phase1Categories.map((category) => (
                      <TableRow key={category.key}>
                        <TableCell className="font-medium">{category.id}</TableCell>
                        <TableCell>
                          <div className="font-semibold">{category.name}</div>
                          <div className="text-xs text-muted-foreground">{category.key}</div>
                        </TableCell>
                        <TableCell className="max-w-md">
                          <div className="truncate text-sm">
                            {category.description}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">
                            {category.weight || 1.0}x
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={category.enabled}
                              onCheckedChange={() => toggleCategory(category)}
                              disabled={updateMutation.isPending}
                            />
                            {category.enabled ? (
                              <Eye className="h-4 w-4 text-green-500" />
                            ) : (
                              <EyeOff className="h-4 w-4 text-gray-400" />
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleEdit(category)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TabsContent>

              {/* Phase 2 Categories */}
              <TabsContent value="phase2" className="space-y-4">
                <div className="text-sm text-muted-foreground mb-4">
                  Decision intelligence categories analyze Phase 1 data to provide strategic insights
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[50px]">ID</TableHead>
                      <TableHead>Category Name</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead className="w-[100px]">Weight</TableHead>
                      <TableHead className="w-[100px]">Status</TableHead>
                      <TableHead className="w-[100px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {phase2Categories.map((category) => (
                      <TableRow key={category.key}>
                        <TableCell className="font-medium">{category.id}</TableCell>
                        <TableCell>
                          <div className="font-semibold">{category.name}</div>
                          <div className="text-xs text-muted-foreground">{category.key}</div>
                        </TableCell>
                        <TableCell className="max-w-md">
                          <div className="truncate text-sm">
                            {category.description}
                          </div>
                          {category.requires_phase1 && (
                            <Badge variant="outline" className="mt-1">
                              <Layers className="h-3 w-3 mr-1" />
                              Requires Phase 1
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">
                            {category.weight || 1.0}x
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={category.enabled}
                              onCheckedChange={() => toggleCategory(category)}
                              disabled={updateMutation.isPending}
                            />
                            {category.enabled ? (
                              <Eye className="h-4 w-4 text-green-500" />
                            ) : (
                              <EyeOff className="h-4 w-4 text-gray-400" />
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleEdit(category)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Configuration Tips */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Configuration Guide
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <h4 className="font-semibold">Phase 1: Data Collection</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Gathers data from multiple API sources</li>
                  <li>• Uses temperature variations (0.1, 0.5, 0.9)</li>
                  <li>• Hierarchical source prioritization applied</li>
                  <li>• Each category focuses on specific intel</li>
                </ul>
              </div>
              <div className="space-y-2">
                <h4 className="font-semibold">Phase 2: Decision Intelligence</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Analyzes Phase 1 collected data</li>
                  <li>• Provides strategic recommendations</li>
                  <li>• Generates investment analysis</li>
                  <li>• Creates executive summaries</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Edit Dialog */}
        <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
          <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Edit Category: {selectedCategory?.name}</DialogTitle>
              <DialogDescription>
                Configure the prompt template and weight for this intelligence category
              </DialogDescription>
            </DialogHeader>
            {selectedCategory && (
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Category Details</Label>
                    <Badge variant={selectedCategory.phase === 1 ? "default" : "secondary"}>
                      Phase {selectedCategory.phase}
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    <p><strong>Key:</strong> {selectedCategory.key}</p>
                    <p><strong>ID:</strong> {selectedCategory.id}</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="weight">Weight (Priority Multiplier)</Label>
                  <div className="flex items-center gap-4">
                    <Input
                      id="weight"
                      type="number"
                      step="0.1"
                      min="0.1"
                      max="2.0"
                      value={weight}
                      onChange={(e) => setWeight(parseFloat(e.target.value))}
                      className="w-32"
                    />
                    <span className="text-sm text-muted-foreground">
                      Higher weight = higher priority in analysis
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="prompt">Prompt Template</Label>
                  <Textarea
                    id="prompt"
                    value={promptTemplate}
                    onChange={(e) => setPromptTemplate(e.target.value)}
                    placeholder="Enter the prompt template for this category..."
                    rows={10}
                    className="font-mono text-sm"
                  />
                  <p className="text-xs text-muted-foreground">
                    Use {'{drug_name}'} as a placeholder for the drug being analyzed
                  </p>
                </div>

                {selectedCategory.source_priorities && (
                  <div className="space-y-2">
                    <Label>Source Priorities</Label>
                    <div className="flex flex-wrap gap-2">
                      {selectedCategory.source_priorities.map((source, idx) => (
                        <Badge key={idx} variant="outline">
                          {source}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setIsEditDialogOpen(false)
                  setSelectedCategory(null)
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleUpdatePrompt}
                disabled={updateMutation.isPending}
              >
                {updateMutation.isPending ? 'Updating...' : 'Save Changes'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </MainLayout>
  )
}