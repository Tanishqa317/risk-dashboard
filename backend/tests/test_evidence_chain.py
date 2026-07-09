import json
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.evidence_models import EvidenceEntry
from app.services.evidence_chain_service import add_evidence, verify_chain, CHAIN_FILE


def setup_function():
    if CHAIN_FILE.exists():
        CHAIN_FILE.unlink()


def test_add_three_entries_and_verify_chain():
    for i in range(3):
        entry = EvidenceEntry(
            event_type="test",
            unit_id="unit-1",
            payload={"value": i},
            timestamp=datetime.utcnow(),
        )
        add_evidence(entry)

    result = verify_chain()
    assert result.is_valid is True
    assert result.total_entries == 3


def test_tampering_breaks_chain():
    for i in range(3):
        entry = EvidenceEntry(
            event_type="test",
            unit_id="unit-1",
            payload={"value": i},
            timestamp=datetime.utcnow(),
        )
        add_evidence(entry)

    chain = json.loads(CHAIN_FILE.read_text(encoding="utf-8"))
    chain[1]["payload"] = {"tampered": True}
    CHAIN_FILE.write_text(json.dumps(chain), encoding="utf-8")

    result = verify_chain()
    assert result.is_valid is False
    assert result.broken_at_entry == 2
