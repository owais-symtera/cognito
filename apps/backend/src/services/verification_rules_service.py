"""
Verification Rules Service
Manages dynamic validation rules for the pipeline verification stage.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class VerificationRulesService:
    """Service for managing verification stage validation rules."""

    CONFIG_FILE = Path("verification_rules.json")

    def __init__(self):
        """Initialize verification rules service."""
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        """Load verification rules from file."""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, "r") as f:
                    rules = json.load(f)
                    logger.info("Verification rules loaded from file")
                    return rules
            except Exception as e:
                logger.error("Error loading verification rules", error=str(e))

        # Return default rules if file doesn't exist
        default_rules = self._get_default_rules()
        self._save_rules(default_rules)
        return default_rules

    def _save_rules(self, rules: Dict[str, Any]) -> bool:
        """Save verification rules to file."""
        try:
            with open(self.CONFIG_FILE, "w") as f:
                json.dump(rules, f, indent=2)
            logger.info("Verification rules saved to file")
            return True
        except Exception as e:
            logger.error("Error saving verification rules", error=str(e))
            return False

    def _get_default_rules(self) -> Dict[str, Any]:
        """Get default verification rules."""
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "source_weights": {
                "chatgpt": {
                    "weight": 10,
                    "description": "Paid AI API - Highest trust",
                    "category": "paid_api"
                },
                "openai": {
                    "weight": 10,
                    "description": "Paid AI API - Highest trust",
                    "category": "paid_api"
                },
                "perplexity": {
                    "weight": 10,
                    "description": "Paid AI API - Highest trust",
                    "category": "paid_api"
                },
                "grok": {
                    "weight": 10,
                    "description": "Paid AI API - Highest trust",
                    "category": "paid_api"
                },
                "gemini": {
                    "weight": 10,
                    "description": "Paid AI API - Highest trust",
                    "category": "paid_api"
                },
                "tavily": {
                    "weight": 10,
                    "description": "Paid Search API - Highest trust",
                    "category": "paid_api"
                },
                "government": {
                    "weight": 8,
                    "description": "Government sources (FDA, NIH, etc.)",
                    "category": "institutional"
                },
                "peer_reviewed": {
                    "weight": 6,
                    "description": "Academic/peer-reviewed sources",
                    "category": "academic"
                },
                "industry": {
                    "weight": 4,
                    "description": "Industry publications",
                    "category": "commercial"
                },
                "company": {
                    "weight": 2,
                    "description": "Company websites",
                    "category": "commercial"
                },
                "news": {
                    "weight": 1,
                    "description": "News media",
                    "category": "media"
                },
                "unknown": {
                    "weight": 0,
                    "description": "Unverified sources",
                    "category": "unverified"
                }
            },
            "credibility_rules": {
                "content_length_threshold": 1000,
                "min_credibility_score": 0.0,
                "max_credibility_score": 1.0,
                "description": "Content length-based credibility: min(max_score, length / threshold)"
            },
            "verification_thresholds": {
                "min_weight_for_verified": 1,
                "min_authority_for_high_confidence": 80,
                "min_authority_for_medium_confidence": 50,
                "description": "Thresholds for verification status classification"
            },
            "quality_gates": {
                "min_sources_required": 1,
                "min_verified_sources_required": 1,
                "min_avg_authority_score": 30,
                "reject_if_all_unverified": True,
                "description": "Quality gates that data must pass"
            }
        }

    def get_all_rules(self) -> Dict[str, Any]:
        """Get all verification rules."""
        return self.rules

    def get_source_weights(self) -> Dict[str, int]:
        """Get simplified source weights dictionary (for backward compatibility)."""
        weights = {}
        for source, config in self.rules.get("source_weights", {}).items():
            weights[source] = config.get("weight", 0)
        return weights

    def get_source_weight(self, source: str) -> int:
        """Get weight for a specific source."""
        source_lower = source.lower()
        source_config = self.rules.get("source_weights", {}).get(source_lower, {})
        return source_config.get("weight", self.rules["source_weights"]["unknown"]["weight"])

    def update_source_weight(self, source: str, weight: int, description: Optional[str] = None) -> bool:
        """Update weight for a specific source."""
        if weight < 0 or weight > 10:
            logger.error("Invalid weight value", source=source, weight=weight)
            return False

        source_lower = source.lower()
        if source_lower not in self.rules["source_weights"]:
            # Create new source entry
            self.rules["source_weights"][source_lower] = {
                "weight": weight,
                "description": description or f"Custom source: {source}",
                "category": "custom"
            }
        else:
            # Update existing source
            self.rules["source_weights"][source_lower]["weight"] = weight
            if description:
                self.rules["source_weights"][source_lower]["description"] = description

        self.rules["last_updated"] = datetime.now().isoformat()
        return self._save_rules(self.rules)

    def update_credibility_rules(self, updates: Dict[str, Any]) -> bool:
        """Update credibility calculation rules."""
        for key, value in updates.items():
            if key in self.rules["credibility_rules"]:
                self.rules["credibility_rules"][key] = value

        self.rules["last_updated"] = datetime.now().isoformat()
        return self._save_rules(self.rules)

    def update_verification_thresholds(self, updates: Dict[str, Any]) -> bool:
        """Update verification threshold rules."""
        for key, value in updates.items():
            if key in self.rules["verification_thresholds"]:
                self.rules["verification_thresholds"][key] = value

        self.rules["last_updated"] = datetime.now().isoformat()
        return self._save_rules(self.rules)

    def update_quality_gates(self, updates: Dict[str, Any]) -> bool:
        """Update quality gate rules."""
        for key, value in updates.items():
            if key in self.rules["quality_gates"]:
                self.rules["quality_gates"][key] = value

        self.rules["last_updated"] = datetime.now().isoformat()
        return self._save_rules(self.rules)

    def calculate_credibility_score(self, content_length: int) -> float:
        """Calculate credibility score based on content length."""
        rules = self.rules["credibility_rules"]
        threshold = rules["content_length_threshold"]
        max_score = rules["max_credibility_score"]
        min_score = rules["min_credibility_score"]

        score = min(max_score, content_length / threshold)
        return max(min_score, score)

    def is_verified(self, weight: int) -> bool:
        """Check if source is verified based on weight."""
        threshold = self.rules["verification_thresholds"]["min_weight_for_verified"]
        return weight >= threshold

    def check_quality_gates(self, verification_result: Dict[str, Any]) -> Dict[str, Any]:
        """Check if verification result passes quality gates."""
        gates = self.rules["quality_gates"]
        metadata = verification_result.get("metadata", {})

        passed = True
        failed_gates = []

        # Check minimum sources
        if metadata.get("total_sources", 0) < gates["min_sources_required"]:
            passed = False
            failed_gates.append(f"Minimum sources required: {gates['min_sources_required']}")

        # Check minimum verified sources
        if metadata.get("verified_count", 0) < gates["min_verified_sources_required"]:
            passed = False
            failed_gates.append(f"Minimum verified sources required: {gates['min_verified_sources_required']}")

        # Check average authority score
        if metadata.get("avg_authority_score", 0) < gates["min_avg_authority_score"]:
            passed = False
            failed_gates.append(f"Minimum average authority score: {gates['min_avg_authority_score']}")

        # Check if all unverified
        if gates["reject_if_all_unverified"] and metadata.get("verified_count", 0) == 0:
            passed = False
            failed_gates.append("At least one verified source required")

        return {
            "passed": passed,
            "failed_gates": failed_gates,
            "quality_score": self._calculate_quality_score(metadata)
        }

    def _calculate_quality_score(self, metadata: Dict[str, Any]) -> float:
        """Calculate overall quality score (0.0 - 1.0)."""
        gates = self.rules["quality_gates"]

        # Calculate component scores
        source_score = min(1.0, metadata.get("total_sources", 0) / max(gates["min_sources_required"], 1))
        verified_score = min(1.0, metadata.get("verified_count", 0) / max(gates["min_verified_sources_required"], 1))
        authority_score = min(1.0, metadata.get("avg_authority_score", 0) / max(gates["min_avg_authority_score"], 1))

        # Weighted average
        return (source_score * 0.3 + verified_score * 0.3 + authority_score * 0.4)

    def get_strictness_level(self) -> str:
        """Get current strictness level based on rules."""
        gates = self.rules["quality_gates"]

        if gates["min_avg_authority_score"] >= 70:
            return "strict"
        elif gates["min_avg_authority_score"] >= 50:
            return "moderate"
        else:
            return "relaxed"

    def set_strictness_level(self, level: str) -> bool:
        """Set overall strictness level (preset configurations)."""
        presets = {
            "strict": {
                "quality_gates": {
                    "min_sources_required": 3,
                    "min_verified_sources_required": 2,
                    "min_avg_authority_score": 70,
                    "reject_if_all_unverified": True
                },
                "verification_thresholds": {
                    "min_weight_for_verified": 6,
                    "min_authority_for_high_confidence": 90,
                    "min_authority_for_medium_confidence": 70
                }
            },
            "moderate": {
                "quality_gates": {
                    "min_sources_required": 2,
                    "min_verified_sources_required": 1,
                    "min_avg_authority_score": 50,
                    "reject_if_all_unverified": True
                },
                "verification_thresholds": {
                    "min_weight_for_verified": 4,
                    "min_authority_for_high_confidence": 80,
                    "min_authority_for_medium_confidence": 50
                }
            },
            "relaxed": {
                "quality_gates": {
                    "min_sources_required": 1,
                    "min_verified_sources_required": 1,
                    "min_avg_authority_score": 30,
                    "reject_if_all_unverified": False
                },
                "verification_thresholds": {
                    "min_weight_for_verified": 1,
                    "min_authority_for_high_confidence": 70,
                    "min_authority_for_medium_confidence": 40
                }
            }
        }

        if level not in presets:
            logger.error("Invalid strictness level", level=level)
            return False

        preset = presets[level]
        self.rules["quality_gates"].update(preset["quality_gates"])
        self.rules["verification_thresholds"].update(preset["verification_thresholds"])
        self.rules["last_updated"] = datetime.now().isoformat()

        logger.info("Strictness level updated", level=level)
        return self._save_rules(self.rules)

    def reset_to_defaults(self) -> bool:
        """Reset all rules to defaults."""
        self.rules = self._get_default_rules()
        return self._save_rules(self.rules)
