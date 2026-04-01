"""Equasis vessel data scraper — equasis.org

Fetches vessel particulars and ownership/management data.
Requires EQUASIS_USERNAME and EQUASIS_PASSWORD in .env.
"""
import re
import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

EQUASIS_BASE = "https://www.equasis.org/EquasisWeb"

# Role mapping: Equasis function labels → internal role keys
_ROLE_MAP = {
    "registered owner": "registered_owner",
    "owner": "registered_owner",
    "ship manager": "technical_manager",
    "ship manager/commercial manager": "commercial_manager",
    "commercial manager": "commercial_manager",
    "technical manager": "technical_manager",
    "ism manager": "ism_manager",
    "ism company": "ism_manager",
    "operator": "operator",
    "bareboat charterer": "operator",
    "doc company": "ism_manager",
}


def _normalize_role(raw: str) -> str:
    low = raw.strip().lower()
    if low in _ROLE_MAP:
        return _ROLE_MAP[low]
    for key, val in _ROLE_MAP.items():
        if key in low:
            return val
    return "registered_owner"


def _parse_int(s: str) -> int:
    try:
        return int(re.sub(r"[^\d]", "", s.split(".")[0]))
    except Exception:
        return 0


def _parse_equasis_date(s: str) -> Optional[str]:
    """Convert Equasis date strings to ISO YYYY-MM-DD.
    Handles: 27/11/2024, since 27/11/2024, during 10/2020, 01/04/2016.
    """
    s = re.sub(r"(since|during)\s*", "", s.strip(), flags=re.I)
    s = s.strip()
    if not s or s in ("-", "—", "N/A", "Not Known"):
        return None
    # DD/MM/YYYY
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    # MM/YYYY → use 1st of month
    m = re.match(r"(\d{1,2})/(\d{4})", s)
    if m:
        return f"{m.group(2)}-{int(m.group(1)):02d}-01"
    # YYYY-MM-DD
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return s
    return None


class EquasisService:
    """Scrapes vessel data from Equasis (equasis.org)."""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self._cookies: dict = {}
        self._logged_in = False

    async def _login(self) -> bool:
        """Authenticate with Equasis and cache session cookies."""
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            try:
                resp = await client.post(
                    f"{EQUASIS_BASE}/authen/HomePage",
                    params={"fs": "HomePage"},
                    data={
                        "j_email": self.username,
                        "j_password": self.password,
                        "submit": "Login",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if resp.status_code == 200:
                    page_text = resp.text.lower()
                    if "login failed" in page_text or "incorrect" in page_text or "invalid" in page_text:
                        logger.warning("Equasis login failed — check credentials")
                        return False
                    if "logout" in page_text or "restricted" in page_text:
                        self._cookies = dict(resp.cookies)
                        self._logged_in = True
                        logger.info("Equasis login successful")
                        return True
                    logger.warning("Equasis: unexpected login response")
            except Exception as e:
                logger.warning("Equasis login error: %s", e)
        return False

    async def lookup_vessel(self, imo: str) -> Optional[dict]:
        """
        Fetch vessel particulars + full ownership chain from Equasis.

        Returns:
          vessel: {name, vessel_type, flag, mmsi, dwt, grt, build_year, class_society}
          ownership: list of {entity_name, role, country, address, from_date, to_date, is_historical}
          source: "equasis"
        """
        if not self._logged_in:
            if not await self._login():
                return None

        async with httpx.AsyncClient(
            cookies=self._cookies, follow_redirects=True, timeout=30
        ) as client:
            try:
                # Fetch current vessel info
                resp_info = await client.get(
                    f"{EQUASIS_BASE}/restricted/ShipInfo",
                    params={"P_IMO": imo},
                )
                # Fetch history (names, flags, companies)
                resp_hist = await client.get(
                    f"{EQUASIS_BASE}/restricted/ShipHistory",
                    params={"P_IMO": imo},
                )
            except Exception as e:
                logger.warning("Equasis fetch error for IMO %s: %s", imo, e)
                return None

        if resp_info.status_code != 200:
            logger.warning("Equasis ShipInfo returned %s for IMO %s", resp_info.status_code, imo)
            return None

        vessel = self._parse_vessel_info(resp_info.text, imo)
        if not vessel:
            return None

        current_ownership = self._parse_current_companies(resp_info.text)
        historical_ownership = []
        name_flag_history: dict = {"name_history": [], "flag_history": []}
        if resp_hist.status_code == 200:
            historical_ownership = self._parse_history_companies(resp_hist.text)
            name_flag_history = self._parse_name_flag_history(resp_hist.text)

        # Merge: remove from history any companies already in current
        current_names = {o["entity_name"] for o in current_ownership}
        historical_ownership = [
            o for o in historical_ownership
            if o["entity_name"] not in current_names
        ]

        return {
            "vessel": vessel,
            "ownership": current_ownership + historical_ownership,
            "name_history": name_flag_history.get("name_history", []),
            "flag_history": name_flag_history.get("flag_history", []),
            "source": "equasis",
        }

    # ── Parsers ─────────────────────────────────────────────────────────────

    def _parse_vessel_info(self, html: str, imo: str) -> Optional[dict]:
        """Extract vessel particulars from ShipInfo page."""
        soup = BeautifulSoup(html, "lxml")

        # Vessel name — try h4 first (Equasis renders it there), then h3/h2, then info-details
        vessel_name = None
        info_div = soup.find("div", class_="info-details")

        for tag in ["h4", "h3", "h2"]:
            for el in soup.find_all(tag):
                # Normalise non-breaking spaces before matching
                text = el.get_text(strip=True).replace("\xa0", " ")
                m = re.match(r"^(.+?)\s*-+\s*IMO", text, re.I)
                if m:
                    vessel_name = m.group(1).strip().upper()
                    break
            if vessel_name:
                break

        if not vessel_name and info_div:
            # Fallback: parse from the info-details div plain text
            text = info_div.get_text(strip=True).replace("\xa0", " ")
            m = re.match(r"^(.+?)\s*-+\s*IMO", text, re.I)
            if m:
                vessel_name = m.group(1).strip().upper()

        if not vessel_name:
            logger.warning("Could not parse vessel name for IMO %s", imo)
            return None

        # Parse key-value pairs from info-details div
        vessel: dict = {"imo": imo, "name": vessel_name}
        if info_div:
            text = info_div.get_text(separator="|", strip=True)
            # Key patterns to extract
            patterns = {
                "flag":       r"Flag\s*\|?\s*\(([^)]+)\)",
                "mmsi":       r"MMSI\s*\|\s*(\d+)",
                "grt":        r"Gross tonnage\s*\|\s*([\d,]+)",
                "dwt":        r"DWT\s*\|\s*([\d,]+)",
                "vessel_type":r"Type of ship\s*\|\s*([^|(]+?)(?:\s*\(since|\|)",
                "build_year": r"Year of build\s*\|\s*(\d{4})",
                "call_sign":  r"Call Sign\s*\|\s*([A-Z0-9]+)",
            }
            for key, pat in patterns.items():
                m = re.search(pat, text, re.I)
                if m:
                    val = m.group(1).strip().rstrip("|").strip()
                    if key in ("grt", "dwt"):
                        vessel[key] = _parse_int(val)
                    elif key == "flag":
                        vessel[key] = val.upper()
                    else:
                        vessel[key] = val

        # Classification society from Table 1
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if not rows:
                continue
            headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
            if "classification society" in headers and len(rows) > 1:
                cells = rows[1].find_all(["td", "th"])
                if cells:
                    vessel["class_society"] = cells[0].get_text(strip=True)
                break

        return vessel

    def _parse_current_companies(self, html: str) -> list:
        """Extract current ownership/management from ShipInfo table."""
        soup = BeautifulSoup(html, "lxml")
        ownership = []

        tables = soup.find_all("table")
        if not tables:
            return ownership

        # Company table is Table 0 with headers: IMO number, Role, Name of company, Address, Date of effect
        table = tables[0]
        rows = table.find_all("tr")
        if len(rows) < 2:
            return ownership

        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
        name_col = next((i for i, h in enumerate(headers) if "name" in h), 2)
        role_col = next((i for i, h in enumerate(headers) if "role" in h or "function" in h), 1)
        addr_col = next((i for i, h in enumerate(headers) if "address" in h), 3)
        date_col = next((i for i, h in enumerate(headers) if "date" in h), 4)

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue

            def cell(i):
                return cells[i].get_text(strip=True) if i < len(cells) else ""

            entity_name = cell(name_col).upper()
            if not entity_name:
                continue

            raw_role = cell(role_col)
            role = _normalize_role(raw_role)
            address = cell(addr_col)
            # Country = last part of address (after last comma)
            country = address.split(".")[-1].split(",")[-1].strip().upper() if address else ""

            date_str = cell(date_col)  # e.g. "since 27/11/2024"
            from_date = _parse_equasis_date(date_str) or ""

            ownership.append({
                "entity_name": entity_name,
                "role": role,
                "country": country,
                "address": address.rstrip("."),
                "from_date": from_date,
                "to_date": "",
                "is_historical": False,
            })

        return ownership

    def _parse_history_companies(self, html: str) -> list:
        """Extract historical ownership from ShipHistory company table."""
        soup = BeautifulSoup(html, "lxml")
        ownership = []

        tables = soup.find_all("table")
        # Company history table has headers: Company, Role, Date of effect, Source(s)
        for table in tables:
            rows = table.find_all("tr")
            if not rows:
                continue
            headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
            if "company" in headers[0] and "role" in headers[1]:
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 3:
                        continue

                    entity_name = cells[0].get_text(strip=True).upper()
                    if not entity_name or entity_name in ("UNKNOWN", ""):
                        continue

                    raw_role = cells[1].get_text(strip=True)
                    role = _normalize_role(raw_role)
                    date_str = cells[2].get_text(strip=True)

                    from_date = _parse_equasis_date(date_str) or ""

                    ownership.append({
                        "entity_name": entity_name,
                        "role": role,
                        "country": "",
                        "address": "",
                        "from_date": from_date,
                        "to_date": "",
                        "is_historical": True,
                    })
                break

        return ownership

    # ── Name / Flag history ──────────────────────────────────────────────────

    def _parse_name_flag_history(self, html: str) -> dict:
        """Extract name history and flag history from ShipHistory page."""
        soup = BeautifulSoup(html, "lxml")
        name_history: list[dict] = []
        flag_history: list[dict] = []

        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if not rows:
                continue
            headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
            header_str = " ".join(headers)

            # Name history table
            if "name" in headers[0] and len(headers) >= 2 and "date" in header_str:
                if "flag" not in header_str and "company" not in header_str:
                    for row in rows[1:]:
                        cells = row.find_all(["td", "th"])
                        if len(cells) < 2:
                            continue
                        vessel_name = cells[0].get_text(strip=True).upper()
                        date_str = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        if vessel_name:
                            name_history.append({
                                "name": vessel_name,
                                "date": _parse_equasis_date(date_str) or date_str,
                            })

            # Flag history table
            elif "flag" in headers[0] and len(headers) >= 2:
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 1:
                        continue
                    flag_val = cells[0].get_text(strip=True).upper()
                    date_str = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    if flag_val:
                        flag_history.append({
                            "flag": flag_val,
                            "date": _parse_equasis_date(date_str) or date_str,
                        })

        return {"name_history": name_history, "flag_history": flag_history}

    # ── PSC Inspections ──────────────────────────────────────────────────────

    async def fetch_inspections(self, imo: str) -> list[dict]:
        """Fetch PSC inspection history from Equasis ShipInspection page."""
        if not self._logged_in:
            if not await self._login():
                return []
        async with httpx.AsyncClient(
            cookies=self._cookies, follow_redirects=True, timeout=30
        ) as client:
            try:
                resp = await client.get(
                    f"{EQUASIS_BASE}/restricted/ShipInspection",
                    params={"P_IMO": imo},
                )
            except Exception as exc:
                logger.warning("Equasis ShipInspection error IMO %s: %s", imo, exc)
                return []
        if resp.status_code != 200:
            return []
        return self._parse_inspections(resp.text)

    def _parse_inspections(self, html: str) -> list[dict]:
        """Parse PSC inspection table."""
        soup = BeautifulSoup(html, "lxml")
        inspections: list[dict] = []

        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if not rows:
                continue
            headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
            if not any("deficien" in h or "detained" in h or "inspection" in h for h in headers):
                continue

            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) < 3:
                    continue
                row_data = [c.get_text(strip=True) for c in cells]

                def gcol(keyword):
                    for i, h in enumerate(headers):
                        if keyword in h and i < len(row_data):
                            return row_data[i]
                    return ""

                date_str   = gcol("date") or (row_data[0] if row_data else "")
                port       = gcol("port") or (row_data[1] if len(row_data) > 1 else "")
                country    = gcol("country") or gcol("state") or ""
                authority  = gcol("mou") or gcol("authority") or gcol("regime") or gcol("admin") or ""
                defic_str  = gcol("deficien") or gcol("no.") or ""
                detained_s = gcol("detain") or gcol("result") or ""

                inspections.append({
                    "date":               _parse_equasis_date(date_str) or date_str,
                    "port":               port,
                    "country":            country,
                    "authority":          authority,
                    "total_deficiencies": _parse_int(defic_str) if defic_str else 0,
                    "detained":           any(
                        w in detained_s.upper() for w in ["YES", "DETAINED", "DET"]
                    ),
                })
            break   # take first matching table

        return inspections

    # ── Certificates ─────────────────────────────────────────────────────────

    async def fetch_certificates(self, imo: str) -> list[dict]:
        """Fetch certificate data from Equasis ShipCertificate page."""
        if not self._logged_in:
            if not await self._login():
                return []
        async with httpx.AsyncClient(
            cookies=self._cookies, follow_redirects=True, timeout=30
        ) as client:
            try:
                resp = await client.get(
                    f"{EQUASIS_BASE}/restricted/ShipCertificate",
                    params={"P_IMO": imo},
                )
            except Exception as exc:
                logger.warning("Equasis ShipCertificate error IMO %s: %s", imo, exc)
                return []
        if resp.status_code != 200:
            return []
        return self._parse_certificates(resp.text)

    def _parse_certificates(self, html: str) -> list[dict]:
        """Parse certificate table."""
        soup = BeautifulSoup(html, "lxml")
        certificates: list[dict] = []

        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if not rows:
                continue
            headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
            if not any("certif" in h or "valid" in h or "expir" in h for h in headers):
                continue

            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                row_data = [c.get_text(strip=True) for c in cells]

                cert_name = row_data[0]
                if not cert_name:
                    continue

                issue_date = None
                expiry_date = None
                issuer = None
                for i, h in enumerate(headers):
                    if i >= len(row_data):
                        continue
                    val = row_data[i]
                    if "issue" in h or "from" in h or "issued" in h:
                        issue_date = _parse_equasis_date(val)
                    elif "expir" in h or "valid" in h or "until" in h or "to" == h.strip():
                        expiry_date = _parse_equasis_date(val)
                    elif "issu" in h and "by" in h:
                        issuer = val

                certificates.append({
                    "name": cert_name,
                    "issuer": issuer,
                    "issue_date": issue_date,
                    "expiry_date": expiry_date,
                })
            break

        return certificates

    # ── Casualties ───────────────────────────────────────────────────────────

    async def fetch_casualties(self, imo: str) -> list[dict]:
        """Fetch casualty history from Equasis ShipCasualty page."""
        if not self._logged_in:
            if not await self._login():
                return []
        async with httpx.AsyncClient(
            cookies=self._cookies, follow_redirects=True, timeout=30
        ) as client:
            try:
                resp = await client.get(
                    f"{EQUASIS_BASE}/restricted/ShipCasualty",
                    params={"P_IMO": imo},
                )
            except Exception as exc:
                logger.warning("Equasis ShipCasualty error IMO %s: %s", imo, exc)
                return []
        if resp.status_code != 200:
            return []
        return self._parse_casualties(resp.text)

    def _parse_casualties(self, html: str) -> list[dict]:
        """Parse casualty table."""
        soup = BeautifulSoup(html, "lxml")
        casualties: list[dict] = []

        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if not rows:
                continue
            headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
            if not any("casualty" in h or "accident" in h or "incident" in h or "type" in h
                       for h in headers):
                continue

            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                row_data = [c.get_text(strip=True) for c in cells]

                def gcol(kw):
                    for i, h in enumerate(headers):
                        if kw in h and i < len(row_data):
                            return row_data[i]
                    return ""

                casualties.append({
                    "date":         _parse_equasis_date(gcol("date")) or gcol("date"),
                    "type":         gcol("type") or gcol("casualty") or (row_data[0] if row_data else ""),
                    "location":     gcol("locat") or gcol("place") or gcol("area") or "",
                    "description":  gcol("descr") or gcol("detail") or "",
                })
            break

        return casualties
