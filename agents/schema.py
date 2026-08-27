"""
Shared data structures passed between agents in the pipeline.
Keeping this in one place avoids each agent guessing the shape of
upstream output.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Report:
    """A citizen-submitted infrastructure report as it moves through the pipeline."""

    raw_text: Optional[str] = None
    image_filename: Optional[str] = None

    # Filled in by IntakeAgent
    issue_type: Optional[str] = None          # e.g. "pothole", "broken streetlight"
    description: Optional[str] = None         # PII-redacted description
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None

    # Filled in by DuplicateCheckAgent
    is_duplicate: bool = False
    duplicate_of_report_id: Optional[str] = None

    # Filled in by SeverityClassifierAgent
    severity_score: Optional[int] = None       # 1 (low) - 5 (critical)
    severity_reasoning: Optional[str] = None   # explainability — not a black box

    # Filled in by DepartmentRouterAgent
    department: Optional[str] = None

    # Filled in by WorkOrderAgent
    work_order_text: Optional[str] = None

    report_id: str = field(default_factory=lambda: "")
    status: str = "open"
