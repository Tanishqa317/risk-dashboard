from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class Permit(BaseModel):
    permit_id: str = Field(default="")
    zone_id: str = Field(default="")
    permit_type: str = Field(default="")
    start_time: datetime
    end_time: datetime


class PermitGamingResult(BaseModel):
    suspicious: bool = Field(default=False)
    reason: str = Field(default="No suspicious permit combination detected.")
    flagged_permits: List[str] = Field(default_factory=list)
