import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import json
import datetime
import tempfile
import csv

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.correlation_service import build_context, call_gemini_for_risk_score, get_risk_assessment


def create_temp_csv(unit_id="unit-1"):
    """Create a temporary CSV with sample combined dataset."""
    fd, path = tempfile.mkstemp(suffix=".csv", text=True)
    
    rows = [
        {
            "sensor_reading_id": "r1",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "sensor_type": "torque",
            "sensor_value": 100.5,
            "unit_id": unit_id,
            "zone_id": f"{unit_id}-zone-1",
            "permit_id": "PERMIT-000001",
            "permit_status": "active",
            "shift_id": "shift_day",
            "shift_staffing": "normal",
            "machine_failure": 0,
            "failure_type": "",
        },
        {
            "sensor_reading_id": "r2",
            "timestamp": (datetime.datetime.utcnow() + datetime.timedelta(minutes=10)).isoformat(),
            "sensor_type": "torque",
            "sensor_value": 101.2,
            "unit_id": unit_id,
            "zone_id": f"{unit_id}-zone-1",
            "permit_id": "PERMIT-000001",
            "permit_status": "active",
            "shift_id": "shift_day",
            "shift_staffing": "normal",
            "machine_failure": 0,
            "failure_type": "",
        },
        {
            "sensor_reading_id": "r3",
            "timestamp": (datetime.datetime.utcnow() + datetime.timedelta(minutes=20)).isoformat(),
            "sensor_type": "air_temperature",
            "sensor_value": 25.5,
            "unit_id": unit_id,
            "zone_id": f"{unit_id}-zone-2",
            "permit_id": "PERMIT-000002",
            "permit_status": "expired",
            "shift_id": "shift_day",
            "shift_staffing": "understaffed",
            "machine_failure": 0,
            "failure_type": "",
        },
    ]
    
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    return path


def test_build_context():
    """Test that build_context correctly extracts data for a unit."""
    csv_path = create_temp_csv("unit-1")
    
    with patch("app.services.correlation_service.COMBINED_CSV", csv_path):
        context = build_context("unit-1")
    
    assert context["unit_id"] == "unit-1"
    assert context["active_permits"] == 2
    assert context["expired_permits"] == 1
    assert "torque" in context["recent_readings"]
    assert "air_temperature" in context["recent_readings"]
    assert len(context["recent_readings"]["torque"]) == 2


def test_build_context_nonexistent_unit():
    """Test that build_context returns reasonable output for missing unit."""
    csv_path = create_temp_csv("unit-1")
    
    with patch("app.services.correlation_service.COMBINED_CSV", csv_path):
        context = build_context("unit-999")
    
    assert context["unit_id"] == "unit-999"
    assert context["error"] is not None


@patch("app.services.correlation_service.genai.Client")
def test_call_gemini_for_risk_score_mocked(mock_client_class):
    """Test that call_gemini_for_risk_score correctly processes mocked Gemini response."""
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "risk_score": 75,
        "risk_level": "high",
        "primary_concern": "Expired permit during operation",
        "reasoning": "Unit has an expired permit while understaffed."
    })
    
    mock_instance = MagicMock()
    mock_instance.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_instance

    context = {
        "unit_id": "unit-1",
        "active_permits": 2,
        "expired_permits": 1,
        "recent_readings": {"torque": [{"value": 100, "timestamp": "2026-06-01T10:00:00"}]},
        "shift_staffing": "understaffed"
    }

    with patch("app.services.correlation_service.GEMINI_AVAILABLE", True):
        with patch("app.services.correlation_service.GEMINI_API_KEY", "test-key"):
            result = call_gemini_for_risk_score(context)

    assert result["risk_score"] == 75
    assert result["risk_level"] == "high"
    assert "Expired permit" in result["primary_concern"]


def test_get_risk_assessment_integration():
    """Test full risk assessment pipeline (with mocked Gemini)."""
    csv_path = create_temp_csv("unit-1")
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "risk_score": 65,
        "risk_level": "medium",
        "primary_concern": "Mixed signals",
        "reasoning": "Some concerns detected."
    })
    
    with patch("app.services.correlation_service.COMBINED_CSV", csv_path):
        with patch("app.services.correlation_service.genai.Client") as mock_client_class:
            mock_instance = MagicMock()
            mock_instance.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_instance
            
            with patch("app.services.correlation_service.GEMINI_AVAILABLE", True):
                with patch("app.services.correlation_service.GEMINI_API_KEY", "test-key"):
                    result = get_risk_assessment("unit-1")

    assert result["unit_id"] == "unit-1"
    assert result["risk_score"] == 65
    assert result["risk_level"] == "medium"
