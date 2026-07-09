from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel


class EvidenceEntry(BaseModel):
    event_type: str
    unit_id: str
    payload: Dict
    timestamp: datetime


class ChainedEvidenceEntry(EvidenceEntry):
    entry_id: int
    previous_hash: str
    entry_hash: str


class ChainVerificationResult(BaseModel):
    is_valid: bool
    total_entries: int
    broken_at_entry: Optional[int] = None
    message: str
