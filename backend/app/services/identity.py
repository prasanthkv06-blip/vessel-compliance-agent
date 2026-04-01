"""Phase 1: Vessel Identity Verification Service"""
import httpx
from typing import Optional
from ..models.vessel import VesselIdentity
from ..config import settings


class IdentityService:
    """Fetches vessel particulars from maritime databases."""

    # Sample data for demo/testing (IMO 9662693 = TWENTYSEVEN)
    SAMPLE_VESSELS = {
        "9662693": VesselIdentity(
            imo="9662693",
            name="TWENTYSEVEN",
            vessel_type="Oil Products Tanker",
            flag="SAUDI ARABIA",
            mmsi="403738380",
            dwt=3591,
            grt=2239,
            build_year=2014,
            build_country="China",
            class_society="Bureau Veritas",
            sanction_status="Not Sanctioned",
        ),
    }

    async def lookup_vessel(self, imo: Optional[str] = None, name: Optional[str] = None) -> Optional[VesselIdentity]:
        """Look up vessel by IMO number or name."""
        # Try sample data first (for demo)
        if imo and imo in self.SAMPLE_VESSELS:
            return self.SAMPLE_VESSELS[imo]

        # Try MarineTraffic API if key is configured
        if settings.marine_traffic_api_key and imo:
            return await self._query_marine_traffic(imo)

        # Try Equasis if credentials configured
        if settings.equasis_username and imo:
            return await self._query_equasis(imo)

        return None

    async def _query_marine_traffic(self, imo: str) -> Optional[VesselIdentity]:
        """Query MarineTraffic API for vessel data."""
        async with httpx.AsyncClient() as client:
            try:
                url = f"https://services.marinetraffic.com/api/vesselsearch/v:2/{settings.marine_traffic_api_key}/imo:{imo}"
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        v = data[0] if isinstance(data, list) else data
                        return VesselIdentity(
                            imo=str(v.get("IMO", imo)),
                            name=v.get("SHIPNAME", "Unknown"),
                            vessel_type=v.get("TYPE_NAME", "Unknown"),
                            flag=v.get("FLAG", "Unknown"),
                            mmsi=str(v.get("MMSI", "")),
                            dwt=int(v.get("DWT", 0)),
                            grt=int(v.get("GRT", 0)),
                            build_year=int(v.get("YEAR_BUILT", 0)),
                            build_country=v.get("BUILD_COUNTRY", "Unknown"),
                        )
            except Exception:
                pass
        return None

    async def _query_equasis(self, imo: str) -> Optional[VesselIdentity]:
        """Query Equasis for vessel data (requires login session)."""
        # Equasis requires session-based auth - implement scraping logic
        # This is a placeholder for the actual implementation
        return None
