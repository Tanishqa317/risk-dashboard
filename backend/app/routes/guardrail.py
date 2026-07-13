import json
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.models.guardrail_models import EngineOutput, GuardrailResult, PlantState
from app.services.correlation_service import get_risk_assessment
from app.services.guardrail_service import check_guardrail

router = APIRouter(tags=["Guardrail"])


@router.post("/guardrail-check", response_model=GuardrailResult)
def guardrail_check(payload: Dict[str, Any]) -> GuardrailResult:
    plant_state = PlantState(**payload.get("plant_state", {}))
    engine_output = EngineOutput(**payload.get("engine_output", {}))
    return check_guardrail(plant_state, engine_output)


@router.get("/guardrail-check/demo/{unit_id}", response_model=Dict[str, Any])
def guardrail_demo(unit_id: str) -> Dict[str, Any]:
    data_dir = Path(__file__).resolve().parents[3] / "data"
    layout_path = data_dir / "plant_layout.json"
    if not layout_path.exists():
        raise HTTPException(status_code=404, detail="plant_layout.json not found")

    layout_data = json.loads(layout_path.read_text(encoding="utf-8"))
    unit_layout = next((item for item in layout_data if item.get("unit_id") == unit_id), None)
    if not unit_layout:
        raise HTTPException(status_code=404, detail=f"Unit {unit_id} not found")

    zones = []
    for zone in unit_layout.get("zones", []):
        zones.append(
            {
                "zone_id": zone.get("zone_id", ""),
                "gas_ppm": 250.0,
                "active_permits": [],
                "supervisors_present": 2,
            }
        )

    plant_state = PlantState(
        zones=[
            {
                "zone_id": zone["zone_id"],
                "gas_ppm": zone["gas_ppm"],
                "active_permits": zone["active_permits"],
                "supervisors_present": zone["supervisors_present"],
            }
            for zone in zones
        ]
    )
    engine_output = get_risk_assessment(unit_id)
    engine_output_model = EngineOutput(**engine_output)
    guardrail_result = check_guardrail(plant_state, engine_output_model)

    return {
        "unit_id": unit_id,
        "plant_state": plant_state.model_dump(),
        "engine_output": engine_output_model.model_dump(),
        "guardrail_result": guardrail_result.model_dump(),
    }
