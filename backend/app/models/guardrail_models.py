from typing import List, Optional
from pydantic import BaseModel, Field


class Permit(BaseModel):
    permit_type: str = Field(default="")


class ZoneState(BaseModel):
    zone_id: str = Field(default="")
    gas_ppm: float = Field(default=0.0)
    active_permits: List[Permit] = Field(default_factory=list)
    supervisors_present: int = Field(default=0)


class PlantState(BaseModel):
    zones: List[ZoneState] = Field(default_factory=list)


class EngineOutput(BaseModel):
    risk_score: int | float = Field(default=0)
    flagged_zone: str = Field(default="")
    reasoning: str = Field(default="")
    contributing_factors: List[str] = Field(default_factory=list)


class GuardrailResult(BaseModel):
    risk_score: int | float = Field(default=0)
    flagged_zone: str = Field(default="")
    reasoning: str = Field(default="")
    contributing_factors: List[str] = Field(default_factory=list)
    overridden: bool = Field(default=False)
    override_reason: Optional[str] = None
