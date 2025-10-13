"""
Initialize pharmaceutical categories in PostgreSQL database.
This script creates the pharmaceutical_categories table and populates it with 17 categories.
"""

import psycopg2
from psycopg2.extras import Json
import json
from datetime import datetime
import os
from typing import List, Dict, Any

# Database connection parameters from environment
DB_CONFIG = {
    'host': os.getenv('DATABASE_HOST', 'localhost'),
    'port': int(os.getenv('DATABASE_PORT', 5432)),
    'database': os.getenv('DATABASE_NAME', 'cognito-engine'),
    'user': os.getenv('DATABASE_USER', 'cognito'),
    'password': os.getenv('DATABASE_PASSWORD', 'cognito')
}

# The 17 pharmaceutical categories
CATEGORIES = [
    # Phase 1: Data Collection Categories (1-10)
    {
        "id": 1,
        "key": "market_overview",
        "name": "Market Overview",
        "phase": 1,
        "enabled": True,
        "prompt_template": "Analyze the global and regional market for {drug_name}. Include: 1) Current global market size in USD, 2) Year-over-year growth rates, 3) Regional market distribution (US, EU, Asia, Others), 4) Market penetration rates, 5) Pricing trends across regions, 6) Reimbursement status by country. Focus on data from the last 3 years. Prioritize data from paid pharmaceutical databases, government sources, and industry reports.",
        "weight": 1.0,
        "source_priorities": ["paid_apis", "government", "industry", "peer_reviewed"]
    },
    {
        "id": 2,
        "key": "competitive_landscape",
        "name": "Competitive Landscape",
        "phase": 1,
        "enabled": True,
        "prompt_template": "Provide comprehensive competitive analysis for {drug_name}. Include: 1) Direct competitors with market share percentages, 2) Indirect/alternative therapies, 3) Competitive advantages and disadvantages, 4) Head-to-head clinical trial comparisons, 5) Pricing comparison with competitors, 6) Pipeline competitors in development. Focus on therapeutic class competition and market positioning.",
        "weight": 1.0,
        "source_priorities": ["paid_apis", "industry", "peer_reviewed", "company"]
    },
    {
        "id": 3,
        "key": "regulatory_patent",
        "name": "Regulatory & Patent Status",
        "phase": 1,
        "enabled": False,
        "prompt_template": "Compile regulatory and patent information for {drug_name}. Include: 1) FDA approval date and indications, 2) EMA and other major regulatory approvals, 3) Patent expiration dates by region, 4) Data exclusivity periods, 5) Generic entry forecasts, 6) Regulatory exclusivities (orphan, pediatric), 7) Patent litigation status. Search FDA Orange Book, EMA databases, and patent registries.",
        "weight": 1.2,
        "source_priorities": ["government", "paid_apis", "peer_reviewed"]
    },
    {
        "id": 4,
        "key": "commercial_opportunities",
        "name": "Commercial Opportunities",
        "phase": 1,
        "enabled": False,
        "prompt_template": "Identify commercial opportunities for {drug_name}. Include: 1) Unmet medical needs in current indications, 2) Potential new indications or expansions, 3) Underserved patient populations, 4) Geographic expansion opportunities, 5) Partnership or licensing opportunities, 6) Value-based contracting potential. Focus on actionable commercial intelligence.",
        "weight": 0.9,
        "source_priorities": ["paid_apis", "industry", "peer_reviewed", "news"]
    },
    {
        "id": 5,
        "key": "current_formulations",
        "name": "Current Formulations",
        "phase": 1,
        "enabled": False,
        "prompt_template": "Detail all current formulations of {drug_name}. Include: 1) Available dosage forms (tablets, capsules, injectable, etc.), 2) Strengths and concentrations, 3) Excipients and inactive ingredients, 4) Storage requirements and stability, 5) Manufacturing sites, 6) Bioequivalence data if generic versions exist. Search drug labels and pharmaceutical databases.",
        "weight": 0.8,
        "source_priorities": ["government", "paid_apis", "company"]
    },
    {
        "id": 6,
        "key": "investigational_formulations",
        "name": "Investigational Formulations",
        "phase": 1,
        "enabled": False,
        "prompt_template": "Research investigational formulations and delivery systems for {drug_name}. Include: 1) New formulations in clinical trials, 2) Novel delivery systems (extended release, patches, etc.), 3) Fixed-dose combinations in development, 4) Pediatric or geriatric formulations, 5) Abuse-deterrent formulations if applicable, 6) Development timeline and status. Search ClinicalTrials.gov and company pipelines.",
        "weight": 0.7,
        "source_priorities": ["government", "company", "peer_reviewed", "paid_apis"]
    },
    {
        "id": 7,
        "key": "physicochemical_profile",
        "name": "Physicochemical Profile",
        "phase": 1,
        "enabled": False,
        "prompt_template": "Provide physicochemical properties of {drug_name}. Include: 1) Molecular weight and formula, 2) LogP and LogD values, 3) Solubility profile (aqueous and organic), 4) pKa values, 5) Melting point and polymorphs, 6) BCS classification, 7) Permeability data, 8) Chemical stability profile. Search pharmaceutical chemistry databases and drug bank resources.",
        "weight": 0.6,
        "source_priorities": ["paid_apis", "peer_reviewed", "government"]
    },
    {
        "id": 8,
        "key": "pharmacokinetics",
        "name": "Pharmacokinetics",
        "phase": 1,
        "enabled": False,
        "prompt_template": "Analyze pharmacokinetic profile of {drug_name}. Include: 1) Absorption (Tmax, bioavailability), 2) Distribution (Vd, protein binding), 3) Metabolism (CYP enzymes, metabolites), 4) Elimination (half-life, clearance routes), 5) Special populations (renal/hepatic impairment, elderly, pediatric), 6) Drug-drug interactions, 7) Food effects. Focus on clinically relevant PK parameters.",
        "weight": 0.9,
        "source_priorities": ["government", "peer_reviewed", "paid_apis"]
    },
    {
        "id": 9,
        "key": "dosage_forms",
        "name": "Dosage Forms",
        "phase": 1,
        "enabled": False,
        "prompt_template": "Compile dosage and administration information for {drug_name}. Include: 1) Approved dosing regimens by indication, 2) Dose adjustments for special populations, 3) Maximum daily doses, 4) Loading and maintenance doses, 5) Titration schedules, 6) Administration instructions and restrictions, 7) Dose conversion between formulations. Search prescribing information and clinical guidelines.",
        "weight": 0.8,
        "source_priorities": ["government", "peer_reviewed", "company"]
    },
    {
        "id": 10,
        "key": "clinical_trials_safety",
        "name": "Clinical Trials & Safety",
        "phase": 1,
        "enabled": False,
        "prompt_template": "Analyze clinical trials and safety profile for {drug_name}. Include: 1) Pivotal trial results with efficacy endpoints, 2) Ongoing clinical trials from ClinicalTrials.gov, 3) Common adverse events (>5% incidence), 4) Serious adverse events and black box warnings, 5) REMS requirements if applicable, 6) Post-marketing surveillance findings, 7) Real-world evidence studies. Search FDA FAERS, clinical trial registries, and medical literature.",
        "weight": 1.1,
        "source_priorities": ["government", "peer_reviewed", "paid_apis", "industry"]
    },
    # Phase 2: Decision Intelligence Categories (11-17)
    {
        "id": 11,
        "key": "parameter_scoring",
        "name": "Parameter-Based Scoring",
        "phase": 2,
        "enabled": False,
        "prompt_template": "Generate parameter-based scoring matrix for {drug_name} using Phase 1 data. Score each parameter on 0-100 scale: 1) Market size score based on TAM, 2) Growth potential score, 3) Competitive advantage score, 4) Regulatory complexity score, 5) Manufacturing feasibility score, 6) Patent strength score, 7) Clinical differentiation score. Provide scoring rationale and confidence intervals.",
        "weight": 1.0,
        "source_priorities": [],
        "requires_phase1": True
    },
    {
        "id": 12,
        "key": "weighted_assessment",
        "name": "Weighted Scoring Assessment",
        "phase": 2,
        "enabled": False,
        "prompt_template": "Create weighted assessment for {drug_name} combining all factors. Apply weights: Commercial factors (35%), Technical/Clinical factors (30%), Regulatory factors (20%), Competitive factors (15%). Calculate composite score and provide sensitivity analysis showing score changes with ±10% weight adjustments. Include risk-adjusted scoring.",
        "weight": 1.0,
        "source_priorities": [],
        "requires_phase1": True
    },
    {
        "id": 13,
        "key": "go_no_go",
        "name": "Go/No-Go Verdict",
        "phase": 2,
        "enabled": False,
        "prompt_template": "Generate Go/No-Go recommendation for {drug_name} based on comprehensive analysis. Consider: 1) Minimum viable market size threshold, 2) Regulatory approval probability, 3) Competitive sustainability, 4) Technical feasibility, 5) Financial projections vs investment required. Provide clear verdict with confidence score (0-100%) and top 3 supporting reasons and top 3 risks.",
        "weight": 1.2,
        "source_priorities": [],
        "requires_phase1": True
    },
    {
        "id": 14,
        "key": "executive_summary",
        "name": "Executive Summary",
        "phase": 2,
        "enabled": False,
        "prompt_template": "Synthesize executive summary for {drug_name} suitable for C-suite presentation. Include: 1) One-paragraph investment thesis, 2) Key value drivers (3-5 bullets), 3) Critical risks and mitigation strategies, 4) Financial highlights and projections, 5) Recommended next steps with timeline, 6) Decision urgency factors. Maximum 500 words, focus on actionable insights.",
        "weight": 1.1,
        "source_priorities": [],
        "requires_phase1": True
    },
    {
        "id": 15,
        "key": "risk_assessment",
        "name": "Risk Assessment",
        "phase": 2,
        "enabled": False,
        "prompt_template": "Conduct comprehensive risk assessment for {drug_name}. Categorize risks as: 1) Regulatory risks (approval delays, label restrictions), 2) Commercial risks (market access, competition), 3) Technical risks (manufacturing, supply chain), 4) Financial risks (development costs, pricing pressure), 5) Strategic risks (IP challenges, partnership dependencies). Rate each risk as High/Medium/Low with mitigation strategies.",
        "weight": 1.0,
        "source_priorities": [],
        "requires_phase1": True
    },
    {
        "id": 16,
        "key": "strategic_recommendations",
        "name": "Strategic Recommendations",
        "phase": 2,
        "enabled": False,
        "prompt_template": "Provide strategic recommendations for {drug_name}. Include: 1) Optimal development strategy (fast-track, standard, lifecycle management), 2) Partnership recommendations (licensing, co-development, acquisition), 3) Market entry strategy by region, 4) Pricing and market access strategy, 5) Portfolio fit and prioritization, 6) Resource allocation recommendations. Focus on actionable 12-24 month roadmap.",
        "weight": 0.9,
        "source_priorities": [],
        "requires_phase1": True
    },
    {
        "id": 17,
        "key": "investment_analysis",
        "name": "Investment Analysis",
        "phase": 2,
        "enabled": False,
        "prompt_template": "Perform investment analysis for {drug_name}. Calculate: 1) Net Present Value (NPV) with assumptions, 2) Internal Rate of Return (IRR), 3) Peak sales projections with timeline, 4) Break-even analysis, 5) Return on Investment (ROI) scenarios, 6) Comparable deals analysis, 7) Valuation range for licensing/M&A. Include bull, base, and bear case scenarios with probability weighting.",
        "weight": 1.0,
        "source_priorities": [],
        "requires_phase1": True
    }
]


def init_postgres_categories():
    """Initialize pharmaceutical categories in PostgreSQL database."""

    conn = None
    cursor = None

    try:
        # Connect to the existing database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print(f"Connected to PostgreSQL database: {DB_CONFIG['database']}")

        # Create pharmaceutical_categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pharmaceutical_categories (
                id INTEGER PRIMARY KEY,
                key VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                phase INTEGER NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                prompt_template TEXT NOT NULL,
                weight DECIMAL(3,2) DEFAULT 1.0,
                source_priorities JSONB,
                requires_phase1 BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index on key for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pharmaceutical_categories_key
            ON pharmaceutical_categories(key)
        """)

        # Create index on phase and enabled for filtering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pharmaceutical_categories_phase_enabled
            ON pharmaceutical_categories(phase, enabled)
        """)

        # Check if categories already exist
        cursor.execute("SELECT COUNT(*) FROM pharmaceutical_categories")
        count = cursor.fetchone()[0]

        if count > 0:
            print(f"Categories already exist in database ({count} found). Clearing and reinitializing...")
            cursor.execute("DELETE FROM pharmaceutical_categories")

        # Insert all categories
        for cat in CATEGORIES:
            cursor.execute("""
                INSERT INTO pharmaceutical_categories
                (id, key, name, phase, enabled, prompt_template, weight, source_priorities, requires_phase1)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                cat["id"],
                cat["key"],
                cat["name"],
                cat["phase"],
                cat["enabled"],
                cat["prompt_template"],
                cat["weight"],
                Json(cat["source_priorities"]) if cat["source_priorities"] else None,
                cat.get("requires_phase1", False)
            ))

        conn.commit()
        print(f"Successfully initialized {len(CATEGORIES)} pharmaceutical categories in PostgreSQL database.")

        # Verify insertion
        cursor.execute("""
            SELECT id, name, phase, enabled
            FROM pharmaceutical_categories
            ORDER BY id
        """)
        rows = cursor.fetchall()

        print("\nCategories in database:")
        for row in rows:
            print(f"  ID: {row[0]:2d} | Phase: {row[2]} | Enabled: {'Yes' if row[3] else 'No'} | {row[1]}")

        # Create update trigger for updated_at
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql'
        """)

        cursor.execute("""
            DROP TRIGGER IF EXISTS update_pharmaceutical_categories_updated_at
            ON pharmaceutical_categories
        """)

        cursor.execute("""
            CREATE TRIGGER update_pharmaceutical_categories_updated_at
            BEFORE UPDATE ON pharmaceutical_categories
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
        """)

        conn.commit()
        print("\nCreated update trigger for updated_at column.")

    except psycopg2.Error as e:
        print(f"PostgreSQL error: {e}")
        if conn:
            conn.rollback()
        raise

    except Exception as e:
        print(f"Error initializing categories: {e}")
        if conn:
            conn.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("\nDatabase connection closed.")


if __name__ == "__main__":
    init_postgres_categories()