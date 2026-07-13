import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.compliance_service import audit_unit_compliance, _gather_current_state


def test_gather_current_state():
    """Test that _gather_current_state correctly gathers operational data."""
    state = _gather_current_state("unit-1")

    assert state["unit_id"] == "unit-1"
    assert "permits" in state
    assert "staffing_level" in state
    assert "guardrail_violations" in state
    assert "recent_alarms" in state
    assert "timestamp" in state


def test_gather_current_state_structure():
    """Test that gathered state has expected structure."""
    state = _gather_current_state("unit-1")

    # Verify state has all required fields
    assert isinstance(state["permits"], list)
    assert isinstance(state["staffing_level"], str)
    assert isinstance(state["guardrail_violations"], list)
    assert isinstance(state["recent_alarms"], int)

    # If permits exist, check structure
    if state["permits"]:
        for permit in state["permits"]:
            assert "permit_id" in permit
            assert "zone_id" in permit
            assert "status" in permit
            assert "type" in permit


@patch("app.services.compliance_service.genai.Client")
def test_audit_unit_compliance_with_mocked_gemini(mock_client_class):
    """Test that audit_unit_compliance correctly passes gathered state to Gemini."""
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "compliance_status": "minor_deviation",
        "deviations_found": [
            "Permit expiration not checked",
            "Staffing level below minimum for confined space entry"
        ],
        "corrective_actions": [
            "Implement daily permit status verification",
            "Increase staffing on night shift"
        ],
        "regulatory_references": [
            "Confined Space Entry Regulations - Second Supervisor Requirement",
            "Work Permit Procedure - Section 2.3"
        ]
    })

    mock_instance = MagicMock()
    mock_instance.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_instance

    with patch("app.services.compliance_service.GEMINI_AVAILABLE", True):
        with patch("app.services.compliance_service.GEMINI_API_KEY", "test-key"):
            result = audit_unit_compliance("unit-1")

    # Verify result structure
    assert result["unit_id"] == "unit-1"
    assert result["compliance_status"] in ["compliant", "minor_deviation", "major_deviation"]
    assert isinstance(result["deviations_found"], list)
    assert isinstance(result["corrective_actions"], list)
    assert isinstance(result["regulatory_references"], list)

    # Verify Gemini was called
    assert mock_instance.models.generate_content.called

    # Verify that the prompt includes the current state
    call_args = mock_instance.models.generate_content.call_args
    assert call_args is not None
    contents = call_args.kwargs.get("contents") or call_args[1]["contents"]

    if isinstance(contents, list) and len(contents) > 0:
        if isinstance(contents[0], dict) and "parts" in contents[0]:
            user_text = contents[0]["parts"][0]["text"]
        else:
            user_text = str(contents)
    else:
        user_text = str(contents)

    # Check that the prompt includes unit-specific information
    assert "unit-1" in user_text
    assert "permits" in user_text.lower() or "operational" in user_text.lower()


@patch("app.services.compliance_service.genai.Client")
def test_audit_unit_compliance_integrates_state_and_guidance(mock_client_class):
    """Test that the compliance audit integrates both current state and regulatory guidance."""
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "compliance_status": "compliant",
        "deviations_found": [],
        "corrective_actions": [],
        "regulatory_references": []
    })

    mock_instance = MagicMock()
    mock_instance.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_instance

    with patch("app.services.compliance_service.GEMINI_AVAILABLE", True):
        with patch("app.services.compliance_service.GEMINI_API_KEY", "test-key"):
            with patch("app.services.compliance_service.retrieve_relevant") as mock_rag:
                mock_rag.return_value = [
                    {
                        "text": "Confined space entry requires a second supervisor",
                        "similarity": 0.95,
                        "source": "guidance_confined_space_entry.txt"
                    }
                ]
                result = audit_unit_compliance("unit-1")

    assert result["compliance_status"] == "compliant"
    assert mock_rag.called
    
    # Verify RAG was called with compliance-related query
    rag_call_args = mock_rag.call_args
    if rag_call_args:
        query = rag_call_args[0][0] if rag_call_args[0] else ""
        assert "compliance" in query.lower() or "audit" in query.lower() or "permit" in query.lower()
