from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AlarmEvent(BaseModel):
    unit_id: str = Field(default="")
    source: str = Field(default="")
    severity: str = Field(default="low")
    message: str = Field(default="")
    timestamp: datetime


class AlarmFatigueResult(BaseModel):
    unit_id: str = Field(default="")
    alert_count_last_hour: int = Field(default=0)
    fatigue_detected: bool = Field(default=False)
    suppressed_count: int = Field(default=0)
    top_priority_alert: Optional[AlarmEvent] = None
    recommendation: str = Field(default="")
