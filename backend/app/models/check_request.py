"""Input model for user-initiated compliance checks."""
from pydantic import BaseModel, Field
from typing import Optional


class OwnerInput(BaseModel):
    """A single owner/operator entity supplied by the user."""
    entity_name: str
    role: str = "registered_owner"  # registered_owner | commercial_manager | technical_manager | ism_manager | operator
    country: Optional[str] = None
    address: Optional[str] = None
    imo_company_number: Optional[str] = None
    from_date: Optional[str] = Field(None, description="Date entity took this role, e.g. 2024-11-27")
    to_date: Optional[str] = Field(None, description="Date entity left this role (omit if current)")
    is_historical: bool = Field(False, description="Set true to place in historical records instead of current")


class VesselCheckRequest(BaseModel):
    """
    Input payload the user provides to trigger a compliance check.
    All fields except imo are optional — if omitted the system will
    attempt to retrieve them from sample data or external APIs.
    """
    imo: str = Field(..., description="IMO number (7 digits)", min_length=7, max_length=7)
    vessel_name: Optional[str] = Field(None, description="Vessel name as per registry")
    vessel_type: Optional[str] = Field(None, description="e.g. Oil Products Tanker")
    flag: Optional[str] = Field(None, description="Flag state in UPPER CASE, e.g. SAUDI ARABIA")
    mmsi: Optional[str] = Field(None, description="Maritime Mobile Service Identity")
    dwt: Optional[int] = Field(None, description="Deadweight tonnage")
    grt: Optional[int] = Field(None, description="Gross register tonnage")
    build_year: Optional[int] = Field(None, description="Year of build")
    build_country: Optional[str] = Field(None, description="Country where vessel was built")
    class_society: Optional[str] = Field(None, description="Classification society")

    # Owner/operator chain (user can supply one or more)
    owners: list[OwnerInput] = Field(
        default_factory=list,
        description="Known current owners/operators. At least one recommended."
    )

    created_by: str = Field("", description="Name of the analyst running this check")
