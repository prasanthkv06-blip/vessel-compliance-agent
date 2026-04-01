"""Phase 4: Compliance Information Service"""
from datetime import date
from typing import Optional
from ..models.report import ComplianceInfo


class ComplianceService:
    """Fetches classification, P&I, and inspection data."""

    SAMPLE_COMPLIANCE = {
        "9662693": ComplianceInfo(
            classification_society="Bureau Veritas",
            classification_member_type="IACS member",
            classification_since=date(2025, 11, 21),
            pi_club="Unknown",
            pi_club_member_type="not an IGP&I member",
            pi_club_since=date(2024, 11, 1),
            inspections_count=0,
            detentions_count=0,
            bans_count=0,
        ),
    }

    async def get_compliance_info(self, imo: str) -> ComplianceInfo:
        """Get classification, P&I, inspections for a vessel."""
        if imo in self.SAMPLE_COMPLIANCE:
            return self.SAMPLE_COMPLIANCE[imo]
        # In production: query Equasis, class society APIs
        return ComplianceInfo()
