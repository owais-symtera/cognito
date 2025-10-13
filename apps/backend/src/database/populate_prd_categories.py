"""
Populate the pharmaceutical_categories table with the 17 PRD categories.
This will update the existing cognito-engine database.
"""

import psycopg2
from psycopg2.extras import Json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../../../.env')

# Database connection from environment
DB_CONFIG = {
    'host': os.getenv('DATABASE_HOST', 'localhost'),
    'port': int(os.getenv('DATABASE_PORT', 5432)),
    'database': os.getenv('DATABASE_NAME', 'cognito-engine'),
    'user': os.getenv('DATABASE_USER', 'cognito'),
    'password': os.getenv('DATABASE_PASSWORD', 'cognito')
}

# The 17 PRD categories
PRD_CATEGORIES = [
    # Phase 1: Data Collection (10 categories)
    {
        'name': 'Market Overview',
        'description': 'Analyze the global and regional market for {drug_name}. Include: 1) Current global market size in USD, 2) Year-over-year growth rates, 3) Regional market distribution (US, EU, Asia, Others), 4) Market penetration rates, 5) Pricing trends across regions, 6) Reimbursement status by country.',
        'phase': 1,
        'is_active': True,
        'display_order': 1
    },
    {
        'name': 'Competitive Landscape',
        'description': 'Provide comprehensive competitive analysis for {drug_name}. Include: 1) Direct competitors with market share percentages, 2) Indirect/alternative therapies, 3) Competitive advantages and disadvantages, 4) Head-to-head clinical trial comparisons, 5) Pricing comparison with competitors, 6) Pipeline competitors in development.',
        'phase': 1,
        'is_active': True,
        'display_order': 2
    },
    {
        'name': 'Regulatory & Patent Status',
        'description': 'Compile regulatory and patent information for {drug_name}. Include: 1) FDA approval date and indications, 2) EMA and other major regulatory approvals, 3) Patent expiration dates by region, 4) Data exclusivity periods, 5) Generic entry forecasts, 6) Regulatory exclusivities (orphan, pediatric), 7) Patent litigation status.',
        'phase': 1,
        'is_active': False,
        'display_order': 3
    },
    {
        'name': 'Commercial Opportunities',
        'description': 'Identify commercial opportunities for {drug_name}. Include: 1) Unmet medical needs in current indications, 2) Potential new indications or expansions, 3) Underserved patient populations, 4) Geographic expansion opportunities, 5) Partnership or licensing opportunities, 6) Value-based contracting potential.',
        'phase': 1,
        'is_active': False,
        'display_order': 4
    },
    {
        'name': 'Current Formulations',
        'description': 'Detail all current formulations of {drug_name}. Include: 1) Available dosage forms (tablets, capsules, injectable, etc.), 2) Strengths and concentrations, 3) Excipients and inactive ingredients, 4) Storage requirements and stability, 5) Manufacturing sites, 6) Bioequivalence data if generic versions exist.',
        'phase': 1,
        'is_active': False,
        'display_order': 5
    },
    {
        'name': 'Investigational Formulations',
        'description': 'Research investigational formulations and delivery systems for {drug_name}. Include: 1) New formulations in clinical trials, 2) Novel delivery systems (extended release, patches, etc.), 3) Fixed-dose combinations in development, 4) Pediatric or geriatric formulations, 5) Abuse-deterrent formulations if applicable, 6) Development timeline and status.',
        'phase': 1,
        'is_active': False,
        'display_order': 6
    },
    {
        'name': 'Physicochemical Profile',
        'description': 'Provide physicochemical properties of {drug_name}. Include: 1) Molecular weight and formula, 2) LogP and LogD values, 3) Solubility profile (aqueous and organic), 4) pKa values, 5) Melting point and polymorphs, 6) BCS classification, 7) Permeability data, 8) Chemical stability profile.',
        'phase': 1,
        'is_active': False,
        'display_order': 7
    },
    {
        'name': 'Pharmacokinetics',
        'description': 'Analyze pharmacokinetic profile of {drug_name}. Include: 1) Absorption (Tmax, bioavailability), 2) Distribution (Vd, protein binding), 3) Metabolism (CYP enzymes, metabolites), 4) Elimination (half-life, clearance routes), 5) Special populations (renal/hepatic impairment, elderly, pediatric), 6) Drug-drug interactions, 7) Food effects.',
        'phase': 1,
        'is_active': False,
        'display_order': 8
    },
    {
        'name': 'Dosage Forms',
        'description': 'Compile dosage and administration information for {drug_name}. Include: 1) Approved dosing regimens by indication, 2) Dose adjustments for special populations, 3) Maximum daily doses, 4) Loading and maintenance doses, 5) Titration schedules, 6) Administration instructions and restrictions, 7) Dose conversion between formulations.',
        'phase': 1,
        'is_active': False,
        'display_order': 9
    },
    {
        'name': 'Clinical Trials & Safety',
        'description': 'Analyze clinical trials and safety profile for {drug_name}. Include: 1) Pivotal trial results with efficacy endpoints, 2) Ongoing clinical trials from ClinicalTrials.gov, 3) Common adverse events (>5% incidence), 4) Serious adverse events and black box warnings, 5) REMS requirements if applicable, 6) Post-marketing surveillance findings, 7) Real-world evidence studies.',
        'phase': 1,
        'is_active': False,
        'display_order': 10
    },
    # Phase 2: Decision Intelligence (7 categories)
    {
        'name': 'Parameter-Based Scoring',
        'description': 'Generate parameter-based scoring matrix for {drug_name} using Phase 1 data. Score each parameter on 0-100 scale: 1) Market size score based on TAM, 2) Growth potential score, 3) Competitive advantage score, 4) Regulatory complexity score, 5) Manufacturing feasibility score, 6) Patent strength score, 7) Clinical differentiation score.',
        'phase': 2,
        'is_active': False,
        'display_order': 11
    },
    {
        'name': 'Weighted Scoring Assessment',
        'description': 'Create weighted assessment for {drug_name} combining all factors. Apply weights: Commercial factors (35%), Technical/Clinical factors (30%), Regulatory factors (20%), Competitive factors (15%). Calculate composite score and provide sensitivity analysis showing score changes with ±10% weight adjustments.',
        'phase': 2,
        'is_active': False,
        'display_order': 12
    },
    {
        'name': 'Go/No-Go Verdict',
        'description': 'Generate Go/No-Go recommendation for {drug_name} based on comprehensive analysis. Consider: 1) Minimum viable market size threshold, 2) Regulatory approval probability, 3) Competitive sustainability, 4) Technical feasibility, 5) Financial projections vs investment required. Provide clear verdict with confidence score (0-100%) and top 3 supporting reasons and top 3 risks.',
        'phase': 2,
        'is_active': False,
        'display_order': 13
    },
    {
        'name': 'Executive Summary',
        'description': 'Synthesize executive summary for {drug_name} suitable for C-suite presentation. Include: 1) One-paragraph investment thesis, 2) Key value drivers (3-5 bullets), 3) Critical risks and mitigation strategies, 4) Financial highlights and projections, 5) Recommended next steps with timeline, 6) Decision urgency factors. Maximum 500 words.',
        'phase': 2,
        'is_active': False,
        'display_order': 14
    },
    {
        'name': 'Risk Assessment',
        'description': 'Conduct comprehensive risk assessment for {drug_name}. Categorize risks as: 1) Regulatory risks (approval delays, label restrictions), 2) Commercial risks (market access, competition), 3) Technical risks (manufacturing, supply chain), 4) Financial risks (development costs, pricing pressure), 5) Strategic risks (IP challenges, partnership dependencies).',
        'phase': 2,
        'is_active': False,
        'display_order': 15
    },
    {
        'name': 'Strategic Recommendations',
        'description': 'Provide strategic recommendations for {drug_name}. Include: 1) Optimal development strategy (fast-track, standard, lifecycle management), 2) Partnership recommendations (licensing, co-development, acquisition), 3) Market entry strategy by region, 4) Pricing and market access strategy, 5) Portfolio fit and prioritization, 6) Resource allocation recommendations.',
        'phase': 2,
        'is_active': False,
        'display_order': 16
    },
    {
        'name': 'Investment Analysis',
        'description': 'Perform investment analysis for {drug_name}. Calculate: 1) Net Present Value (NPV) with assumptions, 2) Internal Rate of Return (IRR), 3) Peak sales projections with timeline, 4) Break-even analysis, 5) Return on Investment (ROI) scenarios, 6) Comparable deals analysis, 7) Valuation range for licensing/M&A.',
        'phase': 2,
        'is_active': False,
        'display_order': 17
    }
]


def populate_prd_categories():
    """Clear existing categories and populate with PRD categories."""
    conn = None
    cursor = None

    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print(f"Connected to database: {DB_CONFIG['database']}")

        # First, clear dependencies
        cursor.execute("DELETE FROM category_dependencies")
        print("Cleared category dependencies")

        # Clear existing categories
        cursor.execute("DELETE FROM pharmaceutical_categories")
        print(f"Cleared existing categories")

        # Insert PRD categories with all required fields
        for i, cat in enumerate(PRD_CATEGORIES, 1):
            # Set source priorities based on category phase
            source_priorities = []
            if cat['phase'] == 1:
                if 'market' in cat['name'].lower() or 'competitive' in cat['name'].lower():
                    source_priorities = ['paid_apis', 'government', 'industry', 'peer_reviewed']
                elif 'regulatory' in cat['name'].lower() or 'patent' in cat['name'].lower():
                    source_priorities = ['government', 'paid_apis', 'peer_reviewed']
                else:
                    source_priorities = ['paid_apis', 'peer_reviewed', 'government']

            cursor.execute("""
                INSERT INTO pharmaceutical_categories
                (id, name, description, display_order, is_active, search_parameters,
                 processing_rules, prompt_templates, verification_criteria,
                 conflict_resolution_strategy, created_at, updated_at, phase)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s)
            """, (
                i,
                cat['name'],
                cat['description'],
                cat['display_order'],
                cat['is_active'],
                Json({'source_priorities': source_priorities, 'enabled': cat['is_active']}),  # search_parameters
                Json({'weight': 1.0}),  # processing_rules
                Json({'default': cat['description']}),  # prompt_templates
                Json({'min_confidence': 0.7}),  # verification_criteria
                'highest_confidence',  # conflict_resolution_strategy
                cat['phase']
            ))

        conn.commit()
        print(f"Successfully populated {len(PRD_CATEGORIES)} PRD categories")

        # Verify
        cursor.execute("SELECT COUNT(*), COUNT(CASE WHEN is_active THEN 1 END) FROM pharmaceutical_categories")
        total, active = cursor.fetchone()
        print(f"Total categories: {total}, Active: {active}")

    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    populate_prd_categories()