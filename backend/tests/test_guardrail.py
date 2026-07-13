import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.guardrail_models import EngineOutput, Permit, PlantState, ZoneState
from app.services.guardrail_service import check_guardrail


def test_guardrail_overrides_for_hot_work_and_high_gas():
    plant_state = PlantState(
        zones=[
            ZoneState(
                zone_id="zone-1",
                gas_ppm=600,
                active_permits=[Permit(permit_type="hot-work")],
                supervisors_present=2,
            )
        ]
    )
    engine_output = EngineOutput(
        risk_score=20,
        flagged_zone="zone-1",
        reasoning="Original engine output",
        contributing_factors=["baseline"],
    )

    result = check_guardrail(plant_state, engine_output)

    assert result.overridden is True
    assert result.risk_score == 100
    assert result.flagged_zone == "zone-1"
    assert "hot work" in result.reasoning.lower()
    assert result.override_reason is not None


def test_guardrail_overrides_for_confined_space_without_second_supervisor():
    plant_state = PlantState(
        zones=[
            ZoneState(
                zone_id="zone-2",
                gas_ppm=100,
                active_permits=[Permit(permit_type="confined-space")],
                supervisors_present=1,
            )
        ]
    )
    engine_output = EngineOutput(
        risk_score=15,
        flagged_zone="zone-2",
        reasoning="Original engine output",
        contributing_factors=["baseline"],
    )

    result = check_guardrail(plant_state, engine_output)

    assert result.overridden is True
    assert result.risk_score == 100
    assert result.flagged_zone == "zone-2"
    assert "second supervisor" in result.reasoning.lower()
    assert result.override_reason is not None


def test_guardrail_passthrough_when_no_rule_is_triggered():
    plant_state = PlantState(
        zones=[
            ZoneState(
                zone_id="zone-3",
                gas_ppm=100,
                active_permits=[Permit(permit_type="general")],
                supervisors_present=2,
            )
        ]
    )
    engine_output = EngineOutput(
        risk_score=5,
        flagged_zone="zone-3",
        reasoning="Original engine output",
        contributing_factors=["baseline"],
    )

    result = check_guardrail(plant_state, engine_output)

    assert result.overridden is False
    assert result.risk_score == engine_output.risk_score
    assert result.flagged_zone == engine_output.flagged_zone
    assert result.reasoning == engine_output.reasoning
    assert result.contributing_factors == engine_output.contributing_factors
    assert result.override_reason is None
