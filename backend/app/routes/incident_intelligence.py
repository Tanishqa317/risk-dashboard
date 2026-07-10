from typing import Any, Dict

from fastapi import APIRouter

from app.models.rag_models import PatternAnalysisResult
from app.services.rag_service import analyze_patterns

router = APIRouter(tags=["Incident Intelligence"])


@router.get("/incident-patterns/{unit_id}", response_model=Dict[str, Any])
def get_incident_patterns(unit_id: str) -> Dict[str, Any]:
    result = analyze_patterns(unit_id)
    return result
