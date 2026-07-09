from pydantic import BaseModel


class CostRequest(BaseModel):
    risk_score: int
    primary_concern: str


class CostResponse(BaseModel):
    estimated_cost_usd: float
    cost_range_low: float
    cost_range_high: float
    category_used: str
    confidence_note: str
