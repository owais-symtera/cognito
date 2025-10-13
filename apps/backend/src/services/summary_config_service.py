"""
Summary Configuration Service
Manages summary styles, category mappings, and provider configuration
"""
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncpg
import structlog

logger = structlog.get_logger(__name__)


class SummaryConfigService:
    """Service for managing summary configuration and history"""

    def __init__(self):
        """Initialize service"""
        # Use environment variables matching the centralized database connection
        self.db_config = {
            'host': os.getenv('DATABASE_HOST', 'localhost'),
            'port': int(os.getenv('DATABASE_PORT', '5432')),
            'database': os.getenv('DATABASE_NAME', 'cognito-engine'),
            'user': os.getenv('DATABASE_USER', 'postgres'),
            'password': os.getenv('DATABASE_PASSWORD', 'postgres')
        }
        self.provider_config_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "provider_config.json"
        )

    async def _get_connection(self):
        """Get database connection"""
        return await asyncpg.connect(**self.db_config)

    # ==================== Provider Configuration ====================

    def get_provider_config(self) -> Dict[str, Any]:
        """Load provider configuration from JSON file"""
        try:
            with open(self.provider_config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load provider config", error=str(e))
            return {}

    def get_summary_providers(self) -> List[Dict[str, Any]]:
        """Get all providers that support summary generation"""
        config = self.get_provider_config()
        summary_providers = []

        for provider_key, provider_data in config.items():
            if provider_data.get('summary_enabled', False):
                summary_providers.append({
                    'key': provider_key,
                    'name': provider_data.get('name', provider_key),
                    'model': provider_data.get('summary_default_model', provider_data.get('model')),
                    'temperature': provider_data.get('summary_temperature', 0.7),
                    'max_tokens': provider_data.get('summary_max_tokens', 2000),
                    'enabled': provider_data.get('enabled', False)
                })

        return summary_providers

    async def get_active_summary_provider(self) -> Dict[str, Any]:
        """Get the currently active summary provider from pipeline_stages"""
        conn = await self._get_connection()
        try:
            result = await conn.fetchrow("""
                SELECT summary_provider, summary_model, summary_temperature, summary_max_tokens
                FROM pipeline_stages
                WHERE stage_name = 'llm_summary'
            """)

            if not result:
                logger.warning("LLM summary stage not found in pipeline_stages")
                return {}

            provider_key = result['summary_provider']
            config = self.get_provider_config()
            provider_data = config.get(provider_key, {})

            return {
                'key': provider_key,
                'name': provider_data.get('name', provider_key),
                'model': result['summary_model'],
                'temperature': float(result['summary_temperature']),
                'max_tokens': result['summary_max_tokens'],
                'api_key': provider_data.get('api_key', '')
            }
        finally:
            await conn.close()

    async def update_active_summary_provider(
        self,
        provider_key: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> bool:
        """Update the active summary provider in pipeline_stages"""
        config = self.get_provider_config()

        if provider_key not in config:
            logger.error("Invalid provider key", provider=provider_key)
            return False

        provider_data = config[provider_key]

        if not provider_data.get('summary_enabled', False):
            logger.error("Provider does not support summaries", provider=provider_key)
            return False

        # Use provided values or defaults from config
        final_model = model or provider_data.get('summary_default_model', provider_data.get('model'))
        final_temperature = temperature if temperature is not None else provider_data.get('summary_temperature', 0.7)
        final_max_tokens = max_tokens or provider_data.get('summary_max_tokens', 2000)

        conn = await self._get_connection()
        try:
            await conn.execute("""
                UPDATE pipeline_stages
                SET summary_provider = $1,
                    summary_model = $2,
                    summary_temperature = $3,
                    summary_max_tokens = $4
                WHERE stage_name = 'llm_summary'
            """, provider_key, final_model, final_temperature, final_max_tokens)
        finally:
            await conn.close()

        logger.info(
            "Updated active summary provider",
            provider=provider_key,
            model=final_model
        )
        return True

    # ==================== Summary Styles ====================

    async def get_summary_styles(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """Get all summary styles"""
        conn = await self._get_connection()
        try:
            query = """
                SELECT id, style_name, display_name, description,
                       system_prompt, user_prompt_template,
                       length_type, target_word_count, enabled,
                       created_at, updated_at
                FROM summary_styles
            """
            if enabled_only:
                query += " WHERE enabled = TRUE"
            query += " ORDER BY style_name"

            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
        finally:
            await conn.close()

    async def get_summary_style(self, style_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific summary style by ID"""
        conn = await self._get_connection()
        try:
            row = await conn.fetchrow("""
                SELECT id, style_name, display_name, description,
                       system_prompt, user_prompt_template,
                       length_type, target_word_count, enabled,
                       created_at, updated_at
                FROM summary_styles
                WHERE id = $1
            """, style_id)

            return dict(row) if row else None
        finally:
            await conn.close()

    async def create_summary_style(
        self,
        style_name: str,
        display_name: str,
        system_prompt: str,
        user_prompt_template: str,
        description: Optional[str] = None,
        length_type: str = "STANDARD",
        target_word_count: int = 500,
        enabled: bool = True
    ) -> str:
        """Create a new summary style"""
        conn = await self._get_connection()
        try:
            row = await conn.fetchrow("""
                INSERT INTO summary_styles (
                    style_name, display_name, description,
                    system_prompt, user_prompt_template,
                    length_type, target_word_count, enabled
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """, style_name, display_name, description, system_prompt,
                user_prompt_template, length_type, target_word_count, enabled)

            style_id = str(row['id'])
            logger.info("Created summary style", style_id=style_id, style_name=style_name)
            return style_id
        finally:
            await conn.close()

    async def update_summary_style(
        self,
        style_id: str,
        **kwargs
    ) -> bool:
        """Update a summary style"""
        allowed_fields = {
            'display_name', 'description', 'system_prompt',
            'user_prompt_template', 'length_type', 'target_word_count', 'enabled'
        }

        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(updates.keys())])
        set_clause += ", updated_at = CURRENT_TIMESTAMP"

        query = f"UPDATE summary_styles SET {set_clause} WHERE id = $1"
        values = [style_id] + list(updates.values())

        conn = await self._get_connection()
        try:
            result = await conn.execute(query, *values)
        finally:
            await conn.close()

        success = result.split()[-1] == '1'
        if success:
            logger.info("Updated summary style", style_id=style_id)
        return success

    # ==================== Category Mapping ====================

    async def get_category_summary_config(self, category_name: str) -> Optional[Dict[str, Any]]:
        """Get summary configuration for a specific category"""
        conn = await self._get_connection()
        try:
            row = await conn.fetchrow("""
                SELECT csc.id, csc.category_name, csc.summary_style_id,
                       csc.enabled, csc.custom_instructions,
                       ss.style_name, ss.display_name, ss.system_prompt,
                       ss.user_prompt_template, ss.length_type, ss.target_word_count
                FROM category_summary_config csc
                JOIN summary_styles ss ON csc.summary_style_id = ss.id
                WHERE csc.category_name = $1
            """, category_name)

            return dict(row) if row else None
        finally:
            await conn.close()

    async def get_all_category_configs(self) -> List[Dict[str, Any]]:
        """Get all category summary configurations"""
        conn = await self._get_connection()
        try:
            rows = await conn.fetch("""
                SELECT csc.id, csc.category_name, csc.summary_style_id,
                       csc.enabled, csc.custom_instructions,
                       ss.style_name, ss.display_name
                FROM category_summary_config csc
                JOIN summary_styles ss ON csc.summary_style_id = ss.id
                ORDER BY csc.category_name
            """)

            return [dict(row) for row in rows]
        finally:
            await conn.close()

    async def set_category_summary_style(
        self,
        category_name: str,
        summary_style_id: str,
        enabled: bool = True,
        custom_instructions: Optional[str] = None
    ) -> bool:
        """Map a category to a summary style"""
        conn = await self._get_connection()
        try:
            # Upsert: Update if exists, insert if not
            await conn.execute("""
                INSERT INTO category_summary_config
                    (category_name, summary_style_id, enabled, custom_instructions)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (category_name)
                DO UPDATE SET
                    summary_style_id = EXCLUDED.summary_style_id,
                    enabled = EXCLUDED.enabled,
                    custom_instructions = EXCLUDED.custom_instructions,
                    updated_at = CURRENT_TIMESTAMP
            """, category_name, summary_style_id, enabled, custom_instructions)
        finally:
            await conn.close()

        logger.info(
            "Mapped category to summary style",
            category=category_name,
            style_id=summary_style_id
        )
        return True

    # ==================== Summary History ====================

    async def save_summary_history(
        self,
        request_id: str,
        category_name: str,
        drug_name: str,
        summary_style_id: str,
        provider_name: str,
        model_name: str,
        input_merged_content: str,
        generated_summary: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tokens_used: Optional[int] = None,
        cost_estimate: Optional[float] = None,
        generation_time_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save summary generation history"""
        conn = await self._get_connection()
        try:
            row = await conn.fetchrow("""
                INSERT INTO summary_history (
                    request_id, category_name, drug_name, summary_style_id,
                    provider_name, model_name, temperature, max_tokens,
                    input_merged_content, generated_summary,
                    tokens_used, cost_estimate, generation_time_ms,
                    success, error_message, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                RETURNING id
            """, request_id, category_name, drug_name, summary_style_id,
                provider_name, model_name, temperature, max_tokens,
                input_merged_content, generated_summary,
                tokens_used, cost_estimate, generation_time_ms,
                success, error_message, json.dumps(metadata) if metadata else None)

            history_id = str(row['id'])
            logger.info("Saved summary history", history_id=history_id, request_id=request_id)
            return history_id
        finally:
            await conn.close()

    async def get_summary_history(
        self,
        request_id: Optional[str] = None,
        category_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get summary generation history with optional filters"""
        conn = await self._get_connection()
        try:
            query = """
                SELECT sh.id, sh.request_id, sh.category_name, sh.drug_name,
                       sh.provider_name, sh.model_name, sh.temperature, sh.max_tokens,
                       sh.generated_summary, sh.tokens_used, sh.cost_estimate,
                       sh.generation_time_ms, sh.success, sh.error_message,
                       sh.metadata, sh.created_at,
                       ss.style_name, ss.display_name
                FROM summary_history sh
                JOIN summary_styles ss ON sh.summary_style_id = ss.id
                WHERE 1=1
            """
            params = []
            param_num = 1

            if request_id:
                query += f" AND sh.request_id = ${param_num}"
                params.append(request_id)
                param_num += 1

            if category_name:
                query += f" AND sh.category_name = ${param_num}"
                params.append(category_name)
                param_num += 1

            query += f" ORDER BY sh.created_at DESC LIMIT ${param_num}"
            params.append(limit)

            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
        finally:
            await conn.close()

    # ==================== Prompt Variables ====================

    async def get_prompt_variables(self) -> List[Dict[str, Any]]:
        """Get all available prompt template variables"""
        conn = await self._get_connection()
        try:
            rows = await conn.fetch("""
                SELECT id, variable_name, display_name, description,
                       example_value, required
                FROM summary_prompt_variables
                ORDER BY variable_name
            """)

            return [dict(row) for row in rows]
        finally:
            await conn.close()

    async def add_prompt_variable(
        self,
        variable_name: str,
        display_name: str,
        description: Optional[str] = None,
        example_value: Optional[str] = None,
        required: bool = False
    ) -> str:
        """Add a new prompt template variable"""
        conn = await self._get_connection()
        try:
            row = await conn.fetchrow("""
                INSERT INTO summary_prompt_variables (
                    variable_name, display_name, description, example_value, required
                )
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, variable_name, display_name, description, example_value, required)

            var_id = str(row['id'])
            logger.info("Added prompt variable", var_id=var_id, variable_name=variable_name)
            return var_id
        finally:
            await conn.close()
