import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.permit_models import Permit
from app.services.permit_detector_service import detect_permit_gaming


def test_detect_permit_gaming_overlapping_confined_and_hot_work():
    permits = [
        Permit(
            permit_id="p1",
            zone_id="zone-a",
            permit_type="confined-space",
            start_time=datetime(2026, 1, 1, 9, 0),
            end_time=datetime(2026, 1, 1, 10, 0),
        ),
        Permit(
            permit_id="p2",
            zone_id="zone-a",
            permit_type="hot-work",
            start_time=datetime(2026, 1, 1, 9, 30),
            end_time=datetime(2026, 1, 1, 10, 30),
        ),
    ]

    result = detect_permit_gaming(permits)

    assert result.suspicious is True
    assert result.flagged_permits == ["p1", "p2"]


def test_detect_permit_gaming_within_thirty_minutes_window():
    permits = [
        Permit(
            permit_id="p1",
            zone_id="zone-a",
            permit_type="confined-space",
            start_time=datetime(2026, 1, 1, 9, 0),
            end_time=datetime(2026, 1, 1, 9, 30),
        ),
        Permit(
            permit_id="p2",
            zone_id="zone-a",
            permit_type="hot-work",
            start_time=datetime(2026, 1, 1, 9, 20),
            end_time=datetime(2026, 1, 1, 10, 0),
        ),
    ]

    result = detect_permit_gaming(permits)

    assert result.suspicious is True


def test_detect_permit_gaming_two_hours_apart_is_not_suspicious():
    permits = [
        Permit(
            permit_id="p1",
            zone_id="zone-a",
            permit_type="confined-space",
            start_time=datetime(2026, 1, 1, 9, 0),
            end_time=datetime(2026, 1, 1, 10, 0),
        ),
        Permit(
            permit_id="p2",
            zone_id="zone-a",
            permit_type="hot-work",
            start_time=datetime(2026, 1, 1, 11, 0),
            end_time=datetime(2026, 1, 1, 12, 0),
        ),
    ]

    result = detect_permit_gaming(permits)

    assert result.suspicious is False


def test_detect_permit_gaming_different_zones_is_not_suspicious():
    permits = [
        Permit(
            permit_id="p1",
            zone_id="zone-a",
            permit_type="confined-space",
            start_time=datetime(2026, 1, 1, 9, 0),
            end_time=datetime(2026, 1, 1, 10, 0),
        ),
        Permit(
            permit_id="p2",
            zone_id="zone-b",
            permit_type="hot-work",
            start_time=datetime(2026, 1, 1, 9, 30),
            end_time=datetime(2026, 1, 1, 10, 30),
        ),
    ]

    result = detect_permit_gaming(permits)

    assert result.suspicious is False
