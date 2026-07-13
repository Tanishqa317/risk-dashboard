import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from fastapi import APIRouter, HTTPException

from app.models.permit_models import Permit, PermitGamingResult
from app.services.permit_detector_service import detect_permit_gaming

router = APIRouter(tags=["Permit Detector"])


@router.post("/permit-gaming-check", response_model=PermitGamingResult)
def permit_gaming_check(permits: List[Permit]) -> PermitGamingResult:
    return detect_permit_gaming(permits)


@router.get("/permit-gaming-check/demo/{unit_id}", response_model=Dict[str, Any])
def permit_gaming_demo(unit_id: str) -> Dict[str, Any]:
    data_path = Path(__file__).resolve().parents[3] / "data" / "combined_dataset.csv"
    if not data_path.exists():
        raise HTTPException(status_code=404, detail="combined_dataset.csv not found")

    df = pd.read_csv(data_path)
    unit_rows = df[df["unit_id"] == unit_id]
    if unit_rows.empty:
        raise HTTPException(status_code=404, detail=f"Unit {unit_id} not found")

    permits: List[Permit] = []
    for _, row in unit_rows.head(10).iterrows():
        permit_id = str(row.get("permit_id", ""))
        if not permit_id:
            continue
        permits.append(
            Permit(
                permit_id=permit_id,
                zone_id=str(row.get("zone_id", "")),
                permit_type="hot-work" if "hot" in str(row.get("permit_status", "")).lower() else "confined-space",
                start_time=pd.to_datetime(row.get("timestamp")).isoformat(),
                end_time=pd.to_datetime(row.get("timestamp")).isoformat(),
            )
        )

    result = detect_permit_gaming(permits)
    return {
        "unit_id": unit_id,
        "permits": [permit.model_dump() for permit in permits],
        "result": result.model_dump(),
    }
