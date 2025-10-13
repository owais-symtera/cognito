"""
Story 5.1: Selectable LLM Processing Framework
Database-driven LLM selection for Phase 2 category processing
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import json
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers for decision processing"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    GROK = "grok"
    PERPLEXITY = "perplexity"
    TAVILY = "tavily"


class LLMSelectionCriteria(BaseModel):
    """Criteria for LLM selection from database"""
    category: str
    complexity: str  # low, medium, high
    data_sensitivity: str  # public, confidential, regulated
    response_time_requirement: int  # seconds
    accuracy_requirement: float  # 0-1
    cost_constraint: Optional[float] = None
    preferred_providers: List[str] = Field(default_factory=list)


class LLMConfiguration(BaseModel):
    """Database-driven LLM configuration"""
    provider: LLMProvider
    model_name: str
    temperature: float
    max_tokens: int
    cost_per_token: float
    avg_response_time: float
    accuracy_score: float
    categories_supported: List[str]
    active: bool = True
    priority: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMDecisionProcessor:
    """
    Database-driven LLM selection and processing for Phase 2 categories
    Following DEVELOPER_GUIDELINES.md - NO hardcoded logic
    """

    def __init__(self, db_session: AsyncSession, api_manager: Any, redis_client: Any):
        self.db = db_session
        self.api_manager = api_manager
        self.redis = redis_client
        self.llm_configs: Dict[str, LLMConfiguration] = {}
        self.performance_history: Dict[str, List[float]] = {}

    async def initialize(self):
        """Load LLM configurations from database"""
        query = """
        SELECT provider, model_name, configuration, performance_metrics, active
        FROM llm_configurations
        WHERE active = true
        ORDER BY priority DESC
        """

        result = await self.db.execute(query)
        configurations = result.fetchall()

        for config in configurations:
            llm_config = LLMConfiguration(
                provider=config['provider'],
                model_name=config['model_name'],
                **config['configuration'],
                **config['performance_metrics']
            )
            self.llm_configs[f"{config['provider']}_{config['model_name']}"] = llm_config

        logger.info(f"Loaded {len(self.llm_configs)} LLM configurations from database")

    async def select_optimal_llm(self, criteria: LLMSelectionCriteria) -> LLMConfiguration:
        """
        Select optimal LLM based on database-driven criteria
        NO hardcoded selection logic - all from database
        """

        # Load selection rules from database
        query = """
        SELECT llm_provider, llm_model, priority, conditions
        FROM llm_selection_rules
        WHERE category = :category
        AND active = true
        ORDER BY priority DESC
        """

        result = await self.db.execute(
            query,
            {"category": criteria.category}
        )
        rules = result.fetchall()

        selected_llm = None
        best_score = -1

        for rule in rules:
            # Evaluate conditions from database
            conditions = json.loads(rule['conditions'])
            if self._evaluate_conditions(conditions, criteria):
                # Calculate score based on database criteria
                score = await self._calculate_llm_score(
                    rule['llm_provider'],
                    rule['llm_model'],
                    criteria
                )

                if score > best_score:
                    best_score = score
                    selected_llm = self.llm_configs.get(
                        f"{rule['llm_provider']}_{rule['llm_model']}"
                    )

        # Fallback to best general LLM if no specific match
        if not selected_llm:
            selected_llm = await self._get_fallback_llm(criteria)

        # Log selection for audit trail
        await self._log_llm_selection(criteria, selected_llm)

        return selected_llm

    async def process_phase2_category(
        self,
        category: str,
        data: Dict[str, Any],
        request_id: str
    ) -> Dict[str, Any]:
        """
        Process Phase 2 category using selected LLM
        All processing logic from database
        """

        # Get category configuration from database
        category_config = await self._load_category_config(category)

        # Select optimal LLM
        criteria = LLMSelectionCriteria(
            category=category,
            complexity=category_config.get('complexity', 'medium'),
            data_sensitivity=category_config.get('data_sensitivity', 'regulated'),
            response_time_requirement=category_config.get('max_response_time', 30),
            accuracy_requirement=category_config.get('min_accuracy', 0.8)
        )

        selected_llm = await self.select_optimal_llm(criteria)

        # Build prompt from database template
        prompt = await self._build_prompt(category_config, data)

        # Process with selected LLM
        start_time = datetime.now()

        try:
            response = await self.api_manager.call_llm(
                provider=selected_llm.provider,
                model=selected_llm.model_name,
                prompt=prompt,
                temperature=selected_llm.temperature,
                max_tokens=selected_llm.max_tokens
            )

            processing_time = (datetime.now() - start_time).total_seconds()

            # Parse and validate response
            parsed_response = await self._parse_llm_response(response, category_config)

            # Update performance metrics
            await self._update_performance_metrics(
                selected_llm,
                processing_time,
                len(parsed_response.get('data_points', []))
            )

            # Store result with source tracking
            result = {
                'category': category,
                'llm_provider': selected_llm.provider,
                'llm_model': selected_llm.model_name,
                'processing_time': processing_time,
                'data': parsed_response,
                'confidence_score': parsed_response.get('confidence', 0.0),
                'sources': await self._extract_sources(response),
                'request_id': request_id,
                'timestamp': datetime.now().isoformat()
            }

            # Store in database for audit trail
            await self._store_processing_result(result)

            return result

        except Exception as e:
            logger.error(f"LLM processing failed for {category}: {e}")

            # Try fallback LLM
            fallback_llm = await self._get_fallback_llm(criteria)
            if fallback_llm and fallback_llm != selected_llm:
                return await self._process_with_fallback(
                    fallback_llm, category, data, request_id
                )

            raise

    async def _load_category_config(self, category: str) -> Dict[str, Any]:
        """Load category configuration from database"""
        query = """
        SELECT configuration, prompt_templates, validation_rules
        FROM pharmaceutical_categories
        WHERE name = :category
        AND active = true
        """

        result = await self.db.execute(query, {"category": category})
        config = result.fetchone()

        if not config:
            raise ValueError(f"No configuration found for category: {category}")

        return {
            **json.loads(config['configuration']),
            'prompt_templates': json.loads(config['prompt_templates']),
            'validation_rules': json.loads(config['validation_rules'])
        }

    async def _build_prompt(self, category_config: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Build prompt from database template - NO hardcoded prompts"""
        template = category_config['prompt_templates'].get('analysis_template', '')

        # Substitute parameters from data
        prompt = template.format(**data)

        # Add context from previous categories if needed
        if category_config.get('requires_context'):
            context = await self._get_category_context(data.get('request_id'))
            prompt = f"{context}\n\n{prompt}"

        return prompt

    async def _parse_llm_response(
        self,
        response: str,
        category_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse LLM response according to database validation rules"""

        # Try to parse as JSON first
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            # Apply parsing rules from database
            parsing_rules = category_config.get('parsing_rules', {})
            parsed = await self._apply_parsing_rules(response, parsing_rules)

        # Validate against database rules
        validation_rules = category_config.get('validation_rules', {})
        validated_data = await self._validate_response(parsed, validation_rules)

        return validated_data

    async def _calculate_llm_score(
        self,
        provider: str,
        model: str,
        criteria: LLMSelectionCriteria
    ) -> float:
        """Calculate LLM fitness score based on database metrics"""

        llm_key = f"{provider}_{model}"
        if llm_key not in self.llm_configs:
            return 0.0

        config = self.llm_configs[llm_key]

        # Load scoring weights from database
        query = """
        SELECT accuracy_weight, speed_weight, cost_weight
        FROM llm_scoring_weights
        WHERE category = :category
        """

        result = await self.db.execute(query, {"category": criteria.category})
        weights = result.fetchone() or {
            'accuracy_weight': 0.5,
            'speed_weight': 0.3,
            'cost_weight': 0.2
        }

        # Calculate weighted score
        accuracy_score = config.accuracy_score * weights['accuracy_weight']
        speed_score = (1.0 - min(config.avg_response_time / criteria.response_time_requirement, 1.0)) * weights['speed_weight']
        cost_score = (1.0 - min(config.cost_per_token / 0.001, 1.0)) * weights['cost_weight'] if criteria.cost_constraint else 0

        total_score = accuracy_score + speed_score + cost_score

        # Apply preference bonus
        if provider in criteria.preferred_providers:
            total_score *= 1.2

        return total_score

    def _evaluate_conditions(self, conditions: Dict[str, Any], criteria: LLMSelectionCriteria) -> bool:
        """Evaluate database-defined conditions"""
        for field, requirement in conditions.items():
            criteria_value = getattr(criteria, field, None)
            if criteria_value is None:
                continue

            if isinstance(requirement, dict):
                # Complex condition (e.g., {"min": 0.8, "max": 1.0})
                if "min" in requirement and criteria_value < requirement["min"]:
                    return False
                if "max" in requirement and criteria_value > requirement["max"]:
                    return False
            else:
                # Simple equality
                if criteria_value != requirement:
                    return False

        return True

    async def _get_fallback_llm(self, criteria: LLMSelectionCriteria) -> Optional[LLMConfiguration]:
        """Get fallback LLM from database configuration"""
        query = """
        SELECT provider, model_name
        FROM llm_configurations
        WHERE is_fallback = true
        AND active = true
        ORDER BY priority DESC
        LIMIT 1
        """

        result = await self.db.execute(query)
        fallback = result.fetchone()

        if fallback:
            return self.llm_configs.get(f"{fallback['provider']}_{fallback['model_name']}")

        # Last resort: return any active LLM
        for config in self.llm_configs.values():
            if config.active:
                return config

        return None

    async def _update_performance_metrics(
        self,
        llm_config: LLMConfiguration,
        processing_time: float,
        data_points: int
    ):
        """Update LLM performance metrics in database"""

        # Calculate moving average
        llm_key = f"{llm_config.provider}_{llm_config.model_name}"
        if llm_key not in self.performance_history:
            self.performance_history[llm_key] = []

        self.performance_history[llm_key].append(processing_time)

        # Keep last 100 measurements
        if len(self.performance_history[llm_key]) > 100:
            self.performance_history[llm_key] = self.performance_history[llm_key][-100:]

        avg_time = sum(self.performance_history[llm_key]) / len(self.performance_history[llm_key])

        # Update database
        query = """
        UPDATE llm_configurations
        SET performance_metrics = jsonb_set(
            performance_metrics,
            '{avg_response_time}',
            :avg_time::text::jsonb
        ),
        last_used = :timestamp
        WHERE provider = :provider
        AND model_name = :model
        """

        await self.db.execute(
            query,
            {
                "avg_time": avg_time,
                "timestamp": datetime.now(),
                "provider": llm_config.provider,
                "model": llm_config.model_name
            }
        )
        await self.db.commit()

    async def _extract_sources(self, llm_response: str) -> List[Dict[str, Any]]:
        """Extract source references from LLM response"""
        sources = []

        # Parse sources from response if provided
        # This would be enhanced based on LLM response format
        if "sources" in llm_response:
            try:
                response_data = json.loads(llm_response)
                for source in response_data.get("sources", []):
                    sources.append({
                        "url": source.get("url"),
                        "title": source.get("title"),
                        "relevance": source.get("relevance", 0.5),
                        "extracted_at": datetime.now().isoformat()
                    })
            except:
                pass

        return sources

    async def _store_processing_result(self, result: Dict[str, Any]):
        """Store processing result in database for audit trail"""
        query = """
        INSERT INTO llm_processing_results
        (request_id, category, llm_provider, llm_model, processing_time,
         confidence_score, data, sources, created_at)
        VALUES
        (:request_id, :category, :llm_provider, :llm_model, :processing_time,
         :confidence_score, :data, :sources, :created_at)
        """

        await self.db.execute(
            query,
            {
                "request_id": result['request_id'],
                "category": result['category'],
                "llm_provider": result['llm_provider'],
                "llm_model": result['llm_model'],
                "processing_time": result['processing_time'],
                "confidence_score": result.get('confidence_score', 0),
                "data": json.dumps(result['data']),
                "sources": json.dumps(result['sources']),
                "created_at": datetime.now()
            }
        )
        await self.db.commit()

    async def _log_llm_selection(self, criteria: LLMSelectionCriteria, selected_llm: LLMConfiguration):
        """Log LLM selection for audit trail"""
        query = """
        INSERT INTO llm_selection_log
        (category, criteria, selected_provider, selected_model, timestamp)
        VALUES
        (:category, :criteria, :provider, :model, :timestamp)
        """

        await self.db.execute(
            query,
            {
                "category": criteria.category,
                "criteria": json.dumps(criteria.dict()),
                "provider": selected_llm.provider,
                "model": selected_llm.model_name,
                "timestamp": datetime.now()
            }
        )
        await self.db.commit()

    async def _process_with_fallback(
        self,
        fallback_llm: LLMConfiguration,
        category: str,
        data: Dict[str, Any],
        request_id: str
    ) -> Dict[str, Any]:
        """Process with fallback LLM when primary fails"""
        logger.warning(f"Using fallback LLM for {category}: {fallback_llm.provider}")

        # Simplified processing with fallback
        category_config = await self._load_category_config(category)
        prompt = await self._build_prompt(category_config, data)

        response = await self.api_manager.call_llm(
            provider=fallback_llm.provider,
            model=fallback_llm.model_name,
            prompt=prompt,
            temperature=fallback_llm.temperature,
            max_tokens=fallback_llm.max_tokens
        )

        return {
            'category': category,
            'llm_provider': fallback_llm.provider,
            'llm_model': fallback_llm.model_name,
            'data': await self._parse_llm_response(response, category_config),
            'is_fallback': True,
            'request_id': request_id,
            'timestamp': datetime.now().isoformat()
        }

    async def _get_category_context(self, request_id: str) -> str:
        """Get context from previously processed categories"""
        query = """
        SELECT category, data
        FROM llm_processing_results
        WHERE request_id = :request_id
        ORDER BY created_at DESC
        LIMIT 5
        """

        result = await self.db.execute(query, {"request_id": request_id})
        previous_results = result.fetchall()

        context = "Previous analysis context:\n"
        for prev in previous_results:
            context += f"- {prev['category']}: {json.loads(prev['data']).get('summary', 'N/A')}\n"

        return context

    async def _apply_parsing_rules(self, response: str, parsing_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Apply database-defined parsing rules to extract structured data"""
        parsed = {}

        for field, rule in parsing_rules.items():
            if rule['type'] == 'regex':
                import re
                match = re.search(rule['pattern'], response)
                if match:
                    parsed[field] = match.group(1)
            elif rule['type'] == 'split':
                parts = response.split(rule['delimiter'])
                if len(parts) > rule['index']:
                    parsed[field] = parts[rule['index']]

        return parsed

    async def _validate_response(self, parsed_data: Dict[str, Any], validation_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parsed response against database rules"""
        validated = {}

        for field, rules in validation_rules.items():
            value = parsed_data.get(field)

            if value is None and rules.get('required'):
                logger.warning(f"Required field {field} missing in response")
                continue

            # Apply validation
            if 'type' in rules:
                if rules['type'] == 'number' and not isinstance(value, (int, float)):
                    try:
                        value = float(value)
                    except:
                        continue
                elif rules['type'] == 'list' and not isinstance(value, list):
                    value = [value]

            if 'min' in rules and value < rules['min']:
                value = rules['min']
            if 'max' in rules and value > rules['max']:
                value = rules['max']

            validated[field] = value

        return validated