"""Ownership Velocity & Anomaly Detection — Phase 1 & 2.

Analyses:
  - Number of ownership/management changes in the last 3 years
  - Flag change count and flag-hopping detection
  - Vessel name change count
  - Combined risk level + human-readable risk notes
"""
from datetime import date, timedelta
from typing import Optional

from ..models.report import OwnershipVelocity, SisterVesselRisk, SisterVessel
from ..models.ownership import OwnershipChain
from ..models.vessel import RiskLevel

_THREE_YEARS = timedelta(days=3 * 365)
_ONE_YEAR    = timedelta(days=365)


def _parse_iso(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        from datetime import datetime
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def analyze_ownership_velocity(
    ownership: OwnershipChain,
    flag_history: list[dict],          # [{flag, date}, ...]
    name_history: list[dict],          # [{name, date}, ...]
) -> OwnershipVelocity:
    """
    Detect rapid ownership changes, flag hopping, and name change anomalies.
    """
    cutoff = date.today() - _THREE_YEARS
    risk_notes: list[str] = []

    # ── Ownership changes in last 3 years ──────────────────────────────────
    changes_3y = 0
    for rec in (ownership.historical_records or []):
        d = rec.from_date
        if d and d >= cutoff:
            changes_3y += 1

    # ── Flag changes ───────────────────────────────────────────────────────
    flag_changes = len(flag_history)
    flag_changes_3y = sum(
        1 for f in flag_history
        if _parse_iso(f.get("date")) and _parse_iso(f.get("date")) >= cutoff
    )

    flag_hopping = flag_changes_3y >= 3
    if flag_hopping:
        risk_notes.append(
            f"Flag changed {flag_changes_3y}× in the last 3 years — possible flag hopping to avoid scrutiny."
        )
    elif flag_changes_3y >= 2:
        risk_notes.append(
            f"Flag changed {flag_changes_3y}× in the last 3 years — monitor for evasion patterns."
        )

    # ── Name changes ───────────────────────────────────────────────────────
    name_changes = len(name_history)
    if name_changes > 1:
        risk_notes.append(
            f"Vessel name changed {name_changes}× — verify identity continuity and compare against sanctions lists."
        )

    # ── Rapid ownership ────────────────────────────────────────────────────
    rapid_ownership = changes_3y >= 3
    if rapid_ownership:
        risk_notes.append(
            f"Ownership/management changed {changes_3y}× in the last 3 years — investigate reason for instability."
        )
    elif changes_3y >= 2:
        risk_notes.append(
            f"Ownership/management changed {changes_3y}× in the last 3 years."
        )

    # ── Risk level ─────────────────────────────────────────────────────────
    if flag_hopping or (changes_3y >= 4):
        risk_level = RiskLevel.HIGH
    elif rapid_ownership or flag_changes_3y >= 2 or name_changes >= 2:
        risk_level = RiskLevel.MEDIUM
    elif changes_3y >= 1 or flag_changes_3y >= 1:
        risk_level = RiskLevel.LOW
    else:
        risk_level = RiskLevel.NONE

    return OwnershipVelocity(
        changes_last_3_years=changes_3y,
        flag_changes_last_3_years=flag_changes_3y,
        name_changes_count=name_changes,
        flag_hopping_detected=flag_hopping,
        rapid_ownership_changes=rapid_ownership,
        risk_level=risk_level,
        risk_notes=risk_notes,
    )


def build_sister_vessel_risk(
    ownership: OwnershipChain,
    equasis_lookup: Optional[dict],
) -> SisterVesselRisk:
    """
    Build a SisterVesselRisk from available ownership data.
    We cannot scrape the full fleet without additional Equasis calls,
    so we provide the owner entity and note fleet context.
    """
    owner = ownership.current_registered_owner
    owner_name = owner.entity_name if owner else "Unknown"

    # If equasis_lookup returned fleet data, use it; otherwise placeholder
    sister_vessels: list[SisterVessel] = []
    fleet_size = 0
    risk_note = ""

    if equasis_lookup and equasis_lookup.get("sister_vessels"):
        for sv in equasis_lookup["sister_vessels"]:
            sister_vessels.append(SisterVessel(
                imo=sv.get("imo", ""),
                name=sv.get("name", ""),
                flag=sv.get("flag", ""),
                has_issues=sv.get("has_issues", False),
                issue_note=sv.get("issue_note", ""),
            ))
        fleet_size = len(sister_vessels) + 1
    else:
        risk_note = (
            f"Owner: {owner_name}. Full fleet profile requires additional registry lookup. "
            "Verify that no sister vessels under this owner are sanctioned or detained."
        )
        fleet_size = 0

    flagged = [s for s in sister_vessels if s.has_issues]
    if flagged:
        fleet_risk = RiskLevel.HIGH if len(flagged) >= 2 else RiskLevel.MEDIUM
    else:
        fleet_risk = RiskLevel.NONE

    return SisterVesselRisk(
        owner_entity=owner_name,
        fleet_size=fleet_size,
        sister_vessels=sister_vessels,
        fleet_risk_level=fleet_risk,
        risk_note=risk_note,
    )
