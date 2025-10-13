/**
 * Shared TypeScript type definitions for CognitoAI Engine
 *
 * This module provides type safety across the entire pharmaceutical intelligence
 * platform, ensuring consistency between frontend and backend components.
 *
 * All types follow pharmaceutical industry standards and regulatory compliance
 * requirements for comprehensive audit trails and source tracking.
 *
 * @version 1.0.0
 * @author CognitoAI Development Team
 * @since 1.0.0
 */

/**
 * Status enumeration for drug request processing.
 *
 * Represents the current state of pharmaceutical intelligence processing
 * with real-time updates and comprehensive state tracking.
 *
 * @since 1.0.0
 */
export type RequestStatus = 'pending' | 'processing' | 'completed' | 'failed';

/**
 * API provider enumeration for multi-source intelligence gathering.
 *
 * Defines the external APIs integrated for comprehensive pharmaceutical
 * data collection with source attribution and conflict resolution.
 *
 * @since 1.0.0
 */
export type APIProvider = 'chatgpt' | 'perplexity' | 'grok' | 'gemini' | 'tavily';

/**
 * Source verification status for regulatory compliance.
 *
 * Tracks the verification state of pharmaceutical sources for audit trails
 * and regulatory compliance reporting.
 *
 * @since 1.0.0
 */
export type VerificationStatus = 'pending' | 'verified' | 'disputed' | 'invalid';

/**
 * Source type classification for pharmaceutical intelligence.
 *
 * Categorizes sources by type for priority scoring and credibility assessment
 * in pharmaceutical regulatory environments.
 *
 * @since 1.0.0
 */
export type SourceType = 'research_paper' | 'clinical_trial' | 'news' | 'regulatory' | 'government' | 'industry' | 'other';

/**
 * Core drug request interface for pharmaceutical intelligence processing.
 *
 * Represents a complete pharmaceutical analysis request with comprehensive
 * tracking, progress monitoring, and audit trail support for regulatory compliance.
 *
 * @interface DrugRequest
 * @since 1.0.0
 *
 * @example
 * ```typescript
 * const request: DrugRequest = {
 *   id: 'req-123',
 *   drugName: 'Aspirin',
 *   status: 'processing',
 *   createdAt: '2024-01-01T10:00:00Z',
 *   updatedAt: '2024-01-01T10:05:00Z',
 *   userId: 'user-456',
 *   totalCategories: 17,
 *   completedCategories: 5,
 *   failedCategories: []
 * };
 * ```
 */
export interface DrugRequest {
  /**
   * Unique identifier for the pharmaceutical request.
   * Generated using UUID v4 for global uniqueness and audit tracking.
   * @since 1.0.0
   */
  id: string;

  /**
   * Name of the pharmaceutical drug being analyzed.
   * Must be non-empty and contain only valid pharmaceutical compound characters.
   * @since 1.0.0
   * @example "Aspirin", "Metformin", "Ibuprofen"
   */
  drugName: string;

  /**
   * Current processing status of the pharmaceutical request.
   * Updated in real-time during processing for user feedback and monitoring.
   * @since 1.0.0
   */
  status: RequestStatus;

  /**
   * ISO 8601 timestamp when the request was created.
   * Used for audit trails, performance tracking, and compliance reporting.
   * @since 1.0.0
   */
  createdAt: string;

  /**
   * ISO 8601 timestamp when the request was last updated.
   * Maintained for real-time progress tracking and audit compliance.
   * @since 1.0.0
   */
  updatedAt: string;

  /**
   * ISO 8601 timestamp when processing completed (if applicable).
   * Used for performance analysis and completion tracking.
   * @since 1.0.0
   */
  completedAt?: string;

  /**
   * Optional identifier of the user who submitted the request.
   * Used for audit trails and user-specific filtering in compliance reporting.
   * @since 1.0.0
   */
  userId?: string;

  /**
   * Total number of pharmaceutical categories to process.
   * Default is 17 for comprehensive pharmaceutical intelligence analysis.
   * @default 17
   * @since 1.0.0
   */
  totalCategories: number;

  /**
   * Number of categories successfully completed.
   * Updated in real-time during processing for progress tracking.
   * @since 1.0.0
   */
  completedCategories: number;

  /**
   * Array of category names that failed during processing.
   * Used for error reporting and retry logic in pharmaceutical analysis.
   * @since 1.0.0
   */
  failedCategories: string[];
}

/**
 * Category processing result interface with comprehensive source tracking.
 *
 * Represents the complete analysis result for a single pharmaceutical category
 * including source attribution, conflict resolution, and quality metrics.
 *
 * @interface CategoryResult
 * @since 1.0.0
 *
 * @example
 * ```typescript
 * const result: CategoryResult = {
 *   id: 'cat-789',
 *   requestId: 'req-123',
 *   categoryName: 'Clinical Trials',
 *   categoryId: 2,
 *   summary: 'Comprehensive clinical trial analysis...',
 *   confidenceScore: 0.92,
 *   dataQualityScore: 0.88,
 *   status: 'completed',
 *   processingTimeMs: 45000,
 *   retryCount: 0,
 *   startedAt: '2024-01-01T10:01:00Z',
 *   completedAt: '2024-01-01T10:01:45Z',
 *   sources: [],
 *   conflicts: []
 * };
 * ```
 */
export interface CategoryResult {
  /**
   * Unique identifier for the category result.
   * Links to audit trail and source tracking for regulatory compliance.
   * @since 1.0.0
   */
  id: string;

  /**
   * Identifier of the parent drug request.
   * Maintains relationship hierarchy for comprehensive audit trails.
   * @since 1.0.0
   */
  requestId: string;

  /**
   * Human-readable name of the pharmaceutical category.
   * @since 1.0.0
   * @example "Clinical Trials", "Market Overview", "Regulatory Status"
   */
  categoryName: string;

  /**
   * Numeric identifier of the pharmaceutical category.
   * Links to database-driven category configuration and rules.
   * @since 1.0.0
   */
  categoryId: number;

  /**
   * Comprehensive summary of pharmaceutical intelligence findings.
   * Generated through multi-source analysis and conflict resolution.
   * @since 1.0.0
   */
  summary: string;

  /**
   * Confidence score for the analysis result (0.0 to 1.0).
   * Based on source credibility, consistency, and verification status.
   * @since 1.0.0
   */
  confidenceScore: number;

  /**
   * Data quality score for regulatory compliance (0.0 to 1.0).
   * Reflects completeness, accuracy, and source reliability.
   * @since 1.0.0
   */
  dataQualityScore: number;

  /**
   * Current processing status of the category analysis.
   * Updated in real-time for progress monitoring and error handling.
   * @since 1.0.0
   */
  status: RequestStatus;

  /**
   * Total processing time in milliseconds.
   * Used for performance monitoring and system optimization.
   * @since 1.0.0
   */
  processingTimeMs: number;

  /**
   * Number of retry attempts for failed processing.
   * Tracks system resilience and error recovery in pharmaceutical analysis.
   * @since 1.0.0
   */
  retryCount: number;

  /**
   * Error message if processing failed.
   * Provides detailed debugging information for pharmaceutical compliance reviews.
   * @since 1.0.0
   */
  errorMessage?: string;

  /**
   * ISO 8601 timestamp when category processing started.
   * Used for performance analysis and audit trail completeness.
   * @since 1.0.0
   */
  startedAt: string;

  /**
   * ISO 8601 timestamp when category processing completed.
   * Used for completion tracking and performance benchmarking.
   * @since 1.0.0
   */
  completedAt?: string;

  /**
   * Array of source references contributing to this category result.
   * Provides complete source attribution for regulatory compliance.
   * @since 1.0.0
   */
  sources: SourceReference[];

  /**
   * Array of detected source conflicts requiring resolution.
   * Maintains transparency in conflict detection and resolution processes.
   * @since 1.0.0
   */
  conflicts: SourceConflict[];
}

/**
 * Source reference interface for comprehensive pharmaceutical source tracking.
 *
 * Represents a single source of pharmaceutical information with complete
 * attribution, credibility assessment, and verification status for regulatory compliance.
 *
 * @interface SourceReference
 * @since 1.0.0
 */
export interface SourceReference {
  /**
   * Unique identifier for the source reference.
   * Links to audit trail and verification history.
   * @since 1.0.0
   */
  id: string;

  /**
   * Identifier of the parent category result.
   * Maintains relationship hierarchy for comprehensive audit trails.
   * @since 1.0.0
   */
  categoryResultId: string;

  /**
   * API provider that supplied this source information.
   * Used for source attribution and credibility weighting.
   * @since 1.0.0
   */
  apiProvider: APIProvider;

  /**
   * URL of the source material (if available).
   * Provides direct access to original pharmaceutical information.
   * @since 1.0.0
   */
  sourceUrl?: string;

  /**
   * Title of the source document or article.
   * Used for source identification and citation in compliance reports.
   * @since 1.0.0
   */
  sourceTitle?: string;

  /**
   * Classification of the source type for priority scoring.
   * Determines credibility weighting in pharmaceutical analysis.
   * @since 1.0.0
   */
  sourceType: SourceType;

  /**
   * Relevant excerpt from the source content.
   * Provides context for pharmaceutical intelligence findings.
   * @since 1.0.0
   */
  contentSnippet: string;

  /**
   * Relevance score for the pharmaceutical query (0.0 to 1.0).
   * Measures how well the source addresses the specific drug analysis.
   * @since 1.0.0
   */
  relevanceScore: number;

  /**
   * Credibility score based on source authority (0.0 to 1.0).
   * Determined by source type, domain authority, and verification status.
   * @since 1.0.0
   */
  credibilityScore: number;

  /**
   * Publication date of the source material.
   * Used for temporal relevance and currency assessment.
   * @since 1.0.0
   */
  publishedDate?: string;

  /**
   * Authors of the source material.
   * Provides additional credibility context for pharmaceutical research.
   * @since 1.0.0
   */
  authors?: string;

  /**
   * Journal or publication name.
   * Used for academic source credibility assessment.
   * @since 1.0.0
   */
  journalName?: string;

  /**
   * Digital Object Identifier for academic sources.
   * Enables direct verification and citation in compliance reports.
   * @since 1.0.0
   */
  doi?: string;

  /**
   * ISO 8601 timestamp when the source was extracted.
   * Used for audit trails and temporal analysis.
   * @since 1.0.0
   */
  extractedAt: string;

  /**
   * Reference to the original API response.
   * Maintains complete audit trail back to raw data.
   * @since 1.0.0
   */
  apiResponseId?: string;

  /**
   * Current verification status for regulatory compliance.
   * Tracks the validation state of pharmaceutical sources.
   * @since 1.0.0
   */
  verificationStatus: VerificationStatus;

  /**
   * ISO 8601 timestamp when verification was completed.
   * Used for verification audit trails and compliance reporting.
   * @since 1.0.0
   */
  verifiedAt?: string;

  /**
   * Identifier of the user or system that verified the source.
   * Maintains accountability in pharmaceutical source verification.
   * @since 1.0.0
   */
  verifiedBy?: string;
}

/**
 * Source conflict interface for transparent conflict resolution.
 *
 * Represents detected conflicts between pharmaceutical sources with
 * resolution details for regulatory compliance and audit transparency.
 *
 * @interface SourceConflict
 * @since 1.0.0
 */
export interface SourceConflict {
  /**
   * Unique identifier for the source conflict.
   * Links to audit trail and resolution history.
   * @since 1.0.0
   */
  id: string;

  /**
   * Identifier of the parent category result.
   * Maintains relationship hierarchy for comprehensive audit trails.
   * @since 1.0.0
   */
  categoryResultId: string;

  /**
   * Type of conflict detected between sources.
   * Classifies the nature of pharmaceutical information discrepancies.
   * @since 1.0.0
   */
  conflictType: 'factual' | 'temporal' | 'methodological' | 'quantitative';

  /**
   * Severity level of the detected conflict.
   * Determines resolution priority and escalation requirements.
   * @since 1.0.0
   */
  severity: 'low' | 'medium' | 'high' | 'critical';

  /**
   * Array of conflicting source references.
   * Identifies all sources involved in the detected conflict.
   * @since 1.0.0
   */
  conflictingSources: string[];

  /**
   * Detailed description of the conflict.
   * Provides human-readable explanation for regulatory compliance reviews.
   * @since 1.0.0
   */
  description: string;

  /**
   * Strategy used to resolve the conflict.
   * Documents the algorithmic approach for audit transparency.
   * @since 1.0.0
   */
  resolutionStrategy: string;

  /**
   * Confidence score for the conflict resolution (0.0 to 1.0).
   * Indicates reliability of the automated resolution process.
   * @since 1.0.0
   */
  resolutionConfidence: number;

  /**
   * Final resolution details and outcome.
   * Documents the resolved pharmaceutical intelligence finding.
   * @since 1.0.0
   */
  resolution: string;

  /**
   * ISO 8601 timestamp when the conflict was detected.
   * Used for audit trails and conflict analysis.
   * @since 1.0.0
   */
  detectedAt: string;

  /**
   * ISO 8601 timestamp when the conflict was resolved.
   * Used for resolution performance tracking and audit trails.
   * @since 1.0.0
   */
  resolvedAt?: string;
}