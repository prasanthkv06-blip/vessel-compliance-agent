"""Phase 2: Ownership & Management Chain Service"""
from datetime import date
from typing import Optional
from ..models.ownership import OwnershipRecord, OwnershipChain
from ..models.vessel import SanctionStatus
from ..config import settings


class OwnershipService:
    """Fetches current and historical ownership/management chain."""

    # Sample data for TWENTYSEVEN (IMO 9662693)
    SAMPLE_OWNERSHIP = {
        "9662693": OwnershipChain(
            current_registered_owner=OwnershipRecord(
                entity_name="ALIYAH BUNKERING CO FZE",
                role="registered_owner",
                from_date=date(2024, 11, 27),
                imo_company_number="44499",
                address="FG2X+WP4 Phase II - Hamriya Free Zone - Sharjah - United Arab Emirates",
                country="UNITED ARAB EMIRATES",
                sanction_status=SanctionStatus.NOT_SANCTIONED,
            ),
            current_commercial_manager=OwnershipRecord(
                entity_name="ALIYAH BUNKERING CO FZE",
                role="commercial_manager",
                from_date=date(2024, 11, 27),
                imo_company_number="44499",
                address="FG2X+WP4 Phase II - Hamriya Free Zone - Sharjah - United Arab Emirates",
                country="UNITED ARAB EMIRATES",
                sanction_status=SanctionStatus.NOT_SANCTIONED,
            ),
            current_technical_manager=OwnershipRecord(
                entity_name="ALIYAH BUNKERING CO FZE",
                role="technical_manager",
                from_date=date(2024, 11, 27),
                imo_company_number="44499",
                address="FG2X+WP4 Phase II - Hamriya Free Zone - Sharjah - United Arab Emirates",
                country="UNITED ARAB EMIRATES",
                sanction_status=SanctionStatus.NOT_SANCTIONED,
            ),
            current_ism_manager=OwnershipRecord(
                entity_name="ALIYAH BUNKERING CO FZE",
                role="ism_manager",
                from_date=date(2024, 11, 27),
                imo_company_number="44499",
                address="FG2X+WP4 Phase II - Hamriya Free Zone - Sharjah - United Arab Emirates",
                country="UNITED ARAB EMIRATES",
                sanction_status=SanctionStatus.NOT_SANCTIONED,
            ),
            historical_records=[
                OwnershipRecord(
                    entity_name="QINHUANGDAO HEZHONG SHIP MANAGEMENT",
                    role="registered_owner",
                    from_date=date(2020, 10, 1),
                    to_date=date(2024, 11, 27),
                    imo_company_number="5834064",
                    address="Haigang District, Qinhuangdao, Hebei, China",
                    country="CHINA",
                    website="http://hzshiptech.com/",
                    sanction_status=SanctionStatus.NOT_SANCTIONED,
                ),
            ],
        ),
    }

    async def get_ownership_chain(self, imo: str) -> OwnershipChain:
        """Get full ownership and management chain for a vessel."""
        if imo in self.SAMPLE_OWNERSHIP:
            return self.SAMPLE_OWNERSHIP[imo]

        # In production, query Lloyd's List Intelligence or IHS Markit API
        return OwnershipChain()

    def get_all_entity_names(self, chain: OwnershipChain) -> list[str]:
        """Extract all unique entity names from ownership chain."""
        names = set()
        for field in [chain.current_registered_owner, chain.current_commercial_manager,
                      chain.current_technical_manager, chain.current_ism_manager,
                      chain.current_beneficial_owner, chain.current_third_party_operator]:
            if field:
                names.add(field.entity_name)
        for record in chain.historical_records:
            names.add(record.entity_name)
        return list(names)
