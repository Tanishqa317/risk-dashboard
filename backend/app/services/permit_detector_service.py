from collections import defaultdict
from datetime import datetime
from typing import List, Optional

from app.models.permit_models import Permit, PermitGamingResult


def _to_minutes(value: datetime | str | None) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.timestamp() / 60.0
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed.timestamp() / 60.0


def detect_permit_gaming(permits: List[Permit]) -> PermitGamingResult:
    permits = list(permits or [])
    grouped: dict[str, list[Permit]] = defaultdict(list)
    for permit in permits:
        grouped[str(permit.zone_id or "")].append(permit)

    for zone_id, zone_permits in grouped.items():
        for i in range(len(zone_permits)):
            for j in range(i + 1, len(zone_permits)):
                first = zone_permits[i]
                second = zone_permits[j]

                first_start = _to_minutes(first.start_time)
                first_end = _to_minutes(first.end_time)
                second_start = _to_minutes(second.start_time)
                second_end = _to_minutes(second.end_time)

                if first_start is None or first_end is None or second_start is None or second_end is None:
                    continue

                overlap_start = max(first_start, second_start)
                overlap_end = min(first_end, second_end)
                overlap_minutes = overlap_end - overlap_start

                within_thirty_minutes = (
                    abs(first_start - second_start) <= 30
                    or abs(first_end - second_end) <= 30
                )

                one_confined_one_hot = (
                    ("confined" in str(first.permit_type).lower() and "hot" in str(second.permit_type).lower())
                    or ("confined" in str(second.permit_type).lower() and "hot" in str(first.permit_type).lower())
                )

                if one_confined_one_hot and (overlap_minutes >= 0 or within_thirty_minutes):
                    return PermitGamingResult(
                        suspicious=True,
                        reason=(
                            f"Suspicious permit combination detected in {zone_id}: "
                            f"{first.permit_type} and {second.permit_type} overlap or occur within 30 minutes in the same zone."
                        ),
                        flagged_permits=[first.permit_id, second.permit_id],
                    )

    return PermitGamingResult(
        suspicious=False,
        reason="No suspicious permit combination detected.",
        flagged_permits=[],
    )
