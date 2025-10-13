"""
Background processor for pharmaceutical drug analysis.

Handles asynchronous processing of drug analysis requests
across multiple categories with comprehensive error handling.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..database.models import AnalysisRequest as AnalysisRequestModel
from ..schemas.analysis import (
    AnalysisStatus,
    CategoryIdentifier,
    CategoryResult,
    DrugAnalysisResult
)
from ..schemas.status import ProcessingStatus, StatusUpdateRequest
from .category_manager import CategoryManager
from .status_tracker import StatusTracker

logger = structlog.get_logger(__name__)


class AnalysisProcessor:
    """
    Processes pharmaceutical drug analysis requests.
    
    Coordinates analysis across multiple categories using
    configured processors and aggregates results.
    
    Since:
        Version 1.0.0
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        request_id: str,
        correlation_id: str
    ):
        """
        Initialize analysis processor.
        
        Args:
            db_session: Database session
            request_id: Analysis request ID
            correlation_id: Correlation ID for tracking
        
        Since:
            Version 1.0.0
        """
        self.db = db_session
        self.request_id = request_id
        self.correlation_id = correlation_id
        self.start_time = None
        self.errors = []
    
    async def process_analysis(
        self,
        drug_names: List[str],
        categories: Optional[List[CategoryIdentifier]],
        priority: str = "normal"
    ) -> None:
        """
        Process drug analysis request asynchronously.
        
        Args:
            drug_names: List of drugs to analyze
            categories: Specific categories to process
            priority: Processing priority
        
        Since:
            Version 1.0.0
        """
        self.start_time = datetime.utcnow()
        
        try:
            logger.info(
                "Starting analysis processing",
                request_id=self.request_id,
                drug_count=len(drug_names),
                priority=priority
            )
            
            # Update status to processing
            await self._update_status(
                AnalysisStatus.PROCESSING,
                progress=0
            )
            
            # Get active categories
            category_manager = CategoryManager(
                self.db,
                "system",
                self.correlation_id
            )
            
            if categories:
                # Filter to requested categories
                active_categories = await self._filter_categories(
                    category_manager,
                    categories
                )
            else:
                # Get all active categories
                active_categories = await category_manager.get_active_categories()
            
            # Process each drug
            results = []
            total_items = len(drug_names) * len(active_categories)
            processed_items = 0
            
            for drug_idx, drug_name in enumerate(drug_names):
                drug_start_time = datetime.utcnow()
                
                logger.info(
                    "Processing drug",
                    drug_name=drug_name,
                    drug_index=drug_idx + 1,
                    total_drugs=len(drug_names)
                )
                
                # Process categories for this drug
                category_results = await self._process_drug_categories(
                    drug_name,
                    active_categories,
                    priority
                )
                
                # Calculate processing time
                drug_processing_time = (
                    datetime.utcnow() - drug_start_time
                ).total_seconds() * 1000
                
                # Create drug result
                drug_result = {
                    "drug_name": drug_name,
                    "status": self._determine_drug_status(category_results),
                    "categories": category_results,
                    "total_sources_analyzed": sum(
                        r.get("source_count", 0) for r in category_results
                    ),
                    "processing_time_ms": int(drug_processing_time),
                    "completed_at": datetime.utcnow().isoformat()
                }
                
                results.append(drug_result)
                
                # Update progress
                processed_items += len(active_categories)
                progress = int((processed_items / total_items) * 100)
                await self._update_status(
                    AnalysisStatus.PROCESSING,
                    progress=progress
                )
            
            # Calculate total processing time
            total_processing_time = (
                datetime.utcnow() - self.start_time
            ).total_seconds() * 1000
            
            # Save results
            await self._save_results(
                results,
                total_processing_time,
                AnalysisStatus.COMPLETED
            )
            
            logger.info(
                "Analysis processing completed",
                request_id=self.request_id,
                drug_count=len(drug_names),
                processing_time_ms=int(total_processing_time)
            )
            
        except Exception as e:
            logger.error(
                "Analysis processing failed",
                request_id=self.request_id,
                error=str(e)
            )
            
            self.errors.append(str(e))
            
            # Save error state
            await self._save_results(
                [],
                0,
                AnalysisStatus.FAILED
            )
    
    async def _filter_categories(
        self,
        category_manager: CategoryManager,
        requested_categories: List[CategoryIdentifier]
    ) -> List[Dict[str, Any]]:
        """
        Filter categories to requested ones.
        
        Args:
            category_manager: Category manager instance
            requested_categories: Requested category identifiers
        
        Returns:
            Filtered active categories
        
        Since:
            Version 1.0.0
        """
        all_categories = await category_manager.get_active_categories()
        
        # Map identifier to category
        category_map = {
            self._normalize_category_name(cat["name"]): cat
            for cat in all_categories
        }
        
        filtered = []
        for requested in requested_categories:
            if requested.value in category_map:
                filtered.append(category_map[requested.value])
        
        return filtered
    
    def _normalize_category_name(self, name: str) -> str:
        """
        Normalize category name to identifier format.
        
        Args:
            name: Category display name
        
        Returns:
            Normalized identifier
        
        Since:
            Version 1.0.0
        """
        # Convert to lowercase and replace spaces/special chars
        return name.lower().replace(" & ", "_").replace(" ", "_")
    
    async def _process_drug_categories(
        self,
        drug_name: str,
        categories: List[Dict[str, Any]],
        priority: str
    ) -> List[Dict[str, Any]]:
        """
        Process all categories for a drug.
        
        Args:
            drug_name: Drug to analyze
            categories: Categories to process
            priority: Processing priority
        
        Returns:
            List of category results
        
        Since:
            Version 1.0.0
        """
        results = []
        
        # Group categories by phase
        phase_1_categories = [c for c in categories if c["phase"] == 1]
        phase_2_categories = [c for c in categories if c["phase"] == 2]
        
        # Process phase 1 categories in parallel
        if phase_1_categories:
            phase_1_tasks = [
                self._process_single_category(drug_name, category, priority)
                for category in phase_1_categories
            ]
            phase_1_results = await asyncio.gather(*phase_1_tasks, return_exceptions=True)
            
            for idx, result in enumerate(phase_1_results):
                if isinstance(result, Exception):
                    # Handle exception
                    error_result = self._create_error_result(
                        phase_1_categories[idx],
                        str(result)
                    )
                    results.append(error_result)
                else:
                    results.append(result)
        
        # Process phase 2 categories SEQUENTIALLY (they have dependencies)
        # Phase 2 categories must run in order:
        # 1. Parameter-Based Scoring Matrix (generates scoring data)
        # 2. Weighted Scoring Assessment (depends on scoring)
        # 3. Risk Assessment Analysis (depends on scoring)
        # 4. Go/No-Go Recommendation (depends on all analyses)
        # 5. Strategic Opportunities Analysis (depends on decisions)
        # 6. Executive Summary & Recommendations (depends on everything)
        if phase_2_categories:
            # Sort by display_order to ensure correct sequential execution
            sorted_phase_2 = sorted(phase_2_categories, key=lambda c: c.get('display_order', 99))

            for category in sorted_phase_2:
                try:
                    result = await self._process_single_category(
                        drug_name,
                        category,
                        priority,
                        phase_1_results=results
                    )
                    results.append(result)
                except Exception as e:
                    error_result = self._create_error_result(
                        category,
                        str(e)
                    )
                    results.append(error_result)
        
        return results
    
    async def _process_single_category(
        self,
        drug_name: str,
        category: Dict[str, Any],
        priority: str,
        phase_1_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Process single category for a drug.
        
        Args:
            drug_name: Drug to analyze
            category: Category configuration
            priority: Processing priority
            phase_1_results: Results from phase 1 (for phase 2 categories)
        
        Returns:
            Category result
        
        Since:
            Version 1.0.0
        """
        start_time = datetime.utcnow()
        
        try:
            # Simulate processing (replace with actual processor)
            await asyncio.sleep(0.1)  # Simulate work
            
            # Mock result (replace with actual processing)
            result = {
                "category": self._normalize_category_name(category["name"]),
                "category_name": category["name"],
                "status": AnalysisStatus.COMPLETED.value,
                "confidence_score": 0.85,
                "data": {
                    "drug_name": drug_name,
                    "findings": f"Processed {category['name']} for {drug_name}",
                    "priority": priority
                },
                "source_count": 5,
                "processing_time_ms": int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                ),
                "error": None
            }
            
            return result
            
        except Exception as e:
            logger.error(
                "Category processing failed",
                category=category["name"],
                drug_name=drug_name,
                error=str(e)
            )
            
            return self._create_error_result(category, str(e))
    
    def _create_error_result(
        self,
        category: Dict[str, Any],
        error: str
    ) -> Dict[str, Any]:
        """
        Create error result for category.
        
        Args:
            category: Category configuration
            error: Error message
        
        Returns:
            Error result
        
        Since:
            Version 1.0.0
        """
        return {
            "category": self._normalize_category_name(category["name"]),
            "category_name": category["name"],
            "status": AnalysisStatus.FAILED.value,
            "confidence_score": None,
            "data": None,
            "source_count": 0,
            "processing_time_ms": 0,
            "error": error
        }
    
    def _determine_drug_status(
        self,
        category_results: List[Dict[str, Any]]
    ) -> str:
        """
        Determine overall status for drug.
        
        Args:
            category_results: Category processing results
        
        Returns:
            Overall status
        
        Since:
            Version 1.0.0
        """
        statuses = [r["status"] for r in category_results]
        
        if all(s == AnalysisStatus.COMPLETED.value for s in statuses):
            return AnalysisStatus.COMPLETED.value
        elif all(s == AnalysisStatus.FAILED.value for s in statuses):
            return AnalysisStatus.FAILED.value
        else:
            return AnalysisStatus.PARTIAL.value
    
    async def _update_status(
        self,
        status: AnalysisStatus,
        progress: int = 0
    ) -> None:
        """
        Update analysis request status.
        
        Args:
            status: New status
            progress: Progress percentage
        
        Since:
            Version 1.0.0
        """
        try:
            stmt = (
                update(AnalysisRequestModel)
                .where(AnalysisRequestModel.request_id == self.request_id)
                .values(
                    status=status.value,
                    progress_percentage=progress,
                    updated_at=datetime.utcnow()
                )
            )
            
            await self.db.execute(stmt)
            await self.db.commit()
            
        except Exception as e:
            logger.error(
                "Failed to update request status",
                request_id=self.request_id,
                status=status.value,
                error=str(e)
            )
    
    async def _save_results(
        self,
        results: List[Dict[str, Any]],
        processing_time: float,
        status: AnalysisStatus
    ) -> None:
        """
        Save analysis results to database.
        
        Args:
            results: Analysis results
            processing_time: Total processing time
            status: Final status
        
        Since:
            Version 1.0.0
        """
        try:
            stmt = (
                update(AnalysisRequestModel)
                .where(AnalysisRequestModel.request_id == self.request_id)
                .values(
                    status=status.value,
                    results=results,
                    processing_time_ms=int(processing_time),
                    completed_at=datetime.utcnow(),
                    errors=self.errors if self.errors else None,
                    progress_percentage=100 if status == AnalysisStatus.COMPLETED else 0
                )
            )
            
            await self.db.execute(stmt)
            await self.db.commit()
            
            logger.info(
                "Analysis results saved",
                request_id=self.request_id,
                status=status.value,
                result_count=len(results)
            )
            
        except Exception as e:
            logger.error(
                "Failed to save analysis results",
                request_id=self.request_id,
                error=str(e)
            )
            self.errors.append(f"Failed to save results: {str(e)}")