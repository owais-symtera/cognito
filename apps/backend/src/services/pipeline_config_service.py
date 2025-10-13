"""
Pipeline Stage Configuration Service
Manages enable/disable state of processing pipeline stages from database.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class PipelineStageConfig:
    """Configuration for a single pipeline stage"""
    def __init__(self, stage_name: str, stage_order: int, enabled: bool,
                 description: str, progress_weight: int):
        self.stage_name = stage_name
        self.stage_order = stage_order
        self.enabled = enabled
        self.description = description
        self.progress_weight = progress_weight


class PipelineConfigService:
    """Service for managing pipeline stage configuration"""

    def __init__(self):
        self.db_config = {
            'host': os.getenv('DATABASE_HOST', 'localhost'),
            'port': int(os.getenv('DATABASE_PORT', 5432)),
            'database': os.getenv('DATABASE_NAME', 'cognito-engine'),
            'user': os.getenv('DATABASE_USER', 'cognito'),
            'password': os.getenv('DATABASE_PASSWORD', 'cognito')
        }
        self._cache = None

    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)

    def get_all_stages(self, force_refresh: bool = False) -> List[PipelineStageConfig]:
        """
        Get all pipeline stages from database

        Args:
            force_refresh: Force refresh from database (bypass cache)

        Returns:
            List of pipeline stage configurations
        """
        if self._cache and not force_refresh:
            return self._cache

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT stage_name, stage_order, enabled, description, progress_weight
                FROM pipeline_stages
                ORDER BY stage_order
            """)

            rows = cursor.fetchall()
            stages = [
                PipelineStageConfig(
                    stage_name=row['stage_name'],
                    stage_order=row['stage_order'],
                    enabled=row['enabled'],
                    description=row['description'],
                    progress_weight=row['progress_weight']
                )
                for row in rows
            ]

            self._cache = stages
            return stages

        finally:
            cursor.close()
            conn.close()

    def is_stage_enabled(self, stage_name: str) -> bool:
        """
        Check if a specific stage is enabled

        Args:
            stage_name: Name of the stage (data_collection, verification, merging, llm_summary)

        Returns:
            True if stage is enabled, False otherwise
        """
        stages = self.get_all_stages()
        for stage in stages:
            if stage.stage_name == stage_name:
                return stage.enabled
        return False

    def get_enabled_stages(self) -> List[PipelineStageConfig]:
        """Get only enabled stages"""
        stages = self.get_all_stages()
        return [stage for stage in stages if stage.enabled]

    def get_stage_config(self, stage_name: str) -> Optional[PipelineStageConfig]:
        """Get configuration for a specific stage"""
        stages = self.get_all_stages()
        for stage in stages:
            if stage.stage_name == stage_name:
                return stage
        return None

    def update_stage_enabled(self, stage_name: str, enabled: bool) -> bool:
        """
        Update enabled status for a stage

        Args:
            stage_name: Name of the stage
            enabled: New enabled status

        Returns:
            True if update successful
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE pipeline_stages
                SET enabled = %s, updated_at = CURRENT_TIMESTAMP
                WHERE stage_name = %s
            """, (enabled, stage_name))

            conn.commit()
            success = cursor.rowcount > 0

            if success:
                self._cache = None  # Invalidate cache

            return success

        finally:
            cursor.close()
            conn.close()

    def calculate_progress_percentage(self, completed_stages: List[str]) -> float:
        """
        Calculate progress percentage based on completed stages

        Args:
            completed_stages: List of completed stage names

        Returns:
            Progress percentage (0-100)
        """
        all_stages = self.get_enabled_stages()
        if not all_stages:
            return 100

        total_weight = sum(stage.progress_weight for stage in all_stages)
        completed_weight = 0

        for stage in all_stages:
            if stage.stage_name in completed_stages:
                completed_weight += stage.progress_weight

        return (completed_weight / total_weight * 100) if total_weight > 0 else 0

    def get_stage_progress_map(self) -> Dict[str, float]:
        """
        Get progress percentage for each stage milestone

        Returns:
            Dict mapping stage names to their completion percentage
        """
        stages = self.get_enabled_stages()
        if not stages:
            return {}

        total_weight = sum(stage.progress_weight for stage in stages)
        progress_map = {}
        cumulative_weight = 0

        for stage in stages:
            cumulative_weight += stage.progress_weight
            progress_map[stage.stage_name] = (cumulative_weight / total_weight * 100) if total_weight > 0 else 0

        return progress_map

    def get_phase2_categories(self) -> List[Dict]:
        """
        Get Phase 2 categories from pharmaceutical_categories table

        Returns:
            List of Phase 2 category configurations
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, name, display_order, is_active, description
                FROM pharmaceutical_categories
                WHERE phase = 2
                ORDER BY display_order
            """)

            rows = cursor.fetchall()
            categories = [
                {
                    "id": row['id'],
                    "name": row['name'],
                    "order": row['display_order'],
                    "enabled": row['is_active'],
                    "description": row['description'] if row['description'] else f"Phase 2 category: {row['name']}",
                    "phase": 2
                }
                for row in rows
            ]

            return categories

        finally:
            cursor.close()
            conn.close()

    def update_phase2_category_enabled(self, category_id: int, enabled: bool) -> bool:
        """
        Update enabled status for a Phase 2 category

        Args:
            category_id: ID of the category
            enabled: New enabled status

        Returns:
            True if update successful
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE pharmaceutical_categories
                SET is_active = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND phase = 2
            """, (enabled, category_id))

            conn.commit()
            return cursor.rowcount > 0

        finally:
            cursor.close()
            conn.close()

    def get_pipeline_summary(self) -> Dict:
        """Get summary of pipeline configuration including Phase 1 and Phase 2"""
        # Get Phase 1 stages
        all_stages = self.get_all_stages()
        enabled_stages = self.get_enabled_stages()

        # Get Phase 2 categories
        phase2_categories = self.get_phase2_categories()
        enabled_phase2 = [cat for cat in phase2_categories if cat['enabled']]

        return {
            "total_stages": len(all_stages),
            "enabled_stages": len(enabled_stages),
            "disabled_stages": len(all_stages) - len(enabled_stages),
            "stages": [
                {
                    "name": stage.stage_name,
                    "order": stage.stage_order,
                    "enabled": stage.enabled,
                    "description": stage.description,
                    "progress_weight": stage.progress_weight,
                    "phase": 1
                }
                for stage in all_stages
            ],
            "progress_map": self.get_stage_progress_map(),
            "phase2_categories": phase2_categories,
            "total_phase2_categories": len(phase2_categories),
            "enabled_phase2_categories": len(enabled_phase2),
            "disabled_phase2_categories": len(phase2_categories) - len(enabled_phase2)
        }
