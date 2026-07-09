from fastapi import APIRouter
from app.models.correlation_models import RiskAssessmentRequest, RiskAssessmentResponse
from app.services.correlation_service import get_risk_assessment

router = APIRouter()


@router.post("/risk-assessment", response_model=RiskAssessmentResponse)
def post_risk_assessment(request: RiskAssessmentRequest):
    """Analyze risk for a given unit."""
    result = get_risk_assessment(request.unit_id)
    return result


@router.get("/risk-assessment/{unit_id}", response_model=RiskAssessmentResponse)
def get_risk_for_unit(unit_id: str):
    """Analyze risk for a given unit (GET endpoint for browser testing)."""
    result = get_risk_assessment(unit_id)
    return result
