"""Analysis service for managing drug analysis results."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import random


class AnalysisService:
    """Service for managing drug analysis results."""

    def __init__(self):
        """Initialize analysis service."""
        # In-memory storage (replace with database in production)
        self.analysis_db: Dict[str, Dict[str, Any]] = {}
        # Initialize with sample data
        self._initialize_sample_analyses()

    def create_analysis(
        self,
        request_id: str,
        drug_name: str,
        analysis_type: str = "full_analysis",
        results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new analysis record."""
        analysis_id = f"ana-{request_id}"

        analysis_data = {
            "id": analysis_id,
            "requestId": request_id,
            "drugName": drug_name,
            "analysisType": analysis_type,
            "status": "pending",
            "createdAt": datetime.now().isoformat(),
            "updatedAt": datetime.now().isoformat(),
            "completedAt": None,
            "results": results or {}
        }

        self.analysis_db[analysis_id] = analysis_data
        return analysis_data

    def get_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific analysis by ID."""
        return self.analysis_db.get(analysis_id)

    def get_analysis_by_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get analysis by request ID."""
        analysis_id = f"ana-{request_id}"
        return self.get_analysis(analysis_id)

    def get_all_analyses(self) -> List[Dict[str, Any]]:
        """Get all analyses."""
        return list(self.analysis_db.values())

    def update_analysis(
        self,
        analysis_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update analysis data."""
        if analysis_id not in self.analysis_db:
            return False

        analysis = self.analysis_db[analysis_id]

        # Update allowed fields
        if "status" in updates:
            analysis["status"] = updates["status"]

        if "results" in updates:
            analysis["results"] = updates["results"]

        if "overallScore" in updates:
            analysis["overallScore"] = updates["overallScore"]

        if "confidenceLevel" in updates:
            analysis["confidenceLevel"] = updates["confidenceLevel"]

        if "riskAssessment" in updates:
            analysis["riskAssessment"] = updates["riskAssessment"]

        if "completedAt" in updates:
            analysis["completedAt"] = updates["completedAt"]

        # Always update timestamp
        analysis["updatedAt"] = datetime.now().isoformat()

        return True

    def complete_analysis(
        self,
        analysis_id: str,
        overall_score: int,
        confidence_level: int,
        risk_assessment: str,
        processing_duration: int,
        analyst: str = "AI System"
    ) -> bool:
        """Mark analysis as completed with results."""
        return self.update_analysis(analysis_id, {
            "status": "completed",
            "overallScore": overall_score,
            "confidenceLevel": confidence_level,
            "riskAssessment": risk_assessment,
            "processingDuration": processing_duration,
            "analyst": analyst,
            "completedAt": datetime.now().isoformat()
        })

    def delete_analysis(self, analysis_id: str) -> bool:
        """Delete an analysis."""
        if analysis_id in self.analysis_db:
            del self.analysis_db[analysis_id]
            return True
        return False

    def get_analyses_by_drug(self, drug_name: str) -> List[Dict[str, Any]]:
        """Get all analyses for a specific drug."""
        return [
            analysis for analysis in self.analysis_db.values()
            if analysis["drugName"].lower() == drug_name.lower()
        ]

    def get_completed_analyses(self) -> List[Dict[str, Any]]:
        """Get all completed analyses."""
        return [
            analysis for analysis in self.analysis_db.values()
            if analysis["status"] == "completed"
        ]

    def get_pending_analyses(self) -> List[Dict[str, Any]]:
        """Get all pending analyses."""
        return [
            analysis for analysis in self.analysis_db.values()
            if analysis["status"] == "pending"
        ]

    def _initialize_sample_analyses(self):
        """Initialize sample analyses for demonstration."""
        drugs = [
            ("Aspirin", "Cardiology", "full_analysis"),
            ("Metformin", "Endocrinology", "safety_profile"),
            ("Ibuprofen", "Pain Management", "interaction_check"),
            ("Amoxicillin", "Antibiotics", "regulatory_compliance"),
            ("Lisinopril", "Cardiology", "full_analysis"),
            ("Atorvastatin", "Cardiology", "safety_profile"),
            ("Omeprazole", "Gastroenterology", "interaction_check"),
            ("Amlodipine", "Cardiology", "full_analysis")
        ]

        requesters = [
            ("Dr. Smith", "Cardiology"),
            ("Dr. Johnson", "Endocrinology"),
            ("Dr. Williams", "Neurology"),
            ("Dr. Brown", "Pediatrics"),
            ("Dr. Jones", "Oncology")
        ]

        for i, (drug_name, category, analysis_type) in enumerate(drugs):
            analysis_id = f"ana-{i+1:03d}"
            request_id = f"req-{i+1:03d}"
            requester = random.choice(requesters)
            status = random.choice(["completed", "failed", "partial"]) if i < 6 else "completed"

            completed_time = datetime.now() - timedelta(hours=random.randint(1, 48))
            processing_duration = random.uniform(0.5, 4.0)

            # Generate realistic findings
            safety_score = random.randint(70, 98)
            efficacy_score = random.randint(65, 95)
            compliance_score = random.randint(75, 100)
            overall_score = int((safety_score + efficacy_score + compliance_score) / 3)

            self.analysis_db[analysis_id] = {
                "id": analysis_id,
                "requestId": request_id,
                "drugName": drug_name,
                "analysisType": analysis_type,
                "status": status,
                "overallScore": overall_score,
                "confidenceLevel": random.randint(85, 98),
                "riskAssessment": self._determine_risk(overall_score),
                "completedAt": completed_time.isoformat(),
                "processingDuration": processing_duration,
                "analyst": "AI System",
                "requesterName": requester[0],
                "department": requester[1],
                "findings": {
                    "safety": {
                        "score": safety_score,
                        "status": "pass" if safety_score > 80 else ("warning" if safety_score > 60 else "fail"),
                        "details": [
                            f"No major safety concerns identified for {drug_name}",
                            "Clinical trials show acceptable safety profile",
                            "Adverse event rate within acceptable limits"
                        ],
                        "adverseEffects": self._generate_adverse_effects()
                    },
                    "efficacy": {
                        "score": efficacy_score,
                        "status": "pass" if efficacy_score > 80 else ("warning" if efficacy_score > 60 else "fail"),
                        "details": [
                            f"{drug_name} shows significant therapeutic benefit",
                            "Efficacy demonstrated in multiple clinical trials",
                            "Superior to placebo in primary endpoints"
                        ],
                        "therapeuticIndex": random.uniform(1.5, 10.0)
                    },
                    "interactions": {
                        "count": random.randint(0, 15),
                        "severity": random.choice(["low", "medium", "high"]),
                        "majorInteractions": self._generate_interactions(drug_name),
                        "contraindicatedWith": self._generate_contraindications()
                    },
                    "regulatory": {
                        "complianceScore": compliance_score,
                        "status": "compliant" if compliance_score > 85 else ("requires_review" if compliance_score > 70 else "non_compliant"),
                        "fdaStatus": random.choice(["Approved", "Under Review", "Approved with Restrictions"]),
                        "requiredStudies": self._generate_required_studies() if compliance_score < 90 else []
                    }
                },
                "recommendations": {
                    "priority": random.choice(["low", "medium", "high", "urgent"]),
                    "actions": self._generate_recommendations(drug_name, overall_score),
                    "followUpRequired": overall_score < 85 or status != "completed",
                    "nextSteps": [
                        "Review detailed analysis report",
                        "Consult with medical team",
                        "Monitor patient response"
                    ] if overall_score < 85 else []
                },
                "reports": [
                    {
                        "id": f"report-{i+1:03d}-1",
                        "name": f"{drug_name}_Full_Analysis.pdf",
                        "type": "pdf",
                        "size": random.randint(500000, 3000000),
                        "generatedAt": completed_time.isoformat(),
                        "url": f"/api/v1/reports/{analysis_id}/full"
                    },
                    {
                        "id": f"report-{i+1:03d}-2",
                        "name": f"{drug_name}_Summary.xlsx",
                        "type": "excel",
                        "size": random.randint(50000, 200000),
                        "generatedAt": completed_time.isoformat(),
                        "url": f"/api/v1/reports/{analysis_id}/summary"
                    }
                ],
                "attachments": [],
                "createdAt": (completed_time - timedelta(hours=processing_duration)).isoformat(),
                "updatedAt": completed_time.isoformat()
            }

    def _determine_risk(self, score: int) -> str:
        """Determine risk level based on overall score."""
        if score >= 90:
            return "low"
        elif score >= 75:
            return "medium"
        elif score >= 60:
            return "high"
        else:
            return "critical"

    def _generate_adverse_effects(self) -> List[str]:
        """Generate sample adverse effects."""
        effects = [
            "Mild nausea (5-10% of patients)",
            "Headache (3-7% of patients)",
            "Dizziness (2-5% of patients)",
            "Fatigue (1-3% of patients)",
            "Gastrointestinal discomfort (4-8% of patients)"
        ]
        return random.sample(effects, random.randint(2, 4))

    def _generate_interactions(self, drug_name: str) -> List[str]:
        """Generate sample drug interactions."""
        interactions = [
            "Warfarin - increased bleeding risk",
            "ACE inhibitors - hypotension risk",
            "NSAIDs - reduced efficacy",
            "Metformin - lactic acidosis risk",
            "Digoxin - increased toxicity"
        ]
        return random.sample(interactions, random.randint(1, 3))

    def _generate_contraindications(self) -> List[str]:
        """Generate sample contraindications."""
        contraindications = [
            "Severe renal impairment",
            "Hepatic dysfunction",
            "Pregnancy",
            "Known hypersensitivity"
        ]
        return random.sample(contraindications, random.randint(0, 2))

    def _generate_required_studies(self) -> List[str]:
        """Generate required studies for regulatory compliance."""
        studies = [
            "Phase IV post-marketing surveillance",
            "Pediatric safety study",
            "Long-term efficacy trial",
            "Drug-drug interaction study"
        ]
        return random.sample(studies, random.randint(1, 2))

    def _generate_recommendations(self, drug_name: str, score: int) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        if score < 70:
            recommendations.append(f"Consider alternative to {drug_name}")
            recommendations.append("Conduct additional safety assessment")
        elif score < 85:
            recommendations.append(f"Monitor patients closely when prescribing {drug_name}")
            recommendations.append("Review drug interactions before administration")
        else:
            recommendations.append(f"{drug_name} is suitable for indicated use")
            recommendations.append("Follow standard dosing guidelines")

        recommendations.append("Document patient response and adverse events")
        return recommendations