from typing import List, Optional
from pydantic import BaseModel, Field


class VibrationAnalysisResult(BaseModel):
    unit_id: str = Field(default="")
    baseline_signature: List[float] = Field(default_factory=list)
    current_signature: List[float] = Field(default_factory=list)
    deviation_score: float = Field(default=0.0)
    status: str = Field(default="healthy")
    time_to_failure_weeks: Optional[float] = None
    explanation: str = Field(default="")
    trend_last_30_days: List[float] = Field(default_factory=list)
