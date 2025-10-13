"""Populate default 17 pharmaceutical categories

Revision ID: 003
Revises: 002
Create Date: 2024-01-26 16:30:00

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Insert default 17 pharmaceutical categories with configurations."""

    # Create a temporary table reference for bulk insert
    pharmaceutical_categories_table = sa.table('pharmaceutical_categories',
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('display_order', sa.Integer),
        sa.column('phase', sa.Integer),
        sa.column('is_active', sa.Boolean),
        sa.column('search_parameters', sa.JSON),
        sa.column('processing_rules', sa.JSON),
        sa.column('prompt_templates', sa.JSON),
        sa.column('verification_criteria', sa.JSON),
        sa.column('conflict_resolution_strategy', sa.String)
    )

    # Insert all 17 categories
    op.bulk_insert(
        pharmaceutical_categories_table,
        [
            {
                'name': 'Clinical Trials & Studies',
                'description': 'Phase I-IV clinical trials, efficacy data, safety profiles, and study outcomes',
                'display_order': 1,
                'phase': 1,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['clinical trial', 'phase', 'efficacy', 'safety', 'randomized controlled trial', 'RCT'],
                    'min_relevance': 0.7,
                    'max_results': 50
                },
                'processing_rules': {
                    'min_confidence': 0.8,
                    'require_peer_review': True,
                    'exclude_preprints': False
                },
                'prompt_templates': {
                    'search': 'Find clinical trials and studies for the pharmaceutical drug {drug_name}. Focus on trial phases, efficacy results, and safety profiles.',
                    'analysis': 'Analyze clinical trial data for {drug_name} focusing on primary endpoints, statistical significance, and adverse events.'
                },
                'verification_criteria': {
                    'required_fields': ['phase', 'status', 'enrollment'],
                    'min_credibility': 0.75
                },
                'conflict_resolution_strategy': 'confidence_weighted'
            },
            {
                'name': 'Drug Interactions & Contraindications',
                'description': 'Drug-drug interactions, contraindications, warnings, and precautions',
                'display_order': 2,
                'phase': 1,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['drug interaction', 'contraindication', 'warning', 'precaution', 'CYP450'],
                    'min_relevance': 0.8,
                    'max_results': 40
                },
                'processing_rules': {
                    'min_confidence': 0.9,
                    'require_clinical_validation': True
                },
                'prompt_templates': {
                    'search': 'Find drug interactions and contraindications for {drug_name}. Include CYP450 interactions, black box warnings, and absolute contraindications.',
                    'analysis': 'Analyze drug interaction severity and mechanisms for {drug_name}. Categorize by severity level.'
                },
                'verification_criteria': {
                    'required_fields': ['severity', 'mechanism', 'clinical_significance'],
                    'min_credibility': 0.85
                },
                'conflict_resolution_strategy': 'most_conservative'
            },
            {
                'name': 'Side Effects & Adverse Events',
                'description': 'Adverse events, side effect profiles, safety signals, and risk assessments',
                'display_order': 3,
                'phase': 1,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['adverse event', 'side effect', 'safety', 'toxicity', 'ADR'],
                    'min_relevance': 0.75,
                    'max_results': 50
                },
                'processing_rules': {
                    'min_confidence': 0.8,
                    'include_post_market': True
                },
                'prompt_templates': {
                    'search': 'Find side effects and adverse events for {drug_name}. Include frequency, severity, and reversibility information.',
                    'analysis': 'Analyze adverse event profile for {drug_name} categorized by system organ class and frequency.'
                },
                'verification_criteria': {
                    'required_fields': ['frequency', 'severity', 'system_organ_class'],
                    'min_credibility': 0.8
                },
                'conflict_resolution_strategy': 'confidence_weighted'
            },
            {
                'name': 'Pharmacokinetics & Pharmacodynamics',
                'description': 'Absorption, distribution, metabolism, excretion (ADME), mechanism of action',
                'display_order': 4,
                'phase': 1,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['pharmacokinetics', 'pharmacodynamics', 'ADME', 'metabolism', 'half-life', 'bioavailability'],
                    'min_relevance': 0.7,
                    'max_results': 30
                },
                'processing_rules': {
                    'min_confidence': 0.75,
                    'require_quantitative_data': True
                },
                'prompt_templates': {
                    'search': 'Find pharmacokinetic and pharmacodynamic properties of {drug_name}. Include ADME parameters, half-life, and mechanism of action.',
                    'analysis': 'Analyze PK/PD parameters for {drug_name} including bioavailability, clearance, and volume of distribution.'
                },
                'verification_criteria': {
                    'required_fields': ['half_life', 'clearance', 'mechanism'],
                    'min_credibility': 0.7
                },
                'conflict_resolution_strategy': 'average_values'
            },
            {
                'name': 'Regulatory Status & Approvals',
                'description': 'FDA approvals, regulatory submissions, compliance status, and guidelines',
                'display_order': 5,
                'phase': 1,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['FDA approval', 'regulatory', 'NDA', 'BLA', 'EMA', 'authorization'],
                    'min_relevance': 0.85,
                    'max_results': 30
                },
                'processing_rules': {
                    'min_confidence': 0.9,
                    'require_official_sources': True
                },
                'prompt_templates': {
                    'search': 'Find regulatory status and approvals for {drug_name}. Include FDA, EMA, and other regulatory body decisions.',
                    'analysis': 'Analyze regulatory history for {drug_name} including approval dates, indications, and restrictions.'
                },
                'verification_criteria': {
                    'required_fields': ['approval_date', 'indication', 'regulatory_body'],
                    'min_credibility': 0.9
                },
                'conflict_resolution_strategy': 'most_recent'
            },
            {
                'name': 'Patent & Intellectual Property',
                'description': 'Patent landscape, exclusivity periods, generic competition timeline',
                'display_order': 6,
                'phase': 2,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['patent', 'exclusivity', 'generic', 'biosimilar', 'intellectual property'],
                    'min_relevance': 0.7,
                    'max_results': 25
                },
                'processing_rules': {
                    'min_confidence': 0.75,
                    'include_legal_databases': True
                },
                'prompt_templates': {
                    'search': 'Find patent and exclusivity information for {drug_name}. Include expiry dates and generic competition timeline.',
                    'analysis': 'Analyze patent landscape for {drug_name} including Orange Book listings and paragraph IV challenges.'
                },
                'verification_criteria': {
                    'required_fields': ['patent_number', 'expiry_date', 'exclusivity_type'],
                    'min_credibility': 0.75
                },
                'conflict_resolution_strategy': 'most_conservative'
            },
            {
                'name': 'Manufacturing & Quality Control',
                'description': 'Manufacturing processes, quality standards, GMP compliance, supply chain',
                'display_order': 7,
                'phase': 2,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['manufacturing', 'GMP', 'quality control', 'formulation', 'supply chain'],
                    'min_relevance': 0.65,
                    'max_results': 20
                },
                'processing_rules': {
                    'min_confidence': 0.7,
                    'include_technical_specs': True
                },
                'prompt_templates': {
                    'search': 'Find manufacturing and quality control information for {drug_name}. Include formulation, stability, and GMP compliance.',
                    'analysis': 'Analyze manufacturing requirements and quality standards for {drug_name}.'
                },
                'verification_criteria': {
                    'required_fields': ['manufacturer', 'formulation', 'stability'],
                    'min_credibility': 0.7
                },
                'conflict_resolution_strategy': 'confidence_weighted'
            },
            {
                'name': 'Pricing & Market Access',
                'description': 'Pricing data, reimbursement status, market access, formulary placement',
                'display_order': 8,
                'phase': 2,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['price', 'cost', 'reimbursement', 'formulary', 'market access', 'WAC', 'ASP'],
                    'min_relevance': 0.7,
                    'max_results': 30
                },
                'processing_rules': {
                    'min_confidence': 0.75,
                    'include_regional_variations': True
                },
                'prompt_templates': {
                    'search': 'Find pricing and market access information for {drug_name}. Include WAC, ASP, and reimbursement status.',
                    'analysis': 'Analyze pricing strategy and market access for {drug_name} across different payers.'
                },
                'verification_criteria': {
                    'required_fields': ['price_range', 'coverage_type', 'tier_placement'],
                    'min_credibility': 0.7
                },
                'conflict_resolution_strategy': 'range_based'
            },
            {
                'name': 'Competitive Analysis',
                'description': 'Competitor products, market share, positioning, differentiation factors',
                'display_order': 9,
                'phase': 2,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['competitor', 'market share', 'comparison', 'alternative', 'therapeutic class'],
                    'min_relevance': 0.65,
                    'max_results': 35
                },
                'processing_rules': {
                    'min_confidence': 0.7,
                    'include_pipeline_products': True
                },
                'prompt_templates': {
                    'search': 'Find competitor analysis for {drug_name}. Include market share, differentiation, and therapeutic alternatives.',
                    'analysis': 'Analyze competitive landscape for {drug_name} including head-to-head comparisons.'
                },
                'verification_criteria': {
                    'required_fields': ['competitors', 'market_position', 'differentiation'],
                    'min_credibility': 0.65
                },
                'conflict_resolution_strategy': 'confidence_weighted'
            },
            {
                'name': 'Real-World Evidence',
                'description': 'Real-world studies, outcomes research, effectiveness in practice',
                'display_order': 10,
                'phase': 1,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['real-world evidence', 'RWE', 'effectiveness', 'outcomes research', 'registry'],
                    'min_relevance': 0.7,
                    'max_results': 40
                },
                'processing_rules': {
                    'min_confidence': 0.75,
                    'include_registries': True
                },
                'prompt_templates': {
                    'search': 'Find real-world evidence for {drug_name}. Include registry data, observational studies, and effectiveness outcomes.',
                    'analysis': 'Analyze real-world effectiveness and outcomes for {drug_name} in clinical practice.'
                },
                'verification_criteria': {
                    'required_fields': ['study_type', 'outcomes', 'population_size'],
                    'min_credibility': 0.7
                },
                'conflict_resolution_strategy': 'weighted_by_sample_size'
            },
            {
                'name': 'Safety Surveillance',
                'description': 'Post-market safety monitoring, signal detection, REMS programs',
                'display_order': 11,
                'phase': 1,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['safety surveillance', 'pharmacovigilance', 'signal detection', 'REMS', 'FAERS'],
                    'min_relevance': 0.8,
                    'max_results': 35
                },
                'processing_rules': {
                    'min_confidence': 0.85,
                    'include_faers_data': True
                },
                'prompt_templates': {
                    'search': 'Find safety surveillance data for {drug_name}. Include FAERS reports, safety signals, and REMS requirements.',
                    'analysis': 'Analyze post-market safety signals and surveillance findings for {drug_name}.'
                },
                'verification_criteria': {
                    'required_fields': ['signal_type', 'action_taken', 'reporting_frequency'],
                    'min_credibility': 0.8
                },
                'conflict_resolution_strategy': 'most_conservative'
            },
            {
                'name': 'Therapeutic Guidelines',
                'description': 'Treatment guidelines, recommendations, protocols, standard of care',
                'display_order': 12,
                'phase': 2,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['guidelines', 'recommendations', 'protocol', 'standard of care', 'consensus'],
                    'min_relevance': 0.75,
                    'max_results': 30
                },
                'processing_rules': {
                    'min_confidence': 0.8,
                    'prioritize_recent': True
                },
                'prompt_templates': {
                    'search': 'Find therapeutic guidelines mentioning {drug_name}. Include professional society recommendations and treatment protocols.',
                    'analysis': 'Analyze guideline recommendations for {drug_name} including line of therapy and patient selection.'
                },
                'verification_criteria': {
                    'required_fields': ['guideline_source', 'recommendation_strength', 'publication_date'],
                    'min_credibility': 0.8
                },
                'conflict_resolution_strategy': 'most_recent'
            },
            {
                'name': 'Research Pipeline',
                'description': 'Pipeline studies, development programs, future indications, ongoing research',
                'display_order': 13,
                'phase': 2,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['pipeline', 'development', 'future indication', 'ongoing trial', 'research'],
                    'min_relevance': 0.65,
                    'max_results': 30
                },
                'processing_rules': {
                    'min_confidence': 0.7,
                    'include_early_stage': True
                },
                'prompt_templates': {
                    'search': 'Find pipeline and development information for {drug_name}. Include new indications and ongoing research.',
                    'analysis': 'Analyze research pipeline and future development plans for {drug_name}.'
                },
                'verification_criteria': {
                    'required_fields': ['development_stage', 'indication', 'timeline'],
                    'min_credibility': 0.65
                },
                'conflict_resolution_strategy': 'confidence_weighted'
            },
            {
                'name': 'Biomarker Information',
                'description': 'Biomarkers, companion diagnostics, personalized medicine applications',
                'display_order': 14,
                'phase': 2,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['biomarker', 'companion diagnostic', 'personalized medicine', 'precision medicine', 'CDx'],
                    'min_relevance': 0.7,
                    'max_results': 25
                },
                'processing_rules': {
                    'min_confidence': 0.75,
                    'require_clinical_validation': True
                },
                'prompt_templates': {
                    'search': 'Find biomarker and companion diagnostic information for {drug_name}. Include patient selection criteria.',
                    'analysis': 'Analyze biomarker requirements and companion diagnostics for {drug_name}.'
                },
                'verification_criteria': {
                    'required_fields': ['biomarker_type', 'clinical_utility', 'test_availability'],
                    'min_credibility': 0.75
                },
                'conflict_resolution_strategy': 'confidence_weighted'
            },
            {
                'name': 'Patient Demographics',
                'description': 'Patient populations, demographics, usage patterns, treatment persistence',
                'display_order': 15,
                'phase': 2,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['patient demographics', 'population', 'usage pattern', 'adherence', 'persistence'],
                    'min_relevance': 0.65,
                    'max_results': 30
                },
                'processing_rules': {
                    'min_confidence': 0.7,
                    'include_epidemiology': True
                },
                'prompt_templates': {
                    'search': 'Find patient demographic and usage information for {drug_name}. Include treatment patterns and adherence data.',
                    'analysis': 'Analyze patient population characteristics and treatment patterns for {drug_name}.'
                },
                'verification_criteria': {
                    'required_fields': ['age_range', 'gender_distribution', 'treatment_duration'],
                    'min_credibility': 0.65
                },
                'conflict_resolution_strategy': 'weighted_average'
            },
            {
                'name': 'Healthcare Economics',
                'description': 'Health economics, cost-effectiveness, budget impact, HEOR studies',
                'display_order': 16,
                'phase': 2,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['health economics', 'cost-effectiveness', 'HEOR', 'budget impact', 'QALY', 'ICER'],
                    'min_relevance': 0.7,
                    'max_results': 25
                },
                'processing_rules': {
                    'min_confidence': 0.75,
                    'include_models': True
                },
                'prompt_templates': {
                    'search': 'Find health economics and outcomes research for {drug_name}. Include cost-effectiveness and budget impact.',
                    'analysis': 'Analyze economic value and cost-effectiveness of {drug_name} including ICER and budget impact.'
                },
                'verification_criteria': {
                    'required_fields': ['cost_effectiveness', 'economic_model', 'perspective'],
                    'min_credibility': 0.7
                },
                'conflict_resolution_strategy': 'range_based'
            },
            {
                'name': 'Post-Market Surveillance',
                'description': 'Post-market studies, phase IV trials, long-term safety and effectiveness',
                'display_order': 17,
                'phase': 2,
                'is_active': True,
                'search_parameters': {
                    'keywords': ['post-market', 'phase IV', 'long-term safety', 'surveillance study', 'PASS'],
                    'min_relevance': 0.75,
                    'max_results': 35
                },
                'processing_rules': {
                    'min_confidence': 0.8,
                    'include_regulatory_commitments': True
                },
                'prompt_templates': {
                    'search': 'Find post-market surveillance studies for {drug_name}. Include Phase IV trials and long-term safety data.',
                    'analysis': 'Analyze post-market surveillance findings and long-term outcomes for {drug_name}.'
                },
                'verification_criteria': {
                    'required_fields': ['study_duration', 'safety_outcomes', 'effectiveness_measures'],
                    'min_credibility': 0.75
                },
                'conflict_resolution_strategy': 'confidence_weighted'
            }
        ]
    )

    # Insert some basic category dependencies
    category_dependencies_table = sa.table('category_dependencies',
        sa.column('dependent_category_id', sa.Integer),
        sa.column('required_category_id', sa.Integer),
        sa.column('description', sa.Text)
    )

    # Note: These dependency IDs assume the categories are inserted in order starting from ID 1
    op.bulk_insert(
        category_dependencies_table,
        [
            {
                'dependent_category_id': 11,  # Safety Surveillance
                'required_category_id': 3,    # Side Effects & Adverse Events
                'description': 'Safety surveillance requires adverse event data as baseline'
            },
            {
                'dependent_category_id': 17,  # Post-Market Surveillance
                'required_category_id': 1,    # Clinical Trials & Studies
                'description': 'Post-market surveillance builds upon clinical trial safety data'
            },
            {
                'dependent_category_id': 10,  # Real-World Evidence
                'required_category_id': 1,    # Clinical Trials & Studies
                'description': 'Real-world evidence complements clinical trial data'
            },
            {
                'dependent_category_id': 12,  # Therapeutic Guidelines
                'required_category_id': 1,    # Clinical Trials & Studies
                'description': 'Guidelines are based on clinical trial evidence'
            },
            {
                'dependent_category_id': 14,  # Biomarker Information
                'required_category_id': 4,    # Pharmacokinetics & Pharmacodynamics
                'description': 'Biomarker selection relates to drug mechanism and PK/PD'
            }
        ]
    )


def downgrade() -> None:
    """Remove default pharmaceutical categories and dependencies."""

    # Delete all category dependencies
    op.execute("DELETE FROM category_dependencies")

    # Delete all pharmaceutical categories
    op.execute("DELETE FROM pharmaceutical_categories")