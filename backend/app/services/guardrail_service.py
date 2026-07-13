from typing import Optional

from app.models.guardrail_models import EngineOutput, GuardrailResult, PlantState


def check_guardrail(plant_state: PlantState, engine_output: EngineOutput) -> GuardrailResult:
    zones = plant_state.zones or []
    permits = []
    supervisors_present = 0

    for zone in zones:
        zone_id = zone.zone_id or ""
        gas_ppm = float(zone.gas_ppm or 0.0)
        hot_work_permit_active = any(
            (permit.permit_type or "").lower().replace("-", " ").replace("_", " ").strip() == "hot work"
            for permit in zone.active_permits or []
        )

        if gas_ppm > 500 and hot_work_permit_active:
            return GuardrailResult(
                risk_score=100,
                flagged_zone=zone_id,
                reasoning=(
                    f"Guardrail rule fired: block hot work when gas_ppm exceeds 500 in {zone_id}. "
                    "This overrides the AI decision."
                ),
                contributing_factors=["hot-work permit active", "gas_ppm > 500"],
                overridden=True,
                override_reason="hot-work permit active with gas_ppm > 500",
            )

        permits.extend(zone.active_permits or [])
        supervisors_present = max(supervisors_present, int(zone.supervisors_present or 0))

    confined_space_permit_active = any(
        (permit.permit_type or "").lower().replace("-", " ").replace("_", " ").strip() == "confined space"
        for permit in permits
    )

    if confined_space_permit_active and supervisors_present < 2:
        zone_id = zones[0].zone_id if zones else "unknown"
        return GuardrailResult(
            risk_score=100,
            flagged_zone=zone_id,
            reasoning=(
                "Guardrail rule fired: confined space entry requires a second supervisor. "
                "This overrides the AI decision."
            ),
            contributing_factors=["confined-space permit active", "missing second supervisor"],
            overridden=True,
            override_reason="confined-space permit active with fewer than 2 supervisors",
        )

    return GuardrailResult(
        risk_score=engine_output.risk_score,
        flagged_zone=engine_output.flagged_zone,
        reasoning=engine_output.reasoning or "No guardrail violation detected.",
        contributing_factors=list(engine_output.contributing_factors or []),
        overridden=False,
        override_reason=None,
    )
