from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.models.alarm_models import AlarmEvent, AlarmFatigueResult
from app.services.correlation_service import get_risk_assessment
from app.services.flatline_service import detect_flatlines
from app.services.guardrail_service import check_guardrail
from app.models.guardrail_models import EngineOutput, PlantState, ZoneState, Permit


SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _severity_rank(severity: str) -> int:
    return SEVERITY_RANK.get((severity or "low").lower(), 0)


def detect_alarm_fatigue(
    events: List[AlarmEvent],
    window_minutes: int = 60,
    fatigue_threshold: int = 5,
) -> AlarmFatigueResult:
    unit_id = ""
    if events:
        unit_id = events[0].unit_id

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    recent_events = [event for event in events if event.timestamp >= cutoff]

    if not recent_events:
        return AlarmFatigueResult(
            unit_id=unit_id,
            alert_count_last_hour=0,
            fatigue_detected=False,
            suppressed_count=0,
            top_priority_alert=None,
            recommendation="No recent alerts detected.",
        )

    if len(recent_events) >= fatigue_threshold:
        top_priority_alert = max(
            recent_events,
            key=lambda event: (_severity_rank(event.severity), event.timestamp),
        )
        suppressed_count = len(recent_events) - 1
        return AlarmFatigueResult(
            unit_id=unit_id,
            alert_count_last_hour=len(recent_events),
            fatigue_detected=True,
            suppressed_count=suppressed_count,
            top_priority_alert=top_priority_alert,
            recommendation=(
                f"Alert fatigue detected: {len(recent_events)} alerts in the last hour. "
                f"Suppressed {suppressed_count} lower-priority alerts and escalated the highest-severity event."
            ),
        )

    top_priority_alert = max(
        recent_events,
        key=lambda event: (_severity_rank(event.severity), event.timestamp),
    )
    return AlarmFatigueResult(
        unit_id=unit_id,
        alert_count_last_hour=len(recent_events),
        fatigue_detected=False,
        suppressed_count=0,
        top_priority_alert=top_priority_alert,
        recommendation=(
            f"{len(recent_events)} alerts in the last hour; no fatigue suppression needed."
        ),
    )


def generate_demo_alerts(unit_id: str) -> List[AlarmEvent]:
    alerts: List[AlarmEvent] = []

    try:
        assessment = get_risk_assessment(unit_id)
        alerts.append(
            AlarmEvent(
                unit_id=unit_id,
                source="correlation",
                severity="high" if assessment.get("risk_score", 0) >= 70 else "medium",
                message=assessment.get("reasoning") or "Correlation engine alert",
                timestamp=datetime.now(timezone.utc),
            )
        )
    except Exception:
        pass

    try:
        flatline_readings = [
            {
                "sensor_reading_id": "demo-1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sensor_type": "torque",
                "sensor_value": 0.0,
                "unit_id": unit_id,
            }
        ]
        flatline_flags = detect_flatlines(flatline_readings)
        if flatline_flags:
            alerts.append(
                AlarmEvent(
                    unit_id=unit_id,
                    source="flatline",
                    severity="critical" if flatline_flags[0].get("severity") == "critical" else "high",
                    message="Flatline watchdog detected a sensor stall",
                    timestamp=datetime.now(timezone.utc) - timedelta(minutes=5),
                )
            )
    except Exception:
        pass

    try:
        plant_state = PlantState(
            zones=[
                ZoneState(
                    zone_id=f"{unit_id}-zone-1",
                    gas_ppm=600.0,
                    active_permits=[Permit(permit_type="hot-work")],
                    supervisors_present=1,
                )
            ]
        )
        engine_output = EngineOutput(
            risk_score=25,
            flagged_zone=f"{unit_id}-zone-1",
            reasoning="Guardrail engine baseline",
            contributing_factors=["baseline"],
        )
        result = check_guardrail(plant_state, engine_output)
        if result.overridden:
            alerts.append(
                AlarmEvent(
                    unit_id=unit_id,
                    source="guardrail",
                    severity="critical",
                    message=result.reasoning,
                    timestamp=datetime.now(timezone.utc) - timedelta(minutes=2),
                )
            )
    except Exception:
        pass

    if len(alerts) < 3:
        synthetic_times = [
            datetime.now(timezone.utc) - timedelta(minutes=20),
            datetime.now(timezone.utc) - timedelta(minutes=10),
            datetime.now(timezone.utc) - timedelta(minutes=1),
        ]
        for index, stamp in enumerate(synthetic_times[: 3 - len(alerts)]):
            alerts.append(
                AlarmEvent(
                    unit_id=unit_id,
                    source="synthetic",
                    severity=["low", "medium", "high"][index],
                    message=f"Synthetic fallback alert {index + 1}",
                    timestamp=stamp,
                )
            )

    return alerts
