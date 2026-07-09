from pydantic import BaseModel
from typing import Optional


class RiskAssessmentRequest(BaseModel):
    unit_id: str


class RiskAssessmentResponse(BaseModel):
    unit_id: str
    risk_score: int
    risk_level: str
    primary_concern: str
    reasoning: str
    error: Optional[str] = None
