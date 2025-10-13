'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import {
  BarChart3,
  Calculator,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Download,
  Info
} from 'lucide-react'
import { api } from '@/lib/api'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

interface ScoringRange {
  score: number
  min_value?: number | null
  max_value?: number | null
  range_text: string
  is_exclusion: boolean
}

interface Parameter {
  id: number
  name: string
  unit: string
  description: string
  category: {
    id: number
    name: string
    weightage: number
  }
}

interface ScoringMatrix {
  id: number
  name: string
  weightage: number
  description: string
  parameters: Array<{
    id: number
    name: string
    unit: string
    description: string
    ranges: {
      transdermal: ScoringRange[]
      transmucosal: ScoringRange[]
    }
  }>
}

export default function TechnologyScoringPage() {
  const [deliveryMethod, setDeliveryMethod] = useState<'Transdermal' | 'Transmucosal'>('Transdermal')
  const [inputValues, setInputValues] = useState<Record<string, string>>({
    'Dose': '',
    'Molecular Weight': '',
    'Melting Point': '',
    'Log P': ''
  })
  const [calculatedScore, setCalculatedScore] = useState<any>(null)

  // Fetch full scoring matrix
  const { data: matrixData, isLoading, error, refetch } = useQuery<{ matrix: ScoringMatrix[] }>({
    queryKey: ['technology-scoring-matrix'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/technology-scoring/matrix`)
      if (!response.ok) throw new Error('Failed to fetch scoring matrix')
      return response.json()
    }
  })

  const handleCalculateScore = async () => {
    try {
      const values: Record<string, number> = {}
      Object.keys(inputValues).forEach(key => {
        if (inputValues[key]) {
          values[key] = parseFloat(inputValues[key])
        }
      })

      const response = await fetch(`${API_BASE_URL}/api/v1/technology-scoring/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          delivery_method: deliveryMethod,
          values
        })
      })

      if (!response.ok) throw new Error('Failed to calculate score')
      const data = await response.json()
      setCalculatedScore(data)
    } catch (error) {
      console.error('Error calculating score:', error)
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 7) return 'bg-green-100 text-green-800'
    if (score >= 4) return 'bg-yellow-100 text-yellow-800'
    return 'bg-red-100 text-red-800'
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load scoring matrix. Please try again later.
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
            <h1 className="text-3xl font-bold text-foreground">Technology Go/No-Go Scoring Matrix</h1>
            <p className="text-muted-foreground mt-1">
              Database-driven pharmaceutical delivery scoring system with weighted parameters
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
            <Button variant="outline">
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {matrixData?.matrix.map((category) => (
            <Card key={category.id}>
              <CardHeader className="pb-2">
                <CardDescription className="text-xs">{category.name}</CardDescription>
                <CardTitle className="text-2xl font-bold">
                  {category.weightage}%
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">
                  {category.parameters.length} parameter{category.parameters.length !== 1 ? 's' : ''}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Scoring Matrix Tables */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <BarChart3 className="h-5 w-5" />
                  <span>Scoring Ranges</span>
                </CardTitle>
                <CardDescription>
                  View detailed scoring ranges for each parameter and delivery method
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="Transdermal" className="w-full">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="Transdermal">Transdermal</TabsTrigger>
                    <TabsTrigger value="Transmucosal">Transmucosal</TabsTrigger>
                  </TabsList>

                  {['Transdermal', 'Transmucosal'].map((method) => (
                    <TabsContent key={method} value={method} className="space-y-6">
                      {isLoading ? (
                        <div className="text-center py-8">
                          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground mx-auto" />
                          <p className="text-sm text-muted-foreground mt-2">Loading matrix...</p>
                        </div>
                      ) : (
                        matrixData?.matrix.map((category) => (
                          <div key={category.id} className="space-y-3">
                            <div className="flex items-center justify-between">
                              <div>
                                <h3 className="font-semibold text-lg">{category.name}</h3>
                                <p className="text-sm text-muted-foreground">
                                  Weightage: {category.weightage}%
                                </p>
                              </div>
                              <Badge variant="outline">{category.parameters.length} params</Badge>
                            </div>

                            {category.parameters.map((param) => {
                              const ranges = method === 'Transdermal' ? param.ranges.transdermal : param.ranges.transmucosal
                              return (
                                <Card key={param.id} className="border-muted">
                                  <CardHeader className="pb-3">
                                    <CardTitle className="text-base">
                                      {param.name} {param.unit && `(${param.unit})`}
                                    </CardTitle>
                                    <CardDescription className="text-xs">
                                      {param.description}
                                    </CardDescription>
                                  </CardHeader>
                                  <CardContent>
                                    <Table>
                                      <TableHeader>
                                        <TableRow>
                                          <TableHead className="w-20">Score</TableHead>
                                          <TableHead>Range</TableHead>
                                          <TableHead className="w-24">Status</TableHead>
                                        </TableRow>
                                      </TableHeader>
                                      <TableBody>
                                        {ranges.map((range, idx) => (
                                          <TableRow key={idx}>
                                            <TableCell>
                                              <Badge className={getScoreColor(range.score)}>
                                                {range.score}
                                              </Badge>
                                            </TableCell>
                                            <TableCell className="font-medium">
                                              {range.range_text}
                                            </TableCell>
                                            <TableCell>
                                              {range.is_exclusion ? (
                                                <Badge variant="destructive" className="text-xs">
                                                  Exclusion
                                                </Badge>
                                              ) : (
                                                <Badge variant="outline" className="text-xs">
                                                  Valid
                                                </Badge>
                                              )}
                                            </TableCell>
                                          </TableRow>
                                        ))}
                                      </TableBody>
                                    </Table>
                                  </CardContent>
                                </Card>
                              )
                            })}
                          </div>
                        ))
                      )}
                    </TabsContent>
                  ))}
                </Tabs>
              </CardContent>
            </Card>
          </div>

          {/* Calculator Sidebar */}
          <div className="lg:col-span-1">
            <Card className="sticky top-6">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Calculator className="h-5 w-5" />
                  <span>Score Calculator</span>
                </CardTitle>
                <CardDescription>
                  Enter parameter values to calculate weighted score
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Delivery Method */}
                <div className="space-y-2">
                  <Label>Delivery Method</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      variant={deliveryMethod === 'Transdermal' ? 'default' : 'outline'}
                      onClick={() => setDeliveryMethod('Transdermal')}
                      className="w-full"
                    >
                      Transdermal
                    </Button>
                    <Button
                      variant={deliveryMethod === 'Transmucosal' ? 'default' : 'outline'}
                      onClick={() => setDeliveryMethod('Transmucosal')}
                      className="w-full"
                    >
                      Transmucosal
                    </Button>
                  </div>
                </div>

                {/* Input Fields */}
                <div className="space-y-3">
                  {Object.keys(inputValues).map((param) => {
                    const paramInfo = matrixData?.matrix
                      .flatMap(c => c.parameters)
                      .find(p => p.name === param)
                    return (
                      <div key={param} className="space-y-1">
                        <Label htmlFor={param}>
                          {param} {paramInfo?.unit && `(${paramInfo.unit})`}
                        </Label>
                        <Input
                          id={param}
                          type="number"
                          step="any"
                          value={inputValues[param]}
                          onChange={(e) => setInputValues({
                            ...inputValues,
                            [param]: e.target.value
                          })}
                          placeholder={`Enter ${param.toLowerCase()}`}
                        />
                      </div>
                    )
                  })}
                </div>

                <Button className="w-full" onClick={handleCalculateScore}>
                  <Calculator className="h-4 w-4 mr-2" />
                  Calculate Score
                </Button>

                {/* Results */}
                {calculatedScore && (
                  <Card className="bg-muted/50">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base">Calculation Results</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Total Weighted Score:</span>
                        <Badge className="text-lg px-3 py-1">
                          {calculatedScore.total_weighted_score}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Max Possible:</span>
                        <span className="text-sm">{calculatedScore.max_possible_score}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Percentage:</span>
                        <span className="text-sm font-bold">{calculatedScore.percentage}%</span>
                      </div>

                      {calculatedScore.has_exclusions && (
                        <Alert variant="destructive">
                          <AlertTriangle className="h-4 w-4" />
                          <AlertDescription className="text-xs">
                            One or more parameters fall in exclusion range
                          </AlertDescription>
                        </Alert>
                      )}

                      <div className="space-y-2 pt-2 border-t">
                        <p className="text-xs font-medium text-muted-foreground">Parameter Scores:</p>
                        {calculatedScore.results?.map((result: any, idx: number) => (
                          <div key={idx} className="flex items-center justify-between text-xs">
                            <span className="text-muted-foreground">{result.parameter}:</span>
                            <div className="flex items-center space-x-2">
                              <span className="font-medium">{result.weighted_score.toFixed(2)}</span>
                              <Badge variant="outline" className="text-xs">
                                {result.raw_score}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Info */}
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription className="text-xs">
                    Weighted scores are calculated by multiplying raw scores (0-9) by category weightages
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
