from pydantic import BaseModel
from typing import Optional
from .vessel import SanctionStatus

class SanctionHit(BaseModel):
    entity_name: str
    list_name: str  # "OFAC SDN", "EU Consolidated", "UK Sanctions"
    program: str
    match_score: float  # 0-100, fuzzy match confidence
    matched_name: str
    details: Optional[str] = None

class SanctionRiskSummary(BaseModel):
    vessel_sanctioned: bool = False
    cargo_sanctioned: bool = False
    trade_sanctioned: bool = False
    ownership_sanctioned: bool = False
    flag_sanctioned: bool = False
    hits: list[SanctionHit] = []
    summary_text: str = "The vessel has not been listed as sanctioned"
