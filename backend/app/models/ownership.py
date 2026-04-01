from pydantic import BaseModel
from datetime import date
from typing import Optional
from .vessel import SanctionStatus

class OwnershipRecord(BaseModel):
    entity_name: str
    role: str  # registered_owner, commercial_manager, technical_manager, ism_manager, beneficial_owner, third_party_operator
    from_date: date
    to_date: Optional[date] = None
    imo_company_number: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    sanction_status: SanctionStatus = SanctionStatus.NOT_SANCTIONED
    sanction_programs: list[str] = []

class OwnershipChain(BaseModel):
    current_registered_owner: Optional[OwnershipRecord] = None
    current_commercial_manager: Optional[OwnershipRecord] = None
    current_technical_manager: Optional[OwnershipRecord] = None
    current_ism_manager: Optional[OwnershipRecord] = None
    current_beneficial_owner: Optional[OwnershipRecord] = None
    current_third_party_operator: Optional[OwnershipRecord] = None
    historical_records: list[OwnershipRecord] = []
