from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from enum import Enum

class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    NONE = "None"

class SanctionStatus(str, Enum):
    NOT_SANCTIONED = "Not Sanctioned"
    SANCTIONED = "Sanctioned"
    FORMERLY_SANCTIONED = "Formerly Sanctioned"
    REVIEW = "Review Required"

class VesselIdentity(BaseModel):
    imo: str
    name: str
    vessel_type: str
    flag: str
    mmsi: str
    dwt: int
    grt: int
    build_year: int
    build_country: str
    class_society: Optional[str] = None
    sanction_status: SanctionStatus = SanctionStatus.NOT_SANCTIONED

class FlagRecord(BaseModel):
    flag: str
    from_date: date
    to_date: Optional[date] = None
    paris_mou_status: Optional[str] = None  # White/Grey/Black
    uscg_targeted: bool = False
    itf_foc: bool = False
