"""
Story 5.2: Rule-Based Decision Logic Engine
Database-driven pharmaceutical decision rules
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import json
import operator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class RuleOperator(str, Enum):
    """Rule comparison operators"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN_RANGE = "in_range"
    NOT_IN_RANGE = "not_in_range"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class RuleAction(str, Enum):
    """Actions to take when rule matches"""
    APPROVE = "approve"
    REJECT = "reject"
    FLAG_FOR_REVIEW = "flag_for_review"
    REQUIRE_ADDITIONAL_DATA = "require_additional_data"
    APPLY_CONDITION = "apply_condition"
    TRIGGER_WORKFLOW = "trigger_workflow"


class DecisionRule(BaseModel):
    """Database-driven decision rule"""
    rule_id: str
    category: str
    name: str
    description: str
    priority: int
    conditions: List[Dict[str, Any]]
    action: RuleAction
    action_params: Dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RuleEvaluationResult(BaseModel):
    """Result of rule evaluation"""
    rule_id: str
    rule_name: str
    matched: bool
    action: Optional[RuleAction] = None
    action_params: Dict[str, Any] = Field(default_factory=dict)
    evaluation_details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class RuleBasedDecisionEngine:
    """
    Database-driven rule engine for pharmaceutical decisions
    Following DEVELOPER_GUIDELINES.md - ALL rules from database
    """

    def __init__(self, db_session: AsyncSession, redis_client: Any = None):
        self.db = db_session
        self.redis = redis_client
        self.rules_cache: Dict[str, List[DecisionRule]] = {}
        self.operators = self._initialize_operators()

    def _initialize_operators(self) -> Dict[str, Any]:
        """Initialize operator functions"""
        return {
            RuleOperator.EQUALS: operator.eq,
            RuleOperator.NOT_EQUALS: operator.ne,
            RuleOperator.GREATER_THAN: operator.gt,
            RuleOperator.LESS_THAN: operator.lt,
            RuleOperator.GREATER_EQUAL: operator.ge,
            RuleOperator.LESS_EQUAL: operator.le,
            RuleOperator.CONTAINS: lambda a, b: b in a if isinstance(a, (str, list)) else False,
            RuleOperator.NOT_CONTAINS: lambda a, b: b not in a if isinstance(a, (str, list)) else True,
            RuleOperator.IN_RANGE: lambda a, b: b[0] <= a <= b[1] if len(b) == 2 else False,
            RuleOperator.NOT_IN_RANGE: lambda a, b: not (b[0] <= a <= b[1]) if len(b) == 2 else True,
            RuleOperator.IS_NULL: lambda a, b: a is None,
            RuleOperator.IS_NOT_NULL: lambda a, b: a is not None
        }

    async def load_rules(self, category: Optional[str] = None):
        """Load decision rules from database"""
        query = """
        SELECT rule_id, category, name, description, priority,
               conditions, action, action_params, metadata, active
        FROM decision_rules
        WHERE active = true
        """

        params = {}
        if category:
            query += " AND category = :category"
            params["category"] = category

        query += " ORDER BY priority DESC"

        result = await self.db.execute(query, params)
        rules_data = result.fetchall()

        for rule_data in rules_data:
            rule = DecisionRule(
                rule_id=rule_data['rule_id'],
                category=rule_data['category'],
                name=rule_data['name'],
                description=rule_data['description'],
                priority=rule_data['priority'],
                conditions=json.loads(rule_data['conditions']),
                action=rule_data['action'],
                action_params=json.loads(rule_data['action_params']),
                metadata=json.loads(rule_data['metadata']) if rule_data['metadata'] else {}
            )

            if rule.category not in self.rules_cache:
                self.rules_cache[rule.category] = []
            self.rules_cache[rule.category].append(rule)

        logger.info(f"Loaded {sum(len(rules) for rules in self.rules_cache.values())} rules from database")

    async def evaluate_rules(
        self,
        category: str,
        data: Dict[str, Any],
        request_id: str
    ) -> List[RuleEvaluationResult]:
        """
        Evaluate all rules for a category against provided data
        All logic from database - NO hardcoded rules
        """

        # Load rules if not cached
        if category not in self.rules_cache:
            await self.load_rules(category)

        rules = self.rules_cache.get(category, [])
        results = []

        for rule in rules:
            # Evaluate rule conditions
            evaluation_result = await self._evaluate_rule(rule, data)

            # Log evaluation for audit trail
            await self._log_rule_evaluation(
                request_id,
                rule,
                evaluation_result,
                data
            )

            results.append(evaluation_result)

            # Stop on first rejection if configured
            if (evaluation_result.matched and
                evaluation_result.action == RuleAction.REJECT and
                rule.metadata.get('stop_on_match', False)):
                break

        return results

    async def _evaluate_rule(
        self,
        rule: DecisionRule,
        data: Dict[str, Any]
    ) -> RuleEvaluationResult:
        """Evaluate a single rule against data"""

        evaluation_details = {
            'conditions_evaluated': [],
            'all_conditions_met': False
        }

        all_conditions_met = True

        for condition in rule.conditions:
            # Extract condition components
            field = condition.get('field')
            operator_type = condition.get('operator')
            value = condition.get('value')
            logical_operator = condition.get('logical_operator', 'AND')

            # Get field value from data
            field_value = self._get_nested_value(data, field)

            # Evaluate condition
            condition_met = self._evaluate_condition(
                field_value,
                operator_type,
                value
            )

            evaluation_details['conditions_evaluated'].append({
                'field': field,
                'operator': operator_type,
                'expected': value,
                'actual': field_value,
                'met': condition_met,
                'logical_operator': logical_operator
            })

            # Apply logical operator
            if logical_operator == 'AND':
                all_conditions_met = all_conditions_met and condition_met
            elif logical_operator == 'OR' and condition_met:
                all_conditions_met = True
                break
            elif logical_operator == 'AND' and not condition_met:
                all_conditions_met = False
                break

        evaluation_details['all_conditions_met'] = all_conditions_met

        return RuleEvaluationResult(
            rule_id=rule.rule_id,
            rule_name=rule.name,
            matched=all_conditions_met,
            action=rule.action if all_conditions_met else None,
            action_params=rule.action_params if all_conditions_met else {},
            evaluation_details=evaluation_details
        )

    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        keys = field_path.split('.')
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value

    def _evaluate_condition(
        self,
        field_value: Any,
        operator_type: str,
        expected_value: Any
    ) -> bool:
        """Evaluate a single condition"""

        try:
            operator_func = self.operators.get(operator_type)
            if not operator_func:
                logger.warning(f"Unknown operator: {operator_type}")
                return False

            # Type conversion for comparison
            if operator_type in [RuleOperator.GREATER_THAN, RuleOperator.LESS_THAN,
                                RuleOperator.GREATER_EQUAL, RuleOperator.LESS_EQUAL,
                                RuleOperator.IN_RANGE, RuleOperator.NOT_IN_RANGE]:
                # Convert to numbers for comparison
                if field_value is not None:
                    try:
                        field_value = float(field_value)
                        if not isinstance(expected_value, list):
                            expected_value = float(expected_value)
                        else:
                            expected_value = [float(v) for v in expected_value]
                    except (ValueError, TypeError):
                        return False

            return operator_func(field_value, expected_value)

        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False

    async def apply_decision_actions(
        self,
        evaluation_results: List[RuleEvaluationResult],
        data: Dict[str, Any],
        request_id: str
    ) -> Dict[str, Any]:
        """
        Apply actions based on rule evaluation results
        All actions defined in database
        """

        decision_summary = {
            'request_id': request_id,
            'rules_evaluated': len(evaluation_results),
            'rules_matched': sum(1 for r in evaluation_results if r.matched),
            'primary_decision': None,
            'actions_applied': [],
            'flags': [],
            'requirements': []
        }

        # Process matched rules by priority (already sorted)
        for result in evaluation_results:
            if not result.matched:
                continue

            action_result = await self._apply_action(
                result.action,
                result.action_params,
                data
            )

            decision_summary['actions_applied'].append({
                'rule_id': result.rule_id,
                'rule_name': result.rule_name,
                'action': result.action,
                'result': action_result
            })

            # Update primary decision based on action
            if result.action == RuleAction.APPROVE and decision_summary['primary_decision'] is None:
                decision_summary['primary_decision'] = 'APPROVED'
            elif result.action == RuleAction.REJECT:
                decision_summary['primary_decision'] = 'REJECTED'
                break  # Stop on rejection
            elif result.action == RuleAction.FLAG_FOR_REVIEW:
                decision_summary['flags'].append(result.action_params)
            elif result.action == RuleAction.REQUIRE_ADDITIONAL_DATA:
                decision_summary['requirements'].append(result.action_params)

        # Default decision if no rules matched
        if decision_summary['primary_decision'] is None:
            decision_summary['primary_decision'] = 'PENDING_REVIEW'

        # Store decision in database
        await self._store_decision(decision_summary)

        return decision_summary

    async def _apply_action(
        self,
        action: RuleAction,
        params: Dict[str, Any],
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply specific action based on rule match"""

        result = {
            'action': action,
            'status': 'applied',
            'details': {}
        }

        if action == RuleAction.APPROVE:
            result['details'] = {
                'approval_level': params.get('level', 'standard'),
                'approval_notes': params.get('notes', '')
            }

        elif action == RuleAction.REJECT:
            result['details'] = {
                'rejection_reason': params.get('reason', 'Rule-based rejection'),
                'rejection_code': params.get('code', 'RULE_REJECT')
            }

        elif action == RuleAction.FLAG_FOR_REVIEW:
            result['details'] = {
                'review_type': params.get('type', 'manual'),
                'reviewer_group': params.get('group', 'analysts'),
                'priority': params.get('priority', 'normal'),
                'reason': params.get('reason', '')
            }

        elif action == RuleAction.REQUIRE_ADDITIONAL_DATA:
            result['details'] = {
                'required_fields': params.get('fields', []),
                'data_sources': params.get('sources', []),
                'deadline': params.get('deadline', 'none')
            }

        elif action == RuleAction.APPLY_CONDITION:
            # Apply conditional logic from database
            condition_query = """
            SELECT condition_logic
            FROM rule_conditions
            WHERE condition_id = :condition_id
            """
            condition_result = await self.db.execute(
                condition_query,
                {"condition_id": params.get('condition_id')}
            )
            condition = condition_result.fetchone()

            if condition:
                result['details'] = {
                    'condition_applied': params.get('condition_id'),
                    'condition_result': json.loads(condition['condition_logic'])
                }

        elif action == RuleAction.TRIGGER_WORKFLOW:
            # Trigger workflow defined in database
            result['details'] = {
                'workflow_id': params.get('workflow_id'),
                'workflow_params': params.get('workflow_params', {}),
                'triggered_at': datetime.now().isoformat()
            }

        return result

    async def _log_rule_evaluation(
        self,
        request_id: str,
        rule: DecisionRule,
        result: RuleEvaluationResult,
        data: Dict[str, Any]
    ):
        """Log rule evaluation for audit trail"""

        query = """
        INSERT INTO rule_evaluation_log
        (request_id, rule_id, rule_name, category, matched,
         action_taken, evaluation_details, input_data, timestamp)
        VALUES
        (:request_id, :rule_id, :rule_name, :category, :matched,
         :action_taken, :evaluation_details, :input_data, :timestamp)
        """

        await self.db.execute(
            query,
            {
                "request_id": request_id,
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "category": rule.category,
                "matched": result.matched,
                "action_taken": result.action if result.matched else None,
                "evaluation_details": json.dumps(result.evaluation_details),
                "input_data": json.dumps(data),
                "timestamp": datetime.now()
            }
        )
        await self.db.commit()

    async def _store_decision(self, decision_summary: Dict[str, Any]):
        """Store decision summary in database"""

        query = """
        INSERT INTO decision_summaries
        (request_id, primary_decision, rules_evaluated, rules_matched,
         actions_applied, flags, requirements, created_at)
        VALUES
        (:request_id, :primary_decision, :rules_evaluated, :rules_matched,
         :actions_applied, :flags, :requirements, :created_at)
        """

        await self.db.execute(
            query,
            {
                "request_id": decision_summary['request_id'],
                "primary_decision": decision_summary['primary_decision'],
                "rules_evaluated": decision_summary['rules_evaluated'],
                "rules_matched": decision_summary['rules_matched'],
                "actions_applied": json.dumps(decision_summary['actions_applied']),
                "flags": json.dumps(decision_summary['flags']),
                "requirements": json.dumps(decision_summary['requirements']),
                "created_at": datetime.now()
            }
        )
        await self.db.commit()

    async def get_rule_statistics(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get rule evaluation statistics for monitoring"""

        query = """
        SELECT
            COUNT(*) as total_evaluations,
            SUM(CASE WHEN matched THEN 1 ELSE 0 END) as total_matches,
            AVG(CASE WHEN matched THEN 1 ELSE 0 END) as match_rate,
            rule_id,
            rule_name
        FROM rule_evaluation_log
        WHERE timestamp > :since
        """

        params = {"since": datetime.now().replace(hour=0, minute=0, second=0)}

        if category:
            query += " AND category = :category"
            params["category"] = category

        query += " GROUP BY rule_id, rule_name ORDER BY total_evaluations DESC"

        result = await self.db.execute(query, params)
        stats = result.fetchall()

        return {
            'statistics': [
                {
                    'rule_id': stat['rule_id'],
                    'rule_name': stat['rule_name'],
                    'total_evaluations': stat['total_evaluations'],
                    'total_matches': stat['total_matches'],
                    'match_rate': float(stat['match_rate']) if stat['match_rate'] else 0
                }
                for stat in stats
            ]
        }

    async def validate_rule_consistency(self) -> List[Dict[str, Any]]:
        """Validate rules for conflicts and consistency"""

        issues = []

        for category, rules in self.rules_cache.items():
            # Check for conflicting rules
            for i, rule1 in enumerate(rules):
                for rule2 in rules[i+1:]:
                    if self._rules_conflict(rule1, rule2):
                        issues.append({
                            'type': 'conflict',
                            'category': category,
                            'rule1': rule1.rule_id,
                            'rule2': rule2.rule_id,
                            'description': f"Rules {rule1.name} and {rule2.name} have conflicting conditions"
                        })

            # Check for redundant rules
            for i, rule1 in enumerate(rules):
                for rule2 in rules[i+1:]:
                    if self._rules_redundant(rule1, rule2):
                        issues.append({
                            'type': 'redundancy',
                            'category': category,
                            'rule1': rule1.rule_id,
                            'rule2': rule2.rule_id,
                            'description': f"Rule {rule2.name} is redundant with {rule1.name}"
                        })

        return issues

    def _rules_conflict(self, rule1: DecisionRule, rule2: DecisionRule) -> bool:
        """Check if two rules have conflicting conditions"""

        # Simple conflict detection - would be enhanced
        if rule1.action == RuleAction.APPROVE and rule2.action == RuleAction.REJECT:
            # Check if conditions overlap
            for cond1 in rule1.conditions:
                for cond2 in rule2.conditions:
                    if (cond1['field'] == cond2['field'] and
                        cond1['operator'] == cond2['operator'] and
                        cond1['value'] == cond2['value']):
                        return True

        return False

    def _rules_redundant(self, rule1: DecisionRule, rule2: DecisionRule) -> bool:
        """Check if one rule makes another redundant"""

        # Simple redundancy check
        if (rule1.action == rule2.action and
            rule1.conditions == rule2.conditions):
            return True

        return False