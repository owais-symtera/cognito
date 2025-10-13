"""
Source Authentication & Hierarchy Verification Module

Implements Story 3.1: Source authentication using established hierarchy
with comprehensive audit documentation for pharmaceutical intelligence data.

This module provides:
- Source classification from URLs, domains, and content patterns
- Hierarchical authority scoring (Paid APIs: 10x, .gov: 8x, etc.)
- Domain whitelist/blacklist management
- Publication date extraction and recency scoring
- Author and publication credibility assessment
- Verification status tracking with audit trail

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import Dict, List, Optional, Tuple, Any
from enum import IntEnum
from datetime import datetime, timedelta
from urllib.parse import urlparse
import re
import hashlib
import json
from dataclasses import dataclass, asdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
import structlog

from ...database.models import (
    SourceReference,
    SourceVerification,
    AuditLog,
    DomainWhitelist,
    DomainBlacklist
)

logger = structlog.get_logger(__name__)


class SourceWeights(IntEnum):
    """
    Source authority weighting hierarchy for pharmaceutical intelligence.

    Higher values indicate more authoritative sources based on
    pharmaceutical industry standards and regulatory requirements.

    Since:
        Version 1.0.0
    """
    PAID_APIS = 10      # ChatGPT, Perplexity, Grok, Gemini, Tavily
    GOVERNMENT = 8      # .gov, FDA, EMA, regulatory bodies
    PEER_REVIEWED = 6   # Academic journals, PubMed, clinical studies
    INDUSTRY = 4        # Professional associations, medical societies
    COMPANY = 2         # Pharmaceutical companies, manufacturers
    NEWS = 1            # News outlets, media sources
    UNKNOWN = 0         # Unclassified sources


class VerificationStatus(str):
    """Verification status for source authentication."""
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FLAGGED = "flagged"
    BLOCKED = "blocked"


@dataclass
class SourceAuthenticationResult:
    """
    Result of source authentication and hierarchy verification.

    Attributes:
        source_id: Unique identifier for the source
        source_type: Classification of source type
        authority_score: Hierarchical weighting score
        credibility_score: Author/publication credibility (0.0-1.0)
        recency_score: Publication date recency score (0.0-1.0)
        verification_status: Current verification status
        confidence_score: Overall confidence in source (0.0-1.0)
        reasoning: Explanation for verification decision
        audit_metadata: Additional metadata for audit trail

    Since:
        Version 1.0.0
    """
    source_id: str
    source_type: str
    authority_score: int
    credibility_score: float
    recency_score: float
    verification_status: str
    confidence_score: float
    reasoning: str
    audit_metadata: Dict[str, Any]


class SourceAuthenticator:
    """
    Source authentication and hierarchy verification engine.

    Implements comprehensive source authentication using established
    hierarchy with audit documentation for pharmaceutical compliance.

    Since:
        Version 1.0.0
    """

    # Domain patterns for source classification
    DOMAIN_PATTERNS = {
        'government': [
            r'\.gov$', r'\.gov\.\w+$',  # US and international gov
            r'fda\.gov', r'ema\.europa\.eu',  # FDA, EMA
            r'who\.int', r'cdc\.gov',  # WHO, CDC
            r'nih\.gov', r'\.edu$'  # NIH, educational institutions
        ],
        'peer_reviewed': [
            r'pubmed', r'ncbi\.nlm\.nih\.gov',  # PubMed, NCBI
            r'sciencedirect', r'nature\.com',  # Major journals
            r'nejm\.org', r'thelancet\.com',  # Medical journals
            r'bmj\.com', r'jamanetwork\.com'  # BMJ, JAMA
        ],
        'industry': [
            r'pharmaintelligence', r'fiercepharma',
            r'pharmaceutical-technology', r'drugdiscoverytoday',
            r'bio\.org', r'phrma\.org'  # Industry associations
        ],
        'company': [
            r'pfizer\.com', r'merck\.com', r'novartis\.com',
            r'roche\.com', r'jnj\.com', r'gsk\.com',
            r'astrazeneca\.com', r'sanofi\.com'
        ],
        'news': [
            r'reuters\.com', r'bloomberg\.com', r'wsj\.com',
            r'ft\.com', r'nytimes\.com', r'cnn\.com'
        ]
    }

    def __init__(
        self,
        db_session: AsyncSession,
        audit_logger: Optional[Any] = None
    ):
        """
        Initialize source authenticator.

        Args:
            db_session: Database session for persistence
            audit_logger: Optional audit logger for compliance

        Since:
            Version 1.0.0
        """
        self.db = db_session
        self.audit_logger = audit_logger or logger
        self._whitelist_cache = {}
        self._blacklist_cache = {}

    async def authenticate_source(
        self,
        source_reference: SourceReference,
        process_id: str
    ) -> SourceAuthenticationResult:
        """
        Authenticate and verify a source with hierarchy scoring.

        Implements comprehensive source authentication including:
        - Source type classification
        - Authority scoring based on hierarchy
        - Domain whitelist/blacklist checking
        - Publication date and recency scoring
        - Author credibility assessment
        - Verification status determination

        Args:
            source_reference: Source to authenticate
            process_id: Process ID for audit trail

        Returns:
            SourceAuthenticationResult with complete verification data

        Since:
            Version 1.0.0
        """
        try:
            # Step 1: Classify source type
            source_type = await self._classify_source(source_reference)

            # Step 2: Calculate authority score
            authority_score = self._get_authority_score(source_type)

            # Step 3: Check domain whitelist/blacklist
            domain_status = await self._check_domain_lists(source_reference.source_url)

            # Step 4: Calculate recency score
            recency_score = self._calculate_recency_score(source_reference.published_date)

            # Step 5: Assess credibility
            credibility_score = await self._assess_credibility(
                source_reference,
                source_type
            )

            # Step 6: Determine verification status
            verification_status, reasoning = self._determine_verification_status(
                domain_status,
                authority_score,
                credibility_score,
                recency_score
            )

            # Step 7: Calculate overall confidence
            confidence_score = self._calculate_confidence_score(
                authority_score,
                credibility_score,
                recency_score,
                verification_status
            )

            # Create result
            result = SourceAuthenticationResult(
                source_id=source_reference.id,
                source_type=source_type,
                authority_score=authority_score,
                credibility_score=credibility_score,
                recency_score=recency_score,
                verification_status=verification_status,
                confidence_score=confidence_score,
                reasoning=reasoning,
                audit_metadata={
                    'process_id': process_id,
                    'domain_status': domain_status,
                    'timestamp': datetime.utcnow().isoformat(),
                    'api_provider': source_reference.api_provider
                }
            )

            # Persist verification result
            await self._persist_verification(result, source_reference.id)

            # Create audit trail
            await self._create_audit_trail(result, process_id)

            return result

        except Exception as e:
            logger.error(f"Source authentication failed: {e}",
                        source_id=source_reference.id)
            raise

    async def _classify_source(self, source: SourceReference) -> str:
        """
        Classify source type from URL, domain, and content patterns.

        Args:
            source: Source reference to classify

        Returns:
            Source type classification

        Since:
            Version 1.0.0
        """
        # Check if it's a paid API source first
        if source.api_provider in ['chatgpt', 'perplexity', 'grok', 'gemini', 'tavily']:
            return 'paid_api'

        # Extract domain from URL
        if source.source_url:
            try:
                parsed = urlparse(source.source_url)
                domain = parsed.netloc.lower()

                # Check against domain patterns
                for source_type, patterns in self.DOMAIN_PATTERNS.items():
                    for pattern in patterns:
                        if re.search(pattern, domain):
                            return source_type

            except Exception as e:
                logger.warning(f"Failed to parse URL: {e}", url=source.source_url)

        # Check source type field
        if source.source_type:
            type_mapping = {
                'research_paper': 'peer_reviewed',
                'clinical_trial': 'peer_reviewed',
                'regulatory': 'government',
                'news': 'news'
            }
            return type_mapping.get(source.source_type, 'unknown')

        return 'unknown'

    def _get_authority_score(self, source_type: str) -> int:
        """
        Get hierarchical authority score for source type.

        Args:
            source_type: Classified source type

        Returns:
            Authority score based on hierarchy

        Since:
            Version 1.0.0
        """
        mapping = {
            'paid_api': SourceWeights.PAID_APIS,
            'government': SourceWeights.GOVERNMENT,
            'peer_reviewed': SourceWeights.PEER_REVIEWED,
            'industry': SourceWeights.INDUSTRY,
            'company': SourceWeights.COMPANY,
            'news': SourceWeights.NEWS,
            'unknown': SourceWeights.UNKNOWN
        }
        return mapping.get(source_type, SourceWeights.UNKNOWN)

    async def _check_domain_lists(self, url: Optional[str]) -> str:
        """
        Check domain against whitelist and blacklist.

        Args:
            url: Source URL to check

        Returns:
            'whitelisted', 'blacklisted', or 'neutral'

        Since:
            Version 1.0.0
        """
        if not url:
            return 'neutral'

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check blacklist first (takes precedence)
            if await self._is_blacklisted(domain):
                return 'blacklisted'

            # Check whitelist
            if await self._is_whitelisted(domain):
                return 'whitelisted'

            return 'neutral'

        except Exception as e:
            logger.warning(f"Domain check failed: {e}", url=url)
            return 'neutral'

    async def _is_whitelisted(self, domain: str) -> bool:
        """Check if domain is whitelisted."""
        if domain in self._whitelist_cache:
            return self._whitelist_cache[domain]

        result = await self.db.execute(
            select(DomainWhitelist).where(
                DomainWhitelist.domain == domain,
                DomainWhitelist.is_active == True
            )
        )
        is_whitelisted = result.scalar() is not None
        self._whitelist_cache[domain] = is_whitelisted
        return is_whitelisted

    async def _is_blacklisted(self, domain: str) -> bool:
        """Check if domain is blacklisted."""
        if domain in self._blacklist_cache:
            return self._blacklist_cache[domain]

        result = await self.db.execute(
            select(DomainBlacklist).where(
                DomainBlacklist.domain == domain,
                DomainBlacklist.is_active == True
            )
        )
        is_blacklisted = result.scalar() is not None
        self._blacklist_cache[domain] = is_blacklisted
        return is_blacklisted

    def _calculate_recency_score(self, published_date: Optional[datetime]) -> float:
        """
        Calculate recency score based on publication date.

        Pharmaceutical data relevance decay:
        - < 1 month: 1.0
        - 1-3 months: 0.9
        - 3-6 months: 0.7
        - 6-12 months: 0.5
        - 1-2 years: 0.3
        - > 2 years: 0.1

        Args:
            published_date: Publication date of source

        Returns:
            Recency score between 0.0 and 1.0

        Since:
            Version 1.0.0
        """
        if not published_date:
            return 0.5  # Unknown date gets middle score

        age = datetime.utcnow() - published_date

        if age < timedelta(days=30):
            return 1.0
        elif age < timedelta(days=90):
            return 0.9
        elif age < timedelta(days=180):
            return 0.7
        elif age < timedelta(days=365):
            return 0.5
        elif age < timedelta(days=730):
            return 0.3
        else:
            return 0.1

    async def _assess_credibility(
        self,
        source: SourceReference,
        source_type: str
    ) -> float:
        """
        Assess author and publication credibility.

        Args:
            source: Source reference to assess
            source_type: Classified source type

        Returns:
            Credibility score between 0.0 and 1.0

        Since:
            Version 1.0.0
        """
        credibility_score = 0.5  # Base score

        # Boost for known credible sources
        if source_type in ['government', 'peer_reviewed']:
            credibility_score += 0.3
        elif source_type == 'paid_api':
            credibility_score += 0.2
        elif source_type == 'industry':
            credibility_score += 0.1

        # Check for author credentials
        if source.authors:
            if any(term in source.authors.lower() for term in ['md', 'phd', 'dr']):
                credibility_score += 0.1

        # Check for journal reputation
        if source.journal_name:
            prestigious_journals = [
                'nature', 'science', 'nejm', 'lancet',
                'jama', 'bmj', 'cell'
            ]
            if any(j in source.journal_name.lower() for j in prestigious_journals):
                credibility_score += 0.2

        # Check for DOI (indicates peer review)
        if source.doi:
            credibility_score += 0.1

        # Use existing credibility score if available
        if source.credibility_score:
            credibility_score = (credibility_score + source.credibility_score) / 2

        return min(1.0, credibility_score)

    def _determine_verification_status(
        self,
        domain_status: str,
        authority_score: int,
        credibility_score: float,
        recency_score: float
    ) -> Tuple[str, str]:
        """
        Determine verification status based on all factors.

        Args:
            domain_status: Whitelist/blacklist status
            authority_score: Hierarchical authority score
            credibility_score: Credibility assessment score
            recency_score: Publication recency score

        Returns:
            Tuple of (verification_status, reasoning)

        Since:
            Version 1.0.0
        """
        # Blacklisted domains are always blocked
        if domain_status == 'blacklisted':
            return VerificationStatus.BLOCKED, "Domain is blacklisted"

        # Whitelisted domains are verified if credible
        if domain_status == 'whitelisted' and credibility_score >= 0.6:
            return VerificationStatus.VERIFIED, "Whitelisted domain with good credibility"

        # High authority sources
        if authority_score >= SourceWeights.GOVERNMENT:
            if credibility_score >= 0.5:
                return VerificationStatus.VERIFIED, f"High authority source (score: {authority_score})"
            else:
                return VerificationStatus.FLAGGED, "High authority but low credibility"

        # Medium authority sources
        if authority_score >= SourceWeights.INDUSTRY:
            if credibility_score >= 0.7 and recency_score >= 0.5:
                return VerificationStatus.VERIFIED, "Medium authority with good credibility and recency"
            elif credibility_score >= 0.5:
                return VerificationStatus.UNVERIFIED, "Medium authority, needs review"
            else:
                return VerificationStatus.FLAGGED, "Medium authority with concerns"

        # Low authority sources
        if authority_score > SourceWeights.UNKNOWN:
            if credibility_score >= 0.8 and recency_score >= 0.7:
                return VerificationStatus.UNVERIFIED, "Low authority, high quality indicators"
            else:
                return VerificationStatus.FLAGGED, "Low authority source"

        # Unknown sources
        return VerificationStatus.FLAGGED, "Unknown source type"

    def _calculate_confidence_score(
        self,
        authority_score: int,
        credibility_score: float,
        recency_score: float,
        verification_status: str
    ) -> float:
        """
        Calculate overall confidence score.

        Args:
            authority_score: Hierarchical authority score
            credibility_score: Credibility assessment score
            recency_score: Publication recency score
            verification_status: Determined verification status

        Returns:
            Confidence score between 0.0 and 1.0

        Since:
            Version 1.0.0
        """
        # Normalize authority score (0-10 to 0-1)
        normalized_authority = authority_score / 10.0

        # Weight components
        confidence = (
            normalized_authority * 0.4 +
            credibility_score * 0.3 +
            recency_score * 0.2
        )

        # Adjust based on verification status
        status_multipliers = {
            VerificationStatus.VERIFIED: 1.0,
            VerificationStatus.UNVERIFIED: 0.7,
            VerificationStatus.FLAGGED: 0.4,
            VerificationStatus.BLOCKED: 0.0
        }

        confidence *= status_multipliers.get(verification_status, 0.5)

        # Add 10% bonus for consistency
        confidence += 0.1

        return min(1.0, confidence)

    async def _persist_verification(
        self,
        result: SourceAuthenticationResult,
        source_id: str
    ):
        """
        Persist verification result to database.

        Args:
            result: Authentication result to persist
            source_id: Source reference ID

        Since:
            Version 1.0.0
        """
        verification = SourceVerification(
            source_id=source_id,
            verification_status=result.verification_status,
            authority_score=result.authority_score,
            credibility_score=result.credibility_score,
            recency_score=result.recency_score,
            confidence_score=result.confidence_score,
            source_type=result.source_type,
            reasoning=result.reasoning,
            metadata=result.audit_metadata,
            verified_at=datetime.utcnow()
        )

        self.db.add(verification)
        await self.db.commit()

    async def _create_audit_trail(
        self,
        result: SourceAuthenticationResult,
        process_id: str
    ):
        """
        Create audit trail for source authentication.

        Args:
            result: Authentication result
            process_id: Process ID for correlation

        Since:
            Version 1.0.0
        """
        audit_entry = AuditLog(
            entity_type='SourceAuthentication',
            entity_id=result.source_id,
            action='authenticate_source',
            process_id=process_id,
            details={
                'source_type': result.source_type,
                'authority_score': result.authority_score,
                'verification_status': result.verification_status,
                'confidence_score': result.confidence_score,
                'reasoning': result.reasoning
            },
            timestamp=datetime.utcnow()
        )

        self.db.add(audit_entry)
        await self.db.commit()

        # Log to audit logger
        await self.audit_logger.log_source_authentication(
            process_id=process_id,
            source_id=result.source_id,
            result=asdict(result)
        )