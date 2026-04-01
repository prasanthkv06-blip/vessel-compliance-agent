from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from .vessel import VesselIdentity, FlagRecord, RiskLevel
from .ownership import OwnershipChain
from .sanctions import SanctionRiskSummary
from .operational import OperationalRiskSummary


class ComplianceInfo(BaseModel):
    classification_society: Optional[str] = None
    classification_member_type: Optional[str] = None  # "IACS member"
    classification_since: Optional[date] = None
    pi_club: Optional[str] = None
    pi_club_member_type: Optional[str] = None  # "IGP&I member" / "not an IGP&I member"
    pi_club_since: Optional[date] = None
    inspections_count: int = 0
    detentions_count: int = 0
    bans_count: int = 0
    inspections_details: list[dict] = []
    detentions_details: list[dict] = []


class FlagRiskSummary(BaseModel):
    current_flag: str = ""
    flag_history: list[FlagRecord] = []
    paris_mou_status: Optional[str] = None       # White / Grey / Black
    uscg_targeted: bool = False
    itf_foc: bool = False
    imo_conventions_ratified: bool = True
    ilo_conventions_ratified: bool = True
    # Phase 1 additions
    fatf_status: str = "Clean"                   # Clean / Grey List / Black List
    composite_risk_score: int = 0                # 0–100
    flag_change_count: int = 0
    flag_hopping_detected: bool = False
    risk_level: RiskLevel = RiskLevel.NONE


# ── Phase 1 & 2 new models ────────────────────────────────────────────────────

class Certificate(BaseModel):
    name: str
    issuer: Optional[str] = None
    issue_date: Optional[str] = None            # ISO date string
    expiry_date: Optional[str] = None           # ISO date string
    status: str = "unknown"                      # valid | expiring_soon | expired | not_found


class CertificateMatrix(BaseModel):
    certificates: list[Certificate] = []
    all_valid: bool = True
    expiring_count: int = 0
    expired_count: int = 0
    not_found_count: int = 0


class PSCDeficiency(BaseModel):
    category: str
    count: int
    percentage: float = 0.0


class PSCInspectionDetail(BaseModel):
    date: Optional[str] = None                  # ISO date string
    authority: str = ""
    port: str = ""
    country: str = ""
    total_deficiencies: int = 0
    detained: bool = False
    deficiency_categories: list[str] = []


class PSCAnalysis(BaseModel):
    total_inspections: int = 0
    total_detentions: int = 0
    detention_rate_pct: float = 0.0
    deficiency_categories: list[PSCDeficiency] = []
    recent_inspections: list[PSCInspectionDetail] = []
    trend: str = "unknown"                       # improving | stable | deteriorating | unknown
    uscg_detentions: int = 0
    uscg_last_inspection: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.NONE


class CIIRating(BaseModel):
    estimated_grade: str = "C"                  # A | B | C | D | E
    grade_color: str = "#27ae60"                # CSS colour for display
    eu_ets_applicable: bool = False
    eu_ets_note: Optional[str] = None
    sulphur_eca_note: Optional[str] = None
    basis: str = ""


class CasualtyEvent(BaseModel):
    date: Optional[str] = None
    casualty_type: str = ""
    location: Optional[str] = None
    description: Optional[str] = None


class CasualtyHistory(BaseModel):
    events: list[CasualtyEvent] = []
    total_count: int = 0
    risk_level: RiskLevel = RiskLevel.NONE


class SisterVessel(BaseModel):
    imo: str = ""
    name: str = ""
    flag: str = ""
    has_issues: bool = False
    issue_note: str = ""


class SisterVesselRisk(BaseModel):
    owner_entity: str = ""
    fleet_size: int = 0
    sister_vessels: list[SisterVessel] = []
    fleet_risk_level: RiskLevel = RiskLevel.NONE
    risk_note: str = ""


class OwnershipVelocity(BaseModel):
    changes_last_3_years: int = 0
    flag_changes_last_3_years: int = 0
    name_changes_count: int = 0
    flag_hopping_detected: bool = False
    rapid_ownership_changes: bool = False
    risk_level: RiskLevel = RiskLevel.NONE
    risk_notes: list[str] = []


class SanctionsMultiListResult(BaseModel):
    """Enhanced sanctions result from multi-list screening."""
    ofac_hit: bool = False
    eu_hit: bool = False
    uk_hit: bool = False
    un_hit: bool = False
    other_list_hit: bool = False
    total_hits: int = 0
    screened_entities: list[str] = []
    hit_details: list[dict] = []                # {entity, list, program, score}


# ── Master report ─────────────────────────────────────────────────────────────

class ComplianceReport(BaseModel):
    report_id: str
    vessel: VesselIdentity
    ownership: OwnershipChain
    sanction_risks: SanctionRiskSummary
    operational_risks: OperationalRiskSummary
    flag_risks: FlagRiskSummary
    compliance_info: ComplianceInfo
    report_date: datetime
    investigation_start: date
    investigation_end: date
    overall_risk: RiskLevel = RiskLevel.NONE
    created_by: str = ""
    vessel_photo: Optional[str] = None          # base64 data URI

    # Phase 1 & 2 additions
    certificates: Optional[CertificateMatrix] = None
    psc_analysis: Optional[PSCAnalysis] = None
    cii_rating: Optional[CIIRating] = None
    casualty_history: Optional[CasualtyHistory] = None
    sister_vessel_risk: Optional[SisterVesselRisk] = None
    ownership_velocity: Optional[OwnershipVelocity] = None
    sanctions_multi: Optional[SanctionsMultiListResult] = None
