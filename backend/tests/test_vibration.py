import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.vibration_service import (
    calculate_deviation,
    generate_baseline_signature,
    generate_current_signature,
    get_vibration_analysis,
)


def test_generate_baseline_signature_returns_expected_length_and_is_deterministic():
    baseline_a = generate_baseline_signature("pump-7", length=120)
    baseline_b = generate_baseline_signature("pump-7", length=120)
    baseline_c = generate_baseline_signature("pump-8", length=120)

    assert len(baseline_a) == 120
    assert baseline_a == baseline_b
    assert baseline_a != baseline_c


def test_calculate_deviation_identical_signatures_are_healthy():
    baseline = generate_baseline_signature("unit-1", length=80)
    result = calculate_deviation(baseline, baseline)

    assert result["deviation_score"] == pytest.approx(0.0, abs=1e-9)
    assert result["status"] == "healthy"
    assert result["time_to_failure_weeks"] is None


def test_calculate_deviation_with_distinct_signatures_is_critical():
    baseline = generate_baseline_signature("unit-2", length=80)
    current = [value * 3.0 for value in baseline]
    result = calculate_deviation(baseline, current)

    assert result["deviation_score"] > 60
    assert result["status"] == "critical"
    assert result["time_to_failure_weeks"] is not None


def test_get_vibration_analysis_returns_all_required_fields_with_correct_types():
    analysis = get_vibration_analysis("fan-3")

    assert analysis["unit_id"] == "fan-3"
    assert isinstance(analysis["baseline_signature"], list)
    assert isinstance(analysis["current_signature"], list)
    assert isinstance(analysis["deviation_score"], float)
    assert isinstance(analysis["status"], str)
    assert isinstance(analysis["explanation"], str)
    assert isinstance(analysis["trend_last_30_days"], list)
    assert len(analysis["trend_last_30_days"]) == 30
    assert analysis["trend_last_30_days"][-1] >= analysis["trend_last_30_days"][0]
