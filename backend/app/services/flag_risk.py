"""Phase 5 (Enhanced): Flag Risk Assessment Service

Phase 1 additions:
  - FATF Grey / Black List (2024–2025)
  - USCG Annual Targeted Flag List (2024)
  - Composite risk score (0–100)
  - Flag-hopping / change-count detection
"""
from __future__ import annotations
from datetime import date
from typing import Optional, List
from ..models.vessel import FlagRecord, RiskLevel
from ..models.report import FlagRiskSummary

# ── Paris MoU performance lists (2024-2025) ───────────────────────────────────
PARIS_MOU_STATUS: dict[str, str] = {
    # White
    "BAHAMAS": "White", "BERMUDA": "White", "CAYMAN ISLANDS": "White",
    "DENMARK": "White", "FRANCE": "White", "GERMANY": "White",
    "GREECE": "White", "HONG KONG": "White", "ISLE OF MAN": "White",
    "JAPAN": "White", "MARSHALL ISLANDS": "White", "NETHERLANDS": "White",
    "NORWAY": "White", "SINGAPORE": "White", "SWEDEN": "White",
    "UNITED KINGDOM": "White", "UNITED STATES": "White",
    "LIBERIA": "White", "CYPRUS": "White", "MALTA": "White",
    "ANTIGUA AND BARBUDA": "White", "BAHRAIN": "White",
    # Grey
    "CHINA": "Grey", "INDIA": "Grey", "INDONESIA": "Grey",
    "KOREA": "Grey", "MALAYSIA": "Grey", "SAUDI ARABIA": "Grey",
    "THAILAND": "Grey", "TURKEY": "Grey", "VIETNAM": "Grey",
    "RUSSIA": "Grey", "UKRAINE": "Grey",
    # Black
    "CAMEROON": "Black", "COMOROS": "Black", "MOLDOVA": "Black",
    "SIERRA LEONE": "Black", "TANZANIA": "Black", "TOGO": "Black",
    "PALAU": "Black", "BELIZE": "Black", "GEORGIA": "Black",
}

# ── ITF Flags of Convenience (2025) ──────────────────────────────────────────
ITF_FOC_FLAGS: set[str] = {
    "ANTIGUA AND BARBUDA", "BAHAMAS", "BARBADOS", "BELIZE", "BERMUDA",
    "BOLIVIA", "CAMBODIA", "CAYMAN ISLANDS", "COMOROS", "CURACAO",
    "CYPRUS", "EQUATORIAL GUINEA", "FAROE ISLANDS", "GEORGIA",
    "GIBRALTAR", "HONDURAS", "JAMAICA", "LEBANON", "LIBERIA",
    "MALTA", "MARSHALL ISLANDS", "MAURITIUS", "MOLDOVA", "MONGOLIA",
    "MYANMAR", "NORTH KOREA", "PALAU", "PANAMA", "SAO TOME AND PRINCIPE",
    "SIERRA LEONE", "SRI LANKA", "ST KITTS AND NEVIS",
    "ST VINCENT AND THE GRENADINES", "TOGO", "TONGA", "VANUATU",
}

# ── FATF Grey / Black Lists (June 2024 update) ───────────────────────────────
FATF_BLACK: set[str] = {
    "IRAN", "NORTH KOREA", "MYANMAR",
}

FATF_GREY: set[str] = {
    "BULGARIA", "BURKINA FASO", "CAMEROON", "CROATIA", "CONGO",
    "DEMOCRATIC REPUBLIC OF THE CONGO", "HAITI", "JAMAICA", "KENYA",
    "LAOS", "MALI", "MONACO", "MOZAMBIQUE", "NAMIBIA", "NIGERIA",
    "PHILIPPINES", "SENEGAL", "SOUTH AFRICA", "SOUTH SUDAN", "SYRIA",
    "TANZANIA", "VENEZUELA", "VIETNAM", "YEMEN",
}

# ── USCG Annual Targeted Flag List (2024) ────────────────────────────────────
USCG_TARGETED: set[str] = {
    "BELIZE", "COMOROS", "GEORGIA", "MOLDOVA", "PALAU",
    "SIERRA LEONE", "TOGO", "TANZANIA", "PANAMA",
}

# ── Non-ratification of key IMO / ILO conventions ────────────────────────────
IMO_NON_RATIFIED: set[str] = {
    "NORTH KOREA", "SOMALIA", "ERITREA",
}
ILO_NON_RATIFIED: set[str] = {
    "NORTH KOREA", "IRAN", "MYANMAR",
}


def _fatf_status(flag: str) -> str:
    f = flag.upper()
    if f in FATF_BLACK:
        return "Black List"
    if f in FATF_GREY:
        return "Grey List"
    return "Clean"


def _composite_score(
    paris: Optional[str],
    fatf: str,
    uscg: bool,
    foc: bool,
    flag_changes: int,
    hopping: bool,
) -> int:
    score = 0
    if paris == "Black":
        score += 35
    elif paris == "Grey":
        score += 15

    if fatf == "Black List":
        score += 35
    elif fatf == "Grey List":
        score += 15

    if uscg:
        score += 15
    if foc:
        score += 8
    if hopping:
        score += 12
    elif flag_changes >= 2:
        score += 5

    return min(score, 100)


class FlagRiskService:
    """Assesses flag-related compliance risks."""

    async def assess(
        self,
        current_flag: str,
        flag_history: Optional[List[FlagRecord]] = None,
        flag_change_count: int = 0,
    ) -> FlagRiskSummary:
        flag_history = flag_history or []
        cf = current_flag.upper()

        paris = PARIS_MOU_STATUS.get(cf, "Unknown")
        is_foc = cf in ITF_FOC_FLAGS
        uscg = cf in USCG_TARGETED
        fatf = _fatf_status(cf)
        imo_rat = cf not in IMO_NON_RATIFIED
        ilo_rat = cf not in ILO_NON_RATIFIED
        hopping = flag_change_count >= 3

        score = _composite_score(paris, fatf, uscg, is_foc, flag_change_count, hopping)

        # Risk level
        if fatf == "Black List" or paris == "Black":
            risk = RiskLevel.HIGH
        elif fatf == "Grey List" or paris == "Grey" or uscg or hopping:
            risk = RiskLevel.MEDIUM
        elif is_foc or flag_change_count >= 2:
            risk = RiskLevel.LOW
        else:
            risk = RiskLevel.NONE

        return FlagRiskSummary(
            current_flag=current_flag,
            flag_history=flag_history,
            paris_mou_status=paris,
            uscg_targeted=uscg,
            itf_foc=is_foc,
            imo_conventions_ratified=imo_rat,
            ilo_conventions_ratified=ilo_rat,
            fatf_status=fatf,
            composite_risk_score=score,
            flag_change_count=flag_change_count,
            flag_hopping_detected=hopping,
            risk_level=risk,
        )
