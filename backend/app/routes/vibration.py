from fastapi import APIRouter

from app.models.vibration_models import VibrationAnalysisResult
from app.services.vibration_service import get_vibration_analysis

router = APIRouter(tags=["Vibration DNA"])


@router.get("/vibration-dna/{unit_id}", response_model=VibrationAnalysisResult)
def get_vibration_dna(unit_id: str) -> VibrationAnalysisResult:
    result = get_vibration_analysis(unit_id)
    return VibrationAnalysisResult(**result)
