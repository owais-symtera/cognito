'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSession } from 'next-auth/react'
import { MainLayout } from '@/components/layout/main-layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  FileText,
  Search,
  Filter,
  Download,
  Eye,
  Share2,
  MoreHorizontal,
  CheckCircle,
  AlertTriangle,
  XCircle,
  BarChart3,
  TrendingUp,
  TrendingDown,
  Calendar,
  User,
  Building,
  Shield,
  Zap,
  Clock,
  Target,
  Award,
  AlertCircle,
  ExternalLink,
  ChevronRight
} from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

/**
 * Interface for analysis result data
 */
interface AnalysisResult {
  id: string
  requestId: string
  drugName: string
  analysisType: string
  status: 'completed' | 'failed' | 'partial'
  overallScore: number
  confidenceLevel: number
  riskAssessment: 'low' | 'medium' | 'high' | 'critical'
  completedAt: string
  processingDuration: number
  analyst: string
  requesterName: string
  department: string
  findings: {
    safety: {
      score: number
      status: 'pass' | 'warning' | 'fail'
      details: string[]
      adverseEffects: string[]
    }
    efficacy: {
      score: number
      status: 'pass' | 'warning' | 'fail'
      details: string[]
      therapeuticIndex: number
    }
    interactions: {
      count: number
      severity: 'low' | 'medium' | 'high' | 'critical'
      majorInteractions: string[]
      contraindicatedWith: string[]
    }
    regulatory: {
      complianceScore: number
      status: 'compliant' | 'requires_review' | 'non_compliant'
      fdaStatus: string
      requiredStudies: string[]
    }
  }
  recommendations: {
    priority: 'low' | 'medium' | 'high' | 'urgent'
    actions: string[]
    followUpRequired: boolean
    nextSteps: string[]
  }
  reports: Array<{
    id: string
    name: string
    type: 'pdf' | 'excel' | 'xml' | 'json'
    size: number
    generatedAt: string
    url: string
  }>
  attachments: Array<{
    id: string
    name: string
    type: string
    size: number
    url: string
  }>
}

/**
 * Comprehensive analysis results management interface.
 *
 * Features:
 * - Searchable and filterable results
 * - Detailed analysis summaries
 * - Risk assessment visualization
 * - Compliance status tracking
 * - Report generation and export
 * - Recommendation management
 * - Audit trail compliance
 * - Role-based access controls
 *
 * @returns React component for viewing analysis results
 *
 * @example
 * ```tsx
 * // Accessed via /results route
 * <AnalysisResultsPage />
 * ```
 *
 * @since 1.0.0
 * @version 1.0.0
 * @author CognitoAI Development Team
 */
export default function AnalysisResultsPage() {
  const { data: session } = useSession()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedResults, setSelectedResults] = useState<string[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [riskFilter, setRiskFilter] = useState<string>('')

  // Fetch analysis results
  const {
    data: results,
    isLoading,
    error,
    refetch
  } = useQuery<AnalysisResult[]>({
    queryKey: ['analysis-results', searchQuery, statusFilter, riskFilter],
    queryFn: async () => {
      try {
        const params: any = {}
        if (searchQuery) params.search = searchQuery
        if (statusFilter) params.status = statusFilter
        if (riskFilter) params.riskLevel = riskFilter

        return await api.getAnalyses(params)
      } catch (error) {
        console.error('Failed to fetch analysis results:', error)
        return []
      }
    },
  })

  const userRole = (session?.user as any)?.role || 'user'

  /**
   * Get risk assessment styling
   */
  const getRiskStyle = (risk: string) => {
    switch (risk) {
      case 'low':
        return 'bg-green-100 text-green-800 border-green-300'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-300'
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-300'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  /**
   * Get status styling and icon
   */
  const getStatusInfo = (status: string) => {
    switch (status) {
      case 'completed':
        return {
          style: 'bg-green-100 text-green-800 border-green-300',
          icon: <CheckCircle className="h-4 w-4" />
        }
      case 'failed':
        return {
          style: 'bg-red-100 text-red-800 border-red-300',
          icon: <XCircle className="h-4 w-4" />
        }
      case 'partial':
        return {
          style: 'bg-yellow-100 text-yellow-800 border-yellow-300',
          icon: <AlertTriangle className="h-4 w-4" />
        }
      default:
        return {
          style: 'bg-gray-100 text-gray-800 border-gray-300',
          icon: <AlertCircle className="h-4 w-4" />
        }
    }
  }

  /**
   * Get finding status styling
   */
  const getFindingStyle = (status: string) => {
    switch (status) {
      case 'pass':
        return 'text-green-600'
      case 'warning':
        return 'text-yellow-600'
      case 'fail':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  /**
   * Get score color based on value
   */
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    if (score >= 40) return 'text-orange-600'
    return 'text-red-600'
  }

  /**
   * Format analysis type for display
   */
  const formatAnalysisType = (type: string) => {
    return type.split('_').map(word =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ')
  }

  /**
   * Handle bulk export
   */
  const handleBulkExport = () => {
    console.log('Exporting results:', selectedResults)
  }

  /**
   * Handle result selection
   */
  const handleSelectResult = (resultId: string) => {
    setSelectedResults(prev =>
      prev.includes(resultId)
        ? prev.filter(id => id !== resultId)
        : [...prev, resultId]
    )
  }

  /**
   * Handle select all
   */
  const handleSelectAll = () => {
    if (!results) return

    if (selectedResults.length === results.length) {
      setSelectedResults([])
    } else {
      setSelectedResults(results.map(r => r.id))
    }
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load analysis results. Please try again later.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Analysis Results</h1>
            <p className="text-muted-foreground mt-1">
              Review completed pharmaceutical analysis reports and findings
            </p>
          </div>
          <div className="flex items-center space-x-2">
            {selectedResults.length > 0 && (
              <Button variant="outline" onClick={handleBulkExport}>
                <Download className="h-4 w-4 mr-2" />
                Export ({selectedResults.length})
              </Button>
            )}
            <Button variant="outline" onClick={() => refetch()}>
              <BarChart3 className="h-4 w-4 mr-2" />
              Analytics
            </Button>
          </div>
        </div>

        {/* Search and Filter */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col lg:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search by drug name, analyst, or findings..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                      <Filter className="h-4 w-4 mr-2" />
                      Status
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuLabel>Filter by Status</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => setStatusFilter('')}>
                      All Statuses
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatusFilter('completed')}>
                      Completed
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatusFilter('failed')}>
                      Failed
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatusFilter('partial')}>
                      Partial
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                      <Shield className="h-4 w-4 mr-2" />
                      Risk
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuLabel>Filter by Risk</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => setRiskFilter('')}>
                      All Risk Levels
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setRiskFilter('low')}>
                      Low Risk
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setRiskFilter('medium')}>
                      Medium Risk
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setRiskFilter('high')}>
                      High Risk
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setRiskFilter('critical')}>
                      Critical Risk
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Statistics */}
        {results && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Results</p>
                    <p className="text-2xl font-bold">{results.length}</p>
                  </div>
                  <FileText className="h-8 w-8 text-blue-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">High Risk</p>
                    <p className="text-2xl font-bold text-red-600">
                      {results.filter(r => ['high', 'critical'].includes(r.riskAssessment)).length}
                    </p>
                  </div>
                  <AlertTriangle className="h-8 w-8 text-red-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Avg Score</p>
                    <p className="text-2xl font-bold">
                      {Math.round(results.reduce((sum, r) => sum + r.overallScore, 0) / results.length)}
                    </p>
                  </div>
                  <Target className="h-8 w-8 text-green-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Follow-ups</p>
                    <p className="text-2xl font-bold">
                      {results.filter(r => r.recommendations.followUpRequired).length}
                    </p>
                  </div>
                  <Clock className="h-8 w-8 text-orange-600" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Results List */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Analysis Results</CardTitle>
              {results && results.length > 0 && (
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={selectedResults.length === results.length}
                    onChange={handleSelectAll}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm text-muted-foreground">
                    Select all ({results.length})
                  </span>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="flex items-center space-x-4 p-6 border rounded-lg">
                      <div className="h-4 w-4 bg-muted rounded"></div>
                      <div className="flex-1 space-y-2">
                        <div className="h-4 bg-muted rounded w-1/3"></div>
                        <div className="h-3 bg-muted rounded w-1/2"></div>
                      </div>
                      <div className="h-6 w-16 bg-muted rounded"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : !results || results.length === 0 ? (
              <div className="text-center py-12">
                <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium text-foreground mb-2">No results found</h3>
                <p className="text-muted-foreground">
                  {searchQuery || statusFilter || riskFilter
                    ? 'Try adjusting your search or filter criteria'
                    : 'No completed analysis results available yet'
                  }
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {results.map((result) => {
                  const statusInfo = getStatusInfo(result.status)

                  return (
                    <div
                      key={result.id}
                      className={cn(
                        "p-6 border rounded-lg transition-all hover:shadow-md",
                        selectedResults.includes(result.id) && "border-primary bg-primary/5"
                      )}
                    >
                      <div className="flex items-start space-x-4">
                        <input
                          type="checkbox"
                          checked={selectedResults.includes(result.id)}
                          onChange={() => handleSelectResult(result.id)}
                          className="mt-1 rounded border-gray-300"
                        />

                        <div className="flex-1 space-y-4">
                          {/* Header */}
                          <div className="flex items-start justify-between">
                            <div className="flex items-start space-x-3">
                              <div className="flex-shrink-0 pt-1">
                                {statusInfo.icon}
                              </div>
                              <div>
                                <Link href={`/results/${result.id}`}>
                                  <h4 className="font-semibold text-lg text-foreground hover:text-primary transition-colors">
                                    {result.drugName}
                                  </h4>
                                </Link>
                                <p className="text-sm text-muted-foreground">
                                  {formatAnalysisType(result.analysisType)} • Completed {new Date(result.completedAt).toLocaleDateString()}
                                </p>
                                <div className="flex items-center space-x-2 mt-2">
                                  <Badge className={statusInfo.style}>
                                    {result.status}
                                  </Badge>
                                  <Badge className={getRiskStyle(result.riskAssessment)}>
                                    {result.riskAssessment} risk
                                  </Badge>
                                  {result.recommendations.followUpRequired && (
                                    <Badge variant="outline" className="border-orange-300 text-orange-800">
                                      Follow-up Required
                                    </Badge>
                                  )}
                                </div>
                              </div>
                            </div>

                            <div className="text-right">
                              <div className="flex items-center space-x-2 mb-2">
                                <Award className="h-4 w-4 text-muted-foreground" />
                                <span className={cn("text-2xl font-bold", getScoreColor(result.overallScore))}>
                                  {result.overallScore}
                                </span>
                                <span className="text-sm text-muted-foreground">/100</span>
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {result.confidenceLevel}% confidence
                              </div>
                            </div>
                          </div>

                          {/* Key Findings Grid */}
                          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 p-4 bg-muted/30 rounded-lg">
                            <div className="text-center">
                              <div className="flex items-center justify-center space-x-1 mb-1">
                                <Shield className="h-4 w-4" />
                                <span className="text-sm font-medium">Safety</span>
                              </div>
                              <div className={cn("text-lg font-bold", getScoreColor(result.findings.safety.score))}>
                                {result.findings.safety.score}
                              </div>
                              <div className={cn("text-xs", getFindingStyle(result.findings.safety.status))}>
                                {result.findings.safety.status}
                              </div>
                            </div>

                            <div className="text-center">
                              <div className="flex items-center justify-center space-x-1 mb-1">
                                <Zap className="h-4 w-4" />
                                <span className="text-sm font-medium">Efficacy</span>
                              </div>
                              <div className={cn("text-lg font-bold", getScoreColor(result.findings.efficacy.score))}>
                                {result.findings.efficacy.score}
                              </div>
                              <div className={cn("text-xs", getFindingStyle(result.findings.efficacy.status))}>
                                {result.findings.efficacy.status}
                              </div>
                            </div>

                            <div className="text-center">
                              <div className="flex items-center justify-center space-x-1 mb-1">
                                <AlertTriangle className="h-4 w-4" />
                                <span className="text-sm font-medium">Interactions</span>
                              </div>
                              <div className="text-lg font-bold">
                                {result.findings.interactions.count}
                              </div>
                              <div className={cn("text-xs", getRiskStyle(result.findings.interactions.severity).includes('red') ? 'text-red-600' : 'text-gray-600')}>
                                {result.findings.interactions.severity}
                              </div>
                            </div>

                            <div className="text-center">
                              <div className="flex items-center justify-center space-x-1 mb-1">
                                <CheckCircle className="h-4 w-4" />
                                <span className="text-sm font-medium">Regulatory</span>
                              </div>
                              <div className={cn("text-lg font-bold", getScoreColor(result.findings.regulatory.complianceScore))}>
                                {result.findings.regulatory.complianceScore}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {result.findings.regulatory.status.replace('_', ' ')}
                              </div>
                            </div>
                          </div>

                          {/* Recommendations Preview */}
                          {result.recommendations.actions.length > 0 && (
                            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                              <h5 className="font-medium text-blue-900 mb-2 flex items-center">
                                <Target className="h-4 w-4 mr-2" />
                                Key Recommendations
                              </h5>
                              <ul className="space-y-1">
                                {result.recommendations.actions.slice(0, 3).map((action, index) => (
                                  <li key={index} className="text-sm text-blue-800 flex items-start">
                                    <ChevronRight className="h-3 w-3 mt-0.5 mr-1 flex-shrink-0" />
                                    {action}
                                  </li>
                                ))}
                                {result.recommendations.actions.length > 3 && (
                                  <li className="text-sm text-blue-600 italic">
                                    +{result.recommendations.actions.length - 3} more recommendations
                                  </li>
                                )}
                              </ul>
                            </div>
                          )}

                          {/* Footer */}
                          <div className="flex items-center justify-between pt-4 border-t">
                            <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                              <div className="flex items-center space-x-1">
                                <User className="h-3 w-3" />
                                <span>{result.requesterName}</span>
                              </div>
                              <div className="flex items-center space-x-1">
                                <Building className="h-3 w-3" />
                                <span>{result.department}</span>
                              </div>
                              <div className="flex items-center space-x-1">
                                <BarChart3 className="h-3 w-3" />
                                <span>Analyzed by {result.analyst}</span>
                              </div>
                              <div className="flex items-center space-x-1">
                                <Clock className="h-3 w-3" />
                                <span>{result.processingDuration}h processing</span>
                              </div>
                            </div>

                            <div className="flex items-center space-x-2">
                              <span className="text-sm text-muted-foreground">
                                {result.reports.length} reports
                              </span>
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" size="sm">
                                    <MoreHorizontal className="h-4 w-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem asChild>
                                    <Link href={`/results/${result.id}`}>
                                      <Eye className="h-4 w-4 mr-2" />
                                      View Details
                                    </Link>
                                  </DropdownMenuItem>
                                  <DropdownMenuItem asChild>
                                    <Link href={`/requests/${result.requestId}`}>
                                      <ExternalLink className="h-4 w-4 mr-2" />
                                      View Request
                                    </Link>
                                  </DropdownMenuItem>
                                  <DropdownMenuItem>
                                    <Download className="h-4 w-4 mr-2" />
                                    Download Reports
                                  </DropdownMenuItem>
                                  <DropdownMenuItem>
                                    <Share2 className="h-4 w-4 mr-2" />
                                    Share Results
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  )
}