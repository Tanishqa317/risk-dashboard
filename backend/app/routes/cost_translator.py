from fastapi import APIRouter
from app.models.cost_models import CostRequest, CostResponse
from app.services.cost_service import calculate_cost
from app.services.correlation_service import get_risk_assessment

router = APIRouter()


@router.post("/cost-of-risk", response_model=CostResponse)
def post_cost_of_risk(request: CostRequest):
    return calculate_cost(request.risk_score, request.primary_concern)


@router.get("/cost-of-risk/{unit_id}")
def get_cost_of_risk(unit_id: str):
    risk = get_risk_assessment(unit_id)
    cost = calculate_cost(risk.get("risk_score", 0), risk.get("primary_concern", ""))
    return {
        "unit_id": unit_id,
        "risk_score": risk.get("risk_score"),
        "risk_level": risk.get("risk_level"),
        "primary_concern": risk.get("primary_concern"),
        "reasoning": risk.get("reasoning"),
        **cost,
    }
