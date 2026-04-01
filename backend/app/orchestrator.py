"""Vessel Compliance Agent -- Orchestrator  v1.1
Coordinates all phases of the compliance check workflow, including
Phase 1 & 2 enhanced checks.
"""
from __future__ import annotations
import uuid
import asyncio
import logging
from datetime import date, datetime
from typing import Optional
from dateutil.relativedelta import relativedelta

from .models.report import ComplianceReport
from .models.vessel import RiskLevel, VesselIdentity, SanctionStatus
from .models.ownership import OwnershipRecord, OwnershipChain
from .models.check_request import VesselCheckRequest

from .services.identity import IdentityService
from .services.ownership import OwnershipService
from .services.sanctions import SanctionsService
from .services.ais_analysis import AISAnalysisService
from .services.flag_risk import FlagRiskService
from .services.compliance import ComplianceService
from .services.equasis import EquasisService
from .services.vessel_photo import fetch_vessel_photo

# Phase 1 & 2 new services
from .services.sanctions_engine import screen_multilists
from .services.psc_analyzer import analyze_psc, fetch_uscg_record
from .services.certificate_service import build_certificate_matrix
from .services.cii_calculator import estimate_cii
from .services.casualty_service import build_casualty_history
from .services.ownership_analyzer import analyze_ownership_velocity, build_sister_vessel_risk

from .config import settings

logger = logging.getLogger(__name__)


class ComplianceOrchestrator:
    """Runs the full compliance check and produces a ComplianceReport."""

    def __init__(self):
        self.identity_svc   = IdentityService()
        self.ownership_svc  = OwnershipService()
        self.sanctions_svc  = SanctionsService()
        self.ais_svc        = AISAnalysisService()
        self.flag_risk_svc  = FlagRiskService()
        self.compliance_svc = ComplianceService()
        self.equasis_svc = (
            EquasisService(settings.equasis_username, settings.equasis_password)
            if settings.equasis_username and settings.equasis_password
            else None
        )

    # ── Internal helpers ────────────────────────────────────────────────────

    async def _run_enhanced_checks(
        self,
        imo: str,
        vessel: VesselIdentity,
        ownership: OwnershipChain,
        entity_names: list[str],
        equasis_data: Optional[dict],
    ) -> dict:
        """
        Run all Phase 1 & 2 enhanced checks concurrently.
        Returns a dict of results keyed by check name.
        """
        raw_inspections: list[dict] = []
        raw_certs: list[dict] = []
        raw_casualties: list[dict] = []
        flag_history_raw: list[dict] = []
        name_history_raw: list[dict] = []

        if self.equasis_svc:
            # Fetch Equasis detail pages concurrently
            insp_task  = self.equasis_svc.fetch_inspections(imo)
            cert_task  = self.equasis_svc.fetch_certificates(imo)
            cas_task   = self.equasis_svc.fetch_casualties(imo)
            raw_inspections, raw_certs, raw_casualties = await asyncio.gather(
                insp_task, cert_task, cas_task,
                return_exceptions=False,
            )
            if equasis_data:
                flag_history_raw = equasis_data.get("flag_history", [])
                name_history_raw = equasis_data.get("name_history", [])

        # Multi-list sanctions (OFAC + OpenSanctions)
        sanctions_multi_task = screen_multilists(imo, vessel.name, entity_names)

        # USCG PSIX (best-effort)
        uscg_task = fetch_uscg_record(imo)

        sanctions_multi, uscg_rec = await asyncio.gather(
            sanctions_multi_task, uscg_task,
            return_exceptions=False,
        )

        # PSC analysis
        psc_analysis = analyze_psc(raw_inspections)
        if uscg_rec:
            psc_analysis.uscg_detentions = uscg_rec.get("detentions", 0)
            if uscg_rec.get("last_inspection"):
                psc_analysis.uscg_last_inspection = uscg_rec["last_inspection"]

        # Certificate matrix
        certificates = build_certificate_matrix(raw_certs, vessel.vessel_type or "")

        # CII & EU ETS
        cii_rating = estimate_cii(
            vessel_type=vessel.vessel_type or "",
            build_year=vessel.build_year or 0,
            dwt=vessel.dwt or 0,
            grt=vessel.grt or 0,
        )

        # Casualty history
        casualty_history = build_casualty_history(raw_casualties)

        # Ownership velocity & anomaly detection
        ownership_velocity = analyze_ownership_velocity(
            ownership, flag_history_raw, name_history_raw
        )

        # Sister vessel risk
        sister_vessel_risk = build_sister_vessel_risk(ownership, equasis_data)

        return {
            "sanctions_multi":   sanctions_multi,
            "psc_analysis":      psc_analysis,
            "certificates":      certificates,
            "cii_rating":        cii_rating,
            "casualty_history":  casualty_history,
            "ownership_velocity": ownership_velocity,
            "sister_vessel_risk": sister_vessel_risk,
            "flag_change_count": len(flag_history_raw),
        }

    def _calculate_overall_risk(self, sanctions, operational, flags,
                                 psc=None, casualties=None,
                                 ownership_vel=None) -> RiskLevel:
        """Aggregate risk from all checks."""
        if sanctions.vessel_sanctioned or sanctions.ownership_sanctioned:
            return RiskLevel.HIGH
        if operational.highest_risk == RiskLevel.HIGH:
            return RiskLevel.HIGH
        if flags.risk_level == RiskLevel.HIGH:
            return RiskLevel.HIGH
        if psc and psc.risk_level == RiskLevel.HIGH:
            return RiskLevel.HIGH
        if casualties and casualties.risk_level == RiskLevel.HIGH:
            return RiskLevel.HIGH

        medium_signals = [
            operational.highest_risk == RiskLevel.MEDIUM,
            flags.risk_level == RiskLevel.MEDIUM,
            psc and psc.risk_level == RiskLevel.MEDIUM,
            ownership_vel and ownership_vel.risk_level == RiskLevel.MEDIUM,
        ]
        if any(medium_signals):
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    # ── Public API ──────────────────────────────────────────────────────────

    async def generate_report(self, imo: str, created_by: str = "") -> ComplianceReport:
        """Execute full compliance workflow from IMO only (uses sample / Equasis data)."""
        end_date   = date.today()
        start_date = end_date - relativedelta(months=settings.investigation_months)

        # Phase 1: Identity
        vessel = await self.identity_svc.lookup_vessel(imo=imo)
        if not vessel:
            raise ValueError(f"Vessel with IMO {imo} not found")

        equasis_data = None
        if self.equasis_svc:
            equasis_data = await self.equasis_svc.lookup_vessel(imo)
            if equasis_data:
                lv = equasis_data.get("vessel", {})
                vessel = VesselIdentity(
                    imo=vessel.imo,
                    name=lv.get("name", vessel.name),
                    vessel_type=lv.get("vessel_type", vessel.vessel_type),
                    flag=(lv.get("flag") or vessel.flag or "UNKNOWN").upper(),
                    mmsi=lv.get("mmsi") or vessel.mmsi or "",
                    dwt=lv.get("dwt") or vessel.dwt or 0,
                    grt=lv.get("grt") or vessel.grt or 0,
                    build_year=lv.get("build_year") or vessel.build_year or 0,
                    build_country=lv.get("build_country") or vessel.build_country or "Unknown",
                    class_society=lv.get("class_society") or vessel.class_society,
                    sanction_status=SanctionStatus.NOT_SANCTIONED,
                )

        # Phase 2: Ownership
        ownership = await self.ownership_svc.get_ownership_chain(imo)
        entity_names = self.ownership_svc.get_all_entity_names(ownership)

        # Core checks (concurrent)
        sanctions_task = self.sanctions_svc.screen_full(imo, entity_names)
        ais_task       = self.ais_svc.analyze(imo, start_date, end_date)
        compliance_task = self.compliance_svc.get_compliance_info(imo)
        photo_task     = fetch_vessel_photo(imo=vessel.imo, mmsi=vessel.mmsi or "")

        sanction_risks, operational_risks, compliance_info, vessel_photo = await asyncio.gather(
            sanctions_task, ais_task, compliance_task, photo_task
        )

        # Enhanced Phase 1 & 2 checks
        enhanced = await self._run_enhanced_checks(imo, vessel, ownership, entity_names, equasis_data)

        # Flag risk (needs flag_change_count from enhanced)
        flag_risks = await self.flag_risk_svc.assess(
            vessel.flag,
            flag_change_count=enhanced["flag_change_count"],
        )

        overall_risk = self._calculate_overall_risk(
            sanction_risks, operational_risks, flag_risks,
            enhanced["psc_analysis"], enhanced["casualty_history"],
            enhanced["ownership_velocity"],
        )

        return ComplianceReport(
            report_id=str(uuid.uuid4())[:8],
            vessel=vessel,
            ownership=ownership,
            sanction_risks=sanction_risks,
            operational_risks=operational_risks,
            flag_risks=flag_risks,
            compliance_info=compliance_info,
            report_date=datetime.utcnow(),
            investigation_start=start_date,
            investigation_end=end_date,
            overall_risk=overall_risk,
            vessel_photo=vessel_photo,
            created_by=created_by,
            # Phase 1 & 2
            sanctions_multi=enhanced["sanctions_multi"],
            psc_analysis=enhanced["psc_analysis"],
            certificates=enhanced["certificates"],
            cii_rating=enhanced["cii_rating"],
            casualty_history=enhanced["casualty_history"],
            ownership_velocity=enhanced["ownership_velocity"],
            sister_vessel_risk=enhanced["sister_vessel_risk"],
        )

    async def generate_report_from_input(self, req: VesselCheckRequest) -> ComplianceReport:
        """
        Execute full compliance workflow from user-supplied vessel details.
        IMO is the primary key; missing fields auto-filled from Equasis.
        """
        end_date   = date.today()
        start_date = end_date - relativedelta(months=settings.investigation_months)

        # ── Phase 1: Vessel Identity ─────────────────────────────────────────
        equasis_data = None
        needs_lookup = not all([req.vessel_name, req.flag, req.vessel_type])

        if needs_lookup or self.equasis_svc:
            if self.equasis_svc:
                equasis_data = await self.equasis_svc.lookup_vessel(req.imo)
            if not equasis_data:
                looked_up = await self.identity_svc.lookup_vessel(imo=req.imo)
                if looked_up:
                    equasis_data = {
                        "vessel": {
                            "name": looked_up.name,
                            "vessel_type": looked_up.vessel_type,
                            "flag": looked_up.flag,
                            "mmsi": looked_up.mmsi,
                            "dwt": looked_up.dwt,
                            "grt": looked_up.grt,
                            "build_year": looked_up.build_year,
                            "build_country": looked_up.build_country,
                            "class_society": looked_up.class_society or "",
                        },
                        "ownership": [],
                        "flag_history": [],
                        "name_history": [],
                    }

        lv = (equasis_data or {}).get("vessel", {})

        vessel_name = (req.vessel_name or lv.get("name") or "").upper()
        if not vessel_name:
            raise ValueError(
                f"Vessel with IMO {req.imo} not found in registry. "
                "Please enter the vessel name manually."
            )

        vessel = VesselIdentity(
            imo=req.imo,
            name=vessel_name,
            vessel_type=req.vessel_type or lv.get("vessel_type") or "Unknown",
            flag=(req.flag or lv.get("flag") or "UNKNOWN").upper(),
            mmsi=req.mmsi or lv.get("mmsi") or "",
            dwt=req.dwt or lv.get("dwt") or 0,
            grt=req.grt or lv.get("grt") or 0,
            build_year=req.build_year or lv.get("build_year") or 0,
            build_country=req.build_country or lv.get("build_country") or "Unknown",
            class_society=req.class_society or lv.get("class_society"),
            sanction_status=SanctionStatus.NOT_SANCTIONED,
        )

        # ── Phase 2: Ownership Chain ─────────────────────────────────────────
        supplied_owners = list(req.owners)
        if not supplied_owners and equasis_data and equasis_data.get("ownership"):
            from .models.check_request import OwnerInput as _OI
            for o in equasis_data["ownership"]:
                supplied_owners.append(_OI(
                    entity_name=o["entity_name"],
                    role=o.get("role", "registered_owner"),
                    country=o.get("country", ""),
                    address=o.get("address", ""),
                    from_date=o.get("from_date", ""),
                    to_date=o.get("to_date", ""),
                    is_historical=o.get("is_historical", False),
                ))

        if supplied_owners:
            from dateutil.parser import parse as parse_date

            current_records: list[OwnershipRecord] = []
            historical_records: list[OwnershipRecord] = []

            for o in supplied_owners:
                try:
                    rec_from = parse_date(o.from_date).date() if o.from_date else date.today()
                except Exception:
                    rec_from = date.today()
                try:
                    rec_to = parse_date(o.to_date).date() if o.to_date else None
                except Exception:
                    rec_to = None

                record = OwnershipRecord(
                    entity_name=o.entity_name,
                    role=o.role,
                    from_date=rec_from,
                    to_date=rec_to,
                    country=o.country,
                    address=o.address,
                    imo_company_number=o.imo_company_number,
                    sanction_status=SanctionStatus.NOT_SANCTIONED,
                )
                if o.is_historical or rec_to is not None:
                    historical_records.append(record)
                else:
                    current_records.append(record)

            def _find(role_names):
                return next((r for r in current_records if r.role in role_names), None)

            current_owner = _find(("registered_owner",)) or (current_records[0] if current_records else None)
            ownership = OwnershipChain(
                current_registered_owner=current_owner,
                current_commercial_manager=_find(("commercial_manager", "manager")) or current_owner,
                current_technical_manager=_find(("technical_manager",)) or current_owner,
                current_ism_manager=_find(("ism_manager",)) or current_owner,
                current_third_party_operator=_find(("operator", "third_party_operator")),
                historical_records=historical_records,
            )
        else:
            ownership = await self.ownership_svc.get_ownership_chain(req.imo)

        entity_names = self.ownership_svc.get_all_entity_names(ownership)

        # Core checks (concurrent)
        sanctions_task  = self.sanctions_svc.screen_full(req.imo, entity_names)
        ais_task        = self.ais_svc.analyze(req.imo, start_date, end_date)
        compliance_task = self.compliance_svc.get_compliance_info(req.imo)
        photo_task      = fetch_vessel_photo(imo=vessel.imo, mmsi=vessel.mmsi or "")

        sanction_risks, operational_risks, compliance_info, vessel_photo = await asyncio.gather(
            sanctions_task, ais_task, compliance_task, photo_task
        )

        # Enhanced Phase 1 & 2 checks
        enhanced = await self._run_enhanced_checks(
            req.imo, vessel, ownership, entity_names, equasis_data
        )

        # Flag risk
        flag_risks = await self.flag_risk_svc.assess(
            vessel.flag,
            flag_change_count=enhanced["flag_change_count"],
        )

        overall_risk = self._calculate_overall_risk(
            sanction_risks, operational_risks, flag_risks,
            enhanced["psc_analysis"], enhanced["casualty_history"],
            enhanced["ownership_velocity"],
        )

        return ComplianceReport(
            report_id=str(uuid.uuid4())[:8],
            vessel=vessel,
            ownership=ownership,
            sanction_risks=sanction_risks,
            operational_risks=operational_risks,
            flag_risks=flag_risks,
            compliance_info=compliance_info,
            report_date=datetime.utcnow(),
            investigation_start=start_date,
            investigation_end=end_date,
            overall_risk=overall_risk,
            vessel_photo=vessel_photo,
            created_by=req.created_by,
            # Phase 1 & 2
            sanctions_multi=enhanced["sanctions_multi"],
            psc_analysis=enhanced["psc_analysis"],
            certificates=enhanced["certificates"],
            cii_rating=enhanced["cii_rating"],
            casualty_history=enhanced["casualty_history"],
            ownership_velocity=enhanced["ownership_velocity"],
            sister_vessel_risk=enhanced["sister_vessel_risk"],
        )
