import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.cost_service import categorize_concern, calculate_cost


def test_categorize_concern_gas_leak():
    assert categorize_concern("gas leak detected in line 3") == "gas_leak"


def test_categorize_concern_fire():
    assert categorize_concern("There is a fire risk") == "fire"


def test_calculate_cost_linear_scaling():
    result = calculate_cost(30, "minor failure")
    assert result["category_used"] == "equipment_failure" or result["category_used"] == "default"
    expected = 300000 * 0.3
    assert result["estimated_cost_usd"] == round(expected, 2)


def test_calculate_cost_nonlinear_scaling():
    low_score_cost = calculate_cost(70, "fire hazard")
    high_score_cost = calculate_cost(90, "fire hazard")
    assert high_score_cost["estimated_cost_usd"] > low_score_cost["estimated_cost_usd"]

    linear_90 = 2000000 * 0.9
    nonlinear_90 = high_score_cost["estimated_cost_usd"]
    assert nonlinear_90 > round(linear_90, 2)
