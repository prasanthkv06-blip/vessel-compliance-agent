"""Casualty History Service — Phase 2.

Converts raw Equasis casualty dicts into a structured CasualtyHistory model.
"""
from ..models.report import CasualtyHistory, CasualtyEvent
from ..models.vessel import RiskLevel

# Casualty types that indicate HIGH risk
_HIGH_RISK_TYPES = {
    "very serious", "constructive total loss", "ctl", "sinking", "foundered",
    "explosion", "fire", "grounding", "capsize",
}

_MEDIUM_RISK_TYPES = {
    "serious", "collision", "contact", "flooding", "structural failure",
    "machinery damage", "pollution",
}


def _severity_of(ctype: str) -> str:
    t = ctype.lower()
    if any(k in t for k in _HIGH_RISK_TYPES):
        return "high"
    if any(k in t for k in _MEDIUM_RISK_TYPES):
        return "medium"
    return "low"


def build_casualty_history(raw: list[dict]) -> CasualtyHistory:
    """Convert raw Equasis casualty records to CasualtyHistory."""
    if not raw:
        return CasualtyHistory()

    events: list[CasualtyEvent] = []
    for r in raw:
        events.append(CasualtyEvent(
            date=r.get("date") or None,
            casualty_type=r.get("type") or "Unknown",
            location=r.get("location") or None,
            description=r.get("description") or None,
        ))

    # Overall risk
    if any(_severity_of(e.casualty_type) == "high" for e in events):
        risk = RiskLevel.HIGH
    elif any(_severity_of(e.casualty_type) == "medium" for e in events):
        risk = RiskLevel.MEDIUM
    elif events:
        risk = RiskLevel.LOW
    else:
        risk = RiskLevel.NONE

    return CasualtyHistory(
        events=events,
        total_count=len(events),
        risk_level=risk,
    )
