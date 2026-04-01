"""Phase 2 & 4: Sanctions Screening Service"""
import xml.etree.ElementTree as ET
import csv
import os
from typing import Optional
from fuzzywuzzy import fuzz
from ..models.sanctions import SanctionHit, SanctionRiskSummary
from ..models.vessel import SanctionStatus
from ..config import settings


class SanctionsService:
    """Screens vessels and entities against global sanctions lists."""

    def __init__(self):
        self._ofac_entries: list[dict] = []
        self._eu_entries: list[dict] = []
        self._uk_entries: list[dict] = []
        self._loaded = False

    async def load_lists(self):
        """Load all sanctions lists into memory."""
        if self._loaded:
            return
        self._ofac_entries = self._load_ofac_sdn()
        self._eu_entries = self._load_eu_list()
        self._uk_entries = self._load_uk_list()
        self._loaded = True

    def _load_ofac_sdn(self) -> list[dict]:
        """Parse OFAC SDN Advanced XML file (current format)."""
        entries = []
        path = settings.ofac_sdn_path
        if not os.path.exists(path):
            return entries
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            # Detect namespace from root tag
            if "}" in root.tag:
                NS = root.tag.split("}")[0].strip("{")
            else:
                NS = ""

            def tag(name: str) -> str:
                return f"{{{NS}}}{name}" if NS else name

            seen: set = set()
            for profile in root.iter(tag("Profile")):
                # Collect all documented names across identities and aliases
                for doc_name in profile.iter(tag("DocumentedName")):
                    parts: list[str] = []
                    for np in doc_name.iter(tag("NamePartValue")):
                        if np.text and np.text.strip():
                            parts.append(np.text.strip())
                    full_name = " ".join(parts).strip()
                    if full_name and full_name not in seen:
                        seen.add(full_name)
                        entries.append({
                            "name": full_name,
                            "program": "OFAC SDN",
                            "list": "OFAC SDN",
                        })
        except Exception:
            pass
        return entries

    def _load_eu_list(self) -> list[dict]:
        """Parse EU Consolidated Sanctions XML."""
        entries = []
        path = settings.eu_sanctions_path
        if not os.path.exists(path):
            return entries
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            for entity in root.iter():
                tag = entity.tag.split("}")[-1] if "}" in entity.tag else entity.tag
                if tag == "nameAlias":
                    name = entity.get("wholeName", "")
                    if name:
                        entries.append({
                            "name": name,
                            "program": entity.get("regulation", "EU Regulation"),
                            "list": "EU Consolidated",
                        })
        except Exception:
            pass
        return entries

    def _load_uk_list(self) -> list[dict]:
        """Parse UK Sanctions CSV."""
        entries = []
        path = settings.uk_sanctions_path
        if not os.path.exists(path):
            return entries
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("Name 6", "") or row.get("name", "") or ""
                    if name:
                        entries.append({
                            "name": name,
                            "program": row.get("Regime", "UK Sanctions"),
                            "list": "UK Sanctions",
                        })
        except Exception:
            pass
        return entries

    async def check_entity(self, entity_name: str, threshold: int = 85) -> list[SanctionHit]:
        """Check an entity name against all sanctions lists using fuzzy matching."""
        await self.load_lists()
        hits = []

        all_entries = self._ofac_entries + self._eu_entries + self._uk_entries

        for entry in all_entries:
            score = fuzz.token_sort_ratio(entity_name.upper(), entry["name"].upper())
            if score >= threshold:
                hits.append(SanctionHit(
                    entity_name=entity_name,
                    list_name=entry["list"],
                    program=entry["program"],
                    match_score=float(score),
                    matched_name=entry["name"],
                ))

        return hits

    async def check_vessel_imo(self, imo: str) -> list[SanctionHit]:
        """Check if a vessel IMO appears on any sanctions list."""
        await self.load_lists()
        hits = []
        # OFAC sometimes lists vessels by IMO in remarks
        # This would require parsing additional fields
        return hits

    async def screen_full(self, imo: str, entities: list[str]) -> SanctionRiskSummary:
        """Run full sanctions screening for a vessel and its entities."""
        summary = SanctionRiskSummary()

        # Check vessel IMO
        vessel_hits = await self.check_vessel_imo(imo)
        if vessel_hits:
            summary.vessel_sanctioned = True
            summary.hits.extend(vessel_hits)

        # Check each entity
        for entity_name in entities:
            entity_hits = await self.check_entity(entity_name)
            if entity_hits:
                summary.ownership_sanctioned = True
                summary.hits.extend(entity_hits)

        # Update summary text
        if summary.vessel_sanctioned:
            summary.summary_text = "SANCTIONED VESSEL - Listed on sanctions program"
        elif summary.ownership_sanctioned:
            summary.summary_text = "REVIEW REQUIRED - Ownership entity matched sanctions list"
        else:
            summary.summary_text = "The vessel has not been listed as sanctioned"

        return summary
