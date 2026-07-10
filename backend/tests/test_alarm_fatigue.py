import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.alarm_models import AlarmEvent
from app.services.alarm_fatigue_service import detect_alarm_fatigue


def test_alarm_fatigue_below_threshold():
    now = datetime.now(timezone.utc)
    events = [
        AlarmEvent(
            unit_id="unit-1",
            source="correlation",
            severity="medium",
            message="Medium alert",
            timestamp=now - timedelta(minutes=10),
        ),
        AlarmEvent(
            unit_id="unit-1",
            source="flatline",
            severity="low",
            message="Low alert",
            timestamp=now - timedelta(minutes=20),
        ),
    ]

    result = detect_alarm_fatigue(events, window_minutes=60, fatigue_threshold=5)

    assert result.fatigue_detected is False
    assert result.suppressed_count == 0
    assert result.alert_count_last_hour == 2
    assert result.top_priority_alert is not None


def test_alarm_fatigue_above_threshold_uses_top_priority_and_suppresses_rest():
    now = datetime.now(timezone.utc)
    events = [
        AlarmEvent(
            unit_id="unit-1",
            source="correlation",
            severity="medium",
            message="Medium alert",
            timestamp=now - timedelta(minutes=5),
        ),
        AlarmEvent(
            unit_id="unit-1",
            source="guardrail",
            severity="critical",
            message="Critical alert",
            timestamp=now - timedelta(minutes=4),
        ),
        AlarmEvent(
            unit_id="unit-1",
            source="flatline",
            severity="high",
            message="High alert",
            timestamp=now - timedelta(minutes=3),
        ),
        AlarmEvent(
            unit_id="unit-1",
            source="synthetic",
            severity="low",
            message="Low alert",
            timestamp=now - timedelta(minutes=2),
        ),
        AlarmEvent(
            unit_id="unit-1",
            source="synthetic",
            severity="medium",
            message="Medium alert",
            timestamp=now - timedelta(minutes=1),
        ),
    ]

    result = detect_alarm_fatigue(events, window_minutes=60, fatigue_threshold=5)

    assert result.fatigue_detected is True
    assert result.suppressed_count == 4
    assert result.top_priority_alert is not None
    assert result.top_priority_alert.severity == "critical"
    assert result.top_priority_alert.source == "guardrail"
