from typing import Any, Dict, List

from fastapi import APIRouter

from app.models.alarm_models import AlarmEvent, AlarmFatigueResult
from app.services.alarm_fatigue_service import detect_alarm_fatigue, generate_demo_alerts

router = APIRouter(tags=["Alarm Fatigue"])


@router.post("/alarm-fatigue", response_model=AlarmFatigueResult)
def alarm_fatigue_check(payload: Dict[str, Any]) -> AlarmFatigueResult:
    unit_id = str(payload.get("unit_id", ""))
    events = [AlarmEvent(**event) for event in payload.get("events", [])]
    return detect_alarm_fatigue(events, window_minutes=60, fatigue_threshold=5)


@router.get("/alarm-fatigue/demo/{unit_id}", response_model=Dict[str, Any])
def alarm_fatigue_demo(unit_id: str) -> Dict[str, Any]:
    events = generate_demo_alerts(unit_id)
    result = detect_alarm_fatigue(events, window_minutes=60, fatigue_threshold=5)
    return {
        "unit_id": unit_id,
        "events": [event.model_dump() for event in events],
        "result": result.model_dump(),
    }
