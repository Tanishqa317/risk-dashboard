from typing import Any, Dict

from fastapi import APIRouter

from app.services.compliance_service import audit_unit_compliance

router = APIRouter(tags=["Compliance"])


@router.get("/compliance-audit/{unit_id}", response_model=Dict[str, Any])
def get_compliance_audit(unit_id: str) -> Dict[str, Any]:
    result = audit_unit_compliance(unit_id)
    return result
