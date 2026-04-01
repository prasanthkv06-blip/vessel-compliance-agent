from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..services.identity import IdentityService
from ..services.ownership import OwnershipService
from ..services.equasis import EquasisService
from ..models.vessel import VesselIdentity
from ..config import settings
import difflib

router = APIRouter(prefix="/api/v1/vessel", tags=["vessel"])
identity_service = IdentityService()
ownership_service = OwnershipService()

# Equasis service (only if credentials are configured)
_equasis: Optional[EquasisService] = None
if settings.equasis_username and settings.equasis_password:
    _equasis = EquasisService(settings.equasis_username, settings.equasis_password)


def _names_match(a: str, b: str) -> bool:
    """Fuzzy name comparison — True if names are close enough."""
    a = a.upper().strip()
    b = b.upper().strip()
    if a == b:
        return True
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return ratio >= 0.85


@router.get("/lookup/{imo}", summary="Lookup vessel details by IMO")
async def lookup_vessel(
    imo: str,
    vessel_name: Optional[str] = Query(None, description="If provided, compare with found vessel name"),
):
    """
    Auto-fetch vessel particulars and ownership from Equasis (or sample data).

    Response:
    - vessel: all known fields
    - ownership: list of owner/manager records
    - name_found: vessel name found in registry
    - name_match: True/False/null (null when no vessel_name query param provided)
    - source: "equasis" | "sample"
    """
    result = None

    # 1. Try Equasis first (real data)
    if _equasis:
        try:
            result = await _equasis.lookup_vessel(imo)
        except Exception:
            result = None

    # 2. Fall back to sample data / identity service
    if not result:
        vessel = await identity_service.lookup_vessel(imo=imo)
        if vessel:
            ownership_chain = await ownership_service.get_ownership_chain(imo)

            # Flatten ownership chain into list format
            ownership_list = []
            for field_name, record in [
                ("registered_owner", ownership_chain.current_registered_owner),
                ("commercial_manager", ownership_chain.current_commercial_manager),
                ("technical_manager", ownership_chain.current_technical_manager),
                ("ism_manager", ownership_chain.current_ism_manager),
            ]:
                if record:
                    ownership_list.append({
                        "entity_name": record.entity_name,
                        "role": record.role or field_name,
                        "country": record.country or "",
                        "address": record.address or "",
                        "from_date": record.from_date.isoformat() if record.from_date else "",
                        "to_date": "",
                        "is_historical": False,
                    })

            for record in ownership_chain.historical_records:
                ownership_list.append({
                    "entity_name": record.entity_name,
                    "role": record.role or "registered_owner",
                    "country": record.country or "",
                    "address": record.address or "",
                    "from_date": record.from_date.isoformat() if record.from_date else "",
                    "to_date": record.to_date.isoformat() if record.to_date else "",
                    "is_historical": True,
                })

            result = {
                "vessel": {
                    "imo": vessel.imo,
                    "name": vessel.name,
                    "vessel_type": vessel.vessel_type,
                    "flag": vessel.flag,
                    "mmsi": vessel.mmsi,
                    "dwt": vessel.dwt,
                    "grt": vessel.grt,
                    "build_year": vessel.build_year,
                    "build_country": vessel.build_country,
                    "class_society": vessel.class_society or "",
                },
                "ownership": ownership_list,
                "source": "sample",
            }

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Vessel IMO {imo} not found. Please enter vessel details manually.",
        )

    # Name comparison
    name_found = result["vessel"].get("name", "")
    name_match = None
    if vessel_name and name_found:
        name_match = _names_match(vessel_name, name_found)

    return {
        "imo": imo,
        "found": True,
        "source": result["source"],
        "vessel": result["vessel"],
        "ownership": result["ownership"],
        "name_found": name_found,
        "name_match": name_match,
    }


@router.get("/{imo}", response_model=VesselIdentity)
async def get_vessel(imo: str):
    vessel = await identity_service.lookup_vessel(imo=imo)
    if not vessel:
        raise HTTPException(status_code=404, detail=f"Vessel IMO {imo} not found")
    return vessel


@router.post("/search")
async def search_vessel(imo: str = None, name: str = None):
    if not imo and not name:
        raise HTTPException(status_code=400, detail="Provide IMO or vessel name")
    vessel = await identity_service.lookup_vessel(imo=imo, name=name)
    if not vessel:
        raise HTTPException(status_code=404, detail="Vessel not found")
    return vessel
