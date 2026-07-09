import hashlib
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from app.models.evidence_models import EvidenceEntry, ChainedEvidenceEntry, ChainVerificationResult
from app.services.correlation_service import get_risk_assessment
from app.services.flatline_service import detect_flatlines
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CHAIN_FILE = DATA_DIR / "evidence_chain.json"
COMBINED_CSV = DATA_DIR / "combined_dataset.csv"


def compute_hash(entry_id: int, event_type: str, unit_id: str, payload: Dict, timestamp: datetime, previous_hash: str) -> str:
    payload_text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    raw = f"{entry_id}|{event_type}|{unit_id}|{payload_text}|{timestamp.isoformat()}|{previous_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_chain() -> List[Dict]:
    if not CHAIN_FILE.exists():
        return []
    with CHAIN_FILE.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_chain(chain: List[Dict]) -> None:
    CHAIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CHAIN_FILE.open("w", encoding="utf-8") as fh:
        json.dump(chain, fh, indent=2)


def add_evidence(entry: EvidenceEntry) -> ChainedEvidenceEntry:
    chain = load_chain()
    previous_hash = chain[-1]["entry_hash"] if chain else "0" * 64
    entry_id = len(chain) + 1
    entry_hash = compute_hash(entry_id, entry.event_type, entry.unit_id, entry.payload, entry.timestamp, previous_hash)

    chained = ChainedEvidenceEntry(
        event_type=entry.event_type,
        unit_id=entry.unit_id,
        payload=entry.payload,
        timestamp=entry.timestamp,
        entry_id=entry_id,
        previous_hash=previous_hash,
        entry_hash=entry_hash,
    )
    chain.append(chained.model_dump(mode="json"))
    save_chain(chain)
    return chained


def verify_chain() -> ChainVerificationResult:
    chain = load_chain()
    if not chain:
        return ChainVerificationResult(is_valid=True, total_entries=0, message="No entries in chain")

    for item in chain:
        expected_hash = compute_hash(
            item["entry_id"],
            item["event_type"],
            item["unit_id"],
            item["payload"],
            datetime.fromisoformat(item["timestamp"]),
            item["previous_hash"],
        )
        if expected_hash != item["entry_hash"]:
            return ChainVerificationResult(
                is_valid=False,
                total_entries=len(chain),
                broken_at_entry=item["entry_id"],
                message=f"Hash mismatch at entry {item['entry_id']}",
            )

        prev_hash = chain[item["entry_id"] - 2]["entry_hash"] if item["entry_id"] > 1 else "0" * 64
        if item["previous_hash"] != prev_hash:
            return ChainVerificationResult(
                is_valid=False,
                total_entries=len(chain),
                broken_at_entry=item["entry_id"],
                message=f"Previous-hash mismatch at entry {item['entry_id']}",
            )

    return ChainVerificationResult(is_valid=True, total_entries=len(chain), message="Chain verified successfully")


def log_demo_events(unit_id: str) -> List[ChainedEvidenceEntry]:
    assessment = get_risk_assessment(unit_id)
    df = pd.read_csv(COMBINED_CSV)
    unit_rows = df[df["unit_id"] == unit_id].copy()
    if not unit_rows.empty:
        sample = unit_rows[["sensor_reading_id", "timestamp", "sensor_type", "sensor_value", "unit_id"]].to_dict(orient="records")
        flatline_result = detect_flatlines(sample[:10])
    else:
        flatline_result = []

    events = [
        EvidenceEntry(
            event_type="risk_assessment",
            unit_id=unit_id,
            payload={"assessment": assessment},
            timestamp=datetime.utcnow(),
        ),
        EvidenceEntry(
            event_type="flatline_check",
            unit_id=unit_id,
            payload={"flatline_flags": flatline_result},
            timestamp=datetime.utcnow(),
        ),
    ]
    return [add_evidence(event) for event in events]
