import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.rag_service import build_index, retrieve_relevant, analyze_patterns


def test_rag_build_index_and_retrieve():
    """Test that build_index loads documents and retrieve_relevant returns relevant results."""
    build_index()

    query = "hot work permit gas safety"
    results = retrieve_relevant(query, top_k=3)

    assert len(results) > 0, "Should retrieve at least one result"
    for result in results:
        assert "text" in result
        assert "similarity" in result
        assert "source" in result
        assert result["similarity"] <= 1.0


def test_retrieve_relevant_ordering():
    """Test that retrieve_relevant returns results ordered by similarity score."""
    build_index()

    query = "confined space entry supervisor safety"
    results = retrieve_relevant(query, top_k=5)

    if len(results) > 1:
        for i in range(len(results) - 1):
            assert results[i]["similarity"] >= results[i + 1]["similarity"], \
                f"Results should be ordered by similarity descending"


@patch("app.services.rag_service.genai.Client")
def test_analyze_patterns_with_mocked_gemini(mock_client_class):
    """Test that analyze_patterns correctly passes retrieved chunks to Gemini."""
    build_index()

    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "recurring_patterns": ["Permit expiration", "Gas monitoring gaps"],
        "prevention_priorities": ["Regular permit audits", "Enhanced gas checks"],
        "most_relevant_precedent": "Near miss: unauthorized welding with expired permit"
    })

    mock_instance = MagicMock()
    mock_instance.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_instance

    with patch("app.services.rag_service.GEMINI_AVAILABLE", True):
        with patch("app.services.rag_service.GEMINI_API_KEY", "test-key"):
            # Call analyze_patterns directly with unit-1; the service internally reads 
            # the current plant state/recent assessment context rather than needing an external patch
            result = analyze_patterns("unit-1")

    assert result["unit_id"] == "unit-1"
    assert len(result["recurring_patterns"]) > 0
    assert len(result["prevention_priorities"]) > 0
    assert result["most_relevant_precedent"] != ""
    assert len(result["source_documents"]) > 0

    call_args = mock_instance.models.generate_content.call_args
    assert call_args is not None
    contents = call_args.kwargs.get("contents") or call_args[1]["contents"]
    
    # Extract the string passed to the prompt block
    if isinstance(contents, list) and len(contents) > 0:
        if isinstance(contents[0], dict) and "parts" in contents[0]:
            user_text = contents[0]["parts"][0]["text"]
        else:
            user_text = str(contents)
    else:
        user_text = str(contents)
        
    assert "unit-1" in user_text
