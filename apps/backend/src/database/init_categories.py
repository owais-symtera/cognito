"""
Initialize pharmaceutical categories in the database.
This script populates the database with the 17 pharmaceutical intelligence categories.
"""

import asyncio
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .models import PharmaceuticalCategory, Base
from .connection import get_db_url

# The 17 pharmaceutical categories with their configurations
CATEGORIES = [
    # Phase 1: Data Collection Categories (1-10)
    {
        "id": 1,
        "name": "Market Overview",
        "description": "Global and regional market analysis for pharmaceutical products",
        "display_order": 1,
        "phase": 1,
        "is_active": True,
        "prompt_templates": {
            "default": "Analyze the global and regional market for {drug_name}. Include: 1) Current global market size in USD, 2) Year-over-year growth rates, 3) Regional market distribution (US, EU, Asia, Others), 4) Market penetration rates, 5) Pricing trends across regions, 6) Reimbursement status by country. Focus on data from the last 3 years. Prioritize data from paid pharmaceutical databases, government sources, and industry reports."
        },
        "search_parameters": {
            "weight": 1.0,
            "source_priorities": ["paid_apis", "government", "industry", "peer_reviewed"]
        }
    },
    {
        "id": 2,
        "name": "Competitive Landscape",
        "description": "Comprehensive competitive analysis for pharmaceutical products",
        "display_order": 2,
        "phase": 1,
        "is_active": True,
        "prompt_templates": {
            "default": "Provide comprehensive competitive analysis for {drug_name}. Include: 1) Direct competitors with market share percentages, 2) Indirect/alternative therapies, 3) Competitive advantages and disadvantages, 4) Head-to-head clinical trial comparisons, 5) Pricing comparison with competitors, 6) Pipeline competitors in development. Focus on therapeutic class competition and market positioning."
        },
        "search_parameters": {
            "weight": 1.0,
            "source_priorities": ["paid_apis", "industry", "peer_reviewed", "company"]
        }
    },
    {
        "id": 3,
        "name": "Regulatory & Patent Status",
        "description": "Regulatory approvals and patent information",
        "display_order": 3,
        "phase": 1,
        "is_active": True,
        "prompt_templates": {
            "default": "Compile regulatory and patent information for {drug_name}. Include: 1) FDA approval date and indications, 2) EMA and other major regulatory approvals, 3) Patent expiration dates by region, 4) Data exclusivity periods, 5) Generic entry forecasts, 6) Regulatory exclusivities (orphan, pediatric), 7) Patent litigation status. Search FDA Orange Book, EMA databases, and patent registries."
        },
        "search_parameters": {
            "weight": 1.2,
            "source_priorities": ["government", "paid_apis", "peer_reviewed"]
        }
    },
    {
        "id": 4,
        "name": "Commercial Opportunities",
        "description": "Identify commercial opportunities and expansion potential",
        "display_order": 4,
        "phase": 1,
        "is_active": True,
        "prompt_templates": {
            "default": "Identify commercial opportunities for {drug_name}. Include: 1) Unmet medical needs in current indications, 2) Potential new indications or expansions, 3) Underserved patient populations, 4) Geographic expansion opportunities, 5) Partnership or licensing opportunities, 6) Value-based contracting potential. Focus on actionable commercial intelligence."
        },
        "search_parameters": {
            "weight": 0.9,
            "source_priorities": ["paid_apis", "industry", "peer_reviewed", "news"]
        }
    },
    {
        "id": 5,
        "name": "Current Formulations",
        "description": "Available formulations and manufacturing details",
        "display_order": 5,
        "phase": 1,
        "is_active": True,
        "prompt_templates": {
            "default": "Detail all current formulations of {drug_name}. Include: 1) Available dosage forms (tablets, capsules, injectable, etc.), 2) Strengths and concentrations, 3) Excipients and inactive ingredients, 4) Storage requirements and stability, 5) Manufacturing sites, 6) Bioequivalence data if generic versions exist. Search drug labels and pharmaceutical databases."
        },
        "search_parameters": {
            "weight": 0.8,
            "source_priorities": ["government", "paid_apis", "company"]
        }
    },
    {
        "id": 6,
        "name": "Investigational Formulations",
        "description": "New formulations and delivery systems in development",
        "display_order": 6,
        "phase": 1,
        "is_active": True,
        "prompt_templates": {
            "default": "Research investigational formulations and delivery systems for {drug_name}. Include: 1) New formulations in clinical trials, 2) Novel delivery systems (extended release, patches, etc.), 3) Fixed-dose combinations in development, 4) Pediatric or geriatric formulations, 5) Abuse-deterrent formulations if applicable, 6) Development timeline and status. Search ClinicalTrials.gov and company pipelines."
        },
        "search_parameters": {
            "weight": 0.7,
            "source_priorities": ["government", "company", "peer_reviewed", "paid_apis"]
        }
    },
    {
        "id": 7,
        "name": "Physicochemical Profile",
        "description": "Chemical and physical properties of the drug",
        "display_order": 7,
        "phase": 1,
        "is_active": True,
        "prompt_templates": {
            "default": "Provide physicochemical properties of {drug_name}. Include: 1) Molecular weight and formula, 2) LogP and LogD values, 3) Solubility profile (aqueous and organic), 4) pKa values, 5) Melting point and polymorphs, 6) BCS classification, 7) Permeability data, 8) Chemical stability profile. Search pharmaceutical chemistry databases and drug bank resources."
        },
        "search_parameters": {
            "weight": 0.6,
            "source_priorities": ["paid_apis", "peer_reviewed", "government"]
        }
    },
    {
        "id": 8,
        "name": "Pharmacokinetics",
        "description": "Absorption, distribution, metabolism, and elimination profile",
        "display_order": 8,
        "phase": 1,
        "is_active": True,
        "prompt_templates": {
            "default": "Analyze pharmacokinetic profile of {drug_name}. Include: 1) Absorption (Tmax, bioavailability), 2) Distribution (Vd, protein binding), 3) Metabolism (CYP enzymes, metabolites), 4) Elimination (half-life, clearance routes), 5) Special populations (renal/hepatic impairment, elderly, pediatric), 6) Drug-drug interactions, 7) Food effects. Focus on clinically relevant PK parameters."
        },
        "search_parameters": {
            "weight": 0.9,
            "source_priorities": ["government", "peer_reviewed", "paid_apis"]
        }
    },
    {
        "id": 9,
        "name": "Dosage Forms",
        "description": "Dosing regimens and administration guidelines",
        "display_order": 9,
        "phase": 1,
        "is_active": True,
        "prompt_templates": {
            "default": "Compile dosage and administration information for {drug_name}. Include: 1) Approved dosing regimens by indication, 2) Dose adjustments for special populations, 3) Maximum daily doses, 4) Loading and maintenance doses, 5) Titration schedules, 6) Administration instructions and restrictions, 7) Dose conversion between formulations. Search prescribing information and clinical guidelines."
        },
        "search_parameters": {
            "weight": 0.8,
            "source_priorities": ["government", "peer_reviewed", "company"]
        }
    },
    {
        "id": 10,
        "name": "Clinical Trials & Safety",
        "description": "Clinical trial results and safety profile",
        "display_order": 10,
        "phase": 1,
        "is_active": True,
        "prompt_templates": {
            "default": "Analyze clinical trials and safety profile for {drug_name}. Include: 1) Pivotal trial results with efficacy endpoints, 2) Ongoing clinical trials from ClinicalTrials.gov, 3) Common adverse events (>5% incidence), 4) Serious adverse events and black box warnings, 5) REMS requirements if applicable, 6) Post-marketing surveillance findings, 7) Real-world evidence studies. Search FDA FAERS, clinical trial registries, and medical literature."
        },
        "search_parameters": {
            "weight": 1.1,
            "source_priorities": ["government", "peer_reviewed", "paid_apis", "industry"]
        }
    },

    # Phase 2: Decision Intelligence Categories (11-17)
    {
        "id": 11,
        "name": "Parameter-Based Scoring",
        "description": "Generate parameter-based scoring matrix from Phase 1 data",
        "display_order": 11,
        "phase": 2,
        "is_active": True,
        "prompt_templates": {
            "default": "Generate parameter-based scoring matrix for {drug_name} using Phase 1 data. Score each parameter on 0-100 scale: 1) Market size score based on TAM, 2) Growth potential score, 3) Competitive advantage score, 4) Regulatory complexity score, 5) Manufacturing feasibility score, 6) Patent strength score, 7) Clinical differentiation score. Provide scoring rationale and confidence intervals."
        },
        "search_parameters": {
            "weight": 1.0,
            "requires_phase1": True
        }
    },
    {
        "id": 12,
        "name": "Weighted Scoring Assessment",
        "description": "Create weighted assessment combining all factors",
        "display_order": 12,
        "phase": 2,
        "is_active": True,
        "prompt_templates": {
            "default": "Create weighted assessment for {drug_name} combining all factors. Apply weights: Commercial factors (35%), Technical/Clinical factors (30%), Regulatory factors (20%), Competitive factors (15%). Calculate composite score and provide sensitivity analysis showing score changes with ±10% weight adjustments. Include risk-adjusted scoring."
        },
        "search_parameters": {
            "weight": 1.0,
            "requires_phase1": True
        }
    },
    {
        "id": 13,
        "name": "Go/No-Go Verdict",
        "description": "Generate investment recommendation based on comprehensive analysis",
        "display_order": 13,
        "phase": 2,
        "is_active": True,
        "prompt_templates": {
            "default": "Generate Go/No-Go recommendation for {drug_name} based on comprehensive analysis. Consider: 1) Minimum viable market size threshold, 2) Regulatory approval probability, 3) Competitive sustainability, 4) Technical feasibility, 5) Financial projections vs investment required. Provide clear verdict with confidence score (0-100%) and top 3 supporting reasons and top 3 risks."
        },
        "search_parameters": {
            "weight": 1.2,
            "requires_phase1": True
        }
    },
    {
        "id": 14,
        "name": "Executive Summary",
        "description": "Synthesize executive summary for C-suite presentation",
        "display_order": 14,
        "phase": 2,
        "is_active": True,
        "prompt_templates": {
            "default": "Synthesize executive summary for {drug_name} suitable for C-suite presentation. Include: 1) One-paragraph investment thesis, 2) Key value drivers (3-5 bullets), 3) Critical risks and mitigation strategies, 4) Financial highlights and projections, 5) Recommended next steps with timeline, 6) Decision urgency factors. Maximum 500 words, focus on actionable insights."
        },
        "search_parameters": {
            "weight": 1.1,
            "requires_phase1": True
        }
    },
    {
        "id": 15,
        "name": "Risk Assessment",
        "description": "Comprehensive risk assessment across all dimensions",
        "display_order": 15,
        "phase": 2,
        "is_active": True,
        "prompt_templates": {
            "default": "Conduct comprehensive risk assessment for {drug_name}. Categorize risks as: 1) Regulatory risks (approval delays, label restrictions), 2) Commercial risks (market access, competition), 3) Technical risks (manufacturing, supply chain), 4) Financial risks (development costs, pricing pressure), 5) Strategic risks (IP challenges, partnership dependencies). Rate each risk as High/Medium/Low with mitigation strategies."
        },
        "search_parameters": {
            "weight": 1.0,
            "requires_phase1": True
        }
    },
    {
        "id": 16,
        "name": "Strategic Recommendations",
        "description": "Provide strategic recommendations and roadmap",
        "display_order": 16,
        "phase": 2,
        "is_active": True,
        "prompt_templates": {
            "default": "Provide strategic recommendations for {drug_name}. Include: 1) Optimal development strategy (fast-track, standard, lifecycle management), 2) Partnership recommendations (licensing, co-development, acquisition), 3) Market entry strategy by region, 4) Pricing and market access strategy, 5) Portfolio fit and prioritization, 6) Resource allocation recommendations. Focus on actionable 12-24 month roadmap."
        },
        "search_parameters": {
            "weight": 0.9,
            "requires_phase1": True
        }
    },
    {
        "id": 17,
        "name": "Investment Analysis",
        "description": "Perform detailed investment and valuation analysis",
        "display_order": 17,
        "phase": 2,
        "is_active": True,
        "prompt_templates": {
            "default": "Perform investment analysis for {drug_name}. Calculate: 1) Net Present Value (NPV) with assumptions, 2) Internal Rate of Return (IRR), 3) Peak sales projections with timeline, 4) Break-even analysis, 5) Return on Investment (ROI) scenarios, 6) Comparable deals analysis, 7) Valuation range for licensing/M&A. Include bull, base, and bear case scenarios with probability weighting."
        },
        "search_parameters": {
            "weight": 1.0,
            "requires_phase1": True
        }
    }
]


async def init_categories():
    """Initialize pharmaceutical categories in the database."""

    # Create database engine
    engine = create_async_engine(
        get_db_url(),
        echo=True
    )

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        try:
            # Check if categories already exist
            from sqlalchemy import select
            result = await session.execute(
                select(PharmaceuticalCategory).limit(1)
            )
            existing = result.scalar_one_or_none()

            if existing:
                print("Categories already exist in database. Skipping initialization.")
                return

            # Insert all categories
            for cat_data in CATEGORIES:
                category = PharmaceuticalCategory(
                    id=cat_data["id"],
                    name=cat_data["name"],
                    description=cat_data["description"],
                    display_order=cat_data["display_order"],
                    phase=cat_data["phase"],
                    is_active=cat_data["is_active"],
                    prompt_templates=json.dumps(cat_data["prompt_templates"]),
                    search_parameters=json.dumps(cat_data["search_parameters"]),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    created_by="system",
                    updated_by="system"
                )
                session.add(category)

            await session.commit()
            print(f"Successfully initialized {len(CATEGORIES)} pharmaceutical categories in the database.")

        except Exception as e:
            print(f"Error initializing categories: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_categories())