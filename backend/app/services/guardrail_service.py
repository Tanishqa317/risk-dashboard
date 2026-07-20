from typing import Optional

from app.models.guardrail_models import EngineOutput, GuardrailResult, PlantState


def _summarize_clear_state(plant_state: PlantState) -> str:
    """Build guardrail-specific reasoning when no override rule fires â€”
    never borrow engine_output.reasoning, which belongs to the upstream
    risk-assessment service and describes a different analysis entirely."""
    zones = plant_state.zones or []
    if not zones:
        return "Guardrail check complete: no zone data available to evaluate."

    zone_ids = [z.zone_id or "unknown" for z in zones]
    max_gas = max((float(z.gas_ppm or 0.0) for z in zones), default=0.0)
    total_permits = sum(len(z.active_permits or []) for z in zones)
    min_supervisors = min((int(z.supervisors_present or 0) for z in zones), default=0)

    return (
        f"Guardrail check complete across {len(zone_ids)} zone(s) "
        f"({', '.join(zone_ids)}): peak gas reading {max_gas:.0f} ppm, "
        f"{total_permits} active permit(s) tracked, minimum supervisor "
        f"coverage {min_supervisors}. No hot-work/gas-threshold or "
        f"confined-space/supervisor rule violations detected."
    )


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

    # No rule fired â€” report the guardrail's own clear-state summary, never
    # engine_output.reasoning (that belongs to a different upstream service
    # and was previously leaking Core Vitals' narrative into this panel).
    return GuardrailResult(
        risk_score=engine_output.risk_score,
        flagged_zone=engine_output.flagged_zone,
        reasoning=_summarize_clear_state(plant_state),
        contributing_factors=list(engine_output.contributing_factors or []),
        overridden=False,
        override_reason=None,
    )