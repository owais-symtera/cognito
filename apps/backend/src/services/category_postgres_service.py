"""
PostgreSQL-backed Category Service for managing pharmaceutical intelligence categories.
Uses the existing pharmaceutical_categories table in the cognito-engine database.
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()


class CategoryPostgresService:
    """Manages pharmaceutical category configurations using existing PostgreSQL database."""

    def __init__(self):
        """Initialize with database connection parameters from environment."""
        self.db_config = {
            'host': os.getenv('DATABASE_HOST', 'localhost'),
            'port': int(os.getenv('DATABASE_PORT', 5432)),
            'database': os.getenv('DATABASE_NAME', 'cognito-engine'),
            'user': os.getenv('DATABASE_USER', 'cognito'),
            'password': os.getenv('DATABASE_PASSWORD', 'cognito')
        }

    def _get_connection(self):
        """Get a database connection with RealDictCursor for dict-like results."""
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)

    def get_all_categories(self) -> Dict[str, Any]:
        """Get all category configurations from PostgreSQL database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, name, description, phase, is_active as enabled,
                       display_order, prompt_templates, search_parameters,
                       processing_rules, verification_criteria
                FROM pharmaceutical_categories
                ORDER BY display_order, id
            """)

            rows = cursor.fetchall()
            categories = {}

            for row in rows:
                # Create a key from the name (lowercase, underscored)
                key = row['name'].lower().replace(' ', '_').replace('&', 'and').replace('-', '_')

                # Extract prompt template from JSONB if it exists
                prompt_template = ""
                if row.get('prompt_templates'):
                    if isinstance(row['prompt_templates'], dict):
                        prompt_template = row['prompt_templates'].get('default', '')
                    elif isinstance(row['prompt_templates'], str):
                        prompt_template = row['prompt_templates']

                # Extract source priorities from search_parameters if it exists
                source_priorities = []
                if row.get('search_parameters'):
                    if isinstance(row['search_parameters'], dict):
                        source_priorities = row['search_parameters'].get('source_priorities', [])

                categories[key] = {
                    "id": row['id'],
                    "name": row['name'],
                    "phase": row['phase'] if row['phase'] else 1,
                    "enabled": row['enabled'] if row['enabled'] is not None else True,
                    "description": row['description'] or "",
                    "prompt_template": prompt_template or row['description'] or "",
                    "weight": 1.0,  # Default weight
                    "source_priorities": source_priorities,
                    "display_order": row['display_order'] or row['id']
                }

            return categories

        finally:
            cursor.close()
            conn.close()

    def get_enabled_categories(self, phase: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get only enabled categories, optionally filtered by phase."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if phase is not None:
                cursor.execute("""
                    SELECT id, name, description, phase, is_active as enabled,
                           display_order, prompt_templates, search_parameters
                    FROM pharmaceutical_categories
                    WHERE is_active = TRUE AND phase = %s
                    ORDER BY display_order, id
                """, (phase,))
            else:
                cursor.execute("""
                    SELECT id, name, description, phase, is_active as enabled,
                           display_order, prompt_templates, search_parameters
                    FROM pharmaceutical_categories
                    WHERE is_active = TRUE
                    ORDER BY display_order, id
                """)

            rows = cursor.fetchall()
            categories = []

            for row in rows:
                key = row['name'].lower().replace(' ', '_').replace('&', 'and').replace('-', '_')

                prompt_template = ""
                if row.get('prompt_templates'):
                    if isinstance(row['prompt_templates'], dict):
                        prompt_template = row['prompt_templates'].get('default', '')
                    elif isinstance(row['prompt_templates'], str):
                        prompt_template = row['prompt_templates']

                source_priorities = []
                if row.get('search_parameters'):
                    if isinstance(row['search_parameters'], dict):
                        source_priorities = row['search_parameters'].get('source_priorities', [])

                categories.append({
                    "id": row['id'],
                    "key": key,
                    "name": row['name'],
                    "phase": row['phase'] if row['phase'] else 1,
                    "enabled": True,
                    "description": row['description'] or "",
                    "prompt_template": prompt_template or row['description'] or "",
                    "weight": 1.0,
                    "source_priorities": source_priorities,
                    "display_order": row['display_order'] or row['id']
                })

            return categories

        finally:
            cursor.close()
            conn.close()

    def get_category(self, category_key: str) -> Optional[Dict[str, Any]]:
        """Get a specific category by key (derived from name)."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Convert key back to potential names
            name_variations = [
                category_key.replace('_', ' ').title(),
                category_key.replace('_', ' ').upper(),
                category_key
            ]

            cursor.execute("""
                SELECT id, name, description, phase, is_active as enabled,
                       display_order, prompt_templates, search_parameters
                FROM pharmaceutical_categories
                WHERE LOWER(REPLACE(REPLACE(name, ' ', '_'), '&', 'and')) = %s
                   OR name = ANY(%s)
                LIMIT 1
            """, (category_key.lower(), name_variations))

            row = cursor.fetchone()

            if row:
                prompt_template = ""
                if row.get('prompt_templates'):
                    if isinstance(row['prompt_templates'], dict):
                        prompt_template = row['prompt_templates'].get('default', '')
                    elif isinstance(row['prompt_templates'], str):
                        prompt_template = row['prompt_templates']

                source_priorities = []
                if row.get('search_parameters'):
                    if isinstance(row['search_parameters'], dict):
                        source_priorities = row['search_parameters'].get('source_priorities', [])

                return {
                    "id": row['id'],
                    "name": row['name'],
                    "phase": row['phase'] if row['phase'] else 1,
                    "enabled": row['enabled'] if row['enabled'] is not None else True,
                    "description": row['description'] or "",
                    "prompt_template": prompt_template or row['description'] or "",
                    "weight": 1.0,
                    "source_priorities": source_priorities,
                    "display_order": row['display_order'] or row['id']
                }

            return None

        finally:
            cursor.close()
            conn.close()

    def get_category_prompt(self, category_key: str, drug_name: str) -> Optional[str]:
        """Get formatted prompt for a category."""
        category = self.get_category(category_key)
        if not category:
            return None

        # Replace placeholders in prompt template
        prompt = category.get("prompt_template", "")
        return prompt.replace("{drug_name}", drug_name)

    def update_category(self, category_key: str, updates: Dict[str, Any]) -> bool:
        """Update category configuration in PostgreSQL database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # First, find the category by trying different matching strategies
            # Strategy 1: Try exact match on the key as lowercase with underscores
            cursor.execute("""
                SELECT id, name FROM pharmaceutical_categories
                WHERE LOWER(REPLACE(REPLACE(REPLACE(name, ' ', '_'), '&', 'and'), '-', '_')) = %s
            """, (category_key.lower(),))

            result = cursor.fetchone()

            # Strategy 2: If not found, try partial match
            if not result:
                # Remove extra underscores and try to match parts
                search_pattern = '%' + '%'.join(category_key.lower().split('_')) + '%'
                cursor.execute("""
                    SELECT id, name FROM pharmaceutical_categories
                    WHERE LOWER(name) LIKE %s
                    ORDER BY LENGTH(name)
                    LIMIT 1
                """, (search_pattern,))
                result = cursor.fetchone()

            if not result:
                return False

            category_id = result['id']

            # Map our field names to database columns
            field_mapping = {
                "enabled": "is_active",
                "description": "description",
                "prompt_template": "prompt_templates",
                "source_priorities": "search_parameters"
            }

            update_parts = []
            values = []

            for field, db_column in field_mapping.items():
                if field in updates:
                    if field == "prompt_template":
                        # Store as JSONB with default key
                        update_parts.append(f"{db_column} = %s")
                        values.append(Json({"default": updates[field]}))
                    elif field == "source_priorities":
                        # Store as part of search_parameters JSONB
                        update_parts.append(f"{db_column} = {db_column} || %s")
                        values.append(Json({"source_priorities": updates[field]}))
                    else:
                        update_parts.append(f"{db_column} = %s")
                        values.append(updates[field])

            if not update_parts:
                return False

            # Add updated_at
            update_parts.append("updated_at = CURRENT_TIMESTAMP")
            values.append(category_id)

            query = f"""
                UPDATE pharmaceutical_categories
                SET {', '.join(update_parts)}
                WHERE id = %s
            """

            cursor.execute(query, values)
            conn.commit()

            success = cursor.rowcount > 0
            return success

        except Exception as e:
            print(f"Error updating category: {e}")
            conn.rollback()
            return False

        finally:
            cursor.close()
            conn.close()

    def enable_category(self, category_key: str) -> bool:
        """Enable a category."""
        return self.update_category(category_key, {"enabled": True})

    def disable_category(self, category_key: str) -> bool:
        """Disable a category."""
        return self.update_category(category_key, {"enabled": False})

    def get_phase1_categories(self) -> List[Dict[str, Any]]:
        """Get all Phase 1 (data collection) categories."""
        return self.get_enabled_categories(phase=1)

    def get_phase2_categories(self) -> List[Dict[str, Any]]:
        """Get all Phase 2 (decision intelligence) categories."""
        return self.get_enabled_categories(phase=2)

    def get_categories_for_drug_analysis(self, drug_name: str) -> List[Dict[str, Any]]:
        """Get all enabled categories with formatted prompts for a specific drug."""
        categories = self.get_enabled_categories()

        for category in categories:
            category["prompt"] = self.get_category_prompt(category["key"], drug_name)

        return categories

    def populate_default_categories(self) -> bool:
        """Populate the database with the 17 default pharmaceutical categories if empty."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Check if categories already exist
            cursor.execute("SELECT COUNT(*) FROM pharmaceutical_categories")
            count = cursor.fetchone()['count']

            if count > 0:
                print(f"Categories already exist ({count} found)")
                return True

            # Default categories based on PRD
            default_categories = [
                {
                    'name': 'Market Overview',
                    'phase': 1,
                    'description': 'Analyze the global and regional market for {drug_name}. Include: 1) Current global market size in USD, 2) Year-over-year growth rates, 3) Regional market distribution (US, EU, Asia, Others), 4) Market penetration rates, 5) Pricing trends across regions, 6) Reimbursement status by country.',
                    'is_active': True,
                    'display_order': 1
                },
                {
                    'name': 'Competitive Landscape',
                    'phase': 1,
                    'description': 'Provide comprehensive competitive analysis for {drug_name}. Include: 1) Direct competitors with market share percentages, 2) Indirect/alternative therapies, 3) Competitive advantages and disadvantages, 4) Head-to-head clinical trial comparisons, 5) Pricing comparison with competitors, 6) Pipeline competitors in development.',
                    'is_active': True,
                    'display_order': 2
                },
                # Add remaining 15 categories here based on PRD...
            ]

            for cat in default_categories:
                cursor.execute("""
                    INSERT INTO pharmaceutical_categories
                    (name, description, phase, is_active, display_order, prompt_templates, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    cat['name'],
                    cat['description'],
                    cat.get('phase', 1),
                    cat.get('is_active', False),
                    cat.get('display_order'),
                    Json({'default': cat['description']})
                ))

            conn.commit()
            print(f"Successfully populated {len(default_categories)} categories")
            return True

        except Exception as e:
            print(f"Error populating categories: {e}")
            conn.rollback()
            return False

        finally:
            cursor.close()
            conn.close()