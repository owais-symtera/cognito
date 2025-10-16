'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  AlertTriangle,
  ArrowLeft,
  FileText,
  Plus
} from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'
import { MainLayout } from '@/components/layout/main-layout'

/**
 * Simple form validation schema matching backend requirements
 */
const drugRequestSchema = z.object({
  drugName: z.string().min(2, 'Drug name must be at least 2 characters'),
  webhookUrl: z.string().url('Please enter a valid URL').optional().or(z.literal('')),
})

type DrugRequestForm = z.infer<typeof drugRequestSchema>

/**
 * Simplified drug request form component matching backend API.
 * Backend expects only: requestId, drugName, webhookUrl
 */
export default function NewDrugRequestPage() {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [generatedRequestId, setGeneratedRequestId] = useState<string>('')

  // Generate request ID on component mount
  useEffect(() => {
    const requestId = `REQ-${Date.now()}-${Math.random().toString(36).substr(2, 9).toUpperCase()}`
    setGeneratedRequestId(requestId)
  }, [])

  const {
    register,
    handleSubmit,
    formState: { errors, isValid }
  } = useForm<DrugRequestForm>({
    resolver: zodResolver(drugRequestSchema),
    mode: 'onChange',
    defaultValues: {
      drugName: '',
      webhookUrl: ''
    }
  })

  const createRequestMutation = useMutation({
    mutationFn: (data: any) => api.createRequest(data),
    onSuccess: (response: any) => {
      // The response contains requestId field
      router.push(`/requests/${response.requestId}`)
    },
    onError: (error: any) => {
      console.error('Failed to create request:', error)
      setIsSubmitting(false)
    }
  })

  /**
   * Handle form submission
   */
  const onSubmit = async (data: DrugRequestForm) => {
    setIsSubmitting(true)
    try {
      // Backend expects: requestId, drugName, webhookUrl
      // Use the pre-generated request ID
      const backendPayload = {
        requestId: generatedRequestId,
        drugName: data.drugName,
        webhookUrl: data.webhookUrl || undefined
      }

      await createRequestMutation.mutateAsync(backendPayload)
    } catch (error) {
      console.error('Failed to create request:', error)
      setIsSubmitting(false)
    }
  }

  return (
    <MainLayout>
      <div className="container mx-auto px-4 py-6 max-w-2xl">
        {/* Header */}
        <div className="flex items-center space-x-4 mb-6">
          <Link href="/requests">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Requests
            </Button>
          </Link>
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-foreground">New Drug Analysis Request</h1>
            <p className="text-muted-foreground mt-1">
              Submit a pharmaceutical compound for analysis
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <FileText className="h-5 w-5" />
                <span>Request Information</span>
              </CardTitle>
              <CardDescription>
                Enter the drug name and optional webhook URL for notifications
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="requestId">Request ID</Label>
                <Input
                  id="requestId"
                  value={generatedRequestId}
                  disabled
                  className="bg-muted"
                />
                <p className="text-xs text-muted-foreground">
                  Auto-generated unique identifier for this request
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="drugName">Drug Name *</Label>
                <Input
                  id="drugName"
                  {...register('drugName')}
                  placeholder="Enter drug or compound name"
                  disabled={isSubmitting}
                />
                {errors.drugName && (
                  <p className="text-sm text-red-600">{errors.drugName.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="webhookUrl">Webhook URL (Optional)</Label>
                <Input
                  id="webhookUrl"
                  {...register('webhookUrl')}
                  placeholder="https://your-server.com/webhook"
                  disabled={isSubmitting}
                />
                {errors.webhookUrl && (
                  <p className="text-sm text-red-600">{errors.webhookUrl.message}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Provide a webhook URL to receive updates when the analysis is complete
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Error Display */}
          {createRequestMutation.error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Failed to submit request: {(createRequestMutation.error as any).message}
              </AlertDescription>
            </Alert>
          )}

          {/* Submit Button */}
          <div className="flex justify-end space-x-4">
            <Link href="/requests">
              <Button type="button" variant="outline" disabled={isSubmitting}>
                Cancel
              </Button>
            </Link>
            <Button
              type="submit"
              disabled={!isValid || isSubmitting}
              className="min-w-32"
            >
              {isSubmitting ? (
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Creating...</span>
                </div>
              ) : (
                <div className="flex items-center space-x-2">
                  <Plus className="h-4 w-4" />
                  <span>Create Request</span>
                </div>
              )}
            </Button>
          </div>
        </form>
      </div>
    </MainLayout>
  )
}