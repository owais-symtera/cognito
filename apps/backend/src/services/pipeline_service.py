"""Pipeline service for managing processing pipelines."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import random


class PipelineService:
    """Service for managing drug analysis pipelines."""

    def __init__(self):
        """Initialize pipeline service."""
        # In-memory storage (replace with database in production)
        self.pipelines_db: Dict[str, Dict[str, Any]] = {}
        # Initialize with sample data
        self._initialize_sample_pipelines()

    def create_pipeline(
        self,
        request_id: str,
        drug_name: str,
        category: str = "General"
    ) -> Dict[str, Any]:
        """Create a new processing pipeline."""
        pipeline_id = f"pipe-{request_id}"

        pipeline_data = {
            "id": pipeline_id,
            "drugName": drug_name,
            "category": category,
            "currentStep": 1,
            "totalSteps": 6,
            "status": "running",
            "startTime": datetime.now().isoformat(),
            "steps": self._create_pipeline_steps()
        }

        self.pipelines_db[pipeline_id] = pipeline_data
        return pipeline_data

    def _create_pipeline_steps(self) -> List[Dict[str, Any]]:
        """Create default pipeline steps."""
        return [
            {"id": "step-1", "name": "Data Collection", "status": "pending", "progress": 0},
            {"id": "step-2", "name": "Source Verification", "status": "pending", "progress": 0},
            {"id": "step-3", "name": "Data Merging", "status": "pending", "progress": 0},
            {"id": "step-4", "name": "Quality Analysis", "status": "pending", "progress": 0},
            {"id": "step-5", "name": "Regulatory Check", "status": "pending", "progress": 0},
            {"id": "step-6", "name": "Final Processing", "status": "pending", "progress": 0}
        ]

    def get_pipeline(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific pipeline by ID."""
        return self.pipelines_db.get(pipeline_id)

    def get_all_pipelines(self) -> List[Dict[str, Any]]:
        """Get all pipelines."""
        return list(self.pipelines_db.values())

    def update_pipeline_step(
        self,
        pipeline_id: str,
        step_index: int,
        status: str,
        progress: int
    ) -> bool:
        """Update a specific step in the pipeline."""
        pipeline = self.get_pipeline(pipeline_id)
        if not pipeline:
            return False

        if 0 <= step_index < len(pipeline["steps"]):
            pipeline["steps"][step_index]["status"] = status
            pipeline["steps"][step_index]["progress"] = progress

            # Update current step if completed
            if status == "completed" and progress == 100:
                pipeline["currentStep"] = min(step_index + 2, pipeline["totalSteps"])

            # Check if all steps are completed
            if all(step["status"] == "completed" for step in pipeline["steps"]):
                pipeline["status"] = "completed"

            return True
        return False

    def update_pipeline_status(
        self,
        pipeline_id: str,
        status: str
    ) -> bool:
        """Update pipeline status."""
        pipeline = self.get_pipeline(pipeline_id)
        if pipeline:
            pipeline["status"] = status
            if status == "completed":
                pipeline["endTime"] = datetime.now().isoformat()
            return True
        return False

    def delete_pipeline(self, pipeline_id: str) -> bool:
        """Delete a pipeline."""
        if pipeline_id in self.pipelines_db:
            del self.pipelines_db[pipeline_id]
            return True
        return False

    def get_active_pipelines(self) -> List[Dict[str, Any]]:
        """Get all active (running) pipelines."""
        return [
            pipeline for pipeline in self.pipelines_db.values()
            if pipeline["status"] == "running"
        ]

    def get_completed_pipelines(self) -> List[Dict[str, Any]]:
        """Get all completed pipelines."""
        return [
            pipeline for pipeline in self.pipelines_db.values()
            if pipeline["status"] == "completed"
        ]

    def get_pipeline_by_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get pipeline by request ID."""
        pipeline_id = f"pipe-{request_id}"
        return self.get_pipeline(pipeline_id)

    def _initialize_sample_pipelines(self):
        """Initialize sample pipelines for demonstration."""
        drugs = [
            ("Aspirin", "Cardiology"),
            ("Metformin", "Endocrinology"),
            ("Ibuprofen", "Pain Management"),
            ("Amoxicillin", "Antibiotics"),
            ("Lisinopril", "Cardiology")
        ]

        for i, (drug_name, category) in enumerate(drugs):
            pipeline_id = f"pipe-{i+1:03d}"
            status = random.choice(["processing", "completed", "processing"])
            current_step = random.randint(1, 6) if status == "processing" else 6

            # Create realistic steps with progress
            steps = []
            for step_idx in range(6):
                step_names = [
                    "Data Collection",
                    "Source Verification",
                    "Data Merging",
                    "Quality Analysis",
                    "Regulatory Check",
                    "Final Processing"
                ]

                if step_idx < current_step - 1:
                    step_status = "completed"
                    progress = 100
                    output = self._generate_step_output(step_names[step_idx], drug_name)
                elif step_idx == current_step - 1:
                    step_status = "running" if status == "processing" else "completed"
                    progress = random.randint(30, 90) if status == "processing" else 100
                    output = self._generate_step_output(step_names[step_idx], drug_name, partial=True)
                else:
                    step_status = "pending"
                    progress = 0
                    output = None

                steps.append({
                    "id": f"step-{step_idx+1}",
                    "name": step_names[step_idx],
                    "status": step_status,
                    "progress": progress,
                    "duration": random.randint(30, 180) if step_status == "completed" else None,
                    "output": output,
                    "apiProvider": "Multiple" if step_idx == 0 else None,
                    "temperature": 0.7 if step_idx == 0 else None
                })

            start_time = datetime.now() - timedelta(minutes=random.randint(10, 60))
            end_time = start_time + timedelta(minutes=random.randint(30, 120)) if status == "completed" else None

            self.pipelines_db[pipeline_id] = {
                "id": pipeline_id,
                "drugName": drug_name,
                "category": category,
                "currentStep": current_step,
                "totalSteps": 6,
                "status": status,
                "startTime": start_time.isoformat(),
                "endTime": end_time.isoformat() if end_time else None,
                "steps": steps
            }

    def _generate_step_output(self, step_name: str, drug_name: str, partial: bool = False) -> str:
        """Generate realistic output for pipeline steps."""
        outputs = {
            "Data Collection": f"Collected data from 6 API providers:\n- OpenAI: {random.randint(150, 350)} data points\n- Claude: {random.randint(150, 350)} data points\n- Gemini: {random.randint(150, 350)} data points\n- Grok: {random.randint(150, 350)} data points\n- Perplexity: {random.randint(150, 350)} data points\n- Tavily: {random.randint(150, 350)} data points",
            "Source Verification": f"Verified {random.randint(1000, 2000)} total data points\n- Primary sources: {random.randint(500, 1000)}\n- Secondary sources: {random.randint(400, 800)}\n- Citation accuracy: {random.uniform(95, 99):.1f}%",
            "Data Merging": f"{'Merging in progress...' if partial else 'Merge completed'}\n- Duplicates removed: {random.randint(100, 400)}\n- Conflicts resolved: {random.randint(5, 20)}\n- Enriched entries: {random.randint(50, 200)}",
            "Quality Analysis": f"Quality score: {random.uniform(85, 98):.1f}%\n- Completeness: {random.uniform(90, 99):.1f}%\n- Accuracy: {random.uniform(88, 97):.1f}%\n- Consistency: {random.uniform(85, 96):.1f}%",
            "Regulatory Check": f"FDA: Compliant\nEMA: Compliant\nWHO: Compliant\n- No critical issues found\n- {random.randint(0, 3)} minor recommendations",
            "Final Processing": f"Report generated successfully\n- Full analysis report: PDF (2.3 MB)\n- Executive summary: DOCX (156 KB)\n- Data export: CSV (892 KB)"
        }
        return outputs.get(step_name, f"Processing {drug_name}...")