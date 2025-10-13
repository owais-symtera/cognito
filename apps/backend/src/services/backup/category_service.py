"""
Category Service for managing 17 pharmaceutical intelligence categories.
Handles category configuration, prompt templates, and database persistence.
"""

from typing import Dict, List, Optional, Any
import json
import os
from datetime import datetime


class CategoryService:
    """Manages pharmaceutical category configurations and prompts."""

    def __init__(self, config_file: str = "categories_config.json"):
        """Initialize with category configurations."""
        self.config_file = os.path.join(
            os.path.dirname(__file__),
            "..",
            "data",
            config_file
        )
        self.categories = self._load_categories()

    def _load_categories(self) -> Dict[str, Any]:
        """Load category configurations from file or create defaults."""
        # Try to load from file
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass

        # Return default configuration if file doesn't exist
        return self._get_default_categories()

    def _get_default_categories(self) -> Dict[str, Any]:
        """Get default 17 pharmaceutical categories with prompts."""
        return {
            # Phase 1: Data Collection Categories (1-10)
            "market_overview": {
                "id": 1,
                "name": "Market Overview",
                "phase": 1,
                "enabled": True,
                "prompt_template": "Analyze the global and regional market for {drug_name}. Include: 1) Current global market size in USD, 2) Year-over-year growth rates, 3) Regional market distribution (US, EU, Asia, Others), 4) Market penetration rates, 5) Pricing trends across regions, 6) Reimbursement status by country. Focus on data from the last 3 years. Prioritize data from paid pharmaceutical databases, government sources, and industry reports.",
                "weight": 1.0,
                "source_priorities": ["paid_apis", "government", "industry", "peer_reviewed"]
            },
            "competitive_landscape": {
                "id": 2,
                "name": "Competitive Landscape",
                "phase": 1,
                "enabled": True,
                "prompt_template": "Provide comprehensive competitive analysis for {drug_name}. Include: 1) Direct competitors with market share percentages, 2) Indirect/alternative therapies, 3) Competitive advantages and disadvantages, 4) Head-to-head clinical trial comparisons, 5) Pricing comparison with competitors, 6) Pipeline competitors in development. Focus on therapeutic class competition and market positioning.",
                "weight": 1.0,
                "source_priorities": ["paid_apis", "industry", "peer_reviewed", "company"]
            },
            "regulatory_patent": {
                "id": 3,
                "name": "Regulatory & Patent Status",
                "phase": 1,
                "enabled": True,
                "prompt_template": "Compile regulatory and patent information for {drug_name}. Include: 1) FDA approval date and indications, 2) EMA and other major regulatory approvals, 3) Patent expiration dates by region, 4) Data exclusivity periods, 5) Generic entry forecasts, 6) Regulatory exclusivities (orphan, pediatric), 7) Patent litigation status. Search FDA Orange Book, EMA databases, and patent registries.",
                "weight": 1.2,
                "source_priorities": ["government", "paid_apis", "peer_reviewed"]
            },
            "commercial_opportunities": {
                "id": 4,
                "name": "Commercial Opportunities",
                "phase": 1,
                "enabled": True,
                "prompt_template": "Identify commercial opportunities for {drug_name}. Include: 1) Unmet medical needs in current indications, 2) Potential new indications or expansions, 3) Underserved patient populations, 4) Geographic expansion opportunities, 5) Partnership or licensing opportunities, 6) Value-based contracting potential. Focus on actionable commercial intelligence.",
                "weight": 0.9,
                "source_priorities": ["paid_apis", "industry", "peer_reviewed", "news"]
            },
            "current_formulations": {
                "id": 5,
                "name": "Current Formulations",
                "phase": 1,
                "enabled": True,
                "prompt_template": "Detail all current formulations of {drug_name}. Include: 1) Available dosage forms (tablets, capsules, injectable, etc.), 2) Strengths and concentrations, 3) Excipients and inactive ingredients, 4) Storage requirements and stability, 5) Manufacturing sites, 6) Bioequivalence data if generic versions exist. Search drug labels and pharmaceutical databases.",
                "weight": 0.8,
                "source_priorities": ["government", "paid_apis", "company"]
            },
            "investigational_formulations": {
                "id": 6,
                "name": "Investigational Formulations",
                "phase": 1,
                "enabled": True,
                "prompt_template": "Research investigational formulations and delivery systems for {drug_name}. Include: 1) New formulations in clinical trials, 2) Novel delivery systems (extended release, patches, etc.), 3) Fixed-dose combinations in development, 4) Pediatric or geriatric formulations, 5) Abuse-deterrent formulations if applicable, 6) Development timeline and status. Search ClinicalTrials.gov and company pipelines.",
                "weight": 0.7,
                "source_priorities": ["government", "company", "peer_reviewed", "paid_apis"]
            },
            "physicochemical_profile": {
                "id": 7,
                "name": "Physicochemical Profile",
                "phase": 1,
                "enabled": True,
                "prompt_template": "Provide physicochemical properties of {drug_name}. Include: 1) Molecular weight and formula, 2) LogP and LogD values, 3) Solubility profile (aqueous and organic), 4) pKa values, 5) Melting point and polymorphs, 6) BCS classification, 7) Permeability data, 8) Chemical stability profile. Search pharmaceutical chemistry databases and drug bank resources.",
                "weight": 0.6,
                "source_priorities": ["paid_apis", "peer_reviewed", "government"]
            },
            "pharmacokinetics": {
                "id": 8,
                "name": "Pharmacokinetics",
                "phase": 1,
                "enabled": True,
                "prompt_template": "Analyze pharmacokinetic profile of {drug_name}. Include: 1) Absorption (Tmax, bioavailability), 2) Distribution (Vd, protein binding), 3) Metabolism (CYP enzymes, metabolites), 4) Elimination (half-life, clearance routes), 5) Special populations (renal/hepatic impairment, elderly, pediatric), 6) Drug-drug interactions, 7) Food effects. Focus on clinically relevant PK parameters.",
                "weight": 0.9,
                "source_priorities": ["government", "peer_reviewed", "paid_apis"]
            },
            "dosage_forms": {
                "id": 9,
                "name": "Dosage Forms",
                "phase": 1,
                "enabled": True,
                "prompt_template": "Compile dosage and administration information for {drug_name}. Include: 1) Approved dosing regimens by indication, 2) Dose adjustments for special populations, 3) Maximum daily doses, 4) Loading and maintenance doses, 5) Titration schedules, 6) Administration instructions and restrictions, 7) Dose conversion between formulations. Search prescribing information and clinical guidelines.",
                "weight": 0.8,
                "source_priorities": ["government", "peer_reviewed", "company"]
            },
            "clinical_trials_safety": {
                "id": 10,
                "name": "Clinical Trials & Safety",
                "phase": 1,
                "enabled": True,
                "prompt_template": "Analyze clinical trials and safety profile for {drug_name}. Include: 1) Pivotal trial results with efficacy endpoints, 2) Ongoing clinical trials from ClinicalTrials.gov, 3) Common adverse events (>5% incidence), 4) Serious adverse events and black box warnings, 5) REMS requirements if applicable, 6) Post-marketing surveillance findings, 7) Real-world evidence studies. Search FDA FAERS, clinical trial registries, and medical literature.",
                "weight": 1.1,
                "source_priorities": ["government", "peer_reviewed", "paid_apis", "industry"]
            },

            # Phase 2: Decision Intelligence Categories (11-17)
            "parameter_scoring": {
                "id": 11,
                "name": "Parameter-Based Scoring",
                "phase": 2,
                "enabled": True,
                "prompt_template": "Generate parameter-based scoring matrix for {drug_name} using Phase 1 data. Score each parameter on 0-100 scale: 1) Market size score based on TAM, 2) Growth potential score, 3) Competitive advantage score, 4) Regulatory complexity score, 5) Manufacturing feasibility score, 6) Patent strength score, 7) Clinical differentiation score. Provide scoring rationale and confidence intervals.",
                "weight": 1.0,
                "requires_phase1": True
            },
            "weighted_assessment": {
                "id": 12,
                "name": "Weighted Scoring Assessment",
                "phase": 2,
                "enabled": True,
                "prompt_template": "Create weighted assessment for {drug_name} combining all factors. Apply weights: Commercial factors (35%), Technical/Clinical factors (30%), Regulatory factors (20%), Competitive factors (15%). Calculate composite score and provide sensitivity analysis showing score changes with ±10% weight adjustments. Include risk-adjusted scoring.",
                "weight": 1.0,
                "requires_phase1": True
            },
            "go_no_go": {
                "id": 13,
                "name": "Go/No-Go Verdict",
                "phase": 2,
                "enabled": True,
                "prompt_template": "Generate Go/No-Go recommendation for {drug_name} based on comprehensive analysis. Consider: 1) Minimum viable market size threshold, 2) Regulatory approval probability, 3) Competitive sustainability, 4) Technical feasibility, 5) Financial projections vs investment required. Provide clear verdict with confidence score (0-100%) and top 3 supporting reasons and top 3 risks.",
                "weight": 1.2,
                "requires_phase1": True
            },
            "executive_summary": {
                "id": 14,
                "name": "Executive Summary",
                "phase": 2,
                "enabled": True,
                "prompt_template": "Synthesize executive summary for {drug_name} suitable for C-suite presentation. Include: 1) One-paragraph investment thesis, 2) Key value drivers (3-5 bullets), 3) Critical risks and mitigation strategies, 4) Financial highlights and projections, 5) Recommended next steps with timeline, 6) Decision urgency factors. Maximum 500 words, focus on actionable insights.",
                "weight": 1.1,
                "requires_phase1": True
            },
            "risk_assessment": {
                "id": 15,
                "name": "Risk Assessment",
                "phase": 2,
                "enabled": True,
                "prompt_template": "Conduct comprehensive risk assessment for {drug_name}. Categorize risks as: 1) Regulatory risks (approval delays, label restrictions), 2) Commercial risks (market access, competition), 3) Technical risks (manufacturing, supply chain), 4) Financial risks (development costs, pricing pressure), 5) Strategic risks (IP challenges, partnership dependencies). Rate each risk as High/Medium/Low with mitigation strategies.",
                "weight": 1.0,
                "requires_phase1": True
            },
            "strategic_recommendations": {
                "id": 16,
                "name": "Strategic Recommendations",
                "phase": 2,
                "enabled": True,
                "prompt_template": "Provide strategic recommendations for {drug_name}. Include: 1) Optimal development strategy (fast-track, standard, lifecycle management), 2) Partnership recommendations (licensing, co-development, acquisition), 3) Market entry strategy by region, 4) Pricing and market access strategy, 5) Portfolio fit and prioritization, 6) Resource allocation recommendations. Focus on actionable 12-24 month roadmap.",
                "weight": 0.9,
                "requires_phase1": True
            },
            "investment_analysis": {
                "id": 17,
                "name": "Investment Analysis",
                "phase": 2,
                "enabled": True,
                "prompt_template": "Perform investment analysis for {drug_name}. Calculate: 1) Net Present Value (NPV) with assumptions, 2) Internal Rate of Return (IRR), 3) Peak sales projections with timeline, 4) Break-even analysis, 5) Return on Investment (ROI) scenarios, 6) Comparable deals analysis, 7) Valuation range for licensing/M&A. Include bull, base, and bear case scenarios with probability weighting.",
                "weight": 1.0,
                "requires_phase1": True
            }
        }

    def save_categories(self) -> bool:
        """Save category configuration to file."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.categories, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving categories: {e}")
            return False

    def get_all_categories(self) -> Dict[str, Any]:
        """Get all category configurations."""
        return self.categories

    def get_enabled_categories(self, phase: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get only enabled categories, optionally filtered by phase."""
        enabled = []
        for key, cat in self.categories.items():
            if cat.get("enabled", False):
                if phase is None or cat.get("phase") == phase:
                    cat["key"] = key
                    enabled.append(cat)
        return sorted(enabled, key=lambda x: x.get("id", 999))

    def get_category(self, category_key: str) -> Optional[Dict[str, Any]]:
        """Get a specific category by key."""
        return self.categories.get(category_key)

    def get_category_prompt(self, category_key: str, drug_name: str) -> Optional[str]:
        """Get formatted prompt for a category."""
        category = self.get_category(category_key)
        if not category:
            return None

        # Replace placeholders in prompt template
        prompt = category.get("prompt_template", "")
        return prompt.replace("{drug_name}", drug_name)

    def update_category(self, category_key: str, updates: Dict[str, Any]) -> bool:
        """Update category configuration."""
        if category_key not in self.categories:
            return False

        # Update allowed fields
        allowed_fields = ["enabled", "weight", "prompt_template", "source_priorities"]
        for field in allowed_fields:
            if field in updates:
                self.categories[category_key][field] = updates[field]

        # Save changes
        return self.save_categories()

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
        result = []
        for key, category in self.categories.items():
            if category.get("enabled", False):
                cat_copy = category.copy()
                cat_copy["key"] = key
                cat_copy["prompt"] = self.get_category_prompt(key, drug_name)
                result.append(cat_copy)
        return sorted(result, key=lambda x: x.get("id", 999))