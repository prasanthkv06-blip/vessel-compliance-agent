"""CII (Carbon Intensity Indicator) Estimator & EU ETS Exposure — Phase 2.

Provides an *indicative* CII grade (A–E) calculated from vessel specs only.
Actual CII requires real voyage distance and fuel consumption data.

Methodology:
  - IMO MEPC.337(76): CII rating based on attained vs required CII
  - Required CII tightens 2% per year (2023 baseline)
  - Estimate = function of vessel age, type, and size efficiency class
  - Result is labelled "Estimated" throughout the report
"""
from datetime import date
from ..models.report import CIIRating

# CII grade colour map
_GRADE_COLORS = {
    "A": "#27ae60",    # green
    "B": "#2ecc71",    # light green
    "C": "#f39c12",    # amber
    "D": "#e67e22",    # orange
    "E": "#c0392b",    # red
}

# Vessel types considered high-efficiency (newer fleet, EEDI Phase 2/3)
_HIGH_EFF_TYPES = {"lng", "lpg", "gas carrier", "ro-ro", "car carrier", "reefer"}
# Vessel types with traditionally lower efficiency per tonne-mile
_LOW_EFF_TYPES  = {"bulk carrier", "general cargo", "multipurpose", "heavy lift"}


def _base_grade_from_age(build_year: int) -> str:
    """Return a baseline CII grade bracket purely from build year."""
    age = date.today().year - build_year if build_year and build_year > 1900 else 15
    if age <= 3:
        return "A"
    if age <= 7:
        return "B"
    if age <= 13:
        return "C"
    if age <= 20:
        return "D"
    return "E"


def _adjust_for_type(grade: str, vessel_type: str) -> str:
    """Bump grade up/down one notch based on vessel type efficiency."""
    ladder = ["A", "B", "C", "D", "E"]
    idx = ladder.index(grade)
    vt = vessel_type.lower() if vessel_type else ""
    if any(t in vt for t in _HIGH_EFF_TYPES):
        idx = max(0, idx - 1)
    elif any(t in vt for t in _LOW_EFF_TYPES):
        idx = min(4, idx + 1)
    return ladder[idx]


def estimate_cii(
    vessel_type: str,
    build_year: int,
    dwt: int,
    grt: int,
) -> CIIRating:
    """
    Return an estimated CII grade and EU ETS applicability.
    """
    if not build_year or build_year < 1950:
        build_year = date.today().year - 15

    grade = _base_grade_from_age(build_year)
    grade = _adjust_for_type(grade, vessel_type)

    # EU ETS: applies to vessels > 5 000 GT trading in/out EU ports (2024+)
    ets_applicable = (grt or 0) >= 5000

    current_year = date.today().year
    age = current_year - build_year

    basis = (
        f"Estimated from vessel age ({age} yrs), type ({vessel_type or 'unknown'}), "
        f"and IMO MEPC.337(76) reference lines. Actual CII requires verified voyage data."
    )

    ets_note = None
    if ets_applicable:
        ets_note = (
            f"This vessel ({grt:,} GT) falls within EU ETS scope. "
            "Operators must surrender EU Allowances (EUAs) for voyages to/from/between EU ports. "
            "2024 obligation: 40%; 2025: 70%; 2026: 100% of CO₂ emissions."
        )
    else:
        ets_note = f"Vessel GRT ({grt:,}) is below 5,000 GT — currently outside EU ETS scope."

    sulphur_note = (
        "Global 0.5% sulphur cap (MARPOL Annex VI). "
        "0.1% cap in North Sea / Baltic / North American ECAs. "
        "Verify scrubber or compliant fuel compliance before deployment."
    )

    return CIIRating(
        estimated_grade=grade,
        grade_color=_GRADE_COLORS.get(grade, "#f39c12"),
        eu_ets_applicable=ets_applicable,
        eu_ets_note=ets_note,
        sulphur_eca_note=sulphur_note,
        basis=basis,
    )
