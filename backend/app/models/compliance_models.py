from typing import List
from pydantic import BaseModel, Field


class ComplianceAuditResult(BaseModel):
    unit_id: str = Field(default="")
    compliance_status: str = Field(default="unknown")
    deviations_found: List[str] = Field(default_factory=list)
    corrective_actions: List[str] = Field(default_factory=list)
    regulatory_references: List[str] = Field(default_factory=list)
