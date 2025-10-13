"""
Database-backed Category Service for managing 17 pharmaceutical intelligence categories.
Uses SQLite database for persistent storage.
"""

import sqlite3
import json
from typing import Dict, List, Optional, Any
from datetime import datetime


class CategoryDBService:
    """Manages pharmaceutical category configurations using SQLite database."""

    def __init__(self, db_file: str = "cognitoai_categories.db"):
        """Initialize with database connection."""
        self.db_file = db_file
        self._ensure_database_exists()

    def _ensure_database_exists(self):
        """Ensure the database and table exist."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pharmaceutical_categories (
                id INTEGER PRIMARY KEY,
                key TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                phase INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                prompt_template TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                source_priorities TEXT,
                requires_phase1 INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def _get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def get_all_categories(self) -> Dict[str, Any]:
        """Get all category configurations from database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, key, name, phase, enabled, prompt_template,
                   weight, source_priorities, requires_phase1
            FROM pharmaceutical_categories
            ORDER BY id
        ''')

        rows = cursor.fetchall()
        categories = {}

        for row in rows:
            key = row['key']
            categories[key] = {
                "id": row['id'],
                "name": row['name'],
                "phase": row['phase'],
                "enabled": bool(row['enabled']),
                "prompt_template": row['prompt_template'],
                "weight": row['weight'],
                "source_priorities": json.loads(row['source_priorities']) if row['source_priorities'] else [],
                "requires_phase1": bool(row['requires_phase1'])
            }

        conn.close()
        return categories

    def get_enabled_categories(self, phase: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get only enabled categories, optionally filtered by phase."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if phase is not None:
            cursor.execute('''
                SELECT id, key, name, phase, enabled, prompt_template,
                       weight, source_priorities, requires_phase1
                FROM pharmaceutical_categories
                WHERE enabled = 1 AND phase = ?
                ORDER BY id
            ''', (phase,))
        else:
            cursor.execute('''
                SELECT id, key, name, phase, enabled, prompt_template,
                       weight, source_priorities, requires_phase1
                FROM pharmaceutical_categories
                WHERE enabled = 1
                ORDER BY id
            ''')

        rows = cursor.fetchall()
        categories = []

        for row in rows:
            categories.append({
                "id": row['id'],
                "key": row['key'],
                "name": row['name'],
                "phase": row['phase'],
                "enabled": True,
                "prompt_template": row['prompt_template'],
                "weight": row['weight'],
                "source_priorities": json.loads(row['source_priorities']) if row['source_priorities'] else [],
                "requires_phase1": bool(row['requires_phase1'])
            })

        conn.close()
        return categories

    def get_category(self, category_key: str) -> Optional[Dict[str, Any]]:
        """Get a specific category by key."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, key, name, phase, enabled, prompt_template,
                   weight, source_priorities, requires_phase1
            FROM pharmaceutical_categories
            WHERE key = ?
        ''', (category_key,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id": row['id'],
                "name": row['name'],
                "phase": row['phase'],
                "enabled": bool(row['enabled']),
                "prompt_template": row['prompt_template'],
                "weight": row['weight'],
                "source_priorities": json.loads(row['source_priorities']) if row['source_priorities'] else [],
                "requires_phase1": bool(row['requires_phase1'])
            }

        return None

    def get_category_prompt(self, category_key: str, drug_name: str) -> Optional[str]:
        """Get formatted prompt for a category."""
        category = self.get_category(category_key)
        if not category:
            return None

        # Replace placeholders in prompt template
        prompt = category.get("prompt_template", "")
        return prompt.replace("{drug_name}", drug_name)

    def update_category(self, category_key: str, updates: Dict[str, Any]) -> bool:
        """Update category configuration in database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Build UPDATE query dynamically based on provided fields
        allowed_fields = ["enabled", "weight", "prompt_template", "source_priorities"]
        update_parts = []
        values = []

        for field in allowed_fields:
            if field in updates:
                if field == "source_priorities":
                    # Convert list to JSON string
                    value = json.dumps(updates[field]) if isinstance(updates[field], list) else updates[field]
                elif field == "enabled":
                    # Convert boolean to integer
                    value = 1 if updates[field] else 0
                else:
                    value = updates[field]

                update_parts.append(f"{field} = ?")
                values.append(value)

        if not update_parts:
            return False

        # Add updated_at timestamp
        update_parts.append("updated_at = ?")
        values.append(datetime.now().isoformat())

        # Add category_key for WHERE clause
        values.append(category_key)

        query = f'''
            UPDATE pharmaceutical_categories
            SET {', '.join(update_parts)}
            WHERE key = ?
        '''

        try:
            cursor.execute(query, values)
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success
        except Exception as e:
            print(f"Error updating category: {e}")
            conn.close()
            return False

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
        """Get all categories with formatted prompts for a specific drug."""
        categories = self.get_enabled_categories()

        for category in categories:
            category["prompt"] = self.get_category_prompt(category["key"], drug_name)

        return categories

    def add_category(self, category_data: Dict[str, Any]) -> bool:
        """Add a new category to the database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO pharmaceutical_categories
                (key, name, phase, enabled, prompt_template, weight, source_priorities, requires_phase1)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                category_data.get("key"),
                category_data.get("name"),
                category_data.get("phase", 1),
                1 if category_data.get("enabled", True) else 0,
                category_data.get("prompt_template", ""),
                category_data.get("weight", 1.0),
                json.dumps(category_data.get("source_priorities", [])),
                1 if category_data.get("requires_phase1", False) else 0
            ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding category: {e}")
            conn.close()
            return False

    def delete_category(self, category_key: str) -> bool:
        """Delete a category from the database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('DELETE FROM pharmaceutical_categories WHERE key = ?', (category_key,))
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success
        except Exception as e:
            print(f"Error deleting category: {e}")
            conn.close()
            return False