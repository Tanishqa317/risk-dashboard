from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
import json

try:
    from vibration_baseline import checkVibrationDrift, buildVibrationBaseline
except Exception:
    import sys
    cur = Path(__file__).resolve()
    repo_root = cur
    # walk up a few levels to find the workspace root containing vibration_baseline.py
    for _ in range(8):
        if (repo_root / 'vibration_baseline.py').exists():
            break
        if repo_root.parent == repo_root:
            break
        repo_root = repo_root.parent
    sys.path.insert(0, str(repo_root))
    from vibration_baseline import checkVibrationDrift, buildVibrationBaseline

router = APIRouter()


class VibrationCheckRequest(BaseModel):
    machine_id: str = Field(..., description="Machine identifier")
    recent_readings: List[float] = Field(..., description="Recent vibration amplitude readings")
    baseline_override: Optional[Dict[str, Any]] = Field(None, description="Optional baseline dict (mean,std,n) to use instead of stored baseline")


class VibrationCheckResponse(BaseModel):
    machine_id: str
    drift_score: int
    status: str
    detected_at: str
    baseline: Optional[Dict[str, Any]] = None


BASELINE_FILE = Path("vibration_baselines.json")


def load_stored_baselines() -> Dict[str, Dict[str, Any]]:
    if not BASELINE_FILE.exists():
        return {}
    try:
        with open(BASELINE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@router.post("/vibration-check", response_model=VibrationCheckResponse)
def vibration_check(req: VibrationCheckRequest):
    """Run checkVibrationDrift for a machine using its stored baseline.

    Request body example:
      { "machine_id": "pump-A", "recent_readings": [0.02,0.021,...] }
    """
    baselines = load_stored_baselines()

    baseline = None
    if req.baseline_override:
        # expect keys 'mean' and 'std'
        if 'mean' not in req.baseline_override or 'std' not in req.baseline_override:
            raise HTTPException(status_code=400, detail="baseline_override must include 'mean' and 'std'")
        baseline = {"mean": float(req.baseline_override['mean']), "std": float(req.baseline_override['std']), "n": int(req.baseline_override.get('n', 0))}
    else:
        if req.machine_id in baselines:
            b = baselines[req.machine_id]
            if isinstance(b, dict) and 'mean' in b and 'std' in b:
                baseline = {"mean": float(b['mean']), "std": float(b['std']), "n": int(b.get('n', 0))}

    if baseline is None:
        raise HTTPException(status_code=404, detail=f"Baseline for machine '{req.machine_id}' not found. Provide baseline_override or add to vibration_baselines.json")

    # run the drift check
    try:
        result = checkVibrationDrift(req.recent_readings, baseline)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return VibrationCheckResponse(
        machine_id=req.machine_id,
        drift_score=int(result['drift_score']),
        status=result['status'],
        detected_at=result['detected_at'],
        baseline=baseline,
    )
