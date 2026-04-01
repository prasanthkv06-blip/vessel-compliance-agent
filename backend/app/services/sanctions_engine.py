"""Multi-list sanctions screening engine.

Sources:
  1. OFAC SDN XML  — US Treasury (direct download, vessel IMO matching)
  2. OpenSanctions — free search API, aggregates 200+ lists (EU, UK, UN, etc.)

No API key required for OpenSanctions search endpoint.
"""
import re
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Optional

import httpx

from ..models.report import SanctionsMultiListResult

logger = logging.getLogger(__name__)

OPENSANCTIONS_SEARCH = "https://api.opensanctions.org/search/default"
OFAC_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"

# Map OpenSanctions dataset IDs → friendly list names
_DATASET_MAP = {
    "us_ofac_sdn": "OFAC SDN",
    "us_ofac_cons": "OFAC Consolidated",
    "eu_fsf": "EU Financial Sanctions",
    "gb_hmt_sanctions": "UK HM Treasury",
    "un_sc_sanctions": "UN Security Council",
    "us_bis_denied": "BIS Denied Persons",
}

# In-process cache
_OFAC_IMO_INDEX: dict[str, dict] = {}       # imo  -> {name, programs}
_OFAC_NAME_INDEX: dict[str, dict] = {}      # NAME -> {imo, programs}
_OFAC_CACHE_TIME: Optional[datetime] = None
_OFAC_CACHE_TTL = timedelta(hours=24)


def _fuzzy(a: str, b: str) -> float:
    return SequenceMatcher(None, a.upper(), b.upper()).ratio()


async def _ensure_ofac_cache() -> bool:
    """Download OFAC SDN XML and build IMO + name indexes. Returns True on success."""
    global _OFAC_IMO_INDEX, _OFAC_NAME_INDEX, _OFAC_CACHE_TIME

    now = datetime.utcnow()
    if _OFAC_CACHE_TIME and (now - _OFAC_CACHE_TIME) < _OFAC_CACHE_TTL:
        return True

    try:
        async with httpx.AsyncClient(timeout=90, follow_redirects=True) as client:
            resp = await client.get(OFAC_SDN_URL)
        if resp.status_code != 200:
            logger.warning("OFAC SDN fetch returned HTTP %s", resp.status_code)
            return False

        root = ET.fromstring(resp.content)

        # Detect namespace (format: {https://tempuri.org/sdnList.xsd}sdnList)
        tag = root.tag
        ns_prefix = ""
        ns_map: dict = {}
        if "{" in tag:
            ns_uri = tag.split("}")[0][1:]
            ns_map = {"ns": ns_uri}
            ns_prefix = "ns:"

        def find_text(el, local_tag):
            child = el.find(f"{ns_prefix}{local_tag}", ns_map)
            return child.text.strip() if child is not None and child.text else ""

        def find_all(el, local_tag):
            return el.findall(f".//{ns_prefix}{local_tag}", ns_map)

        imo_idx: dict[str, dict] = {}
        name_idx: dict[str, dict] = {}

        for entry in find_all(root, "sdnEntry"):
            sdn_type = find_text(entry, "sdnType")
            if sdn_type not in ("Vessel", "Entity", "Individual"):
                continue

            name = find_text(entry, "lastName").upper()
            programs = [p.text.strip() for p in find_all(entry, "program") if p.text]
            uid = find_text(entry, "uid")

            imo = None
            for prop in find_all(entry, "prop"):
                prop_type = find_text(prop, "propType")
                prop_val = find_text(prop, "propValue")
                if "IMO" in prop_type.upper():
                    m = re.search(r"\d{7}", prop_val)
                    if m:
                        imo = m.group()

            rec = {"name": name, "programs": programs, "uid": uid, "imo": imo}
            if imo:
                imo_idx[imo] = rec
            if name:
                name_idx[name] = rec

        _OFAC_IMO_INDEX = imo_idx
        _OFAC_NAME_INDEX = name_idx
        _OFAC_CACHE_TIME = now
        logger.info("OFAC SDN loaded: %d vessels/entities by IMO, %d by name",
                    len(imo_idx), len(name_idx))
        return True

    except Exception as exc:
        logger.warning("OFAC SDN load error: %s", exc)
        return False


def _ofac_check(imo: str, vessel_name: str, entity_names: list[str]) -> list[dict]:
    """Synchronous check against in-memory OFAC cache."""
    hits: list[dict] = []

    # Direct IMO match
    if imo in _OFAC_IMO_INDEX:
        rec = _OFAC_IMO_INDEX[imo]
        hits.append({
            "entity": vessel_name,
            "matched_name": rec["name"],
            "list": "OFAC SDN",
            "program": ", ".join(rec["programs"]),
            "score": 100,
        })

    # Name matches for vessel + entities
    all_names = [vessel_name] + entity_names
    for query_name in all_names:
        qn = query_name.upper()
        # Exact
        if qn in _OFAC_NAME_INDEX:
            rec = _OFAC_NAME_INDEX[qn]
            if not any(h["matched_name"] == rec["name"] and h["entity"] == query_name for h in hits):
                hits.append({
                    "entity": query_name,
                    "matched_name": rec["name"],
                    "list": "OFAC SDN",
                    "program": ", ".join(rec["programs"]),
                    "score": 98,
                })
        else:
            # Fuzzy scan (only for names > 5 chars)
            if len(qn) > 5:
                for sdn_name, rec in _OFAC_NAME_INDEX.items():
                    ratio = _fuzzy(qn, sdn_name)
                    if ratio >= 0.88:
                        if not any(h["matched_name"] == rec["name"] and h["entity"] == query_name for h in hits):
                            hits.append({
                                "entity": query_name,
                                "matched_name": rec["name"],
                                "list": "OFAC SDN",
                                "program": ", ".join(rec["programs"]),
                                "score": int(ratio * 100),
                            })
                        break  # one best hit per entity

    return hits


async def _opensanctions_check(terms: list[str]) -> list[dict]:
    """Query OpenSanctions search API for each term. Returns hit list."""
    hits: list[dict] = []

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        for term in terms[:8]:           # cap at 8 to avoid rate limiting
            if not term or len(term) < 4:
                continue
            try:
                resp = await client.get(
                    OPENSANCTIONS_SEARCH,
                    params={"q": term, "limit": 5},
                    headers={"Accept": "application/json"},
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for result in data.get("results", []):
                    score = result.get("score", 0)
                    if score < 0.72:
                        continue
                    datasets = result.get("datasets", [])
                    caption = result.get("caption", "")
                    for ds in datasets:
                        list_name = _DATASET_MAP.get(ds, ds.replace("_", " ").title())
                        key = (term, list_name)
                        if not any(h["entity"] == term and h["list"] == list_name for h in hits):
                            hits.append({
                                "entity": term,
                                "matched_name": caption,
                                "list": list_name,
                                "program": ", ".join(
                                    result.get("properties", {}).get("program", [])
                                ),
                                "score": int(score * 100),
                            })
            except Exception as exc:
                logger.debug("OpenSanctions error for '%s': %s", term, exc)

    return hits


async def screen_multilists(
    imo: str,
    vessel_name: str,
    entity_names: list[str],
) -> SanctionsMultiListResult:
    """
    Screen vessel and associated entities against multiple sanctions lists.
    Returns a SanctionsMultiListResult.
    """
    all_terms = [vessel_name] + entity_names

    # 1 – OFAC (download XML, cache 24h)
    await _ensure_ofac_cache()
    ofac_hits = _ofac_check(imo, vessel_name, entity_names)

    # 2 – OpenSanctions (EU, UK, UN, others)
    os_hits = await _opensanctions_check(all_terms)

    all_hits = ofac_hits + [h for h in os_hits
                            if not any(oh["entity"] == h["entity"]
                                       and oh["list"] == h["list"] for oh in ofac_hits)]

    hit_lists = {h["list"] for h in all_hits}

    return SanctionsMultiListResult(
        ofac_hit=any("OFAC" in l for l in hit_lists),
        eu_hit=any("EU" in l for l in hit_lists),
        uk_hit=any("UK" in l or "HM Treasury" in l for l in hit_lists),
        un_hit=any("UN" in l for l in hit_lists),
        other_list_hit=bool(all_hits) and not any(
            "OFAC" in l or "EU" in l or "UK" in l or "UN" in l for l in hit_lists
        ),
        total_hits=len(all_hits),
        screened_entities=all_terms,
        hit_details=all_hits,
    )
