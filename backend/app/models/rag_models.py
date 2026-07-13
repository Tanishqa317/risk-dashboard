from typing import List
from pydantic import BaseModel, Field


class PatternAnalysisResult(BaseModel):
    unit_id: str = Field(default="")
    recurring_patterns: List[str] = Field(default_factory=list)
    prevention_priorities: List[str] = Field(default_factory=list)
    most_relevant_precedent: str = Field(default="")
    source_documents: List[str] = Field(default_factory=list)
