from typing import List
from fastapi import APIRouter
from app.models.evidence_models import EvidenceEntry, ChainedEvidenceEntry, ChainVerificationResult
from app.services.evidence_chain_service import add_evidence, load_chain, verify_chain, log_demo_events

router = APIRouter()


@router.post("/evidence", response_model=ChainedEvidenceEntry)
def create_evidence(entry: EvidenceEntry):
    return add_evidence(entry)


@router.get("/evidence/chain", response_model=List[ChainedEvidenceEntry])
def get_evidence_chain():
    return [ChainedEvidenceEntry(**item) for item in load_chain()]


@router.get("/evidence/verify", response_model=ChainVerificationResult)
def verify_evidence_chain():
    return verify_chain()


@router.get("/evidence/demo/{unit_id}", response_model=List[ChainedEvidenceEntry])
def demo_evidence(unit_id: str):
    return log_demo_events(unit_id)


@router.post("/evidence/tamper-test")
def tamper_test(entry_id: int, fake_payload: dict):
    # Demo endpoint only: deliberately overwrites an entry without recomputing hashes.
    # This would never exist in a real production system.
    chain = load_chain()
    for item in chain:
        if item["entry_id"] == entry_id:
            item["payload"] = fake_payload
            break
    with open("data/evidence_chain.json", "w", encoding="utf-8") as fh:
        import json

        json.dump(chain, fh, indent=2)
    return {"message": "Tampering applied; call /api/evidence/verify to inspect the break"}
