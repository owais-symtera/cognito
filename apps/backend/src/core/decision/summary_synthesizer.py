"""
Story 5.6: Executive Summary Synthesis
Natural language synthesis of decision intelligence outputs
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json

from ...utils.database import DatabaseClient
from ...utils.tracking import SourceTracker
from ...utils.logging import get_logger

logger = get_logger(__name__)


class SummaryStyle(Enum):
    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    CLINICAL = "clinical"
    REGULATORY = "regulatory"
    INVESTOR = "investor"


class SummaryLength(Enum):
    BRIEF = "brief"  # 1-2 paragraphs
    STANDARD = "standard"  # 3-5 paragraphs
    DETAILED = "detailed"  # Full page
    COMPREHENSIVE = "comprehensive"  # Multi-page


@dataclass
class SummarySection:
    """Individual section of executive summary"""
    title: str
    content: str
    priority: int
    data_points: List[Dict[str, Any]]
    confidence: float


@dataclass
class ExecutiveSummary:
    """Complete executive summary"""
    summary_id: str
    style: SummaryStyle
    length: SummaryLength
    headline: str
    executive_brief: str
    sections: List[SummarySection]
    key_findings: List[str]
    critical_risks: List[str]
    next_steps: List[str]
    appendices: Dict[str, Any]
    metadata: Dict[str, Any]
    generated_at: datetime


class ExecutiveSummarySynthesizer:
    """Database-driven executive summary synthesis engine"""

    def __init__(self, db_client: DatabaseClient, source_tracker: SourceTracker):
        self.db_client = db_client
        self.source_tracker = source_tracker

    async def initialize(self):
        """Initialize summary synthesizer"""
        await self._ensure_tables_exist()
        logger.info("Executive summary synthesizer initialized")

    async def _ensure_tables_exist(self):
        """Ensure summary-related tables exist"""
        await self.db_client.execute_many([
            """
            CREATE TABLE IF NOT EXISTS summary_templates (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                style VARCHAR(50) NOT NULL,
                length VARCHAR(50) NOT NULL,
                structure JSONB NOT NULL,
                section_templates JSONB,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS summary_sections (
                id SERIAL PRIMARY KEY,
                template_id INTEGER REFERENCES summary_templates(id),
                section_name VARCHAR(100) NOT NULL,
                section_order INTEGER NOT NULL,
                required BOOLEAN DEFAULT TRUE,
                min_confidence DECIMAL(5,2) DEFAULT 60.0,
                data_requirements JSONB,
                prompt_template TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS summary_history (
                id SERIAL PRIMARY KEY,
                summary_id VARCHAR(100) NOT NULL UNIQUE,
                request_id VARCHAR(100) NOT NULL,
                style VARCHAR(50) NOT NULL,
                length VARCHAR(50) NOT NULL,
                headline TEXT NOT NULL,
                executive_brief TEXT NOT NULL,
                sections JSONB NOT NULL,
                key_findings TEXT[],
                critical_risks TEXT[],
                next_steps TEXT[],
                appendices JSONB,
                metadata JSONB,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS summary_phrases (
                id SERIAL PRIMARY KEY,
                category VARCHAR(100) NOT NULL,
                context VARCHAR(100) NOT NULL,
                phrase_type VARCHAR(50) NOT NULL,
                phrase TEXT NOT NULL,
                min_score DECIMAL(5,2),
                max_score DECIMAL(5,2),
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS summary_analytics (
                id SERIAL PRIMARY KEY,
                summary_id VARCHAR(100) REFERENCES summary_history(summary_id),
                word_count INTEGER,
                readability_score DECIMAL(5,2),
                technical_depth DECIMAL(5,2),
                sections_included INTEGER,
                generation_time_ms INTEGER,
                llm_tokens_used INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_summary_history_request
            ON summary_history(request_id, generated_at DESC)
            """
        ])

    async def synthesize_summary(self,
                                request_id: str,
                                verdict_data: Dict[str, Any],
                                assessment_data: Dict[str, Any],
                                style: SummaryStyle = SummaryStyle.EXECUTIVE,
                                length: SummaryLength = SummaryLength.STANDARD) -> ExecutiveSummary:
        """Synthesize executive summary from decision data"""
        logger.info(f"Synthesizing {style.value} summary for request: {request_id}")

        summary_id = f"{request_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Get template for style and length
        template = await self._get_summary_template(style, length)

        # Generate headline
        headline = await self._generate_headline(verdict_data, assessment_data)

        # Generate executive brief
        executive_brief = await self._generate_executive_brief(
            verdict_data, assessment_data, style
        )

        # Generate sections based on template
        sections = await self._generate_sections(
            template, verdict_data, assessment_data, style
        )

        # Extract key findings
        key_findings = await self._extract_key_findings(
            verdict_data, assessment_data, sections
        )

        # Identify critical risks
        critical_risks = await self._identify_critical_risks(
            verdict_data, assessment_data
        )

        # Generate next steps
        next_steps = await self._generate_next_steps(
            verdict_data, assessment_data, style
        )

        # Prepare appendices
        appendices = await self._prepare_appendices(
            verdict_data, assessment_data, length
        )

        # Create summary object
        summary = ExecutiveSummary(
            summary_id=summary_id,
            style=style,
            length=length,
            headline=headline,
            executive_brief=executive_brief,
            sections=sections,
            key_findings=key_findings,
            critical_risks=critical_risks,
            next_steps=next_steps,
            appendices=appendices,
            metadata={
                'request_id': request_id,
                'template_used': template.get('name'),
                'data_sources': self._get_data_sources(assessment_data)
            },
            generated_at=datetime.utcnow()
        )

        # Save summary
        await self._save_summary(request_id, summary)

        # Track analytics
        await self._track_analytics(summary)

        # Track source
        self.source_tracker.add_source(
            request_id=request_id,
            field_name="executive_summary",
            value=summary_id,
            source_system="summary_synthesizer",
            source_detail={
                'style': style.value,
                'length': length.value,
                'sections': len(sections)
            }
        )

        return summary

    async def _get_summary_template(self,
                                   style: SummaryStyle,
                                   length: SummaryLength) -> Dict[str, Any]:
        """Get appropriate summary template"""
        query = """
            SELECT id, name, structure, section_templates
            FROM summary_templates
            WHERE style = %s AND length = %s AND active = TRUE
            ORDER BY updated_at DESC
            LIMIT 1
        """

        result = await self.db_client.fetch_one(query, (style.value, length.value))

        if result:
            return {
                'id': result['id'],
                'name': result['name'],
                'structure': json.loads(result['structure']),
                'section_templates': json.loads(result['section_templates']) if result['section_templates'] else {}
            }

        # Return default template if none found
        return self._get_default_template(style, length)

    def _get_default_template(self,
                             style: SummaryStyle,
                             length: SummaryLength) -> Dict[str, Any]:
        """Get default template structure"""
        if style == SummaryStyle.EXECUTIVE:
            structure = {
                'sections': [
                    {'name': 'Overview', 'order': 1, 'required': True},
                    {'name': 'Key Findings', 'order': 2, 'required': True},
                    {'name': 'Risk Assessment', 'order': 3, 'required': True},
                    {'name': 'Recommendations', 'order': 4, 'required': True}
                ]
            }
        elif style == SummaryStyle.TECHNICAL:
            structure = {
                'sections': [
                    {'name': 'Technical Assessment', 'order': 1, 'required': True},
                    {'name': 'Feasibility Analysis', 'order': 2, 'required': True},
                    {'name': 'Implementation Considerations', 'order': 3, 'required': True},
                    {'name': 'Technical Risks', 'order': 4, 'required': True}
                ]
            }
        else:
            structure = {
                'sections': [
                    {'name': 'Summary', 'order': 1, 'required': True},
                    {'name': 'Analysis', 'order': 2, 'required': True},
                    {'name': 'Conclusion', 'order': 3, 'required': True}
                ]
            }

        return {
            'id': 0,
            'name': f"default_{style.value}_{length.value}",
            'structure': structure,
            'section_templates': {}
        }

    async def _generate_headline(self,
                                verdict_data: Dict[str, Any],
                                assessment_data: Dict[str, Any]) -> str:
        """Generate compelling headline"""
        verdict = verdict_data.get('verdict_type', 'UNKNOWN')
        confidence = verdict_data.get('confidence_score', 0)
        category = assessment_data.get('category', 'pharmaceutical')

        # Get appropriate phrase from database
        query = """
            SELECT phrase
            FROM summary_phrases
            WHERE category = %s
              AND context = 'headline'
              AND phrase_type = %s
              AND active = TRUE
            ORDER BY RANDOM()
            LIMIT 1
        """

        result = await self.db_client.fetch_one(
            query,
            (category, verdict.lower())
        )

        if result:
            return result['phrase']

        # Default headlines
        if verdict == "GO":
            return f"Strong Recommendation: Proceed with {category.title()} Development"
        elif verdict == "NO_GO":
            return f"Not Recommended: Significant Barriers Identified for {category.title()}"
        elif verdict == "CONDITIONAL":
            return f"Conditional Approval: {category.title()} Requires Specific Improvements"
        else:
            return f"{category.title()} Assessment: Further Review Required"

    async def _generate_executive_brief(self,
                                       verdict_data: Dict[str, Any],
                                       assessment_data: Dict[str, Any],
                                       style: SummaryStyle) -> str:
        """Generate executive brief paragraph"""
        verdict = verdict_data.get('verdict_type', 'UNKNOWN')
        confidence = verdict_data.get('confidence_score', 0)
        primary_rationale = verdict_data.get('primary_rationale', '')

        # Build brief based on style
        if style == SummaryStyle.EXECUTIVE:
            brief_parts = [
                f"After comprehensive analysis, our recommendation is {verdict}",
                f"with {confidence:.0f}% confidence.",
                primary_rationale,
                self._get_impact_statement(verdict_data, assessment_data)
            ]
        elif style == SummaryStyle.TECHNICAL:
            brief_parts = [
                f"Technical evaluation indicates a {verdict} verdict",
                f"based on {len(verdict_data.get('supporting_factors', []))} supporting factors",
                f"and {len(verdict_data.get('opposing_factors', []))} risk factors.",
                primary_rationale
            ]
        elif style == SummaryStyle.CLINICAL:
            brief_parts = [
                f"Clinical assessment results in {verdict} recommendation.",
                f"Safety and efficacy profiles {self._get_clinical_assessment(assessment_data)}.",
                primary_rationale
            ]
        else:
            brief_parts = [
                f"Analysis conclusion: {verdict}.",
                primary_rationale,
                f"Confidence level: {self._format_confidence(confidence)}."
            ]

        return " ".join(filter(None, brief_parts))

    def _get_impact_statement(self,
                             verdict_data: Dict[str, Any],
                             assessment_data: Dict[str, Any]) -> str:
        """Generate impact statement"""
        if verdict_data.get('verdict_type') == "GO":
            opportunities = verdict_data.get('opportunities', [])
            if opportunities:
                return f"Key opportunities include: {', '.join(opportunities[:2])}"
        else:
            risks = verdict_data.get('risk_factors', [])
            if risks:
                return f"Primary concerns: {', '.join(risks[:2])}"
        return ""

    def _get_clinical_assessment(self, assessment_data: Dict[str, Any]) -> str:
        """Get clinical assessment summary"""
        clinical = assessment_data.get('clinical_assessment', {})
        score = clinical.get('score', 0)
        if score >= 80:
            return "demonstrate strong potential"
        elif score >= 60:
            return "show acceptable characteristics"
        else:
            return "require further optimization"

    def _format_confidence(self, confidence: float) -> str:
        """Format confidence level"""
        if confidence >= 90:
            return "Very High"
        elif confidence >= 75:
            return "High"
        elif confidence >= 60:
            return "Moderate"
        elif confidence >= 40:
            return "Low"
        else:
            return "Very Low"

    async def _generate_sections(self,
                                template: Dict[str, Any],
                                verdict_data: Dict[str, Any],
                                assessment_data: Dict[str, Any],
                                style: SummaryStyle) -> List[SummarySection]:
        """Generate summary sections based on template"""
        sections = []
        structure = template.get('structure', {}).get('sections', [])

        for section_def in structure:
            section = await self._generate_section(
                section_def,
                verdict_data,
                assessment_data,
                style
            )
            if section:
                sections.append(section)

        # Sort by priority
        sections.sort(key=lambda x: x.priority)

        return sections

    async def _generate_section(self,
                               section_def: Dict[str, Any],
                               verdict_data: Dict[str, Any],
                               assessment_data: Dict[str, Any],
                               style: SummaryStyle) -> Optional[SummarySection]:
        """Generate individual section"""
        section_name = section_def['name']
        section_order = section_def['order']

        # Generate content based on section type
        if section_name == "Overview":
            content = await self._generate_overview(verdict_data, assessment_data)
            data_points = self._extract_overview_data(verdict_data, assessment_data)
        elif section_name == "Key Findings":
            content = await self._generate_key_findings_section(verdict_data, assessment_data)
            data_points = verdict_data.get('supporting_factors', [])
        elif section_name == "Risk Assessment":
            content = await self._generate_risk_section(verdict_data, assessment_data)
            data_points = verdict_data.get('opposing_factors', [])
        elif section_name == "Recommendations":
            content = await self._generate_recommendations_section(verdict_data, assessment_data)
            data_points = []
        elif section_name == "Technical Assessment":
            content = await self._generate_technical_section(verdict_data, assessment_data)
            data_points = self._extract_technical_data(assessment_data)
        else:
            content = f"Section {section_name} content to be generated"
            data_points = []

        if content:
            return SummarySection(
                title=section_name,
                content=content,
                priority=section_order,
                data_points=data_points,
                confidence=self._calculate_section_confidence(data_points)
            )

        return None

    async def _generate_overview(self,
                                verdict_data: Dict[str, Any],
                                assessment_data: Dict[str, Any]) -> str:
        """Generate overview section"""
        parts = []

        # Assessment scope
        category = assessment_data.get('category', 'pharmaceutical')
        parts.append(f"This {category} assessment evaluated multiple criteria across")
        parts.append(f"{len(verdict_data.get('supporting_factors', [])) + len(verdict_data.get('opposing_factors', []))} key factors.")

        # Overall verdict
        verdict = verdict_data.get('verdict_type')
        confidence = verdict_data.get('confidence_score', 0)
        parts.append(f"The analysis resulted in a {verdict} recommendation with {confidence:.0f}% confidence.")

        # Key drivers
        if verdict_data.get('decision_path', {}).get('primary_driver'):
            parts.append(f"The primary decision driver was {verdict_data['decision_path']['primary_driver']}.")

        return " ".join(parts)

    async def _generate_key_findings_section(self,
                                            verdict_data: Dict[str, Any],
                                            assessment_data: Dict[str, Any]) -> str:
        """Generate key findings section"""
        findings = []

        # Positive findings
        supporting = verdict_data.get('supporting_factors', [])
        if supporting:
            findings.append("Positive factors:")
            for factor in supporting[:3]:
                findings.append(f"• {factor.get('name', 'Unknown')}: Score {factor.get('score', 0):.0f}")

        # Areas of concern
        opposing = verdict_data.get('opposing_factors', [])
        if opposing:
            findings.append("\nAreas requiring attention:")
            for factor in opposing[:3]:
                findings.append(f"• {factor.get('name', 'Unknown')}: Score {factor.get('score', 0):.0f}")

        return "\n".join(findings)

    async def _generate_risk_section(self,
                                    verdict_data: Dict[str, Any],
                                    assessment_data: Dict[str, Any]) -> str:
        """Generate risk assessment section"""
        risks = verdict_data.get('risk_factors', [])

        if not risks:
            return "No critical risks identified in the current assessment."

        risk_text = ["The following risks have been identified:"]
        for risk in risks:
            risk_text.append(f"• {risk}")

        # Add mitigation if available
        if verdict_data.get('recommendations'):
            risk_text.append("\nMitigation strategies:")
            for rec in verdict_data.get('recommendations', [])[:2]:
                risk_text.append(f"• {rec}")

        return "\n".join(risk_text)

    async def _generate_recommendations_section(self,
                                               verdict_data: Dict[str, Any],
                                               assessment_data: Dict[str, Any]) -> str:
        """Generate recommendations section"""
        recommendations = verdict_data.get('recommendations', [])
        next_steps = verdict_data.get('next_steps', [])

        rec_text = []

        if recommendations:
            rec_text.append("Recommendations:")
            for rec in recommendations:
                rec_text.append(f"• {rec}")

        if next_steps:
            rec_text.append("\nImmediate next steps:")
            for step in next_steps:
                rec_text.append(f"• {step}")

        if verdict_data.get('conditions'):
            rec_text.append("\nConditions to be met:")
            for condition in verdict_data.get('conditions', []):
                rec_text.append(f"• {condition}")

        return "\n".join(rec_text) if rec_text else "No specific recommendations at this time."

    async def _generate_technical_section(self,
                                         verdict_data: Dict[str, Any],
                                         assessment_data: Dict[str, Any]) -> str:
        """Generate technical assessment section"""
        tech_parts = []

        # Technology score if available
        if 'technology_score' in assessment_data:
            score = assessment_data['technology_score']
            tech_parts.append(f"Technology feasibility score: {score:.1f}/100")

        # Manufacturing assessment
        if 'manufacturing' in assessment_data:
            mfg = assessment_data['manufacturing']
            tech_parts.append(f"Manufacturing feasibility: {mfg.get('feasibility', 'Not assessed')}")

        # Technical factors
        tech_factors = [
            f for f in verdict_data.get('supporting_factors', [])
            if 'technical' in f.get('category', '').lower()
        ]
        if tech_factors:
            tech_parts.append("Technical strengths:")
            for factor in tech_factors:
                tech_parts.append(f"• {factor.get('name')}")

        return "\n".join(tech_parts) if tech_parts else "Technical assessment pending."

    def _extract_overview_data(self,
                              verdict_data: Dict[str, Any],
                              assessment_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract data points for overview section"""
        data_points = []

        # Verdict data point
        data_points.append({
            'type': 'verdict',
            'value': verdict_data.get('verdict_type'),
            'confidence': verdict_data.get('confidence_score', 0)
        })

        # Assessment scores
        for key in ['technology_score', 'clinical_score', 'regulatory_score']:
            if key in assessment_data:
                data_points.append({
                    'type': key,
                    'value': assessment_data[key],
                    'confidence': 90
                })

        return data_points

    def _extract_technical_data(self, assessment_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract technical data points"""
        data_points = []

        technical_keys = [
            'technology_score',
            'manufacturing',
            'formulation',
            'stability',
            'scalability'
        ]

        for key in technical_keys:
            if key in assessment_data:
                data_points.append({
                    'type': key,
                    'value': assessment_data[key],
                    'confidence': 85
                })

        return data_points

    def _calculate_section_confidence(self, data_points: List[Dict[str, Any]]) -> float:
        """Calculate confidence for a section"""
        if not data_points:
            return 50.0

        confidences = [
            dp.get('confidence', 50)
            for dp in data_points
            if isinstance(dp, dict) and 'confidence' in dp
        ]

        return sum(confidences) / len(confidences) if confidences else 50.0

    async def _extract_key_findings(self,
                                   verdict_data: Dict[str, Any],
                                   assessment_data: Dict[str, Any],
                                   sections: List[SummarySection]) -> List[str]:
        """Extract key findings from all data"""
        findings = []

        # Verdict as key finding
        verdict = verdict_data.get('verdict_type')
        confidence = verdict_data.get('confidence_score', 0)
        findings.append(f"{verdict} recommendation with {confidence:.0f}% confidence")

        # Top supporting factors
        supporting = verdict_data.get('supporting_factors', [])
        if supporting and supporting[0].get('score', 0) > 80:
            findings.append(f"Strong {supporting[0].get('name', 'performance')} performance")

        # Critical risks
        risks = verdict_data.get('risk_factors', [])
        if risks:
            findings.append(f"{len(risks)} risk factors identified")

        # Technology viability
        if 'technology_score' in assessment_data:
            score = assessment_data['technology_score']
            if score > 80:
                findings.append("High technology feasibility")
            elif score < 50:
                findings.append("Technology challenges identified")

        return findings[:5]  # Limit to 5 key findings

    async def _identify_critical_risks(self,
                                      verdict_data: Dict[str, Any],
                                      assessment_data: Dict[str, Any]) -> List[str]:
        """Identify critical risks"""
        risks = verdict_data.get('risk_factors', [])

        # Add any exclusion factors
        if 'exclusions' in assessment_data:
            for exclusion in assessment_data['exclusions']:
                risks.append(f"Exclusion criterion: {exclusion}")

        # Add critical failures
        opposing = verdict_data.get('opposing_factors', [])
        for factor in opposing:
            if factor.get('score', 100) < 40:
                risks.append(f"Critical: {factor.get('name', 'Unknown factor')}")

        return list(set(risks))[:5]  # Unique risks, limited to 5

    async def _generate_next_steps(self,
                                  verdict_data: Dict[str, Any],
                                  assessment_data: Dict[str, Any],
                                  style: SummaryStyle) -> List[str]:
        """Generate next steps based on verdict and style"""
        next_steps = []
        verdict = verdict_data.get('verdict_type')

        if verdict == "GO":
            if style == SummaryStyle.EXECUTIVE:
                next_steps.extend([
                    "Proceed to detailed project planning",
                    "Allocate resources for development phase",
                    "Establish project governance structure"
                ])
            elif style == SummaryStyle.TECHNICAL:
                next_steps.extend([
                    "Initiate technical feasibility studies",
                    "Develop proof-of-concept prototype",
                    "Define technical specifications"
                ])

        elif verdict == "NO_GO":
            next_steps.extend([
                "Document lessons learned",
                "Explore alternative approaches",
                "Re-evaluate after addressing critical issues"
            ])

        elif verdict == "CONDITIONAL":
            next_steps.extend([
                "Address specified conditions",
                "Schedule reassessment after improvements",
                "Develop mitigation plan for identified risks"
            ])

        else:
            next_steps.extend([
                "Gather additional data for comprehensive assessment",
                "Consult subject matter experts",
                "Schedule follow-up review"
            ])

        return next_steps[:5]

    async def _prepare_appendices(self,
                                 verdict_data: Dict[str, Any],
                                 assessment_data: Dict[str, Any],
                                 length: SummaryLength) -> Dict[str, Any]:
        """Prepare appendices based on summary length"""
        appendices = {}

        if length in [SummaryLength.DETAILED, SummaryLength.COMPREHENSIVE]:
            # Add detailed scoring breakdown
            appendices['scoring_details'] = {
                'factors': verdict_data.get('supporting_factors', []) +
                          verdict_data.get('opposing_factors', []),
                'total_score': assessment_data.get('total_score')
            }

            # Add methodology
            appendices['methodology'] = {
                'assessment_types': list(assessment_data.keys()),
                'confidence_calculation': verdict_data.get('confidence_score')
            }

        if length == SummaryLength.COMPREHENSIVE:
            # Add full data tables
            appendices['raw_data'] = assessment_data
            appendices['decision_path'] = verdict_data.get('decision_path', {})
            appendices['historical_context'] = {}  # Would fetch from database

        return appendices

    def _get_data_sources(self, assessment_data: Dict[str, Any]) -> List[str]:
        """Extract data sources used"""
        sources = set()

        for key, value in assessment_data.items():
            if isinstance(value, dict) and 'source' in value:
                sources.add(value['source'])

        return list(sources)

    async def _save_summary(self, request_id: str, summary: ExecutiveSummary):
        """Save executive summary to database"""
        sections_json = [
            {
                'title': s.title,
                'content': s.content,
                'priority': s.priority,
                'confidence': s.confidence
            } for s in summary.sections
        ]

        query = """
            INSERT INTO summary_history
            (summary_id, request_id, style, length, headline, executive_brief,
             sections, key_findings, critical_risks, next_steps, appendices, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        await self.db_client.execute(
            query,
            (
                summary.summary_id,
                request_id,
                summary.style.value,
                summary.length.value,
                summary.headline,
                summary.executive_brief,
                json.dumps(sections_json),
                summary.key_findings,
                summary.critical_risks,
                summary.next_steps,
                json.dumps(summary.appendices),
                json.dumps(summary.metadata)
            )
        )

    async def _track_analytics(self, summary: ExecutiveSummary):
        """Track summary analytics"""
        # Calculate metrics
        word_count = len(summary.executive_brief.split())
        for section in summary.sections:
            word_count += len(section.content.split())

        query = """
            INSERT INTO summary_analytics
            (summary_id, word_count, readability_score, technical_depth,
             sections_included, generation_time_ms, llm_tokens_used)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        await self.db_client.execute(
            query,
            (
                summary.summary_id,
                word_count,
                85.0,  # Placeholder for readability calculation
                70.0,  # Placeholder for technical depth
                len(summary.sections),
                500,  # Placeholder for generation time
                word_count * 2  # Estimate tokens
            )
        )

    async def get_summary_history(self, request_id: str) -> List[Dict[str, Any]]:
        """Get summary generation history"""
        query = """
            SELECT summary_id, style, length, headline, generated_at
            FROM summary_history
            WHERE request_id = %s
            ORDER BY generated_at DESC
        """

        results = await self.db_client.fetch_all(query, (request_id,))

        history = []
        for row in results:
            history.append({
                'summary_id': row['summary_id'],
                'style': row['style'],
                'length': row['length'],
                'headline': row['headline'],
                'generated_at': row['generated_at'].isoformat()
            })

        return history